import json
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from app.main import app

def mid(meta,group,code): return next(x['id'] for x in meta['master-data'] if x['group']==group and x['code']==code)
def asset(client,meta,code='TEST-001',type_name='Laptop'):
    response=client.post('/api/assets',json={'code':code,'name':'Test device','type_id':next(x['id'] for x in meta['asset-types'] if x['name']==type_name),'status_id':mid(meta,'asset_status','available')})
    assert response.status_code==201,response.text
    return response.json()['id']

def test_auth_rbac_and_csrf(client):
    with TestClient(app) as anonymous:
        assert anonymous.get('/api/assets').status_code==401
        assert anonymous.post('/api/auth/login',json={'username':'admin','password':'TestPassword2026!'}).status_code==403
    for role in ['viewer','support']:
        with TestClient(app,headers={'X-Requested-With':'Helpdesk'}) as c:
            assert c.post('/api/auth/login',json={'username':role,'password':'TestPassword2026!'}).status_code==200
            assert c.post('/api/users',json={}).status_code==403
            assert c.post('/api/assets',json={}).status_code==403
            assert c.get('/api/users').status_code==403
            assert 'password_hash' not in c.get('/api/meta').text
            if role=='viewer': assert c.post('/api/tickets',json={}).status_code==403

def test_location_and_assignment_history(client,meta):
    id=asset(client,meta)
    locs=[x['id'] for x in meta['locations'] if x['kind']=='station'][:2]
    for loc in locs:
        assert client.post(f'/api/assets/{id}/move',json={'location_id':loc,'reason':'Operational relocation'}).status_code==200
    assert client.post(f'/api/assets/{id}/move',json={'location_id':locs[-1],'reason':'No change'}).status_code==422
    body={'user_id':4,'condition_out':'Good condition'}
    assert client.post(f'/api/assets/{id}/assign',json=body).status_code==200
    assert client.post(f'/api/assets/{id}/assign',json=body).status_code==422
    assert client.post(f'/api/assets/{id}/transfer',json={**body,'user_id':2,'condition_in':'Good condition'}).status_code==200
    assert client.post(f'/api/assets/{id}/return',json={'condition_in':'Good condition'}).status_code==200
    data=client.get(f'/api/assets/{id}/detail').json()
    assert len(data['location-history'])==2
    assert sum(x['ended_at'] is None for x in data['location-history'])==1
    assert len(data['assignments'])==2 and all(x['returned_at'] for x in data['assignments'])
    assert data['location_id']==locs[-1]
    assert data['assignment_id'] is None
    assert len(data['audit-logs'])>=6
    assert client.patch('/api/location-history/1',json={'reason':'tamper'}).status_code==405
    assert client.delete('/api/assignments/1').status_code==405

def test_validation(client,meta):
    id=asset(client,meta,'TEST-NOASSIGN','Label Printer')
    assert client.post(f'/api/assets/{id}/assign',json={'user_id':4,'condition_out':'Good'}).status_code==422
    retired=asset(client,meta,'TEST-RETIRED')
    assert client.patch(f'/api/assets/{retired}',json={'status_id':mid(meta,'asset_status','retired')}).status_code==200
    assert client.post(f'/api/assets/{retired}/assign',json={'user_id':4,'condition_out':'Good'}).status_code==422
    assert client.post('/api/assets',json={'code':'PRN-012','name':'Duplicate','type_id':1,'status_id':mid(meta,'asset_status','available')}).status_code==409
    assert client.patch(f'/api/assets/{id}',json={'status_id':mid(meta,'priority','high')}).status_code==422
    assert client.patch(f'/api/assets/{id}',json={'serial':'ZEBRA-2026-1000'}).status_code==409
    assert client.post('/api/interfaces',json={'asset_id':id,'name':'LAN','mac':'bad'}).status_code==422
    assert client.post('/api/ip-addresses',json={'address':'192.168.20.80','interface_id':1,'subnet_id':1,'status_id':mid(meta,'ip_status','used')}).status_code==409
    assert client.post('/api/ip-addresses',json={'address':'999.2.3.4','subnet_id':1,'status_id':mid(meta,'ip_status','available')}).status_code==422
    assert client.post('/api/ip-addresses',json={'address':'10.0.0.80','subnet_id':1,'status_id':mid(meta,'ip_status','available')}).status_code==422
    assert client.patch('/api/locations/1',json={'parent_id':2}).status_code==422
    assert client.post('/api/audit-logs',json={}).status_code==405

def test_ticket_maintenance_knowledge(client,meta):
    id=asset(client,meta,'TEST-REPAIR')
    payload={'title':'End-to-end ticket','description':'Sensor malfunction','asset_id':id,'category_id':mid(meta,'ticket_category','hardware'),'priority_id':mid(meta,'priority','high'),'status_id':mid(meta,'ticket_status','open')}
    r=client.post('/api/tickets',json=payload);assert r.status_code==201,r.text
    ticket=r.json();tid=ticket['id'];assert ticket['number'].startswith('INC-')
    assert client.post(f'/api/tickets/{tid}/comments',json={'body':'Internal diagnostic','internal':True}).status_code==200
    assert client.post(f'/api/tickets/{tid}/comments',json={'body':'Public update'}).status_code==200
    attachment=client.post(f'/api/tickets/{tid}/attachments',files={'file':('diagnosis.txt',b'Sensor test results','text/plain')});assert attachment.status_code==200
    assert client.get('/api/attachments/'+str(attachment.json()['id'])).content==b'Sensor test results'
    maintenance=client.post('/api/maintenance',json={'asset_id':id,'ticket_id':tid,'problem':'Sensor malfunction','technician_id':3,'type_id':mid(meta,'maintenance_type','repair'),'status_id':mid(meta,'maintenance_status','open')});assert maintenance.status_code==201,maintenance.text
    assert client.get(f'/api/assets/{id}').json()['status_label']=='Repair'
    assert client.patch('/api/maintenance/'+str(maintenance.json()['id']),json={'status_id':mid(meta,'maintenance_status','completed'),'action_taken':'Replaced sensor'}).status_code==200
    assert client.get(f'/api/assets/{id}').json()['status_label']=='Available'
    assert client.patch(f'/api/tickets/{tid}',json={'status_id':mid(meta,'ticket_status','resolved')}).status_code==200
    article=client.post('/api/articles',json={'title':'Sensor repair','resolution':'Replace the sensor and verify operation.','category_id':mid(meta,'kb_category','hardware'),'status_id':mid(meta,'article_status','published')});assert article.status_code==201
    assert client.post('/api/ticket-articles',json={'ticket_id':tid,'article_id':article.json()['id']}).status_code==201
    data=client.get(f'/api/tickets/{tid}/detail').json();assert data['resolved_at'];assert len(data['articles'])==1;assert len(data['maintenance'])==1
    with TestClient(app,headers={'X-Requested-With':'Helpdesk'}) as viewer:
        viewer.post('/api/auth/login',json={'username':'viewer','password':'TestPassword2026!'})
        assert all(not a['internal'] for a in viewer.get(f'/api/tickets/{tid}/detail').json()['activities'])

def test_search_exports_dashboard(client):
    for q in ['PRN-012','PDA-035','192.168.20.80','7C:71:76:36:F5:F9']:
        data=client.get('/api/search',params={'q':q}).json();assert any(r['resource']=='assets' for r in data)
    ip=client.get('/api/ip-addresses/1').json();assert ip['asset_label']=='PRN-012';assert ip['port']=='Gi3';assert 'DG-18BD' in ip['location_label']
    assert client.get('/api/assets/1/qr').headers['content-type']=='image/png'
    for fmt in ['csv','xlsx']:
        r=client.get('/api/reports/assets/export',params={'format':fmt});assert r.status_code==200;assert len(r.content)>100
    data=client.get('/api/dashboard').json();assert len(data['stats'])==10;assert len(data['trend'])==7;assert data['attention']
    assert client.get('/api/assets?page_size=2').json()['page_size']==2
    assert client.get('/api/assets?filters=not-json').status_code==422

def test_concurrent_ticket_numbers(client,meta):
    payload={'title':'Concurrent issue','description':'Concurrency test','category_id':mid(meta,'ticket_category','hardware'),'priority_id':mid(meta,'priority','low'),'status_id':mid(meta,'ticket_status','open')}
    cookies=dict(client.cookies)
    def create(_):
        with TestClient(app,headers={'X-Requested-With':'Helpdesk'},cookies=cookies) as c:
            r=c.post('/api/tickets',json=payload);assert r.status_code==201,r.text;return r.json()['number']
    with ThreadPoolExecutor(max_workers=3) as pool: numbers=list(pool.map(create,range(6)))
    assert len(set(numbers))==6

def test_filters_reports_network_lookup(client,meta):
    for q in ['7C:71:76:36:F5:F9','PRN-012','SWKHOMAT1','Gi3']:
        rows=client.get('/api/ip-addresses',params={'q':q}).json()['items']
        assert any(r['address']=='192.168.20.80' for r in rows)
    assert client.get('/api/tickets?view=overdue').json()['total']>0
    dash=client.get('/api/dashboard').json()
    assert dash['stats']['Overdue tickets']==client.get('/api/tickets?view=overdue').json()['total']
    assert client.get('/api/assets',params={'location':'Q7 / OUTBOUND / DG-18BD'}).json()['total']==2
    report=client.get('/api/reports/maintenance/summary?group_by=asset_label').json()
    assert 'Total cost' in report['totals'] and report['groups']
    assert client.get('/api/reports/tickets/summary').json()['totals']['Avg resolution (hours)']>=0

def test_maintenance_return_preserves_state(client,meta):
    id=asset(client,meta,'TEST-RETURN-REPAIR')
    assert client.post(f'/api/assets/{id}/assign',json={'user_id':4,'condition_out':'Good'}).status_code==200
    maintenance=client.post('/api/maintenance',json={'asset_id':id,'problem':'Hardware fault','technician_id':3,'type_id':mid(meta,'maintenance_type','repair'),'status_id':mid(meta,'maintenance_status','open')}).json()
    assert client.post(f'/api/assets/{id}/return',json={'condition_in':'Requires repair'}).status_code==200
    assert client.get(f'/api/assets/{id}').json()['status_label']=='Repair'
    assert client.patch('/api/maintenance/'+str(maintenance['id']),json={'status_id':mid(meta,'maintenance_status','completed')}).status_code==200
    assert client.get(f'/api/assets/{id}').json()['status_label']=='Available'
    assert client.post(f'/api/assets/{id}/assign',json={'user_id':4,'condition_out':'Repaired'}).status_code==200
    assert client.patch('/api/maintenance/'+str(maintenance['id']),json={'note':'Invoice received'}).status_code==200
    assert client.get(f'/api/assets/{id}').json()['status_label']=='Assigned'

def test_create_article_from_ticket_is_atomic(client,meta):
    before=client.get('/api/articles').json()['total']
    payload={'title':'Atomic knowledge creation','resolution':'Inspect, replace, then verify.','category_id':mid(meta,'kb_category','hardware'),'status_id':mid(meta,'article_status','published')}
    assert client.post('/api/tickets/999999/article',json=payload).status_code==404
    assert client.get('/api/articles').json()['total']==before
    response=client.post('/api/tickets/1/article',json=payload)
    assert response.status_code==201,response.text
    detail=client.get('/api/tickets/1/detail').json()
    assert any(article['id']==response.json()['id'] for article in detail['articles'])
    assert any('Linked knowledge article' in a['body'] for a in detail['activities'])
