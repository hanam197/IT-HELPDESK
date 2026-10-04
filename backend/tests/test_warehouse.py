from datetime import datetime, timedelta, timezone
import io
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app


def receive(client,meta,serial):
    response=client.post('/api/assets/register',json={'warehouse_id':meta['warehouses'][0]['id'],'type_id':next(r['id'] for r in meta['asset-types'] if r['name']=='Laptop'),'model':'Warehouse laptop','serial':serial})
    assert response.status_code==201,response.text
    return response.json()


def test_asset_receipt_issue_and_return(client,meta):
    warehouse=meta['warehouses'][0]; station=next(r for r in meta['locations'] if r['name']=='DG-01BD')
    asset=receive(client,meta,'STOCK-ASSET-1')
    assert asset['warehouse_id']==warehouse['id']
    assert asset['location_id']==warehouse['location_id']
    assert asset['current_status']=='AVAILABLE'
    assert client.patch(f"/api/assets/{asset['id']}",json={'warehouse_id':None}).status_code==422
    assert client.post(f"/api/assets/{asset['id']}/assign",json={'user_id':4,'condition_out':'Good'}).status_code==422
    assert client.post(f"/api/assets/{asset['id']}/move",json={'location_id':station['id'],'reason':'Bypass warehouse'}).status_code==422
    issue={'transaction_type':'ISSUE','warehouse_id':warehouse['id'],'asset_id':asset['id']}
    assert client.post('/api/inventory/transactions',json=issue).status_code==422
    assert client.post('/api/inventory/transactions',json={**issue,'recipient_location_id':station['parent_id']}).status_code==422
    assert client.post('/api/inventory/transactions',json={**issue,'recipient_location_id':warehouse['location_id']}).status_code==422
    assert client.post('/api/inventory/transactions',json={**issue,'warehouse_id':meta['warehouses'][1]['id'],'recipient_user_id':4}).status_code==422
    when=datetime.now(timezone.utc).isoformat()
    issued=client.post('/api/inventory/transactions',json={**issue,'recipient_user_id':4,'recipient_location_id':station['id'],'transaction_date':when})
    assert issued.status_code==201,issued.text
    assert issued.json()['transaction_date']==when
    assert client.post('/api/inventory/transactions',json={**issue,'recipient_user_id':4}).status_code==422
    detail=client.get(f"/api/assets/{asset['id']}/detail").json()
    assert detail['warehouse_id'] is None and detail['location_id']==station['id']
    assert detail['assignment_user_id']==4 and detail['handover_date']==when[:10]
    returned=client.post('/api/inventory/transactions',json={'transaction_type':'RECEIVE','return_status':'AVAILABLE','warehouse_id':warehouse['id'],'asset_id':asset['id'],'condition':'Good on return'})
    assert returned.status_code==201,returned.text
    detail=client.get(f"/api/assets/{asset['id']}/detail").json()
    assert detail['warehouse_id']==warehouse['id'] and detail['assignment_id'] is None
    assert detail['current_status']=='AVAILABLE'
    assert detail['assignments'][0]['condition_in']=='Good on return'
    history=client.get('/api/inventory-transactions',params={'filters':'{"asset_id":'+str(asset['id'])+'}'}).json()
    assert [r['transaction_type'] for r in history['items']]==['RECEIVE','ISSUE','RECEIVE']


def test_user_only_issue_preserves_last_known_location(client,meta):
    asset=receive(client,meta,'STOCK-USER-ONLY')
    result=client.post('/api/inventory/transactions',json={'transaction_type':'ISSUE','warehouse_id':asset['warehouse_id'],'asset_id':asset['id'],'recipient_user_id':4})
    assert result.status_code==201,result.text
    current=client.get(f"/api/assets/{asset['id']}").json()
    assert current['warehouse_id'] is None and current['location_id']==asset['location_id']
    assert current['assignment_user_id']==4


def test_consumables_balance_recipients_and_atomic_failures(client,meta):
    warehouse=meta['warehouses'][0]
    payload={'transaction_type':'RECEIVE','warehouse_id':warehouse['id'],'new_item':{'code':'CONS-001','name':'Printer ribbon','category':'Consumable','unit':'roll'},'quantity':10}
    response=client.post('/api/inventory/transactions',json=payload)
    assert response.status_code==201,response.text
    item=response.json()['item_id']
    assert client.patch(f'/api/inventory-items/{item}',json={'quantity':500}).status_code==422
    assert client.patch(f'/api/inventory-items/{item}',json={'warehouse_id':meta['warehouses'][1]['id']}).status_code==422
    issue={'transaction_type':'ISSUE','warehouse_id':warehouse['id'],'item_id':item,'quantity':3}
    assert client.post('/api/inventory/transactions',json=issue).status_code==422
    assert client.post('/api/inventory/transactions',json={**issue,'recipient_user_id':4,'quantity':11}).status_code==422
    assert client.post('/api/inventory/transactions',json={**issue,'recipient_user_id':4,'quantity':'NaN'}).status_code==422
    assert client.get(f'/api/inventory-items/{item}').json()['quantity']==10
    station=next(r for r in meta['locations'] if r['name']=='DG-12AD')
    result=client.post('/api/inventory/transactions',json={**issue,'recipient_location_id':station['id']})
    assert result.status_code==201,result.text
    assert client.get(f'/api/inventory-items/{item}').json()['quantity']==7
    detail=client.get(f"/api/locations/{station['id']}/detail").json()
    assert any(r['id']==result.json()['id'] for r in detail['stock_movements'])
    assert client.post('/api/inventory/transactions',json={**payload,'new_item':{**payload['new_item'],'code':'CONS-ROLLBACK'},'recipient_user_id':4}).status_code==422
    assert client.get('/api/inventory-items?q=CONS-ROLLBACK').json()['total']==0


def test_station_metadata_photo_and_inactive_issue(client,meta):
    station=next(r for r in meta['locations'] if r['name']=='DG-18BD')
    response=client.patch(f"/api/locations/{station['id']}",json={'physical_location':'Building D, Floor 1','floor':'1st floor','area':'B','department':'Operations','active':False})
    assert response.status_code==200,response.text
    image=Image.new('RGB',(20,20),'blue'); buffer=io.BytesIO(); image.save(buffer,format='PNG')
    upload=client.post(f"/api/locations/{station['id']}/photo",files={'file':('station.png',buffer.getvalue(),'image/png')})
    assert upload.status_code==200,upload.text
    assert client.get(f"/api/locations/{station['id']}/photo").headers['content-type']=='image/png'
    assert client.post(f"/api/locations/{station['id']}/photo",files={'file':('bad.png',b'bad','image/png')}).status_code==422
    detail=client.get(f"/api/locations/{station['id']}/detail").json()
    assert detail['physical_location']=='Building D, Floor 1' and detail['active'] is False
    assert detail['network'] and detail['history'] and detail['site_name']=='Q7'
    assert detail['team_name']=='OUTBOUND' and detail['updated_by']
    asset=receive(client,meta,'INACTIVE-STATION')
    assert client.post('/api/inventory/transactions',json={'transaction_type':'ISSUE','warehouse_id':asset['warehouse_id'],'asset_id':asset['id'],'recipient_location_id':station['id']}).status_code==422
    assert client.patch(f"/api/locations/{station['id']}",json={'active':True}).status_code==200


def test_warehouse_permissions_and_dates(client,meta):
    asset=receive(client,meta,'STOCK-DATE')
    payload={'transaction_type':'ISSUE','warehouse_id':asset['warehouse_id'],'asset_id':asset['id'],'recipient_user_id':4}
    for when in [datetime.now(timezone.utc)-timedelta(days=1),datetime.now(timezone.utc)+timedelta(days=1)]:
        assert client.post('/api/inventory/transactions',json={**payload,'transaction_date':when.isoformat()}).status_code==422
    with TestClient(app,headers={'X-Requested-With':'Helpdesk'}) as viewer:
        assert viewer.post('/api/auth/login',json={'username':'viewer','password':'TestPassword2026!'}).status_code==200
        assert viewer.post('/api/inventory/transactions',json=payload).status_code==403
        assert viewer.post('/api/assets/register',json={}).status_code==403
        assert viewer.patch('/api/locations/1',json={'active':False}).status_code==403
    assert client.get(f"/api/assets/{asset['id']}").json()['warehouse_id']==asset['warehouse_id']


def test_inventory_custody_and_history_search(client,meta):
    asset=receive(client,meta,'CENTRAL-HISTORY-SEARCH')
    params={'view':'in-stock','q':asset['serial']}
    assert client.get('/api/assets',params=params).json()['total']==1
    for resource in ['asset-operations','inventory-transactions']:
        result=client.get('/api/'+resource,params={'q':asset['serial']})
        assert result.status_code==200,result.text
        assert result.json()['total']>=1
        assert all(row['asset_id']==asset['id'] for row in result.json()['items'])
    response=client.post('/api/inventory/transactions',json={'transaction_type':'ISSUE','warehouse_id':asset['warehouse_id'],'asset_id':asset['id'],'recipient_user_id':4})
    assert response.status_code==201,response.text
    assert client.get('/api/assets',params=params).json()['total']==0
    assert client.get('/api/assets',params={'q':asset['serial']}).json()['total']==1


def test_complete_asset_lifecycle_and_retirement(client,meta):
    asset=receive(client,meta,'LIFECYCLE-001'); id=asset['id']
    actor=client.get('/api/auth/me').json()['name']
    detail=client.get(f'/api/assets/{id}/detail').json()
    assert detail['received_by']==actor and detail['handed_over_by'] is None
    assert client.post('/api/inventory/transactions',json={'transaction_type':'ISSUE','warehouse_id':asset['warehouse_id'],'asset_id':id,'recipient_user_id':4}).status_code==201
    detail=client.get(f'/api/assets/{id}/detail').json()
    assert detail['handed_over_by']==actor
    assert detail['assigned_to']!=detail['handed_over_by']
    assert client.post(f'/api/assets/{id}/return',json={'warehouse_id':meta['warehouses'][0]['id'],'return_status':'AVAILABLE','condition_in':'Good, returned'}).status_code==200
    station=next(r for r in meta['locations'] if r['name']=='DG-01BD')
    assert client.post(f'/api/assets/{id}/move',json={'location_id':station['id'],'reason':'Service area'}).status_code==422
    mid=lambda group,code:next(r['id'] for r in meta['master-data'] if r['group']==group and r['code']==code)
    maintenance=client.post('/api/maintenance',json={'asset_id':id,'type_id':mid('maintenance_type','other'),'status_id':mid('maintenance_status','open'),'technician_id':1,'problem':'Lifecycle inspection'})
    assert maintenance.status_code==201,maintenance.text
    assert client.patch('/api/maintenance/'+str(maintenance.json()['id']),json={'status_id':mid('maintenance_status','completed'),'resolution_outcome':'FIXED','diagnosis':'Đã xác định nguyên nhân','action_taken':'Inspected and completed'}).status_code==200
    assert client.post(f'/api/assets/{id}/retire',json={'reason':'End of service'}).status_code==200
    detail=client.get(f'/api/assets/{id}/detail').json()
    assert detail['current_status']=='RETIRED' and detail['warehouse_id']==asset['warehouse_id'] and detail['location_id']==asset['location_id']
    events=detail['lifecycle']
    assert [e['event_type'] for e in events]==['RETIRED','MAINTENANCE','MAINTENANCE','RETURNED','ISSUED','RECEIVED']
    assert next(e for e in events if e['event_type']=='RETURNED')['performed_by']==actor
    assert next(e for e in events if e['event_type']=='RETIRED')['description']=='End of service'
    assert [e['occurred_at'] for e in events]==sorted([e['occurred_at'] for e in events],reverse=True)
    assert client.post(f'/api/assets/{id}/move',json={'location_id':station['id'],'reason':'Cannot move retired'}).status_code==422
    assert client.post(f'/api/assets/{id}/retire',json={'reason':'Duplicate retirement'}).status_code==422


def test_retiring_stock_keeps_warehouse_location_and_requires_permission(client,meta):
    asset=receive(client,meta,'RETIRE-STOCK')
    with TestClient(app,headers={'X-Requested-With':'Helpdesk'}) as viewer:
        assert viewer.post('/api/auth/login',json={'username':'viewer','password':'TestPassword2026!'}).status_code==200
        assert viewer.post(f"/api/assets/{asset['id']}/retire",json={'reason':'End of service'}).status_code==403
    assert client.post(f"/api/assets/{asset['id']}/retire",json={'reason':'End of service'}).status_code==200
    assert client.get('/api/assets',params={'view':'in-stock','q':asset['serial']}).json()['total']==1


def test_return_endpoint_requires_warehouse_and_records_stock(client,meta):
    asset=receive(client,meta,'UNIFIED-RETURN'); id=asset['id']
    warehouse=meta['warehouses'][1]
    assert client.post('/api/inventory/transactions',json={'transaction_type':'ISSUE','warehouse_id':asset['warehouse_id'],'asset_id':id,'recipient_user_id':4}).status_code==201
    for payload in [{'condition_in':'Good'}, {'warehouse_id':999999,'condition_in':'Good'}]:
        assert client.post(f'/api/assets/{id}/return',json=payload).status_code in {404,422}
        current=client.get(f'/api/assets/{id}/detail').json()
        assert current['warehouse_id'] is None and current['assignment_user_id']==4
        assert current['current_status']=='IN_USE'
    payload={'warehouse_id':warehouse['id'],'return_status':'AVAILABLE','condition_in':'Good','note':'Return to another warehouse'}
    assert client.post(f'/api/assets/{id}/return',json=payload).status_code==200
    assert client.post(f'/api/assets/{id}/return',json=payload).status_code==422
    current=client.get(f'/api/assets/{id}/detail').json()
    assert current['warehouse_id']==warehouse['id'] and current['location_id']==warehouse['location_id']
    assert current['assignment_id'] is None and current['current_status']=='AVAILABLE'
    assert current['assignments'][0]['condition_in']=='Good'
    assert len([e for e in current['lifecycle'] if e['event_type']=='RETURNED'])==1
    history=client.get('/api/inventory-transactions',params={'filters':'{"asset_id":'+str(id)+'}'}).json()['items']
    assert len(history)==3 and history[0]['warehouse_id']==warehouse['id']
    assert history[0]['transaction_type']=='RECEIVE'


def test_return_condition_required_and_repair_blocks_issue(client,meta):
    asset=receive(client,meta,'RETURN-NEEDS-REPAIR'); id=asset['id']; warehouse=asset['warehouse_id']
    issue={'transaction_type':'ISSUE','warehouse_id':warehouse,'asset_id':id,'recipient_user_id':4}
    assert client.post('/api/inventory/transactions',json=issue).status_code==201
    receipt={'transaction_type':'RECEIVE','warehouse_id':warehouse,'asset_id':id,'condition':'Màn hình hỏng'}
    for extra in [{},{'return_status':'UNKNOWN'},{'return_status':''},{'return_status':'REPAIR_NEEDED'},{'return_status':'BROKEN'},{'return_status':'DAMAGED'},{'return_status':'WAITING_REPAIR'}]:
        assert client.post('/api/inventory/transactions',json={**receipt,**extra}).status_code==422
        current=client.get(f'/api/assets/{id}/detail').json()
        assert current['current_status']=='IN_USE' and current['assignment_user_id']==4 and current['warehouse_id'] is None
    result=client.post(f'/api/assets/{id}/return',json={'warehouse_id':warehouse,'condition_in':'Màn hình hỏng','return_status':'MAINTENANCE'})
    assert result.status_code==200,result.text
    current=client.get(f'/api/assets/{id}/detail').json()
    assert current['current_status']=='MAINTENANCE' and current['warehouse_id']==warehouse
    assert current['assignment_id'] is None
    assert current['lifecycle'][0]['after_state']['current_status']=='MAINTENANCE'
    assert client.post('/api/inventory/transactions',json=issue).status_code==422
    mid=lambda group,code:next(r['id'] for r in meta['master-data'] if r['group']==group and r['code']==code)
    for outcome in ['completed']:
        repair=client.post('/api/maintenance',json={'asset_id':id,'problem':'Replace screen','technician_id':1,'type_id':mid('maintenance_type','hardware'),'status_id':mid('maintenance_status','open')})
        assert repair.status_code==201,repair.text
        assert client.patch('/api/maintenance/'+str(repair.json()['id']),json={'status_id':mid('maintenance_status',outcome),'resolution_outcome':'FIXED','diagnosis':'Đã xác định lỗi','action_taken':'Đã xử lý'}).status_code==200
        expected='AVAILABLE'
        assert client.get(f'/api/assets/{id}').json()['current_status']==expected
    assert client.post('/api/inventory/transactions',json=issue).status_code==201


def test_return_uses_allowed_shared_asset_statuses(client,meta):
    from app.asset_events import STATUS_CODES
    statuses=meta['asset-statuses']
    assert {s['id'] for s in statuses}==set(STATUS_CODES)
    for index,status in enumerate(statuses):
        if status['id'] in {'IN_USE','DISPOSED'}: continue
        asset=receive(client,meta,'SHARED-RETURN-'+str(index)); id=asset['id']
        issue={'transaction_type':'ISSUE','warehouse_id':asset['warehouse_id'],'asset_id':id,'recipient_user_id':4}
        assert client.post('/api/inventory/transactions',json=issue).status_code==201
        payload={'warehouse_id':asset['warehouse_id'],'return_status':status['id'],'condition_in':status['name']}
        if index%2:
            result=client.post(f'/api/assets/{id}/return',json=payload)
            assert result.status_code==200,result.text
        else:
            result=client.post('/api/inventory/transactions',json={'transaction_type':'RECEIVE','warehouse_id':asset['warehouse_id'],'asset_id':id,'return_status':status['id'],'condition':status['name']})
            assert result.status_code==201,result.text
        current=client.get(f'/api/assets/{id}/detail').json()
        assert current['current_status']==status['id']
        assert current['warehouse_id']==asset['warehouse_id'] and current['location_id']==meta['warehouses'][0]['location_id']
        assert current['assignment_id'] is None
        assert current['lifecycle'][0]['event_type']=='RETURNED'
        assert current['lifecycle'][0]['after_state']['current_status']==status['id']


def test_warehouse_generates_unique_codes_and_skips_existing_codes(client, meta):
    site = next(row for row in meta['locations'] if row['kind'] == 'site' and row['active'])
    payload = {'name': 'IT Store tự sinh', 'location_id': site['id']}
    first = client.post('/api/warehouses', json=payload)
    assert first.status_code == 201, first.text
    first_code = first.json()['code']
    assert first_code.startswith(f'WH-{datetime.now(timezone.utc).year}-')
    prefix, sequence = first_code.rsplit('-', 1)
    reserved_code = f'{prefix}-{int(sequence) + 1:05d}'
    reserved = client.post('/api/warehouses', json={**payload, 'code': reserved_code})
    assert reserved.status_code == 201, reserved.text
    assert client.delete(f"/api/warehouses/{reserved.json()['id']}").status_code == 200
    second = client.post('/api/warehouses', json=payload)
    assert second.status_code == 201, second.text
    assert second.json()['code'] == f'{prefix}-{int(sequence) + 2:05d}'
    edited = client.patch(f"/api/warehouses/{first.json()['id']}", json={'name': 'IT Store đổi tên'})
    assert edited.status_code == 200 and edited.json()['code'] == first_code


def test_new_warehouse_requires_an_active_site(client, meta):
    for kind in ('team', 'station'):
        location = next(row for row in meta['locations'] if row['kind'] == kind)
        response = client.post('/api/warehouses', json={'name': 'Kho sai cấp', 'location_id': location['id']})
        assert response.status_code == 422
        assert 'Cơ sở' in response.json()['detail']
    site = client.post('/api/locations', json={'kind': 'site', 'name': 'Cơ sở ngừng hoạt động', 'active': False})
    assert site.status_code == 201, site.text
    response = client.post('/api/warehouses', json={'name': 'Kho ngừng hoạt động', 'location_id': site.json()['id']})
    assert response.status_code == 422
    assert 'đang hoạt động' in response.json()['detail']
    assert client.get('/api/warehouses', params={'q': 'Kho sai cấp'}).json()['total'] == 0


def test_existing_warehouse_location_is_preserved(client, meta):
    warehouse = meta['warehouses'][0]
    response = client.patch(f"/api/warehouses/{warehouse['id']}", json={'description': 'Kho IT hiện có'})
    assert response.status_code == 200, response.text
    assert response.json()['code'] == warehouse['code']
    assert response.json()['location_id'] == warehouse['location_id']


def test_site_warehouse_supports_receipt_issue_and_return(client, meta):
    site = next(row for row in meta['locations'] if row['kind'] == 'site' and row['active'])
    created = client.post('/api/warehouses', json={'name': 'IT Store cấp cơ sở', 'location_id': site['id']})
    assert created.status_code == 201, created.text
    warehouse_id = created.json()['id']
    received = client.post('/api/assets/register', json={
        'warehouse_id': warehouse_id,
        'type_id': next(row['id'] for row in meta['asset-types'] if row['name'] == 'Laptop'),
        'model': 'Site warehouse laptop', 'serial': 'SITE-WAREHOUSE-ROUNDTRIP',
    })
    assert received.status_code == 201, received.text
    asset_id = received.json()['id']
    assert received.json()['location_id'] == site['id']
    station = next(row for row in meta['locations'] if row['kind'] == 'station' and row['active'])
    issued = client.post('/api/inventory/transactions', json={
        'transaction_type': 'ISSUE', 'warehouse_id': warehouse_id,
        'asset_id': asset_id, 'recipient_user_id': 4, 'recipient_location_id': station['id'],
    })
    assert issued.status_code == 201, issued.text
    returned = client.post('/api/inventory/transactions', json={
        'transaction_type': 'RECEIVE', 'warehouse_id': warehouse_id,
        'asset_id': asset_id, 'return_status': 'AVAILABLE',
    })
    assert returned.status_code == 201, returned.text
    current = client.get(f'/api/assets/{asset_id}/detail').json()
    assert current['warehouse_id'] == warehouse_id
    assert current['location_id'] == site['id']
    assert current['assignment_id'] is None
    assert current['current_status'] == 'AVAILABLE'
