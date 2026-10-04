import json
import secrets
from pathlib import Path
from app.database import settings
from stock_helpers import post_stock, TEMPLATE, INFO

def asset(client,meta):
    response=client.post('/api/assets/register',json={'model':'Latitude 5530','serial':'RET-'+secrets.token_hex(4),'type_id':next(t['id'] for t in meta['asset-types'] if t['name']=='Laptop'),'warehouse_id':meta['warehouses'][0]['id']})
    assert response.status_code==201,response.text
    return response.json()

def test_generated_device_name_and_print_snapshot(client,meta):
    row=asset(client,meta)
    expected=f"Laptop - Latitude 5530 - {row['serial']}"
    assert row['name']==expected
    issued=post_stock(client,json={'transaction_type':'ISSUE','warehouse_id':row['warehouse_id'],'asset_id':row['id'],'recipient_user_id':4})
    assert issued.status_code==201,issued.text
    assert issued.json()['handover_snapshot']['device_name']==expected
    assert issued.json()['handover_snapshot']['document_kind']=='ISSUE'

def test_name_updates_when_model_changes_without_changing_saved_document(client,meta):
    row=asset(client,meta)
    issued=post_stock(client,json={'transaction_type':'ISSUE','warehouse_id':row['warehouse_id'],'asset_id':row['id'],'recipient_user_id':4}).json()
    changed=client.patch(f"/api/assets/{row['id']}",json={'model':'Latitude 5540'})
    assert changed.status_code==200,changed.text
    assert changed.json()['name']==f"Laptop - Latitude 5540 - {row['serial']}"
    assert client.get(f"/api/inventory-transactions/{issued['id']}").json()['handover_snapshot']['device_name']==row['name']

def test_return_requires_file_and_legacy_route_cannot_bypass(client,meta):
    row=asset(client,meta)
    assert post_stock(client,json={'transaction_type':'ISSUE','warehouse_id':row['warehouse_id'],'asset_id':row['id'],'recipient_user_id':4}).status_code==201
    payload={'transaction_type':'RECEIVE','warehouse_id':row['warehouse_id'],'asset_id':row['id'],'return_status':'AVAILABLE','condition':'Tốt','reason':'Thu hồi về kho'}
    assert client.post('/api/inventory/transactions',json=payload).status_code==422
    assert client.post(f"/api/assets/{row['id']}/return",json={'warehouse_id':row['warehouse_id'],'return_status':'AVAILABLE'}).status_code==422
    assert client.post('/api/inventory/movement-with-document',data={'payload':json.dumps(payload),'handover_info':json.dumps(INFO)}).status_code==422
    detail=client.get(f"/api/assets/{row['id']}/detail").json()
    assert detail['current_status']=='IN_USE' and detail['assignment_user_id']==4
    returned=post_stock(client,json=payload)
    assert returned.status_code==201,returned.text
    saved=returned.json()
    assert saved['handover_snapshot']['document_kind']=='RETURN'
    assert saved['handover_snapshot']['recipient_name']==client.get('/api/auth/me').json()['name']
    assert saved['handover_snapshot']['reason']=='Thu hồi về kho'
    assert saved['handover_snapshot']['device_name']==row['name']
    assert client.get(saved['handover_url']).content==TEMPLATE
    detail=client.get(f"/api/assets/{row['id']}/detail").json()
    assert detail['warehouse_id']==row['warehouse_id'] and detail['assignment_id'] is None

def test_return_and_maintenance_rollback_together(client,meta):
    row=asset(client,meta)
    assert post_stock(client,json={'transaction_type':'ISSUE','warehouse_id':row['warehouse_id'],'asset_id':row['id'],'recipient_user_id':4}).status_code==201
    payload={'transaction_type':'RECEIVE','warehouse_id':row['warehouse_id'],'asset_id':row['id'],'return_status':'MAINTENANCE','reason':'Thiết bị cần sửa','condition':'Cần sửa','maintenance':{'type_id':next(m['id'] for m in meta['master-data'] if m['group']=='maintenance_type' and m['code']=='hardware'),'technician_id':999999,'problem':'Lỗi phần cứng'}}
    directory=Path(settings.upload_dir)/'handovers';before=set(directory.iterdir())
    response=post_stock(client,json=payload)
    assert response.status_code in (404,422)
    assert set(directory.iterdir())==before
    detail=client.get(f"/api/assets/{row['id']}/detail").json()
    assert detail['warehouse_id'] is None and detail['assignment_user_id']==4
    payload['maintenance']['technician_id']=3
    response=post_stock(client,json=payload)
    assert response.status_code==201,response.text
    detail=client.get(f"/api/assets/{row['id']}/detail").json()
    assert detail['warehouse_id']==row['warehouse_id'] and detail['current_status']=='MAINTENANCE'
    assert any(r['end_at'] is None for r in detail['maintenance'])
