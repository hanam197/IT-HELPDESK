import ipaddress

def status(meta,code):
    return next(r['id'] for r in meta['master-data'] if r['group']=='ip_status' and r['code']==code)

def test_workspace_dhcp(client):
    r=client.get('/api/network/workspace'); assert r.status_code==200
    d=r.json(); assert {'subnets','devices','history','conflicts'}<=d.keys()
    s=d['subnets'][0]
    assert client.patch(f"/api/subnets/{s['id']}",json={'dhcp_start':'bad','dhcp_end':'bad'}).status_code==422
    assert client.patch(f"/api/subnets/{s['id']}",json={'dhcp_start':'203.0.113.10','dhcp_end':'203.0.113.20'}).status_code==422

def test_import_atomic_permissions(client,meta):
    d=client.get('/api/network/workspace').json(); s=d['subnets'][0]
    existing={p['address'] for p in d['ip-addresses']}
    address=next(str(h) for h in ipaddress.ip_network(s['cidr']).hosts() if str(h) not in existing)
    payload=f"address,subnet_id,status_id,assignment_type\n{address},{s['id']},{status(meta,'available')},DHCP\ninvalid,{s['id']},{status(meta,'available')},Static\n"
    r=client.post('/api/network/import/ip-addresses',files={'file':('ips.csv',payload,'text/csv')})
    assert r.status_code==422,r.text
    assert address not in {p['address'] for p in client.get('/api/network/workspace').json()['ip-addresses']}
    payload='\n'.join(payload.splitlines()[:2])
    r=client.post('/api/network/import/ip-addresses',files={'file':('ips.csv',payload,'text/csv')}); assert r.status_code==200,r.text
    assert client.post('/api/ip-addresses',json={'address':address,'subnet_id':s['id'],'status_id':status(meta,'available')}).status_code==409
    assert client.get('/api/network/export/ip-addresses').status_code==200
    client.post('/api/auth/login',json={'username':'viewer','password':'TestPassword2026!'})
    assert client.get('/api/network/workspace').status_code==200
    assert client.post('/api/network/import/ip-addresses',files={'file':('ips.csv',payload,'text/csv')}).status_code==403

def test_assignment_history(client,meta):
    d=client.get('/api/network/workspace').json(); ip=next(p for p in d['ip-addresses'] if p.get('interface_id'))
    r=client.patch(f"/api/ip-addresses/{ip['id']}",json={'interface_id':None,'status_id':status(meta,'available')}); assert r.status_code==200,r.text
    r=client.patch(f"/api/ip-addresses/{ip['id']}",json={'interface_id':ip['interface_id'],'status_id':status(meta,'used')}); assert r.status_code==200,r.text
    events={h['event'] for h in client.get('/api/network/workspace').json()['history'] if h['object_type']=='ip-addresses' and h['object_id']==ip['id']}
    assert {'Gán IP','Thu hồi IP'}<=events

def test_direct_ip_defaults_used_without_interface_or_status(client,meta):
    data=client.get('/api/network/workspace').json()
    subnet=data['subnets'][0]
    existing={row['address'] for row in data['ip-addresses']}
    address=next(str(host) for host in ipaddress.ip_network(subnet['cidr']).hosts() if str(host) not in existing)
    payload={'address':address,'subnet_id':subnet['id'],'mac':'aa-bb-cc-dd-ee-66','hostname':'direct-host'}
    result=client.post('/api/ip-addresses',json=payload)
    assert result.status_code==201,result.text
    row=result.json()
    assert row['status_id']==status(meta,'used')
    assert row['interface_id'] is None
    assert row['mac']=='AA:BB:CC:DD:EE:66'
    assert client.patch(f"/api/ip-addresses/{row['id']}",json={'mac':'invalid'}).status_code==422
    asset=data['assets'][0]
    result=client.patch(f"/api/ip-addresses/{row['id']}",json={'asset_id':asset['id']})
    assert result.status_code==200,result.text
    assert result.json()['asset_label']==asset['code']
    detail=client.get(f"/api/assets/{asset['id']}/detail").json()
    assert any(ip['id']==row['id'] for ip in detail['ip-addresses'])
    assert any(ip['id']==row['id'] for ip in client.get('/api/ip-addresses',params={'q':asset['code']}).json()['items'])
    refreshed=client.get('/api/network/workspace').json()
    subnet_row=next(s for s in refreshed['subnets'] if s['id']==subnet['id'])
    assert subnet_row['used_ips']==len([ip for ip in refreshed['ip-addresses'] if ip['subnet_id']==subnet['id']])

def test_router_ports_can_connect_downstream_switch(client,meta):
    router_type=next(t for t in meta['asset-types'] if t['name']=='Router')
    result=client.post('/api/assets/register',json={'type_id':router_type['id'],'warehouse_id':meta['warehouses'][0]['id'],'model':'Topology router','serial':'TOPOLOGY-ROUTER-TEST'})
    assert result.status_code==201,result.text
    router=result.json()
    mode=next(r['id'] for r in meta['master-data'] if r['group']=='port_mode')
    result=client.post('/api/switch-ports',json={'switch_id':router['id'],'name':'ether2','mode_id':mode})
    assert result.status_code==201,result.text
    port=result.json()
    assert client.patch(f"/api/switch-ports/{port['id']}",json={'connected_asset_id':router['id']}).status_code==422

def test_counted_port_mapping_minimal_fields_and_validation(client,meta):
    def create(kind,serial,**extra):
        type_id=next(t['id'] for t in meta['asset-types'] if t['name']==kind)
        result=client.post('/api/assets/register',json={'type_id':type_id,'warehouse_id':meta['warehouses'][0]['id'],'model':'Port test','serial':serial,**extra})
        assert result.status_code==201,result.text
        return result.json()
    switch=create('Switch','COUNTED-SWITCH',port_count=24)
    target=create('Laptop','COUNTED-TARGET')
    assert switch['port_count']==24
    result=client.post('/api/switch-ports',json={'switch_id':switch['id'],'name':'gi24','connected_asset_id':target['id']})
    assert result.status_code==201,result.text
    port=result.json()
    assert port['name']=='Gi24' and port['mode_id'] and port['status_id']
    assert client.post('/api/switch-ports',json={'switch_id':switch['id'],'name':'Gi25'}).status_code==422
    assert client.post('/api/switch-ports',json={'switch_id':switch['id'],'name':'Gi024'}).status_code==422
    assert client.patch(f"/api/assets/{switch['id']}",json={'port_count':12}).status_code==422
    assert client.patch(f"/api/assets/{switch['id']}",json={'port_count':24.5}).status_code==422
    assert client.post('/api/switch-ports',json={'switch_id':target['id'],'name':'Gi01'}).status_code==422
    part_type=next(t for t in meta['asset-types'] if t['name']=='Linh kiện')
    assert client.patch(f"/api/asset-types/{part_type['id']}",json={'track_network':False}).status_code==200
    no_network=create('Linh kiện','COUNTED-NONNETWORK')
    assert client.patch(f"/api/switch-ports/{port['id']}",json={'connected_asset_id':no_network['id']}).status_code==422
    assert client.patch(f"/api/asset-types/{part_type['id']}",json={'track_network':part_type['track_network']}).status_code==200
    ap=create('Access Point','COUNTED-AP',port_count=2)
    assert client.post('/api/switch-ports',json={'switch_id':ap['id'],'name':'Gi01'}).status_code==201
    assert client.patch(f"/api/switch-ports/{port['id']}",json={'connected_asset_id':None}).status_code==200

def test_uplink_and_sfp_capacities_and_port_names(client,meta):
    kind=next(t['id'] for t in meta['asset-types'] if t['name']=='Switch')
    result=client.post('/api/assets/register',json={'type_id':kind,'warehouse_id':meta['warehouses'][0]['id'],'model':'24P 2 uplink 2 SFP','serial':'GROUPED-PORTS-TEST','port_count':24,'uplink_port_count':2,'sfp_port_count':2})
    assert result.status_code==201,result.text
    asset=result.json()
    assert asset['uplink_port_count']==2 and asset['sfp_port_count']==2
    for name,expected in [('Gi01','Gi01'),('uplink2','Uplink02'),('sfp1','SFP01')]:
        result=client.post('/api/switch-ports',json={'switch_id':asset['id'],'name':name})
        assert result.status_code==201,result.text
        assert result.json()['name']==expected
    for name in ('Gi25','Uplink03','SFP03'):
        assert client.post('/api/switch-ports',json={'switch_id':asset['id'],'name':name}).status_code==422
    for field in ('uplink_port_count','sfp_port_count'):
        assert client.patch(f"/api/assets/{asset['id']}",json={field:0}).status_code==422
        assert client.patch(f"/api/assets/{asset['id']}",json={field:-1}).status_code==422
    assert client.post('/api/switch-ports',json={'switch_id':asset['id'],'name':'SFP001'}).status_code==422
    assert client.patch(f"/api/assets/{asset['id']}",json={'uplink_port_count':4,'sfp_port_count':4}).status_code==200
