import ipaddress
import re
import hashlib
from datetime import date, datetime, timezone
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import select, inspect, update
from . import models as m
from .schemas import RESOURCES
from .security import passwords
from .asset_events import snapshot, set_status, emit, normalize_status

def fail(message): raise HTTPException(422, message)
def get(db, model, id):
    obj = db.get(model, id)
    if not obj or getattr(obj, 'archived', False): raise HTTPException(404, f'Không tìm thấy bản ghi ({model.__name__})')
    return obj

def serialize(obj):
    result = {}
    for c in inspect(type(obj)).columns:
        if c.name in {'password_hash', 'storage_key'}: continue
        v = getattr(obj, c.name)
        result[c.name] = (v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v.astimezone(timezone.utc)).isoformat() if isinstance(v, datetime) else v.isoformat() if isinstance(v,date) else float(v) if isinstance(v, Decimal) else v
    return result

def audit(db, user, action, resource, obj, old=None):
    db.add(m.AuditLog(user_id=user.id, action=action, object_type=resource, object_id=obj.id, old_value=old, new_value=serialize(obj)))

def master(db, group, code):
    item = db.scalar(select(m.MasterData).where(m.MasterData.group == group, m.MasterData.code == code, m.MasterData.archived == False))
    if not item: fail(f'Thiếu danh mục: {group}/{code}')
    return item.id

def asset_code(model, serial):
    raw=f'{model}-{serial}'.upper()
    code=re.sub(r'[^A-Z0-9]+','-',raw).strip('-')
    if not code: fail('Model và số sê-ri phải chứa chữ hoặc số')
    if len(code)>40:
        digest=hashlib.sha256(code.encode()).hexdigest()[:8].upper()
        code=f'{code[:31].rstrip("-")}-{digest}'
    return code

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
        if value is not None and get(db, m.MasterData, value).group != group: fail(f'{field} phải thuộc danh mục {group}')
    model = RESOURCES[resource]
    for c in inspect(model).columns:
        if c.name not in data: continue
        if data[c.name] is None and not c.nullable: fail(f'{c.name} không được để trống')
        for fk in c.foreign_keys:
            if data[c.name] is not None:
                target = next((x for x in RESOURCES.values() if x.__tablename__ == fk.column.table.name), None)
                if target: get(db, target, data[c.name])
    if resource == 'users':
        if val('role') not in {'ADMIN', 'IT_MANAGER', 'IT_SUPPORT', 'VIEWER'}: fail('Vai trò không hợp lệ')
        if 'password' in data: data['password_hash'] = passwords.hash(data.pop('password'))
    if resource == 'assets':
        identity_changed='model' in data or 'serial' in data
        model=str(val('model') or '').strip(); serial=str(val('serial') or '').strip().upper()
        if not model: fail('Vui lòng nhập model')
        if not serial: fail('Vui lòng nhập số sê-ri')
        if obj is None and not data.get('name'): data['name']=model
        elif obj and 'model' in data and obj.name==obj.model: data['name']=model
        if obj is None or identity_changed:
            data['model']=model; data['serial']=serial
            if 'code' not in data: data['code']=asset_code(model,serial)
        if val('received_date') and val('handover_date') and val('handover_date') < val('received_date'): fail('Ngày bàn giao không được trước ngày nhập')
        if obj and 'type_id' in data and data['type_id'] != obj.type_id: fail('Không thể thay đổi loại tài sản sau khi tạo')
        if obj and 'status_id' in data and data['status_id']!=obj.status_id: fail('Trạng thái chỉ thay đổi qua thao tác cấp phát, thu hồi, bảo trì hoặc ngừng sử dụng')
    if resource == 'master-data' and obj and any(k in data and data[k] != getattr(obj,k) for k in ['group','code']): fail('Nhóm và mã danh mục là định danh cố định; chỉ được sửa tên hiển thị')
    if resource=='master-data' and val('group')=='asset_status' and val('code') not in {'available','in_use','maintenance','retired'}: fail('Tài sản chỉ có bốn trạng thái: sẵn sàng, đang sử dụng, đang bảo trì và ngừng sử dụng')
    if resource == 'asset-types' and obj:
        if data.get('allow_assignment') is False and db.scalar(select(m.Assignment.id).join(m.Asset,m.Assignment.asset_id==m.Asset.id).where(m.Asset.type_id==obj.id,m.Assignment.returned_at==None).limit(1)): fail('Thu hồi thiết bị đã cấp trước khi tắt quyền cấp phát')
    if resource == 'inventory-items' and obj and 'warehouse_id' in data and data['warehouse_id']!=obj.warehouse_id: fail('Không thể đổi kho của vật tư; cần nhập vật tư tại kho đích')
    if resource == 'warehouses' and obj and 'location_id' in data and data['location_id']!=obj.location_id: fail('Không thể đổi vị trí kho sau khi tạo')
    if resource == 'locations':
        if val('kind') not in {'site','team','station'}: fail('Cấp vị trí phải là cơ sở, bộ phận hoặc trạm')
        parent = get(db, m.Location, val('parent_id')) if val('parent_id') else None
        if val('kind') == 'site' and parent: fail('Cơ sở không có vị trí cấp trên')
        if val('kind') != 'site' and not parent: fail('Bộ phận và trạm phải có vị trí cấp trên')
        if parent and (val('kind') == 'team' and parent.kind != 'site' or val('kind') == 'station' and parent.kind != 'team'): fail('Cấu trúc vị trí phải theo Cơ sở → Bộ phận → Trạm')
        visited = {obj.id} if obj else set()
        while parent:
            if parent.id in visited: fail('Cấu trúc vị trí không được tạo vòng lặp')
            visited.add(parent.id)
            parent = db.get(m.Location, parent.parent_id) if parent.parent_id else None
    if resource in {'interfaces', 'maintenance', 'tickets'} and val('asset_id'):
        asset = get(db, m.Asset, val('asset_id')); at = get(db, m.AssetType, asset.type_id)
        flag = {'interfaces':'track_network','maintenance':'track_maintenance','tickets':'allow_ticket'}[resource]
        if not getattr(at, flag): fail(f'Loại tài sản không hỗ trợ thao tác này ({resource})')
    if resource == 'interfaces' and 'mac' in data:
        mac = data['mac'].upper().replace('-', ':')
        if not re.fullmatch(r'(?:[0-9A-F]{2}:){5}[0-9A-F]{2}', mac): fail('Địa chỉ MAC không hợp lệ')
        data['mac'] = mac
    if resource == 'vlans':
        if not 1 <= val('tag') <= 4094: fail('Mã VLAN phải từ 1 đến 4094')
        if get(db, m.Location, val('site_id')).kind != 'site': fail('Vui lòng chọn cơ sở')
    if resource == 'subnets':
        try:
            network = ipaddress.ip_network(val('cidr'), strict=True)
            if val('gateway') and ipaddress.ip_address(val('gateway')) not in network: fail('Cổng mạng phải thuộc dải mạng')
            if val('dns'):
                for dns in val('dns').split(','): ipaddress.ip_address(dns.strip())
        except ValueError: fail('Dải mạng, cổng mạng hoặc DNS không hợp lệ')
        data['cidr'] = str(network)
        if get(db,m.VLAN,val('vlan_id')).site_id != val('site_id'): fail('VLAN và dải mạng phải thuộc cùng cơ sở')
        if obj and val('cidr') != obj.cidr:
            for ip in db.scalars(select(m.IPAddress).where(m.IPAddress.subnet_id == obj.id)):
                if ipaddress.ip_address(ip.address) not in network: fail('Địa chỉ IP đã có sẽ nằm ngoài dải mạng')
    if resource == 'ip-addresses':
        try: address = ipaddress.ip_address(val('address'))
        except ValueError: fail('Địa chỉ IPv4/IPv6 không hợp lệ')
        subnet = get(db, m.Subnet, val('subnet_id'))
        network = ipaddress.ip_network(subnet.cidr)
        if address not in network: fail('Địa chỉ IP phải thuộc dải mạng đã chọn')
        if network.version == 4 and network.prefixlen < 31 and address in (network.network_address, network.broadcast_address): fail('Không được cấp phát địa chỉ mạng hoặc địa chỉ quảng bá')
        data['address'] = str(address)
        code = get(db, m.MasterData, val('status_id')).code
        if code == 'used' and not val('interface_id'): fail('IP đang sử dụng phải có giao diện mạng')
        if code == 'available' and val('interface_id'): fail('IP sẵn sàng không được gắn giao diện mạng')
    if resource == 'switch-ports':
        switch = get(db,m.Asset,val('switch_id'))
        if not get(db,m.AssetType,switch.type_id).has_ports: fail('Tài sản được chọn không có cổng switch')
        if val('connected_asset_id') == val('switch_id'): fail('Switch không thể kết nối với chính nó')
        for vlan in val('tagged_vlans') or []: get(db,m.VLAN,int(vlan))
    if resource == 'maintenance':
        if val('cost') is not None and val('cost') < 0: fail('Chi phí không được âm')
        if val('ticket_id') and get(db,m.Ticket,val('ticket_id')).asset_id != val('asset_id'): fail('Phiếu bảo trì và phiếu hỗ trợ phải cùng tài sản')
        if obj and 'asset_id' in data and data['asset_id'] != obj.asset_id: fail('Không thể thay đổi tài sản của phiếu bảo trì')

def activity(db, ticket, user, body, kind='update', internal=False):
    db.add(m.TicketActivity(ticket_id=ticket.id, user_id=user.id, body=body, kind=kind, internal=internal))

def operation(db, asset_id, operation_type, user, *, from_entity_type=None, from_entity_id=None,
              to_entity_type=None, to_entity_id=None, condition_before=None,
              condition_after=None, reason=None, note=None):
    row = m.AssetOperation(
        number=next_number(db, 'AOP'), asset_id=asset_id, operation_type=operation_type,
        from_entity_type=from_entity_type, from_entity_id=from_entity_id,
        to_entity_type=to_entity_type, to_entity_id=to_entity_id,
        operation_date=m.now(), condition_before=condition_before,
        condition_after=condition_after, performed_by=user.id, reason=reason, note=note,
    )
    db.add(row)
    db.flush()
    audit(db, user, operation_type.lower(), 'asset-operations', row)
    return row

def save(db, resource, data, user, obj=None, emit_event=True):
    if obj and resource=='assets': obj=lock_asset(db,obj.id)
    state_before=snapshot(db,obj) if obj and resource=='assets' else None
    maintenance_before=None
    if resource=='maintenance':
        target=lock_asset(db,data.get('asset_id',getattr(obj,'asset_id',None)))
        maintenance_before=snapshot(db,target)
    validate(db, resource, data, obj)
    old = serialize(obj) if obj else None
    if not obj:
        if resource in {'tickets','maintenance','articles'}: data['number'] = next_number(db, {'tickets':'INC','maintenance':'MNT','articles':'KB'}[resource])
        if resource == 'tickets': data['reporter_id'] = user.id
        if resource == 'articles': data['author_id'] = user.id
        obj = RESOURCES[resource](**data); db.add(obj)
    else:
        for k,v in data.items(): setattr(obj,k,v)
    if resource=='assets' and old is None:
        set_status(db,obj,'AVAILABLE')
    db.flush()
    if resource == 'tickets':
        code = get(db,m.MasterData,obj.status_id).code
        obj.resolved_at = (obj.resolved_at or m.now()) if code in {'resolved','closed'} else None
        changes = ', '.join(f'{key}: {old.get(key)} → {serialize(obj).get(key)}' for key in data if key != 'password_hash' and old and old.get(key)!=serialize(obj).get(key))
        activity(db,obj,user,'Ticket created' if old is None else f'Updated {changes}')
    if resource == 'maintenance':
        asset=target; code=get(db,m.MasterData,obj.status_id).code
        if old is None:
            if asset.current_status=='RETIRED': fail('Tài sản đã ngừng sử dụng, không thể bảo trì')
            active=db.scalar(select(m.Maintenance).where(m.Maintenance.asset_id==obj.asset_id,m.Maintenance.id!=obj.id,m.Maintenance.end_at==None))
            if active: fail('Tài sản đang có phiếu bảo trì chưa hoàn tất')
            obj.previous_status_id=asset.status_id
            set_status(db,asset,'MAINTENANCE')
        if code in {'completed','cancelled'} and (old is None or old['end_at'] is None):
            obj.end_at=m.now()
            previous=normalize_status(get(db,m.MasterData,obj.previous_status_id).code) if obj.previous_status_id else 'AVAILABLE'
            # A return during maintenance updates previous_status_id to AVAILABLE.
            set_status(db,asset,'IN_USE' if asset.current_assignee_id or previous=='IN_USE' else 'AVAILABLE')
        elif old and old['end_at'] and code not in {'completed','cancelled'}:
            fail('Phiếu bảo trì đã kết thúc; vui lòng tạo phiếu mới')
        if old is None or any(old.get(k)!=serialize(obj).get(k) for k in data):
            emit(db,asset,'MAINTENANCE',user,maintenance_before,
                 description=('Hoàn tất bảo trì' if code=='completed' else 'Hủy bảo trì' if code=='cancelled' else 'Bảo trì: '+obj.problem),
                 source_ref='maintenance:'+str(obj.id)+':'+str(m.now().timestamp()),
                 extra_before={'maintenance':{'status':get(db,m.MasterData,old['status_id']).name,'problem':old.get('problem'),'action_taken':old.get('action_taken')}} if old else {},
                 extra_after={'maintenance':{'id':obj.id,'number':obj.number,'status':get(db,m.MasterData,obj.status_id).name,'problem':obj.problem,'action_taken':obj.action_taken}})
    if resource=='maintenance' and obj.ticket_id:
        activity(db,get(db,m.Ticket,obj.ticket_id),user,f"Maintenance {obj.number}: {get(db,m.MasterData,obj.status_id).name}",'maintenance')
    if resource=='ticket-articles' and old is None:
        activity(db,get(db,m.Ticket,obj.ticket_id),user,f"Linked knowledge article {get(db,m.Article,obj.article_id).number}",'knowledge')
    db.flush(); audit(db,user,'created' if old is None else 'updated',resource,obj,old)
    if resource=='assets' and emit_event:
        emit(db,obj,'RECEIVED' if old is None else 'UPDATED',user,state_before,description='Nhập tài sản' if old is None else 'Cập nhật thông tin tài sản')
    return obj

def lock_asset(db, id):
    asset = db.scalar(select(m.Asset).where(m.Asset.id == id, m.Asset.archived == False).with_for_update())
    if not asset: raise HTTPException(404,'Không tìm thấy tài sản')
    return asset

def move(db, id, payload, user, warehouse_flow=False):
    asset=lock_asset(db,id); before=snapshot(db,asset)
    if asset.current_status=='RETIRED': fail('Tài sản đã ngừng sử dụng, không thể điều chuyển')
    if asset.warehouse_id and not warehouse_flow: fail('Vui lòng xuất kho trước khi điều chuyển')
    if not warehouse_flow and not get(db,m.AssetType,asset.type_id).track_location: fail('Loại tài sản không theo dõi vị trí')
    destination=get(db,m.Location,payload.location_id)
    if not destination.active: fail('Vị trí không hoạt động')
    if not warehouse_flow and db.scalar(select(m.Warehouse.id).where(m.Warehouse.location_id==destination.id,m.Warehouse.archived==False)): fail('Sử dụng thao tác nhập kho để thu hồi vào kho')
    current=db.scalar(select(m.LocationHistory).where(m.LocationHistory.asset_id==id,m.LocationHistory.ended_at==None))
    if asset.current_location_id==destination.id: fail('Tài sản đã ở vị trí này')
    previous=asset.current_location_id
    if current: current.ended_at=m.now(); db.flush()
    row=m.LocationHistory(asset_id=id,from_location_id=previous,technician_id=user.id,**payload.model_dump())
    asset.current_location_id=destination.id
    db.add(row); db.flush(); audit(db,user,'moved','location-history',row)
    if not warehouse_flow: emit(db,asset,'MOVED',user,before,description=payload.reason)
    return row

def assign(db,id,payload,user,warehouse_flow=False):
    asset=lock_asset(db,id); before=snapshot(db,asset)
    if asset.current_status not in {'AVAILABLE','IN_USE'}: fail('Tài sản không sẵn sàng để cấp phát')
    if db.scalar(select(m.Maintenance.id).where(m.Maintenance.asset_id==id,m.Maintenance.end_at==None)): fail('Hoàn tất bảo trì trước khi cấp phát')
    if asset.warehouse_id and not warehouse_flow: fail('Sử dụng thao tác xuất kho để cấp phát')
    if not get(db,m.AssetType,asset.type_id).allow_assignment: fail('Loại tài sản không cho phép cấp cho người dùng')
    get(db,m.User,payload.user_id)
    if asset.current_assignee_id: fail('Tài sản đã có người chịu trách nhiệm; sử dụng Chuyển người phụ trách')
    row=m.Assignment(asset_id=id,assigned_by=user.id,**payload.model_dump())
    asset.current_assignee_id=payload.user_id; asset.handover_date=m.now().date(); set_status(db,asset,'IN_USE')
    db.add(row); db.flush(); audit(db,user,'assigned','assignments',row)
    if not warehouse_flow: emit(db,asset,'ISSUED',user,before,description=payload.note or payload.condition_out)
    return row

def return_asset(db,id,payload,user,warehouse_flow=False):
    asset=lock_asset(db,id); before=snapshot(db,asset)
    if asset.current_status=='RETIRED': fail('Tài sản đã ngừng sử dụng')
    row=db.scalar(select(m.Assignment).where(m.Assignment.asset_id==id,m.Assignment.returned_at==None))
    if not row and asset.current_status!='IN_USE': fail('Tài sản chưa được cấp phát')
    if row:
        old=serialize(row); row.returned_at=m.now(); row.condition_in=payload.condition_in
        if payload.note: row.note=(row.note or '')+'\nThu hồi: '+payload.note
        audit(db,user,'returned','assignments',row,old)
    asset.current_assignee_id=None; set_status(db,asset,'AVAILABLE')
    active=db.scalar(select(m.Maintenance).where(m.Maintenance.asset_id==id,m.Maintenance.end_at==None))
    if active: active.previous_status_id=master(db,'asset_status','available')
    db.flush()
    if not warehouse_flow: emit(db,asset,'RETURNED',user,before,description=payload.note or payload.condition_in)
    return row or asset

def reassign_asset(db,id,payload,user):
    asset=lock_asset(db,id); before=snapshot(db,asset)
    if asset.current_status!='IN_USE' or not asset.current_assignee_id: fail('Chỉ chuyển người phụ trách khi tài sản đang được sử dụng và đã có người nhận')
    if payload.user_id==asset.current_assignee_id: fail('Vui lòng chọn người phụ trách khác')
    get(db,m.User,payload.user_id)
    old=db.scalar(select(m.Assignment).where(m.Assignment.asset_id==id,m.Assignment.returned_at==None))
    if not old: fail('Không tìm thấy bản ghi cấp phát hiện tại')
    previous=serialize(old); old.returned_at=m.now(); old.condition_in='Chuyển người chịu trách nhiệm'
    db.flush(); audit(db,user,'reassigned','assignments',old,previous)
    row=m.Assignment(asset_id=id,user_id=payload.user_id,assigned_by=user.id,department=get(db,m.User,payload.user_id).department,condition_out=old.condition_out,note=payload.note)
    db.add(row); asset.current_assignee_id=payload.user_id; set_status(db,asset,'IN_USE'); db.flush()
    audit(db,user,'reassigned','assignments',row)
    emit(db,asset,'REASSIGNED',user,before,description=payload.reason)
    return row

def retire_asset(db,id,payload,user):
    asset=lock_asset(db,id); before=snapshot(db,asset)
    if asset.current_status=='RETIRED': fail('Tài sản đã ngừng sử dụng')
    if asset.current_assignee_id: fail('Thu hồi tài sản trước khi ngừng sử dụng')
    if db.scalar(select(m.Maintenance.id).where(m.Maintenance.asset_id==id,m.Maintenance.end_at==None)): fail('Hoàn tất bảo trì trước khi ngừng sử dụng')
    set_status(db,asset,'RETIRED'); asset.warehouse_id=None; asset.current_location_id=None; asset.current_assignee_id=None
    current=db.scalar(select(m.LocationHistory).where(m.LocationHistory.asset_id==id,m.LocationHistory.ended_at==None))
    if current: current.ended_at=m.now()
    emit(db,asset,'RETIRED',user,before,description=payload.reason)
    return asset
