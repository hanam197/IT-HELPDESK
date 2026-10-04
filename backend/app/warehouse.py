"""Atomic warehouse receipts and issues for serialized assets and quantity stock."""
from datetime import timezone
from decimal import Decimal
from sqlalchemy import select
from . import models as m
from .schemas import Move, Assign, Return
from .services import get, fail, save, move, assign, return_asset, master, audit, serialize, next_number, lock_asset, asset_device_name, operation, close_maintenance_for_operation
from .asset_events import snapshot, set_status, emit, TERMINAL_STATUSES


def transaction_time(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def receive_new_asset(db, warehouse_id, data, user):
    warehouse=get(db,m.Warehouse,warehouse_id)
    if not get(db,m.Location,warehouse.location_id).active: fail('Vị trí kho đã ngừng hoạt động')
    data.setdefault('name',data.get('model'))
    data.setdefault('status_id',master(db,'asset_status','available'))
    data.setdefault('received_date',m.now().date())
    asset=save(db,'assets',data,user,emit_event=False)
    move(db,asset.id,Move(location_id=warehouse.location_id,reason='Warehouse receipt'),user,warehouse_flow=True)
    before=serialize(asset); asset.warehouse_id=warehouse.id
    if asset.current_status=='IN_USE': asset.warehouse_id=None
    if asset.current_status=='DISPOSED':
        asset.warehouse_id=None; asset.current_location_id=None
        current=db.scalar(select(m.LocationHistory).where(m.LocationHistory.asset_id==asset.id,m.LocationHistory.ended_at==None))
        if current: current.ended_at=m.now()
    row=m.InventoryTransaction(number=next_number(db,'STK'),transaction_type='RECEIVE',warehouse_id=warehouse.id,asset_id=asset.id,quantity=1,performed_by=user.id)
    db.add(row); db.flush()
    emit(db,asset,'RECEIVED',user,None,description='Nhập kho: '+warehouse.name,when=row.transaction_date,source_ref='stock:'+str(row.id))
    audit(db,user,'received','assets',asset,before); audit(db,user,'receive','inventory-transactions',row)
    return asset


def stock_movement(db, payload, user, new_item_data=None, handover=None):
    if payload.transaction_type=='ISSUE' and payload.recipient_user_id and handover is None:
        fail('Phải tải lên biên bản bàn giao đã ký trước khi hoàn tất xuất kho cho người phụ trách')
    return_document=payload.transaction_type=='RECEIVE' and payload.asset_id is not None
    if return_document and handover is None:
        fail('Phải tải lên biên bản thu hồi đã ký trước khi hoàn tất thu hồi')
    if handover is not None and not (return_document or payload.transaction_type=='ISSUE' and payload.recipient_user_id):
        fail('Biên bản chỉ áp dụng cho xuất kho có người phụ trách hoặc thu hồi thiết bị')
    if payload.reason is not None and (payload.transaction_type!='RECEIVE' or not payload.asset_id):
        fail('Nguyên nhân thu hồi chỉ áp dụng cho tài sản thu hồi')
    if payload.maintenance is not None:
        if payload.transaction_type!='RECEIVE' or not payload.asset_id or payload.return_status!='MAINTENANCE':
            fail('Thu hồi để bảo trì phải chọn trạng thái Đang bảo trì')
        if not payload.reason: fail('Vui lòng nhập nguyên nhân thu hồi')
        if db.scalar(select(m.Maintenance.id).where(m.Maintenance.asset_id==payload.asset_id,m.Maintenance.end_at==None)):
            fail('Thiết bị đã có phiếu xử lý mở; thu hồi và tiếp tục trên phiếu hiện tại')
    warehouse=get(db,m.Warehouse,payload.warehouse_id)
    if not get(db,m.Location,warehouse.location_id).active: fail('Vị trí kho đã ngừng hoạt động')
    if sum(x is not None for x in [payload.asset_id,payload.item_id,payload.new_item])!=1:
        fail('Chọn một tài sản có số sê-ri hoặc một loại vật tư')
    issue=payload.transaction_type=='ISSUE'
    if payload.asset_id and not issue and payload.return_status is None: fail('Vui lòng chọn tình trạng thu hồi')
    if payload.return_status is not None and (issue or not payload.asset_id): fail('Chỉ chọn tình trạng thu hồi khi nhập lại tài sản')
    if issue and not (payload.recipient_user_id or payload.recipient_location_id): fail('Vui lòng chọn người hoặc trạm nhận')
    if not issue and (payload.recipient_user_id or payload.recipient_location_id): fail('Chỉ chọn người nhận khi xuất kho')
    if payload.recipient_user_id: get(db,m.User,payload.recipient_user_id)
    if payload.recipient_location_id:
        station=get(db,m.Location,payload.recipient_location_id)
        if station.kind!='station' or not station.active: fail('Vui lòng chọn trạm đang hoạt động')
        if db.scalar(select(m.Warehouse.id).where(m.Warehouse.location_id==station.id,m.Warehouse.archived==False)):
            fail('Vui lòng chọn trạm vận hành để cấp phát')
    when=transaction_time(payload.transaction_date)
    if when>m.now(): fail('Ngày nhập xuất kho không được ở tương lai')
    quantity=payload.quantity
    asset=None; item=None; repair_before=None; repair_after=None
    if payload.asset_id:
        if quantity!=1: fail('Tài sản có số sê-ri phải có số lượng là 1')
        asset=lock_asset(db,payload.asset_id)
        before=serialize(asset); state_before=snapshot(db,asset)
        last=db.scalar(select(m.InventoryTransaction).where(m.InventoryTransaction.asset_id==asset.id).order_by(m.InventoryTransaction.transaction_date.desc()).limit(1))
        if last and when<transaction_time(last.transaction_date): fail('Ngày giao dịch không được trước lần nhập xuất kho gần nhất')
        if issue:
            if asset.warehouse_id!=warehouse.id: fail('Tài sản không thuộc kho này')
            if asset.current_status!='AVAILABLE': fail('Chỉ có thể xuất tài sản đang sẵn sàng')
            asset_type=get(db,m.AssetType,asset.type_id)
            if payload.recipient_location_id and not asset_type.allow_station: fail('Loại tài sản này không cho phép cấp phát cho trạm')
            if payload.recipient_user_id:
                assignment=assign(db,asset.id,Assign(user_id=payload.recipient_user_id,condition_out=payload.condition,note=payload.note),user,warehouse_flow=True)
                assignment.created_at=when
            if payload.recipient_location_id:
                location=move(db,asset.id,Move(location_id=payload.recipient_location_id,reason='Warehouse issue',note=payload.note),user,warehouse_flow=True)
                location.created_at=when
                set_status(db,asset,'IN_USE')
            # User-only issuance retains the last recorded physical location.
            if not asset.current_location_id: fail('Vui lòng chọn vị trí thiết bị trước khi xuất kho')
            set_status(db,asset,'IN_USE')
            asset.warehouse_id=None; asset.handover_date=when.date()
        else:
            if payload.return_status not in {'AVAILABLE','MAINTENANCE','RETIRED'}: fail('Thu hồi chỉ chọn Sẵn sàng, Đang bảo trì hoặc Hư / Ngừng sử dụng')
            if asset.warehouse_id: fail('Tài sản đã nằm trong kho')
            if asset.current_status=='DISPOSED': fail('Thiết bị đã thanh lý, không thể nhập lại kho')
            if asset.current_status=='RETIRED' and payload.return_status!='RETIRED': fail('Thiết bị Hư / Ngừng sử dụng phải giữ nguyên trạng thái khi thu hồi')
            if db.scalar(select(m.Assignment.id).where(m.Assignment.asset_id==asset.id,m.Assignment.returned_at==None)):
                returned=return_asset(db,asset.id,Return(condition_in=payload.condition,note=payload.note),user,warehouse_flow=True); returned.returned_at=when
            current=db.scalar(select(m.LocationHistory).where(m.LocationHistory.asset_id==asset.id,m.LocationHistory.ended_at==None))
            if not current or current.location_id!=warehouse.location_id:
                location=move(db,asset.id,Move(location_id=warehouse.location_id,reason='Warehouse return',note=payload.note),user,warehouse_flow=True); location.created_at=when
            asset.warehouse_id=warehouse.id; asset.current_assignee_id=None; set_status(db,asset,payload.return_status)
            if payload.return_status in {'AVAILABLE','RETIRED'}:
                repair_before,repair_after=close_maintenance_for_operation(db,asset,user,when,payload.return_status=='AVAILABLE','Hoàn tất và thu hồi về kho' if payload.return_status=='AVAILABLE' else 'Thu hồi thiết bị không tiếp tục sử dụng')
            else:
                repair=db.scalar(select(m.Maintenance).where(m.Maintenance.asset_id==asset.id,m.Maintenance.end_at==None))
                if repair: repair.previous_status_id=master(db,'asset_status','available')
        audit(db,user,payload.transaction_type.lower(),'assets',asset,before)
    else:
        if payload.new_item is not None:
            if issue: fail('Cần nhập vật tư trước khi xuất kho')
            item=save(db,'inventory-items',{**new_item_data,'warehouse_id':warehouse.id},user)
        else:
            item=db.scalar(select(m.InventoryItem).where(m.InventoryItem.id==payload.item_id,m.InventoryItem.archived==False).with_for_update())
            if not item: fail('Không tìm thấy vật tư')
        if item.warehouse_id!=warehouse.id: fail('Vật tư không thuộc kho này')
        last=db.scalar(select(m.InventoryTransaction).where(m.InventoryTransaction.item_id==item.id).order_by(m.InventoryTransaction.transaction_date.desc()).limit(1))
        if last and when<transaction_time(last.transaction_date): fail('Ngày giao dịch không được trước giao dịch tồn kho gần nhất')
        before=serialize(item); current=Decimal(item.quantity or 0)
        if issue and current<quantity: fail('Số lượng tồn kho không đủ')
        item.quantity=current-quantity if issue else current+quantity
        audit(db,user,payload.transaction_type.lower(),'inventory-items',item,before)
    row=m.InventoryTransaction(number=next_number(db,'STK'),transaction_type=payload.transaction_type,warehouse_id=warehouse.id,asset_id=asset.id if asset else None,item_id=item.id if item else None,quantity=quantity,transaction_date=when,recipient_user_id=payload.recipient_user_id,recipient_location_id=payload.recipient_location_id,source_vendor=payload.source_vendor,condition=payload.condition,performed_by=user.id,note='\n'.join(filter(None,['Nguyên nhân thu hồi: '+payload.reason if payload.reason else None,payload.note])) or None)
    if handover is not None:
        recipient=get(db,m.User,payload.recipient_user_id) if issue else user
        row.handover_filename=handover['filename']
        row.handover_storage_key=handover['storage_key']
        row.handover_content_type=handover['content_type']
        row.handover_size=handover['size']
        row.handover_snapshot={**handover['info'], 'document_kind':'ISSUE' if issue else 'RETURN','recipient_name':recipient.name,
            'warehouse_name':warehouse.name,'transaction_date':when.isoformat(),
            'asset_code':asset.code if asset else item.code,'serial':asset.serial if asset else None,
            'model':asset.model if asset else None,'device_name':asset_device_name(get(db,m.AssetType,asset.type_id).name,asset.model,asset.serial) if asset else item.name,
            'quantity':float(quantity),'unit':'thiết bị' if asset else item.unit,
            'condition':payload.condition,'reason':payload.reason,'recipient_location':get(db,m.Location,payload.recipient_location_id).name if payload.recipient_location_id else None}
    db.add(row); db.flush(); audit(db,user,payload.transaction_type.lower(),'inventory-transactions',row)
    if asset:
        emit(db,asset,'ISSUED' if issue else 'RETURNED',user,state_before,description=' · '.join(filter(None,[warehouse.name,payload.reason,payload.condition,payload.note])),when=when,source_ref='stock:'+str(row.id),extra_before={'maintenance':repair_before} if repair_before else None,extra_after={'maintenance':repair_after} if repair_after else None)
    if payload.maintenance is not None:
        save(db,'maintenance',{**payload.maintenance.model_dump(),'asset_id':asset.id,
             'status_id':master(db,'maintenance_status','open'),'start_at':when,
             'note':'Nguyên nhân thu hồi: '+payload.reason},user)
    return row


def issue_maintenance_parts(db, record, target, part_ids, user):
    """Install serialized warehouse components atomically with the maintenance save."""
    if not part_ids: return
    from .security import authorize
    authorize(user,'warehouses')
    if not target.current_location_id: fail('Thiết bị nhận linh kiện phải có vị trí')
    if target.current_status in TERMINAL_STATUSES:
        fail('Không thể xuất linh kiện cho thiết bị đã ngừng sử dụng hoặc thanh lý')
    for part_id in sorted(part_ids):
        # The service locks target and components in ID order before validation.
        part=lock_asset(db,part_id)
        if not part.warehouse_id or part.current_status!='AVAILABLE':
            fail('Linh kiện không còn sẵn sàng trong kho; vui lòng tải lại phiếu')
        warehouse=get(db,m.Warehouse,part.warehouse_id)
        if not get(db,m.Location,warehouse.location_id).active:
            fail('Vị trí kho đã ngừng hoạt động')
        when=m.now(); before=serialize(part); state_before=snapshot(db,part)
        last=db.scalar(select(m.InventoryTransaction).where(m.InventoryTransaction.asset_id==part.id).order_by(m.InventoryTransaction.transaction_date.desc()).limit(1))
        if last and when<transaction_time(last.transaction_date): fail('Ngày xuất không được trước giao dịch kho gần nhất')
        note=f'Xuất linh kiện cho phiếu {record.number} · Thiết bị {target.code}'
        current=db.scalar(select(m.LocationHistory).where(m.LocationHistory.asset_id==part.id,m.LocationHistory.ended_at==None))
        if current:
            previous=serialize(current); current.ended_at=when
            audit(db,user,'ended','location-history',current,previous)
        if target.current_location_id:
            location=m.LocationHistory(asset_id=part.id,from_location_id=part.current_location_id,location_id=target.current_location_id,technician_id=user.id,reason=note,created_at=when)
            db.add(location); db.flush(); audit(db,user,'moved','location-history',location)
        part.current_location_id=target.current_location_id
        part.warehouse_id=None; part.handover_date=when.date()
        set_status(db,part,'IN_USE')
        row=m.InventoryTransaction(number=next_number(db,'STK'),transaction_type='ISSUE',warehouse_id=warehouse.id,asset_id=part.id,quantity=1,transaction_date=when,recipient_location_id=target.current_location_id,condition='Lắp vào thiết bị',performed_by=user.id,note=note)
        db.add(row); db.flush()
        audit(db,user,'issue','assets',part,before)
        audit(db,user,'issue','inventory-transactions',row)
        emit(db,part,'ISSUED',user,state_before,description=note,when=when,source_ref='stock:'+str(row.id),extra_after={'maintenance':{'id':record.id,'number':record.number},'installed_in_asset':{'id':target.id,'code':target.code}})
