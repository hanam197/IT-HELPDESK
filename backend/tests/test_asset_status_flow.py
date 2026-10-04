from stock_helpers import post_stock
import io
import json
import pytest
from openpyxl import Workbook
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from app.main import app
from app.database import SessionLocal
from app import models as m
from app.asset_events import STATUS_CODES
from test_warehouse import receive

STATES={'AVAILABLE','IN_USE','MAINTENANCE','RETIRED','DISPOSED'}

def mid(meta,group,code):
    return next(r['id'] for r in meta['master-data'] if r['group']==group and r['code']==code)


def issue(client,asset):
    result=post_stock(client, json={'transaction_type':'ISSUE','asset_id':asset['id'],'warehouse_id':asset['warehouse_id'],'recipient_user_id':4})
    assert result.status_code==201,result.text


def maintenance(client,meta,asset):
    result=client.post('/api/maintenance',json={'asset_id':asset['id'],'type_id':mid(meta,'maintenance_type','hardware'),'status_id':mid(meta,'maintenance_status','open'),'technician_id':1,'problem':'Màn hình không hiển thị','diagnosis':'Cáp màn hình lỗi'})
    assert result.status_code==201,result.text
    assert client.post('/api/maintenance/'+str(result.json()['id'])+'/stop-asset').status_code==200
    return result.json()


@pytest.mark.parametrize('status',sorted(STATES))
def test_registration_respects_selected_status_and_records_actor(client,meta,status):
    assert set(STATUS_CODES)==STATES
    assert {r['id'] for r in meta['asset-statuses']}==STATES
    result=client.post('/api/assets/register',json={'warehouse_id':meta['warehouses'][0]['id'],'type_id':meta['asset-types'][0]['id'],'model':'Initial state','serial':'INITIAL-'+status,'status_id':mid(meta,'asset_status',status.lower())})
    assert result.status_code==201,result.text
    asset=result.json()
    assert asset['current_status']==status
    assert asset['status_id']==mid(meta,'asset_status',status.lower())
    if status in {'IN_USE','DISPOSED'}: assert asset['warehouse_id'] is None
    detail=client.get(f"/api/assets/{asset['id']}/detail").json()
    event=detail['lifecycle'][0]
    assert event['before_state']=={} and event['after_state']['current_status']==status
    assert event['performed_by']==client.get('/api/auth/me').json()['name'] and event['occurred_at']
    for filters in [{'status_id':asset['status_id']},{'current_status':status}]:
        rows=client.get('/api/assets',params={'q':asset['serial'],'filters':json.dumps(filters)}).json()
        assert rows['total']==1
    summary=client.get('/api/reports/assets/summary',params={'q':asset['serial'],'group_by':'status_label'})
    assert summary.status_code==200


def test_registration_rejects_invalid_status_and_keeps_default(client,meta):
    data={'warehouse_id':meta['warehouses'][0]['id'],'type_id':meta['asset-types'][0]['id'],'model':'Invalid','serial':'INVALID-STATUS'}
    for value in [None,'',999999,mid(meta,'priority','high')]:
        result=client.post('/api/assets/register',json={**data,'status_id':value})
        assert result.status_code in {404,422},result.text
    result=client.post('/api/assets/register',json=data)
    assert result.status_code==201 and result.json()['current_status']=='AVAILABLE'
    for status in ['REPAIR_NEEDED','BROKEN','DAMAGED','WAITING_REPAIR','UNKNOWN']:
        assert client.post('/api/master-data',json={'group':'asset_status','code':status.lower(),'name':status}).status_code==422
        assert client.get('/api/assets',params={'filters':json.dumps({'current_status':status})}).status_code==422
    with SessionLocal() as db:
        with pytest.raises(IntegrityError):
            db.execute(update(m.Asset).where(m.Asset.id==result.json()['id']).values(current_status='BROKEN'))
            db.flush()
        db.rollback()


@pytest.mark.parametrize('in_maintenance',[False,True])
def test_retire_in_use_or_maintenance_then_dispose_atomic_history(client,meta,in_maintenance):
    asset=receive(client,meta,'TERMINAL-'+str(in_maintenance));id=asset['id'];issue(client,asset)
    repair=maintenance(client,meta,asset) if in_maintenance else None
    before=client.get(f'/api/assets/{id}/detail').json()
    result=client.post(f'/api/assets/{id}/retire',json={'reason':'Không thể khôi phục thiết bị'})
    assert result.status_code==200,result.text
    detail=client.get(f'/api/assets/{id}/detail').json()
    assert detail['current_status']=='RETIRED' and detail['assignment_id'] is None
    assert detail['warehouse_id'] is None and detail['current_location']==before['current_location']
    assert detail['assignments'][0]['returned_at']
    event=detail['lifecycle'][0]
    assert len(detail['lifecycle'])==len(before['lifecycle'])+1
    assert event['before_state']['current_status']==('MAINTENANCE' if in_maintenance else 'IN_USE')
    assert event['after_state']['current_status']=='RETIRED' and event['performed_by'] and event['occurred_at']
    if repair:
        record=client.get('/api/maintenance/'+str(repair['id'])).json()
        assert record['end_at'] and record['diagnosis']=='Cáp màn hình lỗi'
        assert 'Không thể khôi phục' in record['note']
        # Editing the closed maintenance record must not resurrect a retired asset.
        assert client.patch('/api/maintenance/'+str(repair['id']),json={'status_id':mid(meta,'maintenance_status','completed'),'resolution_outcome':'FIXED','diagnosis':'Đã xác định nguyên nhân','action_taken':'Đã xử lý'}).status_code==422
        assert client.get(f'/api/assets/{id}').json()['current_status']=='RETIRED'
    with TestClient(app,headers={'X-Requested-With':'Helpdesk'}) as viewer:
        assert viewer.post('/api/auth/login',json={'username':'viewer','password':'TestPassword2026!'}).status_code==200
        assert viewer.post(f'/api/assets/{id}/dispose',json={'reason':'Thanh lý'}).status_code==403
    assert client.post(f'/api/assets/{id}/dispose',json={'reason':'Đã bàn giao thanh lý'}).status_code==200
    detail=client.get(f'/api/assets/{id}/detail').json()
    assert detail['current_status']=='DISPOSED'
    event=detail['lifecycle'][0]
    assert event['event_type']=='DISPOSED'
    assert event['before_state']['current_status']=='RETIRED' and event['after_state']['current_status']=='DISPOSED'
    count=len(detail['lifecycle'])
    for action,payload in [('dispose',{'reason':'Lặp thanh lý'}),('retire',{'reason':'Ngừng lại'}),('assign',{'user_id':4,'condition_out':'Tốt'}),('move',{'location_id':meta['locations'][0]['id'],'reason':'Điều chuyển'}),('return',{'warehouse_id':asset['warehouse_id'],'return_status':'AVAILABLE','condition_in':'Tốt'})]:
        assert client.post(f'/api/assets/{id}/{action}',json=payload).status_code==422
    assert client.post('/api/maintenance',json={'asset_id':id,'type_id':mid(meta,'maintenance_type','hardware'),'status_id':mid(meta,'maintenance_status','open'),'technician_id':1,'problem':'Không được bảo trì'}).status_code==422
    assert len(client.get(f'/api/assets/{id}/detail').json()['lifecycle'])==count


def test_cannot_skip_retirement_or_return_in_use_disposed(client,meta):
    asset=receive(client,meta,'NO-SKIP-DISPOSAL');id=asset['id']
    for stage in ['AVAILABLE','IN_USE','MAINTENANCE']:
        if stage=='IN_USE': issue(client,asset)
        if stage=='MAINTENANCE': maintenance(client,meta,asset)
        assert client.post(f'/api/assets/{id}/dispose',json={'reason':'Skip retirement'}).status_code==422
        assert client.get(f'/api/assets/{id}').json()['current_status']==stage
    other=receive(client,meta,'NO-BAD-RETURN');issue(client,other)
    for state in ['IN_USE','DISPOSED','REPAIR_NEEDED']:
        assert client.post(f"/api/assets/{other['id']}/return",json={'warehouse_id':other['warehouse_id'],'return_status':state,'condition_in':'Tốt'}).status_code==422
        assert client.get(f"/api/assets/{other['id']}").json()['current_status']=='IN_USE'


def test_import_status_is_validated_and_transactional(client,meta):
    def upload(rows):
        book=Workbook();sheet=book.active
        sheet.append(['asset_type','warehouse','model','serial','status'])
        for serial,status in rows: sheet.append(['Laptop',meta['warehouses'][0]['code'],'Imported',serial,status])
        buffer=io.BytesIO();book.save(buffer)
        return client.post('/api/assets/import',files={'file':('assets.xlsx',buffer.getvalue(),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')})
    result=upload([('IMPORT-STATE-GOOD','MAINTENANCE'),('IMPORT-STATE-BAD','REPAIR_NEEDED')])
    assert result.status_code==422
    assert client.get('/api/assets',params={'q':'IMPORT-STATE-GOOD'}).json()['total']==0
    result=upload([('IMPORT-STATE-'+s,s) for s in sorted(STATES)])
    assert result.status_code==201,result.text
    for status in STATES:
        row=client.get('/api/assets',params={'q':'IMPORT-STATE-'+status}).json()['items'][0]
        assert row['current_status']==status
