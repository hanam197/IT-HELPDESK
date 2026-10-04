import json
from pathlib import Path
import pytest
from app.database import settings
from stock_helpers import TEMPLATE, INFO, post_stock

@pytest.fixture
def issue(client, meta):
    warehouse=meta['warehouses'][0]['id']
    created=client.post('/api/assets/register',json={'type_id':next(t['id'] for t in meta['asset-types'] if t['name']=='Laptop'),'warehouse_id':warehouse,'model':'Handover model','serial':'SIGNED-'+__import__('secrets').token_hex(4)})
    assert created.status_code==201,created.text
    return {'transaction_type':'ISSUE','warehouse_id':warehouse,'asset_id':created.json()['id'],'recipient_user_id':4,'condition':'Tốt'}

def send(client,issue,content=TEMPLATE,info=INFO):
    return client.post('/api/inventory/issue-with-handover',data={'payload':json.dumps(issue),'handover_info':json.dumps(info)},files={'file':('signed.pdf',content,'application/pdf')})

def test_document_required_on_server(client,issue):
    response=client.post('/api/inventory/transactions',json=issue)
    assert response.status_code==422
    assert 'biên bản' in response.json()['detail']
    asset=client.get(f"/api/assets/{issue['asset_id']}").json()
    assert asset['warehouse_id']==issue['warehouse_id'] and asset['current_status']=='AVAILABLE'
    assert client.post('/api/inventory/issue-with-handover',data={'payload':json.dumps(issue),'handover_info':json.dumps(INFO)}).status_code==422

def test_signed_document_saved_and_downloadable(client,issue):
    response=send(client,issue)
    assert response.status_code==201,response.text
    row=response.json()
    assert row['handover_filename']=='signed.pdf' and row['handover_size']==len(TEMPLATE)
    assert 'handover_storage_key' not in row
    snapshot=row['handover_snapshot']
    assert snapshot['serial'].startswith('SIGNED-') and snapshot['model']=='Handover model'
    assert snapshot['recipient_name']==client.get('/api/users/4').json()['name']
    download=client.get(row['handover_url'])
    assert download.status_code==200 and download.content==TEMPLATE
    assert download.headers['content-type']=='application/pdf'
    asset=client.get(f"/api/assets/{issue['asset_id']}").json()
    assert asset['warehouse_id'] is None and asset['current_status']=='IN_USE'
    assert client.get(f"/api/inventory-transactions/{row['id']}").json()['handover_url']==row['handover_url']

@pytest.mark.parametrize('content',[b'',b'not a document',b'%PDF-incomplete',b'x'*(10*1024*1024+1)])
def test_bad_document_keeps_stock_unchanged(client,issue,content):
    response=send(client,issue,content)
    assert response.status_code in (422,413),response.text
    assert client.get(f"/api/assets/{issue['asset_id']}").json()['warehouse_id']==issue['warehouse_id']

def test_failed_issue_cleans_uploaded_file(client,issue):
    directory=Path(settings.upload_dir)/'handovers'
    before=set(directory.iterdir()) if directory.exists() else set()
    response=send(client,{**issue,'asset_id':999999})
    assert response.status_code in (404,422)
    assert set(directory.iterdir())==before
    assert client.get(f"/api/assets/{issue['asset_id']}").json()['warehouse_id']==issue['warehouse_id']

def test_image_handover(client,issue):
    import io
    from PIL import Image
    image=io.BytesIO();Image.new('RGB',(50,50),'white').save(image,format='PNG')
    response=send(client,issue,image.getvalue())
    assert response.status_code==201,response.text
    assert response.json()['handover_content_type']=='image/png'

def test_station_only_issue_still_works(client,issue,meta):
    station=next(l for l in meta['locations'] if l['kind']=='station' and l['active'])
    payload={k:v for k,v in issue.items() if k!='recipient_user_id'}
    response=post_stock(client,{**payload,'recipient_location_id':station['id']})
    assert response.status_code==201,response.text
    assert response.json()['handover_url'] is None

def test_info_validation_and_no_client_snapshot_override(client,issue):
    for info in ({**INFO,'sender_name':'   '},{**INFO,'recipient_name':'Forged recipient'}):
        assert send(client,issue,info=info).status_code==422
    assert client.get(f"/api/assets/{issue['asset_id']}").json()['warehouse_id']==issue['warehouse_id']

def test_upload_failure_keeps_transaction_and_assignment_unchanged(client,issue,monkeypatch):
    def fail_write(self,content): raise OSError('Disk unavailable')
    monkeypatch.setattr(Path,'write_bytes',fail_write)
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app,raise_server_exceptions=False,headers={'X-Requested-With':'Helpdesk'}) as c:
        c.cookies.update(client.cookies)
        assert send(c,issue).status_code==500
    detail=client.get(f"/api/assets/{issue['asset_id']}/detail").json()
    assert detail['warehouse_id']==issue['warehouse_id'] and not detail['assignment_id']

def test_upload_and_download_permissions(client,issue):
    from fastapi.testclient import TestClient
    from app.main import app
    response=send(client,issue);assert response.status_code==201
    with TestClient(app,headers={'X-Requested-With':'Helpdesk'}) as guest:
        assert guest.get(response.json()['handover_url']).status_code==401
        assert send(guest,issue).status_code==401
        assert guest.post('/api/auth/login',json={'username':'support','password':'TestPassword2026!'}).status_code==200
        assert send(guest,issue).status_code==403

def test_consumable_issue_requires_document_before_decreasing_quantity(client,meta):
    receipt=client.post('/api/inventory/transactions',json={'transaction_type':'RECEIVE','warehouse_id':meta['warehouses'][0]['id'],'new_item':{'code':'SIGNED-CONS-'+__import__('secrets').token_hex(4),'name':'Vật tư bàn giao','category':'Vật tư','unit':'cái'},'quantity':10})
    assert receipt.status_code==201,receipt.text
    item_id=receipt.json()['item_id']
    payload={'transaction_type':'ISSUE','warehouse_id':meta['warehouses'][0]['id'],'item_id':item_id,'quantity':3,'recipient_user_id':4,'condition':'Mới'}
    assert client.post('/api/inventory/transactions',json=payload).status_code==422
    assert float(client.get(f'/api/inventory-items/{item_id}').json()['quantity'])==10
    assert send(client,{**payload,'quantity':11}).status_code==422
    assert float(client.get(f'/api/inventory-items/{item_id}').json()['quantity'])==10
    response=send(client,payload)
    assert response.status_code==201,response.text
    assert response.json()['handover_snapshot']['device_name']=='Vật tư bàn giao'
    assert float(client.get(f'/api/inventory-items/{item_id}').json()['quantity'])==7
