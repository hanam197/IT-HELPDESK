"""Read canonical business events; audit and implementation rows are not timeline events."""
from datetime import timezone
from sqlalchemy import select
from . import models as m
from .asset_events import EVENT_TYPES, EVENT_LABELS, STATUS_LABELS


def asset_lifecycle(db,asset,data,enrich):
    rows=db.scalars(select(m.AssetOperation).where(m.AssetOperation.asset_id==asset.id,m.AssetOperation.operation_type.in_(EVENT_TYPES)).order_by(m.AssetOperation.operation_date.desc(),m.AssetOperation.id.desc())).all()
    events=[]
    for row in rows:
        before=row.before_state or {}; after=row.after_state or {}
        def display(key,value):
            if key=='current_status': return STATUS_LABELS.get(value,value)
            if isinstance(value,dict) and 'name' in value: return value['name']
            return value
        changes=[{'field':key,'before':display(key,before.get(key)),'after':display(key,after.get(key))} for key in dict.fromkeys([*before,*after]) if key!='actor_unknown' and before.get(key)!=after.get(key)]
        actor=db.get(m.User,row.performed_by)
        events.append({'id':row.id,'reference':row.number,'event_type':row.operation_type,'category':row.operation_type,'title':EVENT_LABELS[row.operation_type],
                       'occurred_at':(row.operation_date.replace(tzinfo=timezone.utc) if row.operation_date.tzinfo is None else row.operation_date).isoformat(),'performed_by':actor.name if actor and not after.get('actor_unknown') else None,'description':row.reason or row.note,
                       'before_state':before,'after_state':after,'changes':changes,
                       'resource':'maintenance' if 'maintenance' in after else None,'record_id':(after.get('maintenance') or {}).get('id')})
    data['lifecycle']=events
    received=[e for e in events if e['event_type']=='RECEIVED']; issued=[e for e in events if e['event_type'] in {'ISSUED','REASSIGNED'}]
    data['received_by']=received[-1]['performed_by'] if received else None
    data['handed_over_by']=issued[0]['performed_by'] if issued else None
