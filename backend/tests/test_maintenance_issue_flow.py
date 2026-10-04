from stock_helpers import post_stock
"""Maintenance is an issue record; only explicit operations change asset use/custody."""
from datetime import datetime,timedelta,timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect
from app.database import engine
from app.main import app
from test_warehouse import receive


def mid(meta,group,code):
    return next(r['id'] for r in meta['master-data'] if r['group']==group and r['code']==code)


def create_issue(client,meta,asset,**extra):
    payload={'asset_id':asset['id'],'type_id':mid(meta,'maintenance_type','network'),'status_id':mid(meta,'maintenance_status','open'),'problem':'Máy in mất kết nối','technician_id':3,'diagnosis':'Cáp mạng lỗi','action_taken':'Thay cáp và kiểm tra kết nối',**extra}
    response=client.post('/api/maintenance',json=payload)
    assert response.status_code==201,response.text
    return response.json()


def using_asset(client,meta,name,assigned=True):
    asset=receive(client,meta,name)
    station=next(r for r in meta['locations'] if r['name']=='DG-01BD')
    response=post_stock(client, json={'transaction_type':'ISSUE','asset_id':asset['id'],'warehouse_id':asset['warehouse_id'],'recipient_location_id':station['id'],**({'recipient_user_id':4} if assigned else {})})
    assert response.status_code==201,response.text
    return asset


def detail(client,asset):
    return client.get(f"/api/assets/{asset['id']}/detail").json()


def assert_custody_same(before,after):
    for key in ['current_location','current_assignee','warehouse_id','assignment_id']:
        assert before[key]==after[key],key
    assert before['assignments']==after['assignments']
    assert before['location-history']==after['location-history']


@pytest.mark.parametrize('flow',['onsite','resume','return','retire'])
@pytest.mark.parametrize('assigned',[False,True])
def test_four_required_flows_preserve_custody_and_history(client,meta,flow,assigned):
    asset=using_asset(client,meta,f'ISSUE-FLOW-{flow}-{assigned}',assigned)
    before=detail(client,asset); issue=create_issue(client,meta,asset)
    recorded=detail(client,asset)
    assert recorded['current_status']=='IN_USE'
    assert_custody_same(before,recorded)
    assert recorded['lifecycle'][0]['before_state']['current_status']=='IN_USE'
    assert recorded['lifecycle'][0]['after_state']['current_status']=='IN_USE'
    assert recorded['lifecycle'][0]['after_state']['maintenance']['problem']=='Máy in mất kết nối'
    id=issue['id']
    # Updating a new record does not automatically stop the asset.
    update=client.patch(f'/api/maintenance/{id}',json={'status_id':mid(meta,'maintenance_status','open'),'diagnosis':'Cáp mạng lỗi','action_taken':'Thay cáp và kiểm tra kết nối','parts_replaced':'Cáp mạng','vendor':'IT nội bộ','cost':25000,'note':'Kiểm tra tại trạm'})
    assert update.status_code==200,update.text
    assert detail(client,asset)['current_status']=='IN_USE'
    assert_custody_same(before,detail(client,asset))
    if flow!='onsite':
        stopped=client.post(f'/api/maintenance/{id}/stop-asset')
        assert stopped.status_code==200,stopped.text
        current=detail(client,asset)
        assert current['current_status']=='MAINTENANCE'
        assert_custody_same(before,current)
        assert current['lifecycle'][0]['before_state']['current_status']=='IN_USE'
        assert current['lifecycle'][0]['after_state']['current_status']=='MAINTENANCE'
        assert client.post(f'/api/maintenance/{id}/stop-asset').status_code==422
    count=len(detail(client,asset)['lifecycle'])
    if flow in {'onsite','resume'}:
        result=client.patch(f'/api/maintenance/{id}',json={'status_id':mid(meta,'maintenance_status','completed'),'resolution_outcome':'FIXED'})
        assert result.status_code==200,result.text
        current=detail(client,asset)
        assert current['current_status']=='AVAILABLE'
        assert current['current_location']==before['current_location']
        assert current['current_assignee'] is None
        event_type='MAINTENANCE'
    elif flow=='return':
        result=client.post(f"/api/assets/{asset['id']}/return",json={'warehouse_id':asset['warehouse_id'],'return_status':'AVAILABLE','condition_in':'Đã kiểm tra hoạt động'})
        assert result.status_code==200,result.text
        current=detail(client,asset)
        assert current['current_status']=='AVAILABLE' and current['warehouse_id']==asset['warehouse_id']
        assert current['current_location']==meta['warehouses'][0]['location_id']
        assert current['current_assignee'] is None and current['assignment_id'] is None
        event_type='RETURNED'
    else:
        result=client.post(f"/api/assets/{asset['id']}/retire",json={'reason':'Không thể sửa, xác định ngừng sử dụng'})
        assert result.status_code==200,result.text
        current=detail(client,asset)
        assert current['current_status']=='RETIRED' and current['warehouse_id'] is None
        assert current['current_assignee'] is None
        assert current['current_location']==before['current_location']
        event_type='RETIRED'
    assert len(current['lifecycle'])==count+1
    event=current['lifecycle'][0]
    assert event['event_type']==event_type and event['performed_by'] and event['occurred_at']
    assert event['before_state']['current_status']==('IN_USE' if flow=='onsite' else 'MAINTENANCE')
    assert event['after_state']['current_status']==current['current_status']
    repair=event['after_state']['maintenance']
    assert repair['diagnosis']=='Cáp mạng lỗi' and repair['action_taken']=='Thay cáp và kiểm tra kết nối'
    assert repair['parts_replaced']=='Cáp mạng' and repair['vendor']=='IT nội bộ' and repair['cost']==25000
    closed=client.get(f'/api/maintenance/{id}').json()
    assert closed['end_at'] and 'ticket_id' not in closed
    if flow=='retire':
        assert client.post(f"/api/assets/{asset['id']}/dispose",json={'reason':'Thanh lý theo biên bản'}).status_code==200
        assert detail(client,asset)['current_status']=='DISPOSED'
    # Late repair notes must not change custody or revive/return assets.
    state=detail(client,asset)
    assert client.patch(f'/api/maintenance/{id}',json={'note':'Đã nhận hóa đơn'}).status_code==422
    assert detail(client,asset)['current_status']==state['current_status']
    assert_custody_same(state,detail(client,asset))
    assert client.patch(f'/api/maintenance/{id}',json={'status_id':mid(meta,'maintenance_status','open')}).status_code==422


def test_issue_category_ticket_independence_dates_and_required_fields(client,meta):
    assert {r['code'] for r in meta['master-data'] if r['group']=='maintenance_type'}=={'hardware','network','software','power','peripheral','other'}
    assert 'ticket_id' not in {c['name'] for c in inspect(engine).get_columns('maintenance')}
    asset=using_asset(client,meta,'MAINT-VALIDATION')
    body={'asset_id':asset['id'],'type_id':mid(meta,'maintenance_type','power'),'status_id':mid(meta,'maintenance_status','open'),'problem':'PC không lên nguồn','technician_id':3}
    for key in ['asset_id','type_id','problem','technician_id']:
        assert client.post('/api/maintenance',json={k:v for k,v in body.items() if k!=key}).status_code==422
    for extra in [{'ticket_id':1},{'previous_status_id':1},{'type_id':mid(meta,'ticket_category','hardware')},{'cost':-1},{'cost':'NaN'},{'problem':'   '},{'end_at':datetime.now(timezone.utc).isoformat()},{'start_at':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()}]:
        assert client.post('/api/maintenance',json={**body,**extra}).status_code==422
    issue=create_issue(client,meta,asset,start_at=(datetime.now(timezone.utc)-timedelta(hours=2)).isoformat())
    id=issue['id'];count=len(detail(client,asset)['lifecycle'])
    assert client.patch(f'/api/maintenance/{id}',json={'status_id':mid(meta,'maintenance_status','completed'),'resolution_outcome':'FIXED','end_at':(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()}).status_code==422
    assert len(detail(client,asset)['lifecycle'])==count
    assert client.patch(f'/api/maintenance/{id}',json={'status_id':mid(meta,'maintenance_status','completed'),'resolution_outcome':'FIXED','end_at':(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat()}).status_code==200
    for code in ['printer_disconnected','repair','inspection']:
        assert client.post('/api/master-data',json={'group':'maintenance_type','code':code,'name':code}).status_code==422


def test_only_two_states_and_completion_restores_stopped_asset(client,meta):
    assert {r['code'] for r in meta['master-data'] if r['group']=='maintenance_status'}=={'open','completed'}
    for code in ['cancelled','diagnosing','repairing','waiting_parts']:
        assert client.post('/api/master-data',json={'group':'maintenance_status','code':code,'name':code}).status_code==422
    asset=using_asset(client,meta,'MAINT-TWO-STATES');issue=create_issue(client,meta,asset)
    assert issue['status_label']=='Mới'
    assert client.post(f"/api/maintenance/{issue['id']}/stop-asset").status_code==200
    assert detail(client,asset)['current_status']=='MAINTENANCE'
    result=client.patch(f"/api/maintenance/{issue['id']}",json={'status_id':mid(meta,'maintenance_status','completed'),'resolution_outcome':'FIXED'})
    assert result.status_code==200 and result.json()['status_label']=='Hoàn tất'
    assert detail(client,asset)['current_status']=='AVAILABLE'


def test_stop_permission_and_onsite_issue_does_not_block_issuance(client,meta):
    asset=receive(client,meta,'ONSITE-AVAILABLE');issue=create_issue(client,meta,asset)
    assert detail(client,asset)['current_status']=='AVAILABLE'
    with TestClient(app,headers={'X-Requested-With':'Helpdesk'}) as viewer:
        assert viewer.post('/api/auth/login',json={'username':'viewer','password':'TestPassword2026!'}).status_code==200
        assert viewer.post(f"/api/maintenance/{issue['id']}/stop-asset").status_code==403
    result=post_stock(client, json={'transaction_type':'ISSUE','asset_id':asset['id'],'warehouse_id':asset['warehouse_id'],'recipient_user_id':4})
    assert result.status_code==201,result.text
    assert detail(client,asset)['current_status']=='IN_USE'
    assert client.get(f"/api/maintenance/{issue['id']}").json()['end_at'] is None


def test_return_starts_maintenance_atomically_and_can_issue_after_repair(client,meta):
    asset=using_asset(client,meta,'RETURN-AND-REPAIR')
    payload={'transaction_type':'RECEIVE','asset_id':asset['id'],'warehouse_id':asset['warehouse_id'],'return_status':'MAINTENANCE','reason':'Máy không in được, cần kiểm tra','maintenance':{'type_id':mid(meta,'maintenance_type','hardware'),'technician_id':3,'problem':'Máy không in được','diagnosis':'Nghi lỗi cụm sấy'}}
    count=len(detail(client,asset)['lifecycle'])
    invalid=post_stock(client, json={**payload,'maintenance':{**payload['maintenance'],'technician_id':999999}})
    assert invalid.status_code in (404,422)
    unchanged=detail(client,asset)
    assert unchanged['current_status']=='IN_USE' and unchanged['warehouse_id'] is None
    assert unchanged['current_assignee']==4 and len(unchanged['lifecycle'])==count
    response=post_stock(client, json=payload)
    assert response.status_code==201,response.text
    current=detail(client,asset)
    assert current['current_status']=='MAINTENANCE' and current['warehouse_id']==asset['warehouse_id']
    assert current['current_assignee'] is None
    assert len(current['lifecycle'])==count+2
    returned=next(e for e in current['lifecycle'] if e['event_type']=='RETURNED')
    assert payload['reason'] in returned['description']
    repair=current['lifecycle'][0]['after_state']['maintenance']
    assert repair['diagnosis']=='Nghi lỗi cụm sấy'
    assert client.patch(f"/api/maintenance/{repair['id']}",json={'status_id':mid(meta,'maintenance_status','completed'),'resolution_outcome':'FIXED','action_taken':'Thay cụm sấy, test OK'}).status_code==200
    assert detail(client,asset)['current_status']=='AVAILABLE'
    assert post_stock(client, json={'transaction_type':'ISSUE','asset_id':asset['id'],'warehouse_id':asset['warehouse_id'],'recipient_user_id':4}).status_code==201
    assert detail(client,asset)['current_status']=='IN_USE'


def test_return_maintenance_rejects_wrong_status_and_duplicate_issue(client,meta):
    asset=using_asset(client,meta,'RETURN-REPAIR-VALIDATION')
    payload={'transaction_type':'RECEIVE','asset_id':asset['id'],'warehouse_id':asset['warehouse_id'],'return_status':'AVAILABLE','reason':'Thu hồi để sửa','maintenance':{'type_id':mid(meta,'maintenance_type','hardware'),'technician_id':3,'problem':'Không lên nguồn'}}
    assert post_stock(client, json=payload).status_code==422
    payload['return_status']='MAINTENANCE'
    create_issue(client,meta,asset)
    assert post_stock(client, json=payload).status_code==422
    assert detail(client,asset)['current_status']=='IN_USE'
    del payload['maintenance']
    assert post_stock(client, json=payload).status_code==201
    assert detail(client,asset)['current_status']=='MAINTENANCE'


def test_estimate_hours_sets_due_time_without_closing_issue(client,meta):
    asset=using_asset(client,meta,'ESTIMATE-HOURS')
    start=(datetime.now(timezone.utc)-timedelta(minutes=5)).replace(microsecond=0)
    issue=create_issue(client,meta,asset,start_at=start.isoformat(),estimate_hours=2.5)
    assert datetime.fromisoformat(issue['due_at'])==start+timedelta(hours=2.5)
    assert issue['end_at'] is None
    assert detail(client,asset)['current_status']=='IN_USE'
    snapshot=detail(client,asset)['lifecycle'][0]['after_state']['maintenance']
    assert snapshot['due_at']==issue['due_at']
    updated=client.patch(f"/api/maintenance/{issue['id']}",json={'estimate_hours':4}).json()
    assert datetime.fromisoformat(updated['due_at'])==start+timedelta(hours=4)
    for value in [0,-1,'NaN',1e300]:
        assert client.patch(f"/api/maintenance/{issue['id']}",json={'estimate_hours':value}).status_code==422
    done=client.patch(f"/api/maintenance/{issue['id']}",json={'status_id':mid(meta,'maintenance_status','completed'),'resolution_outcome':'FIXED'}).json()
    assert done['end_at'] and done['due_at']==updated['due_at']
    assert datetime.fromisoformat(done['end_at'])<datetime.fromisoformat(done['due_at'])


def test_quick_maintenance_completes_in_one_save_without_changing_custody(client,meta):
    asset=using_asset(client,meta,'QUICK-REPAIR')
    before=detail(client,asset)
    record=create_issue(client,meta,asset,status_id=mid(meta,'maintenance_status','completed'),resolution_outcome='FIXED',diagnosis='Cáp lỏng',action_taken='Cắm lại cáp và kiểm tra')
    assert record['end_at'] and record['due_at'] is None
    current=detail(client,asset)
    assert current['current_status']=='AVAILABLE'
    assert current['current_location']==before['current_location']
    assert current['current_assignee'] is None
    assert len(current['lifecycle'])==len(before['lifecycle'])+1
    assert 'Hoàn tất bảo trì nhanh' in current['lifecycle'][0]['description']
    assert current['lifecycle'][0]['after_state']['maintenance']['action_taken']=='Cắm lại cáp và kiểm tra'
