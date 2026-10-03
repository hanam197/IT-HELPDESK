import pytest
from app.database import SessionLocal
from app import models as m
from test_warehouse import receive
from test_maintenance_issue_flow import create_issue,mid,using_asset

@pytest.mark.parametrize('outcome,state',[('FIXED','AVAILABLE'),('UNREPAIRABLE','RETIRED')])
@pytest.mark.parametrize('in_warehouse',[True,False])
def test_outcome_changes_state_preserves_location_and_locks_record(client,meta,outcome,state,in_warehouse):
    asset=(receive if in_warehouse else using_asset)(client,meta,f'OUTCOME-{outcome}-{in_warehouse}')
    record=create_issue(client,meta,asset)
    assert client.post(f"/api/maintenance/{record['id']}/stop-asset").status_code==200
    before=client.get(f"/api/assets/{asset['id']}/detail").json()
    path=f"/api/maintenance/{record['id']}"
    result=client.patch(path,json={'status_id':mid(meta,'maintenance_status','completed'),'resolution_outcome':outcome})
    assert result.status_code==200,result.text
    assert result.json()['resolution_outcome']==outcome
    after=client.get(f"/api/assets/{asset['id']}/detail").json()
    assert after['current_status']==state
    assert after['warehouse_id']==before['warehouse_id']
    assert after['current_location']==before['current_location'] and after['current_location'] is not None
    assert after['current_assignee'] is None and after['assignment_id'] is None
    for patch in [{'problem':'Overwrite'},{'resolution_outcome':'FIXED'},{'note':'changed'},{'replacement_asset_ids':[]},{}]:
        assert client.patch(path,json=patch).status_code==422
    assert client.get(path).json()==result.json()
    if state=='RETIRED':
        assert after['status_label']=='Hư / Ngừng sử dụng'
        assert client.post(f"/api/assets/{asset['id']}/dispose",json={'reason':'Thanh lý theo quyết định'}).status_code==200
        disposed=client.get(f"/api/assets/{asset['id']}/detail").json()
        assert disposed['current_location'] is None
        assert disposed['lifecycle'][0]['before_state']['current_location']['id']==before['current_location']


def test_required_outcome_and_content_fail_atomically(client,meta):
    asset=receive(client,meta,'OUTCOME-VALIDATION');record=create_issue(client,meta,asset,diagnosis=None,action_taken=None)
    path=f"/api/maintenance/{record['id']}";complete={'status_id':mid(meta,'maintenance_status','completed')}
    for values in [{},{'resolution_outcome':'OTHER'},{'resolution_outcome':'FIXED'},{'resolution_outcome':'FIXED','diagnosis':'Lỗi nguồn','action_taken':' '}]:
        assert client.patch(path,json={**complete,**values}).status_code==422
        assert client.get(path).json()['end_at'] is None
    assert client.patch(path,json={'problem':'Lưu nháp trực tiếp','resolution_outcome':'UNREPAIRABLE'}).status_code==200
    assert client.get(f"/api/assets/{asset['id']}").json()['current_status']=='AVAILABLE'


def test_location_required_before_disposal_and_completion(client,meta):
    asset=receive(client,meta,'OUTCOME-LOCATION');record=create_issue(client,meta,asset)
    with SessionLocal() as db:
        row=db.get(m.Asset,asset['id']);row.current_location_id=None;db.commit()
    assert client.patch(f"/api/maintenance/{record['id']}",json={'status_id':mid(meta,'maintenance_status','completed'),'resolution_outcome':'FIXED'}).status_code==422
    assert client.post(f"/api/assets/{asset['id']}/retire",json={'reason':'Thiếu vị trí'}).status_code==422
    with SessionLocal() as db:
        row=db.get(m.Asset,asset['id']);row.current_status='RETIRED';row.status_id=mid(meta,'asset_status','retired');db.commit()
    assert client.post(f"/api/assets/{asset['id']}/dispose",json={'reason':'Thiếu vị trí'}).status_code==422


def test_backdated_completion_does_not_backdate_custody(client,meta):
    from datetime import datetime,timedelta,timezone
    asset=using_asset(client,meta,'OUTCOME-BACKDATED')
    now=datetime.now(timezone.utc)
    record=create_issue(client,meta,asset,status_id=mid(meta,'maintenance_status','completed'),resolution_outcome='FIXED',start_at=(now-timedelta(hours=2)).isoformat(),end_at=(now-timedelta(hours=1)).isoformat())
    assert record['end_at']
    current=client.get(f"/api/assets/{asset['id']}/detail").json()
    assignment=current['assignments'][0]
    assert datetime.fromisoformat(assignment['returned_at'])>=datetime.fromisoformat(assignment['created_at'])
