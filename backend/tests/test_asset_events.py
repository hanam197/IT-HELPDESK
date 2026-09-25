from fastapi.testclient import TestClient
from app.main import app
from test_warehouse import receive


def detail(client,id):
    r=client.get(f'/api/assets/{id}/detail'); assert r.status_code==200,r.text
    return r.json()

def command(client,id,path,payload):
    r=client.post(f'/api/assets/{id}/{path}',json=payload); assert r.status_code==200,r.text
    return r.json()

def test_one_event_per_operation_current_state_and_reassign(client,meta):
    asset=receive(client,meta,'CANONICAL-001'); id=asset['id']; d=detail(client,id)
    assert d['current_status']=='AVAILABLE' and [e['event_type'] for e in d['lifecycle']]==['RECEIVED']
    station=next(r for r in meta['locations'] if r['name']=='DG-01BD')
    issue=client.post('/api/inventory/transactions',json={'transaction_type':'ISSUE','warehouse_id':asset['warehouse_id'],'asset_id':id,'recipient_user_id':4,'recipient_location_id':station['id']})
    assert issue.status_code==201,issue.text
    d=detail(client,id)
    assert [e['event_type'] for e in d['lifecycle']]==['ISSUED','RECEIVED']
    event=d['lifecycle'][0]
    assert event['before_state']['current_status']=='AVAILABLE' and event['after_state']['current_status']=='IN_USE'
    assert d['current_status']=='IN_USE' and d['current_assignee']==4 and d['current_location']==station['id']
    next_station=next(r for r in meta['locations'] if r['name']=='DG-12AD')
    command(client,id,'move',{'location_id':next_station['id'],'reason':'Đổi vị trí làm việc'})
    d=detail(client,id); assert d['current_assignee']==4 and d['current_status']=='IN_USE'
    assert d['lifecycle'][0]['event_type']=='MOVED'
    command(client,id,'reassign',{'user_id':2,'reason':'Đổi người phụ trách'})
    d=detail(client,id); assert len(d['lifecycle'])==4
    assert d['current_location']==next_station['id'] and d['current_status']=='IN_USE' and d['current_assignee']==2
    e=d['lifecycle'][0]; assert e['event_type']=='REASSIGNED'
    assert e['before_state']['current_assignee']['id']==4 and e['after_state']['current_assignee']['id']==2
    assert len(d['assignments'])==2 and sum(a['returned_at'] is None for a in d['assignments'])==1
    assert client.post(f'/api/assets/{id}/reassign',json={'user_id':2,'reason':'Không đổi người'}).status_code==422
    assert client.post(f'/api/assets/{id}/reassign',json={'user_id':99999,'reason':'Người không tồn tại'}).status_code==404
    assert len(detail(client,id)['lifecycle'])==4
    command(client,id,'return',{'condition_in':'Tốt'})
    d=detail(client,id); assert d['current_status']=='AVAILABLE' and d['current_assignee'] is None
    assert d['lifecycle'][0]['event_type']=='RETURNED'
    command(client,id,'retire',{'reason':'Ngừng sử dụng thiết bị'})
    d=detail(client,id); assert d['current_status']=='RETIRED'
    assert [e['event_type'] for e in d['lifecycle']]==['RETIRED','RETURNED','REASSIGNED','MOVED','ISSUED','RECEIVED']
    for path,payload in [('assign',{'user_id':4,'condition_out':'Tốt'}),('move',{'location_id':station['id'],'reason':'Không được điều chuyển'}),('reassign',{'user_id':4,'reason':'Không được cấp lại'})]:
        assert client.post(f'/api/assets/{id}/{path}',json=payload).status_code==422
    assert len(detail(client,id)['lifecycle'])==6


def test_maintenance_restores_previous_state_and_records_only_business_events(client,meta):
    master=lambda group,code:next(r['id'] for r in meta['master-data'] if r['group']==group and r['code']==code)
    for index,issued in enumerate([False,True]):
        a=receive(client,meta,'MAINT-EVENT-'+str(index));id=a['id']
        if issued:
            station=next(r for r in meta['locations'] if r['name']=='DG-01BD')
            assert client.post('/api/inventory/transactions',json={'transaction_type':'ISSUE','warehouse_id':a['warehouse_id'],'asset_id':id,'recipient_location_id':station['id']}).status_code==201
        before=detail(client,id);count=len(before['lifecycle'])
        r=client.post('/api/maintenance',json={'asset_id':id,'type_id':master('maintenance_type','inspection'),'status_id':master('maintenance_status','open'),'technician_id':1,'problem':'Kiểm tra định kỳ'})
        assert r.status_code==201,r.text
        d=detail(client,id);assert d['current_status']=='MAINTENANCE' and len(d['lifecycle'])==count+1
        assert d['lifecycle'][0]['event_type']=='MAINTENANCE'
        assert client.patch('/api/maintenance/'+str(r.json()['id']),json={'status_id':master('maintenance_status','completed')}).status_code==200
        d=detail(client,id);assert d['current_status']==('IN_USE' if issued else 'AVAILABLE')
        assert d['current_location']==before['current_location'] and d['current_assignee']==before['current_assignee']
        assert len(d['lifecycle'])==count+2 and d['lifecycle'][0]['event_type']=='MAINTENANCE'
        assert all(e['event_type']!='STATUS_CHANGED' for e in d['lifecycle'])


def test_updated_only_for_important_changes_and_read_only_event_state(client,meta):
    a=receive(client,meta,'EVENT-UPDATES'); id=a['id']
    for payload in [{'model':a['model']},{'notes':'Legacy note'}]:
        assert client.patch(f'/api/assets/{id}',json=payload).status_code==200
    assert len(detail(client,id)['lifecycle'])==1
    assert client.patch(f'/api/assets/{id}',json={'description':'Thay đổi quan trọng'}).status_code==200
    d=detail(client,id);assert len(d['lifecycle'])==2 and d['lifecycle'][0]['event_type']=='UPDATED'
    assert any(c['field']=='description' and c['after']=='Thay đổi quan trọng' for c in d['lifecycle'][0]['changes'])
    for payload in [{'current_status':'RETIRED'},{'current_location_id':1},{'current_assignee_id':4},{'status_id':next(r['id'] for r in meta['master-data'] if r['group']=='asset_status' and r['code']=='retired')}]:
        assert client.patch(f'/api/assets/{id}',json=payload).status_code==422
    event_id=d['lifecycle'][0]['id']
    assert client.patch(f'/api/asset-operations/{event_id}',json={'operation_type':'RETIRED'}).status_code==405
    with TestClient(app,headers={'X-Requested-With':'Helpdesk'}) as c:
        assert c.post('/api/auth/login',json={'username':'viewer','password':'TestPassword2026!'}).status_code==200
        assert c.post(f'/api/assets/{id}/reassign',json={'user_id':4,'reason':'Không có quyền'}).status_code==403


def test_warehouse_return_is_one_returned_event(client,meta):
    a=receive(client,meta,'EVENT-STOCK-RETURN');id=a['id']
    assert client.post('/api/inventory/transactions',json={'transaction_type':'ISSUE','warehouse_id':a['warehouse_id'],'asset_id':id,'recipient_user_id':4}).status_code==201
    assert client.post('/api/inventory/transactions',json={'transaction_type':'RECEIVE','warehouse_id':a['warehouse_id'],'asset_id':id}).status_code==201
    d=detail(client,id)
    assert [e['event_type'] for e in d['lifecycle']]==['RETURNED','ISSUED','RECEIVED']
    assert d['current_status']=='AVAILABLE' and d['current_assignee'] is None and d['warehouse_id']==a['warehouse_id']
