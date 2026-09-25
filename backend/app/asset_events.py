"""Canonical current state and one durable business event per asset operation."""
from sqlalchemy import select
from . import models as m

EVENT_TYPES={'RECEIVED','ISSUED','RETURNED','MOVED','REASSIGNED','MAINTENANCE','RETIRED','UPDATED'}
STATUS_CODES={'AVAILABLE':'available','IN_USE':'in_use','MAINTENANCE':'maintenance','RETIRED':'retired'}
EVENT_LABELS={'RECEIVED':'Nhập tài sản','ISSUED':'Cấp phát','RETURNED':'Thu hồi','MOVED':'Điều chuyển vị trí','REASSIGNED':'Chuyển người chịu trách nhiệm','MAINTENANCE':'Sửa chữa / bảo trì','RETIRED':'Ngừng sử dụng','UPDATED':'Cập nhật thông tin'}
STATUS_LABELS={'AVAILABLE':'Sẵn sàng','IN_USE':'Đang sử dụng','MAINTENANCE':'Đang bảo trì','RETIRED':'Ngừng sử dụng'}
IMPORTANT_FIELDS=('code','type_id','brand','model','serial','received_date','description')

def normalize_status(code):
    return {'assigned':'IN_USE','active':'IN_USE','in_use':'IN_USE','repair':'MAINTENANCE','broken':'MAINTENANCE','maintenance':'MAINTENANCE','retired':'RETIRED','lost':'RETIRED'}.get(str(code).lower(),'AVAILABLE')

def set_status(db,asset,status):
    from .services import master
    asset.current_status=status
    asset.status_id=master(db,'asset_status',STATUS_CODES[status])

def location_name(db,id):
    names=[]; seen=set()
    while id and id not in seen:
        seen.add(id); row=db.get(m.Location,id)
        if not row: break
        names.insert(0,row.name); id=row.parent_id
    return ' › '.join(names)

def snapshot(db,asset):
    from .services import serialize
    values=serialize(asset); user=db.get(m.User,asset.current_assignee_id) if asset.current_assignee_id else None
    return {**{key:values.get(key) for key in IMPORTANT_FIELDS},'current_status':asset.current_status,
            'current_location':{'id':asset.current_location_id,'name':location_name(db,asset.current_location_id)} if asset.current_location_id else None,
            'current_assignee':{'id':asset.current_assignee_id,'name':user.name if user else None} if asset.current_assignee_id else None}

def emit(db,asset,event_type,user,before,*,description=None,when=None,source_ref=None,extra_before=None,extra_after=None):
    from .services import next_number, audit
    assert event_type in EVENT_TYPES
    after=snapshot(db,asset)
    if event_type=='UPDATED' and before==after: return None
    old={**(before or {}),**(extra_before or {})}; new={**after,**(extra_after or {})}
    row=m.AssetOperation(number=next_number(db,'AOP'),asset_id=asset.id,operation_type=event_type,performed_by=user.id,reason=description)
    db.add(row)
    row.before_state=old; row.after_state=new; row.source_ref=source_ref
    if event_type=='REASSIGNED':
        row.from_entity_type='USER'; row.from_entity_id=(old.get('current_assignee') or {}).get('id')
        row.to_entity_type='USER'; row.to_entity_id=(new.get('current_assignee') or {}).get('id')
    if when: row.operation_date=when
    db.flush()
    audit(db,user,event_type.lower(),'asset-operations',row)
    return row
