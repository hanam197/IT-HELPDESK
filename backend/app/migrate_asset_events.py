"""One-time conversion of legacy records; original operation/audit rows remain intact."""
from copy import deepcopy
from datetime import timezone
from sqlalchemy import select
from . import models as m
from .asset_events import EVENT_TYPES, STATUS_CODES, normalize_status, location_name


def upgrade_data(db):
    statuses={r.code:r for r in db.scalars(select(m.MasterData).where(m.MasterData.group=='asset_status'))}
    for status,code in STATUS_CODES.items():
        if code not in statuses:
            row=m.MasterData(group='asset_status',code=code,name={'AVAILABLE':'Available','IN_USE':'In Use','MAINTENANCE':'Maintenance','RETIRED':'Retired'}[status]);db.add(row);db.flush();statuses[code]=row
    codes={r.id:normalize_status(r.code) for r in statuses.values()}
    def loc(id): return {'id':id,'name':location_name(db,id)} if id else None
    def person(id):
        row=db.get(m.User,id) if id else None
        return {'id':id,'name':row.name if row else None} if id else None
    def utc(dt): return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    def nearby(a,b): return abs((utc(a)-utc(b)).total_seconds())<1
    for asset in db.scalars(select(m.Asset)):
        locations=list(db.scalars(select(m.LocationHistory).where(m.LocationHistory.asset_id==asset.id)))
        assignments=list(db.scalars(select(m.Assignment).where(m.Assignment.asset_id==asset.id)))
        current_loc=next((r for r in locations if r.ended_at is None),None)
        current_ass=next((r for r in assignments if r.returned_at is None),None)
        asset.current_location_id=current_loc.location_id if current_loc else None
        asset.current_assignee_id=current_ass.user_id if current_ass else None
        asset.current_status=codes.get(asset.status_id,'AVAILABLE')
        if asset.current_assignee_id and asset.current_status not in {'MAINTENANCE','RETIRED'}: asset.current_status='IN_USE'
        asset.status_id=statuses[STATUS_CODES[asset.current_status]].id
        if db.scalar(select(m.AssetOperation.id).where(m.AssetOperation.asset_id==asset.id,m.AssetOperation.operation_type.in_(EVENT_TYPES))): continue
        stock=list(db.scalars(select(m.InventoryTransaction).where(m.InventoryTransaction.asset_id==asset.id).order_by(m.InventoryTransaction.transaction_date,m.InventoryTransaction.id)))
        ops=list(db.scalars(select(m.AssetOperation).where(m.AssetOperation.asset_id==asset.id).order_by(m.AssetOperation.id)))
        audits=list(db.scalars(select(m.AuditLog).order_by(m.AuditLog.id)))
        related=[a for a in audits if (a.object_type=='assets' and a.object_id==asset.id) or (a.new_value or {}).get('asset_id')==asset.id]
        actor=next((a.user_id for a in related if a.user_id),None) or next((o.performed_by for o in ops),None) or db.scalar(select(m.User.id).order_by(m.User.id))
        if not actor: continue
        candidates=[]
        def add(source,kind,when,user,delta,description='',extra=None): candidates.append((utc(when),source,kind,user or actor,delta,description,{**(extra or {}),**({'actor_unknown':True} if not user else {})}))
        first_receipt=next((r for r in stock if r.transaction_type=='RECEIVE'),None)
        registered=next((a for a in related if a.object_type=='assets' and a.action=='created'),None)
        initial=(registered.new_value if registered else None) or {k:getattr(asset,k) for k in ('code','model','serial','brand','description')}
        if not first_receipt or not nearby(first_receipt.created_at,asset.created_at):
            add('asset:'+str(asset.id),'RECEIVED',asset.created_at,registered.user_id if registered else None,{'current_status':'AVAILABLE','current_location':None,'current_assignee':None},'Bản ghi nhập tài sản từ dữ liệu cũ')
        for r in stock:
            issue=r.transaction_type=='ISSUE'; first=r is first_receipt and nearby(r.created_at,asset.created_at)
            warehouse=db.get(m.Warehouse,r.warehouse_id)
            delta={'current_status':'IN_USE' if issue else 'AVAILABLE','current_location':loc(r.recipient_location_id) if issue else loc(warehouse.location_id),'current_assignee':person(r.recipient_user_id) if issue else None}
            add('stock:'+str(r.id),'ISSUED' if issue else 'RECEIVED' if first else 'RETURNED',r.transaction_date,r.performed_by,delta,' · '.join(filter(None,[warehouse.name,r.condition,r.note])))
        skip=set()
        for i,o in enumerate(ops):
            if o.id in skip: continue
            if o.operation_type in {'RECEIVE','ISSUE'} and o.to_entity_type=='WAREHOUSE': continue
            # Internal location and assignment rows from a warehouse command are one stock event.
            if o.reason in {'Warehouse receipt','Warehouse issue','Warehouse return'}: continue
            if any(nearby(o.created_at,r.created_at) and (o.operation_type in {'ISSUE','RECEIVE'} or o.operation_type=='ASSIGN' and o.to_entity_id==r.recipient_user_id or o.operation_type=='RETURN' and r.transaction_type=='RECEIVE') for r in stock): continue
            kind={'ASSIGN':'ISSUED','RETURN':'RETURNED','RETIRE':'RETIRED','TRANSFER':'MOVED','RECEIVE':'MOVED'}.get(o.operation_type)
            if not kind: continue
            delta={}
            if kind=='MOVED': delta['current_location']=loc(o.to_entity_id)
            if kind=='ISSUED': delta.update(current_status='IN_USE',current_assignee=person(o.to_entity_id))
            if kind=='RETURNED': delta.update(current_status='AVAILABLE',current_assignee=None)
            if kind=='RETIRED': delta.update(current_status='RETIRED',current_location=None,current_assignee=None)
            add('op:'+str(o.id),kind,o.operation_date,o.performed_by,delta,o.reason or o.note or '')
        # Older versions wrote only assignment/location records, without operation rows.
        # Match by both destination/assignee and time to avoid duplicating newer operations.
        for r in sorted(locations,key=lambda r:r.created_at):
            if r.reason in {'Warehouse receipt','Warehouse issue','Warehouse return'}: continue
            if any(o.to_entity_type=='LOCATION' and o.to_entity_id==r.location_id and nearby(o.created_at,r.created_at) and o.reason==r.reason for o in ops): continue
            initial_use=r.from_location_id is None and codes.get(initial.get('status_id'))=='IN_USE'
            delta={'current_location':loc(r.location_id)}
            if initial_use: delta['current_status']='IN_USE'
            add('location:'+str(r.id),'ISSUED' if initial_use else 'MOVED',r.created_at,r.technician_id,delta,r.reason or 'Vị trí từ dữ liệu cũ')
        for r in assignments:
            if not any(o.operation_type=='ASSIGN' and o.to_entity_id==r.user_id and nearby(o.created_at,r.created_at) for o in ops) and not any(t.transaction_type=='ISSUE' and t.recipient_user_id==r.user_id and nearby(t.created_at,r.created_at) for t in stock):
                add('assignment:'+str(r.id),'ISSUED',r.created_at,r.assigned_by,{'current_status':'IN_USE','current_assignee':person(r.user_id)},r.note or r.condition_out)
            if r.returned_at and not any(o.operation_type=='RETURN' and nearby(o.created_at,r.returned_at) for o in ops) and not any(t.transaction_type=='RECEIVE' and nearby(t.created_at,r.returned_at) for t in stock):
                audit=next((a for a in related if a.object_type=='assignments' and a.object_id==r.id and a.action=='returned'),None)
                add('return:'+str(r.id),'RETURNED',r.returned_at,audit.user_id if audit else None,{'current_status':'AVAILABLE','current_assignee':None},r.condition_in or 'Thu hồi từ dữ liệu cũ')
        for a in related:
            old=a.old_value or {}; new=a.new_value or {}
            if a.object_type=='maintenance':
                status=db.get(m.MasterData,new.get('status_id'))
                done=status and status.code in {'completed','cancelled'}
                delta={'current_status':codes.get(new.get('previous_status_id'),'AVAILABLE') if done else 'MAINTENANCE'}
                add('audit:'+str(a.id),'MAINTENANCE',a.created_at,a.user_id,delta,('Hoàn tất bảo trì' if done else 'Bảo trì')+' · '+str(new.get('problem') or ''),{'maintenance':{'id':a.object_id,'status':status.name if status else None,'action_taken':new.get('action_taken')}})
            elif a.object_type=='assets' and a.action=='updated' and old:
                delta={k:new.get(k) for k in ('code','model','serial','brand','type_id','description','received_date') if old.get(k)!=new.get(k)}
                if delta: add('audit:'+str(a.id),'UPDATED',a.created_at,a.user_id,delta,'Cập nhật thông tin (dữ liệu cũ)')
                if codes.get(new.get('status_id'))=='RETIRED' and codes.get(old.get('status_id'))!='RETIRED' and not any(o.operation_type=='RETIRE' and nearby(o.created_at,a.created_at) for o in ops):
                    add('retire:'+str(a.id),'RETIRED',a.created_at,a.user_id,{'current_status':'RETIRED','current_assignee':None,'current_location':None},'Ngừng sử dụng (dữ liệu cũ)')
        state={k:v for k,v in initial.items() if k in ('code','model','serial','brand','type_id','description','received_date')}
        for when,source,kind,user,delta,description,extra in sorted(candidates,key=lambda c:(c[0],c[1])):
            before=deepcopy(state); state.update(delta); after={**deepcopy(state),**extra}
            ref='legacy:'+source
            if db.scalar(select(m.AssetOperation.id).where(m.AssetOperation.source_ref==ref)): continue
            row=m.AssetOperation(number='EVT-'+str(asset.id)+'-'+source.replace(':','-'),asset_id=asset.id,operation_type=kind,operation_date=when,performed_by=user,reason=description,before_state=before,after_state=after,source_ref=ref)
            if kind=='REASSIGNED':
                row.from_entity_type='USER';row.from_entity_id=(before.get('current_assignee') or {}).get('id');row.to_entity_type='USER';row.to_entity_id=(after.get('current_assignee') or {}).get('id')
            db.add(row)
    for maintenance in db.scalars(select(m.Maintenance)):
        if maintenance.previous_status_id: maintenance.previous_status_id=statuses[STATUS_CODES[codes.get(maintenance.previous_status_id,'AVAILABLE')]].id
    for code,row in statuses.items():
        row.archived=code not in STATUS_CODES.values()
    db.flush()
