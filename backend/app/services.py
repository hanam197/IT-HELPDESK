import ipaddress
import re
from datetime import datetime, timezone
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import select, inspect, update
from . import models as m
from .schemas import RESOURCES
from .security import passwords

def fail(message): raise HTTPException(422, message)
def get(db, model, id):
    obj = db.get(model, id)
    if not obj or getattr(obj, 'archived', False): raise HTTPException(404, f'{model.__name__} not found')
    return obj

def serialize(obj):
    result = {}
    for c in inspect(type(obj)).columns:
        if c.name in {'password_hash', 'storage_key'}: continue
        v = getattr(obj, c.name)
        result[c.name] = (v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v.astimezone(timezone.utc)).isoformat() if isinstance(v, datetime) else float(v) if isinstance(v, Decimal) else v
    return result

def audit(db, user, action, resource, obj, old=None):
    db.add(m.AuditLog(user_id=user.id, action=action, object_type=resource, object_id=obj.id, old_value=old, new_value=serialize(obj)))

def master(db, group, code):
    item = db.scalar(select(m.MasterData).where(m.MasterData.group == group, m.MasterData.code == code, m.MasterData.archived == False))
    if not item: fail(f'Missing master data: {group}/{code}')
    return item.id

def next_number(db, prefix):
    key = f'{prefix}-{datetime.now(timezone.utc).year}'
    # Seed creates counters for the current year. An upsert also handles a year rollover.
    dialect = db.bind.dialect.name
    if dialect == 'postgresql':
        from sqlalchemy.dialects.postgresql import insert
    else:
        from sqlalchemy.dialects.sqlite import insert
    db.execute(insert(m.Counter).values(key=key, value=0).on_conflict_do_nothing(index_elements=['key']))
    n = db.scalar(update(m.Counter).where(m.Counter.key == key).values(value=m.Counter.value + 1).returning(m.Counter.value))
    return f'{key}-{n:05d}'

GROUPS = {'assets': {'status_id': 'asset_status'}, 'tickets': {'status_id': 'ticket_status', 'priority_id': 'priority', 'category_id': 'ticket_category'}, 'ip-addresses': {'status_id': 'ip_status'}, 'switch-ports': {'status_id': 'port_status', 'mode_id': 'port_mode'}, 'maintenance': {'status_id': 'maintenance_status', 'type_id': 'maintenance_type'}, 'articles': {'status_id': 'article_status', 'category_id': 'kb_category'}}

def validate(db, resource, data, obj=None):
    def val(k): return data.get(k, getattr(obj, k, None))
    for field, group in GROUPS.get(resource, {}).items():
        value = val(field)
        if value is not None and get(db, m.MasterData, value).group != group: fail(f'{field} must reference {group}')
    model = RESOURCES[resource]
    for c in inspect(model).columns:
        if c.name not in data: continue
        if data[c.name] is None and not c.nullable: fail(f'{c.name} cannot be null')
        for fk in c.foreign_keys:
            if data[c.name] is not None:
                target = next((x for x in RESOURCES.values() if x.__tablename__ == fk.column.table.name), None)
                if target: get(db, target, data[c.name])
    if resource == 'users':
        if val('role') not in {'ADMIN', 'IT_MANAGER', 'IT_SUPPORT', 'VIEWER'}: fail('Invalid role')
        if 'password' in data: data['password_hash'] = passwords.hash(data.pop('password'))
    if resource == 'assets':
        if 'code' in data: data['code'] = data['code'].upper()
        if 'serial' in data: data['serial'] = data['serial'].upper() if data['serial'] else None
        if val('cost') is not None and val('cost') < 0: fail('Cost must be nonnegative')
        if obj and 'type_id' in data and data['type_id'] != obj.type_id: fail('Asset type is immutable after creation; archive and register the correct asset')
        if obj and 'status_id' in data and get(db, m.MasterData, data['status_id']).code in {'retired', 'lost'}:
            if db.scalar(select(m.Assignment).where(m.Assignment.asset_id == obj.id, m.Assignment.returned_at == None)): fail('Return the asset before retiring it')
    if resource == 'master-data' and obj and any(k in data and data[k] != getattr(obj,k) for k in ['group','code']): fail('Master data group and code are stable identifiers; edit the display name instead')
    if resource == 'asset-types' and obj:
        if data.get('allow_assignment') is False and db.scalar(select(m.Assignment.id).join(m.Asset,m.Assignment.asset_id==m.Asset.id).where(m.Asset.type_id==obj.id,m.Assignment.returned_at==None).limit(1)): fail('Return assigned devices before disabling assignments')
    if resource == 'locations':
        if val('kind') not in {'site','area','station'}: fail('Location kind must be site, area or station')
        parent = get(db, m.Location, val('parent_id')) if val('parent_id') else None
        if val('kind') == 'site' and parent: fail('A site cannot have a parent')
        if val('kind') != 'site' and not parent: fail('Area/station requires a parent')
        if parent and (parent.kind == 'station' or val('kind') == 'station' and parent.kind != 'area'): fail('Invalid location hierarchy')
        visited = {obj.id} if obj else set()
        while parent:
            if parent.id in visited: fail('Location hierarchy cannot contain cycles')
            visited.add(parent.id)
            parent = db.get(m.Location, parent.parent_id) if parent.parent_id else None
    if resource in {'interfaces', 'maintenance', 'tickets'} and val('asset_id'):
        asset = get(db, m.Asset, val('asset_id')); at = get(db, m.AssetType, asset.type_id)
        flag = {'interfaces':'track_network','maintenance':'track_maintenance','tickets':'allow_ticket'}[resource]
        if not getattr(at, flag): fail(f'Asset type does not allow {resource}')
    if resource == 'interfaces' and 'mac' in data:
        mac = data['mac'].upper().replace('-', ':')
        if not re.fullmatch(r'(?:[0-9A-F]{2}:){5}[0-9A-F]{2}', mac): fail('Invalid MAC address')
        data['mac'] = mac
    if resource == 'vlans':
        if not 1 <= val('tag') <= 4094: fail('VLAN must be between 1 and 4094')
        if get(db, m.Location, val('site_id')).kind != 'site': fail('Select a site')
    if resource == 'subnets':
        try:
            network = ipaddress.ip_network(val('cidr'), strict=True)
            if val('gateway') and ipaddress.ip_address(val('gateway')) not in network: fail('Gateway must belong to subnet')
            if val('dns'):
                for dns in val('dns').split(','): ipaddress.ip_address(dns.strip())
        except ValueError: fail('Invalid subnet, gateway or DNS')
        data['cidr'] = str(network)
        if get(db,m.VLAN,val('vlan_id')).site_id != val('site_id'): fail('VLAN and subnet must belong to the same site')
        if obj and val('cidr') != obj.cidr:
            for ip in db.scalars(select(m.IPAddress).where(m.IPAddress.subnet_id == obj.id)):
                if ipaddress.ip_address(ip.address) not in network: fail('Existing IP would fall outside the subnet')
    if resource == 'ip-addresses':
        try: address = ipaddress.ip_address(val('address'))
        except ValueError: fail('Invalid IPv4/IPv6 address')
        subnet = get(db, m.Subnet, val('subnet_id'))
        network = ipaddress.ip_network(subnet.cidr)
        if address not in network: fail('IP must belong to selected subnet')
        if network.version == 4 and network.prefixlen < 31 and address in (network.network_address, network.broadcast_address): fail('Network and broadcast addresses cannot be allocated')
        data['address'] = str(address)
        code = get(db, m.MasterData, val('status_id')).code
        if code == 'used' and not val('interface_id'): fail('Used IP requires a network interface')
        if code == 'available' and val('interface_id'): fail('Available IP cannot be assigned')
    if resource == 'switch-ports':
        switch = get(db,m.Asset,val('switch_id'))
        if not get(db,m.AssetType,switch.type_id).has_ports: fail('Selected asset does not have switch ports')
        if val('connected_asset_id') == val('switch_id'): fail('Switch cannot connect to itself')
        for vlan in val('tagged_vlans') or []: get(db,m.VLAN,int(vlan))
    if resource == 'maintenance':
        if val('cost') is not None and val('cost') < 0: fail('Cost must be nonnegative')
        if val('ticket_id') and get(db,m.Ticket,val('ticket_id')).asset_id != val('asset_id'): fail('Maintenance and ticket must reference the same asset')
        if obj and 'asset_id' in data and data['asset_id'] != obj.asset_id: fail('Maintenance asset cannot change')

def activity(db, ticket, user, body, kind='update', internal=False):
    db.add(m.TicketActivity(ticket_id=ticket.id, user_id=user.id, body=body, kind=kind, internal=internal))

def save(db, resource, data, user, obj=None):
    validate(db, resource, data, obj)
    old = serialize(obj) if obj else None
    if not obj:
        if resource in {'tickets','maintenance','articles'}: data['number'] = next_number(db, {'tickets':'INC','maintenance':'MNT','articles':'KB'}[resource])
        if resource == 'tickets': data['reporter_id'] = user.id
        if resource == 'articles': data['author_id'] = user.id
        obj = RESOURCES[resource](**data); db.add(obj)
    else:
        for k,v in data.items(): setattr(obj,k,v)
    db.flush()
    if resource == 'tickets':
        code = get(db,m.MasterData,obj.status_id).code
        obj.resolved_at = (obj.resolved_at or m.now()) if code in {'resolved','closed'} else None
        changes = ', '.join(f'{key}: {old.get(key)} → {serialize(obj).get(key)}' for key in data if key != 'password_hash' and old and old.get(key)!=serialize(obj).get(key))
        activity(db,obj,user,'Ticket created' if old is None else f'Updated {changes}')
    if resource == 'maintenance':
        asset = db.scalar(select(m.Asset).where(m.Asset.id == obj.asset_id).with_for_update())
        before = serialize(asset)
        code = get(db,m.MasterData,obj.status_id).code
        if old is None:
            active = db.scalars(select(m.Maintenance).where(m.Maintenance.asset_id == obj.asset_id, m.Maintenance.id != obj.id, m.Maintenance.end_at == None)).first()
            if active: fail('Asset already has active maintenance')
            obj.previous_status_id = asset.status_id
            asset.status_id = master(db,'asset_status','repair')
        if code in {'completed','cancelled'} and (old is None or old['end_at'] is None):
            obj.end_at = m.now()
            active_assignment=db.scalar(select(m.Assignment.id).where(m.Assignment.asset_id==asset.id,m.Assignment.returned_at==None))
            previous=obj.previous_status_id or master(db,'asset_status','available')
            if active_assignment: asset.status_id=master(db,'asset_status','assigned')
            elif get(db,m.MasterData,previous).code=='assigned': asset.status_id=master(db,'asset_status','available')
            else: asset.status_id=previous
        elif old and old['end_at'] and code not in {'completed','cancelled'}: fail('Completed maintenance cannot be reopened; create a new record')
        if before != serialize(asset): audit(db,user,'maintenance status','assets',asset,before)
    if resource=='maintenance' and obj.ticket_id:
        activity(db,get(db,m.Ticket,obj.ticket_id),user,f"Maintenance {obj.number}: {get(db,m.MasterData,obj.status_id).name}",'maintenance')
    if resource=='ticket-articles' and old is None:
        activity(db,get(db,m.Ticket,obj.ticket_id),user,f"Linked knowledge article {get(db,m.Article,obj.article_id).number}",'knowledge')
    db.flush(); audit(db,user,'created' if old is None else 'updated',resource,obj,old)
    return obj

def lock_asset(db, id):
    asset = db.scalar(select(m.Asset).where(m.Asset.id == id, m.Asset.archived == False).with_for_update())
    if not asset: raise HTTPException(404,'Asset not found')
    return asset

def move(db, id, payload, user):
    asset = lock_asset(db,id)
    if not get(db,m.AssetType,asset.type_id).track_location: fail('Location tracking is disabled')
    get(db,m.Location,payload.location_id)
    current = db.scalar(select(m.LocationHistory).where(m.LocationHistory.asset_id == id,m.LocationHistory.ended_at == None))
    if current and current.location_id == payload.location_id: fail('Asset is already at this location')
    if current: current.ended_at = m.now(); db.flush()
    row = m.LocationHistory(asset_id=id,from_location_id=current.location_id if current else None,technician_id=user.id,**payload.model_dump())
    db.add(row); db.flush(); audit(db,user,'moved','location-history',row)
    return row

def assign(db,id,payload,user):
    asset = lock_asset(db,id)
    if not get(db,m.AssetType,asset.type_id).allow_assignment: fail('This asset type cannot be assigned')
    if get(db,m.MasterData,asset.status_id).code in {'retired','lost','broken','repair','maintenance'}: fail('Asset is not available for assignment')
    get(db,m.User,payload.user_id)
    if db.scalar(select(m.Assignment).where(m.Assignment.asset_id == id,m.Assignment.returned_at == None)): fail('Asset already has an active assignment')
    row = m.Assignment(asset_id=id,assigned_by=user.id,**payload.model_dump())
    before = serialize(asset); asset.status_id = master(db,'asset_status','assigned')
    db.add(row); db.flush(); audit(db,user,'assigned','assignments',row); audit(db,user,'assigned','assets',asset,before)
    return row

def return_asset(db,id,payload,user):
    asset = lock_asset(db,id)
    row = db.scalar(select(m.Assignment).where(m.Assignment.asset_id == id,m.Assignment.returned_at == None))
    if not row: fail('No active assignment')
    old = serialize(row); row.returned_at = m.now(); row.condition_in = payload.condition_in
    if payload.note: row.note = (row.note or '') + '\nReturn: ' + payload.note
    before = serialize(asset)
    if get(db,m.MasterData,asset.status_id).code == 'assigned': asset.status_id = master(db,'asset_status','available')
    db.flush(); audit(db,user,'returned','assignments',row,old); audit(db,user,'returned','assets',asset,before)
    return row
