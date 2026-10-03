import ipaddress
import re
import hashlib
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import select, inspect, update
from . import models as m
from .schemas import RESOURCES
from .security import passwords
from .asset_events import snapshot, set_status, emit, normalize_status, STATUS_CODES, TERMINAL_STATUSES

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

ISSUE_CATEGORIES={'hardware','network','software','power','peripheral','other'}
MAINTENANCE_STATES={'open','completed'}

def utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)

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
        if val('status_id') is None or get(db,m.MasterData,val('status_id')).code not in STATUS_CODES.values(): fail('Chọn một trong 5 trạng thái tài sản hợp lệ')
        if obj and 'status_id' in data and data['status_id']!=obj.status_id: fail('Trạng thái chỉ thay đổi qua thao tác cấp phát, thu hồi, bảo trì, ngừng sử dụng hoặc thanh lý')
    if resource == 'master-data' and obj and any(k in data and data[k] != getattr(obj,k) for k in ['group','code']): fail('Nhóm và mã danh mục là định danh cố định; chỉ được sửa tên hiển thị')
    if resource=='master-data' and val('group')=='asset_status' and val('code') not in STATUS_CODES.values(): fail('Tài sản chỉ có 5 trạng thái: AVAILABLE, IN_USE, MAINTENANCE, RETIRED, DISPOSED')
    if resource=='master-data' and val('group')=='maintenance_type' and val('code') not in ISSUE_CATEGORIES: fail('Nhóm vấn đề chỉ gồm Phần cứng, Mạng, Phần mềm, Nguồn điện, Thiết bị ngoại vi, Khác')
    if resource=='master-data' and val('group')=='maintenance_status' and val('code') not in MAINTENANCE_STATES: fail('Trạng thái xử lý không hợp lệ')
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
        if obj and obj.end_at: fail('Phiếu đã hoàn tất, không được chỉnh sửa')
        parts=val('replacement_asset_ids') or []
        if len(parts)!=len(set(parts)): fail('Linh kiện không được trùng lặp')
        previous=set(obj.replacement_asset_ids or []) if obj else set()
        if previous-set(parts): fail('Linh kiện đã xuất kho không thể xóa khỏi phiếu; dùng thao tác thu hồi kho nếu cần trả lại')
        for part_id in sorted(set(parts)-previous):
            part=get(db,m.Asset,part_id)
            kind=get(db,m.AssetType,part.type_id)
            if part.id==val('asset_id') or kind.name.strip().casefold() not in {'linh kiện','component','components'}:
                fail('Chỉ chọn tài sản có loại Linh kiện')
            if not part.warehouse_id or part.current_status!='AVAILABLE':
                fail('Linh kiện phải sẵn sàng trong kho')
        if val('cost') is not None and (not Decimal(str(val('cost'))).is_finite() or val('cost') < 0): fail('Chi phí phải là số không âm')
        if get(db,m.MasterData,val('type_id')).code not in ISSUE_CATEGORIES: fail('Nhóm vấn đề không hợp lệ')
        status=get(db,m.MasterData,val('status_id')).code
        if status not in MAINTENANCE_STATES: fail('Trạng thái xử lý không hợp lệ')
        if status=='completed':
            if val('resolution_outcome') not in {'FIXED','UNREPAIRABLE'}: fail('Vui lòng chọn kết quả xử lý')
            if not (val('diagnosis') or '').strip() or not (val('action_taken') or '').strip(): fail('Vui lòng nhập nguyên nhân và cách xử lý trước khi hoàn tất')
            if not get(db,m.Asset,val('asset_id')).current_location_id: fail('Thiết bị phải có vị trí trước khi hoàn tất')
        start=val('start_at') or m.now(); end=val('end_at')
        if utc(start)>m.now(): fail('Thời gian bắt đầu không được ở tương lai')
        if end:
            if status not in {'completed'}: fail('Chỉ nhập thời gian kết thúc khi đã hoàn tất')
            if utc(end)<utc(start): fail('Thời gian kết thúc không được trước thời gian bắt đầu')
            if utc(end)>m.now(): fail('Thời gian kết thúc không được ở tương lai')
        if obj and obj.end_at and status not in {'completed'}: fail('Phiếu bảo trì đã kết thúc; vui lòng tạo phiếu mới')
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
        if 'estimate_hours' in data:
            hours=data.pop('estimate_hours')
            if 'due_at' in data: fail('Chỉ truyền số giờ dự kiến hoặc thời điểm dự kiến')
            start=data.get('start_at') or (obj.start_at if obj else m.now())
            if not obj: data.setdefault('start_at',start)
            try: data['due_at']=utc(start)+timedelta(hours=hours) if hours is not None else None
            except (OverflowError,ValueError): fail('Số giờ dự kiến không hợp lệ')
        target_id=data.get('asset_id',getattr(obj,'asset_id',None))
        locked={}
        for asset_id in sorted({target_id,*(data.get('replacement_asset_ids') or [])}):
            locked[asset_id]=lock_asset(db,asset_id)
            db.refresh(locked[asset_id])
        target=locked[target_id]
        if obj: db.refresh(obj)
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
        set_status(db,obj,normalize_status(get(db,m.MasterData,obj.status_id).code),initial=True)
    db.flush()
    if resource == 'tickets':
        code = get(db,m.MasterData,obj.status_id).code
        obj.resolved_at = (obj.resolved_at or m.now()) if code in {'resolved','closed'} else None
        changes = ', '.join(f'{key}: {old.get(key)} → {serialize(obj).get(key)}' for key in data if key != 'password_hash' and old and old.get(key)!=serialize(obj).get(key))
        activity(db,obj,user,'Ticket created' if old is None else f'Updated {changes}')
    if resource == 'maintenance':
        asset=target; code=get(db,m.MasterData,obj.status_id).code
        if old is None:
            if asset.current_status in TERMINAL_STATUSES: fail('Tài sản đã ngừng sử dụng hoặc thanh lý, không thể ghi nhận vấn đề mới')
            active=db.scalar(select(m.Maintenance.id).where(m.Maintenance.asset_id==obj.asset_id,m.Maintenance.id!=obj.id,m.Maintenance.end_at==None))
            if active: fail('Tài sản đang có phiếu xử lý chưa hoàn tất; vui lòng cập nhật phiếu hiện tại')
            # Logging an issue never changes the operational state or custody.
        from .warehouse import issue_maintenance_parts
        issue_maintenance_parts(db,obj,asset,set(obj.replacement_asset_ids or [])-set((old or {}).get('replacement_asset_ids') or []),user)
        if code in {'completed'}:
            obj.end_at=obj.end_at or m.now()
            finish_maintenance_asset(db,asset,obj.resolution_outcome,user,obj.end_at)
        if old is None or old!=serialize(obj):
            emit(db,asset,'MAINTENANCE',user,maintenance_before,
                 description=('Hoàn tất bảo trì nhanh: ' if code=='completed' else 'Ghi nhận vấn đề: ')+obj.problem if old is None else 'Hoàn tất xử lý' if code=='completed' and not old['end_at'] else 'Cập nhật xử lý: '+obj.problem,
                 extra_before={'maintenance':maintenance_snapshot(db,old)} if old else {},
                 extra_after={'maintenance':maintenance_snapshot(db,obj)})
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
    if asset.current_status=='DISPOSED' and not warehouse_flow: fail('Thiết bị đã thanh lý, không thể điều chuyển')
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
    if asset.warehouse_id and not warehouse_flow: fail('Sử dụng thao tác xuất kho để cấp phát')
    if not asset.current_location_id: fail('Thiết bị phải có vị trí trước khi cấp phát')
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
    if asset.current_status in TERMINAL_STATUSES: fail('Tài sản đã ngừng sử dụng hoặc thanh lý')
    row=db.scalar(select(m.Assignment).where(m.Assignment.asset_id==id,m.Assignment.returned_at==None))
    if not row and asset.current_status!='IN_USE': fail('Tài sản chưa được cấp phát')
    if row:
        old=serialize(row); row.returned_at=m.now(); row.condition_in=payload.condition_in
        if payload.note: row.note=(row.note or '')+'\nThu hồi: '+payload.note
        audit(db,user,'returned','assignments',row,old)
    asset.current_assignee_id=None
    if not warehouse_flow: set_status(db,asset,'AVAILABLE')
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


def maintenance_snapshot(db,record):
    data=record if isinstance(record,dict) else serialize(record)
    result={key:data.get(key) for key in ('id','number','problem','diagnosis','action_taken','start_at','due_at','end_at','parts_replaced','replacement_asset_ids','resolution_outcome','vendor','cost','note')}
    for source,target in [('type_id','issue_category'),('status_id','status'),('technician_id','technician')]:
        row=db.get(m.User if source=='technician_id' else m.MasterData,data.get(source))
        result[target]=row.name if row else None
    return result


def stop_asset_for_maintenance(db,id,user):
    record=get(db,m.Maintenance,id); asset=lock_asset(db,record.asset_id); db.refresh(record)
    if record.end_at: fail('Phiếu xử lý đã kết thúc')
    if asset.current_status not in {'IN_USE','AVAILABLE'}: fail('Chỉ dừng thiết bị đang sử dụng hoặc sẵn sàng')
    before=snapshot(db,asset); old=serialize(record); old_asset=serialize(asset)
    record.previous_status_id=asset.status_id
    set_status(db,asset,'MAINTENANCE')
    # Station, assignment and warehouse custody deliberately remain unchanged.
    audit(db,user,'updated','maintenance',record,old); audit(db,user,'maintenance','assets',asset,old_asset)
    emit(db,asset,'MAINTENANCE',user,before,description='Dừng thiết bị để sửa: '+record.problem,
         extra_before={'maintenance':maintenance_snapshot(db,old)},extra_after={'maintenance':maintenance_snapshot(db,record)})
    return record


def close_maintenance_for_operation(db,asset,user,when,completed,note):
    record=db.scalar(select(m.Maintenance).where(m.Maintenance.asset_id==asset.id,m.Maintenance.end_at==None))
    if not record: return None,None
    if utc(when)<utc(record.start_at): fail('Thời gian thao tác không được trước thời gian ghi nhận vấn đề')
    before=maintenance_snapshot(db,record); old=serialize(record)
    record.end_at=when; record.status_id=master(db,'maintenance_status','completed')
    record.resolution_outcome='FIXED' if completed else 'UNREPAIRABLE'
    record.note='\n'.join(filter(None,[record.note,note]))
    audit(db,user,'updated','maintenance',record,old)
    return before,maintenance_snapshot(db,record)

def retire_asset(db,id,payload,user):
    asset=lock_asset(db,id); before=snapshot(db,asset); old=serialize(asset)
    if asset.current_status in TERMINAL_STATUSES: fail('Tài sản đã ngừng sử dụng hoặc thanh lý')
    when=m.now()
    assignment=db.scalar(select(m.Assignment).where(m.Assignment.asset_id==id,m.Assignment.returned_at==None))
    if assignment:
        previous=serialize(assignment); assignment.returned_at=when; assignment.condition_in='Ngừng sử dụng'
        audit(db,user,'returned','assignments',assignment,previous)
    repair_before,repair_after=close_maintenance_for_operation(db,asset,user,when,False,'Không tiếp tục sử dụng: '+payload.reason)
    if not asset.current_location_id: fail('Thiết bị phải có vị trí trước khi đánh dấu Hư / Ngừng sử dụng')
    set_status(db,asset,'RETIRED'); asset.current_assignee_id=None
    audit(db,user,'retired','assets',asset,old)
    emit(db,asset,'RETIRED',user,before,description=payload.reason,when=when,extra_before={'maintenance':repair_before} if repair_before else None,extra_after={'maintenance':repair_after} if repair_after else None)
    return asset


def dispose_asset(db,id,payload,user):
    asset=lock_asset(db,id); before=snapshot(db,asset); old=serialize(asset)
    if asset.current_status!='RETIRED': fail('Chỉ thanh lý thiết bị Hư / Ngừng sử dụng')
    if not asset.current_location_id: fail('Thiết bị phải có vị trí trước khi thanh lý')
    set_status(db,asset,'DISPOSED'); asset.warehouse_id=None; asset.current_location_id=None; asset.current_assignee_id=None
    current=db.scalar(select(m.LocationHistory).where(m.LocationHistory.asset_id==id,m.LocationHistory.ended_at==None))
    if current: current.ended_at=m.now()
    audit(db,user,'disposed','assets',asset,old)
    emit(db,asset,'DISPOSED',user,before,description=payload.reason)
    return asset


def finish_maintenance_asset(db,asset,outcome,user,when):
    if asset.current_status in TERMINAL_STATUSES: fail('Thiết bị đã ngừng sử dụng hoặc thanh lý; không thể hoàn tất bảo trì lần nữa')
    if not asset.current_location_id: fail('Thiết bị phải có vị trí trước khi hoàn tất')
    old=serialize(asset)
    assignment=db.scalar(select(m.Assignment).where(m.Assignment.asset_id==asset.id,m.Assignment.returned_at==None))
    if assignment:
        # Custody closes now; a backdated repair end must not predate the assignment.
        previous=serialize(assignment); assignment.returned_at=m.now()
        assignment.condition_in='Đã khắc phục' if outcome=='FIXED' else 'Không khắc phục được'
        audit(db,user,'returned','assignments',assignment,previous)
    asset.current_assignee_id=None
    set_status(db,asset,'AVAILABLE' if outcome=='FIXED' else 'RETIRED')
    audit(db,user,'maintenance-completed','assets',asset,old)
