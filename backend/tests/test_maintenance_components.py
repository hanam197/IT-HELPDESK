from fastapi.testclient import TestClient
from app.main import app
from test_warehouse import receive
from test_maintenance_issue_flow import create_issue, mid


def component(client,meta,serial):
    response=client.post('/api/assets/register',json={'warehouse_id':meta['warehouses'][0]['id'],'type_id':next(r['id'] for r in meta['asset-types'] if r['name']=='Linh kiện'),'model':'RAM 16GB','serial':serial})
    assert response.status_code==201,response.text
    return response.json()


def issues(client,part):
    return [e for e in client.get(f"/api/assets/{part['id']}/detail").json()['lifecycle'] if e['event_type']=='ISSUED']


def test_component_selection_issues_once_with_history(client,meta):
    asset=receive(client,meta,'COMPONENT-TARGET');part=component(client,meta,'COMPONENT-RAM')
    record=create_issue(client,meta,asset);path=f"/api/maintenance/{record['id']}"
    for ids in [[asset['id']],[999999],[part['id'],part['id']],['invalid']]:
        assert client.patch(path,json={'replacement_asset_ids':ids}).status_code in {404,422}
    result=client.patch(path,json={'replacement_asset_ids':[part['id']]})
    assert result.status_code==200,result.text
    saved=client.get(path).json()
    assert saved['replacement_asset_ids']==[part['id']]
    assert saved['replacement_assets'][0]['serial']=='COMPONENT-RAM'
    current=client.get(f"/api/assets/{part['id']}").json()
    assert current['warehouse_id'] is None and current['current_status']=='IN_USE'
    assert current['current_location_id']==asset['current_location_id']
    events=issues(client,part)
    assert len(events)==1
    assert events[0]['after_state']['maintenance']['id']==record['id']
    assert events[0]['after_state']['installed_in_asset']['id']==asset['id']
    transactions=client.get('/api/inventory-transactions',params={'q':record['number']}).json()['items']
    assert len(transactions)==1 and transactions[0]['transaction_type']=='ISSUE'
    assert transactions[0]['asset_id']==part['id'] and transactions[0]['quantity']==1
    for _ in range(2):
        assert client.patch(path,json={'replacement_asset_ids':[part['id']],'note':'Kiểm tra lại'}).status_code==200
    assert len(issues(client,part))==1
    assert client.patch(path,json={'replacement_asset_ids':[]}).status_code==422
    assert client.patch(path,json={'status_id':mid(meta,'maintenance_status','completed'),'resolution_outcome':'FIXED','diagnosis':'Đã xác định nguyên nhân','action_taken':'Đã xử lý'}).status_code==200
    assert len(issues(client,part))==1
    other=receive(client,meta,'COMPONENT-OTHER');second=create_issue(client,meta,other)
    assert client.patch(f"/api/maintenance/{second['id']}",json={'replacement_asset_ids':[part['id']]}).status_code==422


def test_component_batch_failure_rolls_back_all_stock_and_record(client,meta):
    asset=receive(client,meta,'PARTS-ROLLBACK');a=component(client,meta,'PART-A');b=component(client,meta,'PART-B')
    # First component is valid; the later component's warehouse is disabled.
    warehouses=meta['warehouses'];other=warehouses[1]
    second=client.post('/api/assets/register',json={'warehouse_id':other['id'],'type_id':b['type_id'],'model':'SSD','serial':'PART-DISABLED-WH'}).json()
    record=create_issue(client,meta,asset)
    assert client.patch(f"/api/locations/{other['location_id']}",json={'active':False}).status_code==200
    try:
        result=client.patch(f"/api/maintenance/{record['id']}",json={'replacement_asset_ids':[a['id'],second['id']],'diagnosis':'Must roll back'})
        assert result.status_code==422,result.text
        assert client.get(f"/api/maintenance/{record['id']}").json()['replacement_asset_ids'] is None
        assert client.get(f"/api/assets/{a['id']}").json()['warehouse_id']==a['warehouse_id']
        assert issues(client,a)==[]
    finally:
        assert client.patch(f"/api/locations/{other['location_id']}",json={'active':True}).status_code==200


def test_component_issue_requires_warehouse_permission(client,meta):
    asset=receive(client,meta,'PARTS-PERMISSION');part=component(client,meta,'PART-PERMISSION')
    record=create_issue(client,meta,asset)
    with TestClient(app,headers={'X-Requested-With':'Helpdesk'}) as support:
        assert support.post('/api/auth/login',json={'username':'support','password':'TestPassword2026!'}).status_code==200
        assert support.patch(f"/api/maintenance/{record['id']}",json={'replacement_asset_ids':[part['id']]}).status_code==403
    assert client.get(f"/api/assets/{part['id']}").json()['warehouse_id']==part['warehouse_id']
    assert issues(client,part)==[]


def test_create_completed_record_issues_components(client,meta):
    asset=receive(client,meta,'PARTS-COMPLETED');part=component(client,meta,'PART-COMPLETED')
    record=create_issue(client,meta,asset,status_id=mid(meta,'maintenance_status','completed'),resolution_outcome='FIXED',replacement_asset_ids=[part['id']])
    assert record['end_at']
    assert len(issues(client,part))==1
    assert client.get(f"/api/assets/{asset['id']}").json()['current_status']=='AVAILABLE'
