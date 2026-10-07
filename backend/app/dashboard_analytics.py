"""Daily business activity, using Vietnam dates and complete event history."""
from collections import Counter
from datetime import datetime, time, timedelta, timezone
from sqlalchemy import select
from . import models as m
from .asset_events import EVENT_TYPES

VN=timezone(timedelta(hours=7))

def activity_analytics(db,days=30,now=None):
    today=(now or datetime.now(timezone.utc)).astimezone(VN).date()
    first=today-timedelta(days=days-1)
    previous=first-timedelta(days=days)
    start=datetime.combine(previous,time.min,VN).astimezone(timezone.utc)
    end=datetime.combine(today+timedelta(days=1),time.min,VN).astimezone(timezone.utc)
    buckets={first+timedelta(days=index):Counter() for index in range(days)}
    counts=Counter(); previous_total=0
    events=db.execute(select(m.AssetOperation.operation_date,m.AssetOperation.operation_type).where(m.AssetOperation.operation_date>=start,m.AssetOperation.operation_date<end,m.AssetOperation.operation_type.in_(EVENT_TYPES)))
    for when,kind in events:
        local=(when.replace(tzinfo=timezone.utc) if when.tzinfo is None else when).astimezone(VN).date()
        if local<first: previous_total+=1
        elif local in buckets:
            buckets[local][kind]+=1;counts[kind]+=1
    return {'days':days,'from':first.isoformat(),'to':today.isoformat(),'timezone':'Asia/Ho_Chi_Minh','total':sum(counts.values()),'previous_total':previous_total,'events':dict(counts),'daily':[{'date':day.isoformat(),'total':sum(values.values()),'received':values['RECEIVED'],'issued':values['ISSUED'],'returned':values['RETURNED'],'other':sum(values.values())-values['RECEIVED']-values['ISSUED']-values['RETURNED']} for day,values in buckets.items()]}
