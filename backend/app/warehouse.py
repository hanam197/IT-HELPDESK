"""Atomic warehouse receipts and issues for serialized assets and quantity stock."""
from datetime import timezone
from decimal import Decimal
from sqlalchemy import select
from . import models as m
from .schemas import Move, Assign, Return
from .services import get, fail, save, move, assign, return_asset, master, audit, serialize, next_number, lock_asset, operation
from .asset_events import snapshot, set_status, emit


def transaction_time(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def receive_new_asset(db, warehouse_id, data, user):
    warehouse=get(db,m.Warehouse,warehouse_id)
    if not get(db,m.Location,warehouse.location_id).active: fail('Vị trí kho đã ngừng hoạt động')
    data.setdefault('name',data.get('model'))
    data['status_id']=master(db,'asset_status','available')
    data.setdefault('received_date',m.now().date())
    asset=save(db,'assets',data,user,emit_event=False)
    move(db,asset.id,Move(location_id=warehouse.location_id,reason='Warehouse receipt'),user,warehouse_flow=True)
    before=serialize(asset); asset.warehouse_id=warehouse.id
    row=m.InventoryTransaction(number=next_number(db,'STK'),transaction_type='RECEIVE',warehouse_id=warehouse.id,asset_id=asset.id,quantity=1,performed_by=user.id)
    db.add(row); db.flush()
    emit(db,asset,'RECEIVED',user,None,description='Nhập kho: '+warehouse.name,when=row.transaction_date,source_ref='stock:'+str(row.id))
    audit(db,user,'received','assets',asset,before); audit(db,user,'receive','inventory-transactions',row)
    return asset


def stock_movement(db, payload, user, new_item_data=None):
    warehouse=get(db,m.Warehouse,payload.warehouse_id)
    if not get(db,m.Location,warehouse.location_id).active: fail('Vị trí kho đã ngừng hoạt động')
    if sum(x is not None for x in [payload.asset_id,payload.item_id,payload.new_item])!=1:
        fail('Chọn một tài sản có số sê-ri hoặc một loại vật tư')
    issue=payload.transaction_type=='ISSUE'
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
    asset=None; item=None
    if payload.asset_id:
        if quantity!=1: fail('Tài sản có số sê-ri phải có số lượng là 1')
        asset=lock_asset(db,payload.asset_id)
        before=serialize(asset); state_before=snapshot(db,asset)
        last=db.scalar(select(m.InventoryTransaction).where(m.InventoryTransaction.asset_id==asset.id).order_by(m.InventoryTransaction.transaction_date.desc()).limit(1))
        if last and when<transaction_time(last.transaction_date): fail('Ngày giao dịch không được trước lần nhập xuất kho gần nhất')
        if issue:
            if asset.warehouse_id!=warehouse.id: fail('Tài sản không thuộc kho này')
            if asset.current_status!='AVAILABLE': fail('Chỉ có thể xuất tài sản đang sẵn sàng')
            if db.scalar(select(m.Maintenance.id).where(m.Maintenance.asset_id==asset.id,m.Maintenance.end_at==None)): fail('Hoàn tất bảo trì trước khi xuất kho')
            asset_type=get(db,m.AssetType,asset.type_id)
            if payload.recipient_location_id and not asset_type.allow_station: fail('Loại tài sản này không cho phép cấp phát cho trạm')
            if payload.recipient_user_id:
                assignment=assign(db,asset.id,Assign(user_id=payload.recipient_user_id,condition_out=payload.condition,note=payload.note),user,warehouse_flow=True)
                assignment.created_at=when
            if payload.recipient_location_id:
                location=move(db,asset.id,Move(location_id=payload.recipient_location_id,reason='Warehouse issue',note=payload.note),user,warehouse_flow=True)
                location.created_at=when
                set_status(db,asset,'IN_USE')
            else:
                current=db.scalar(select(m.LocationHistory).where(m.LocationHistory.asset_id==asset.id,m.LocationHistory.ended_at==None))
                if current: current.ended_at=when
                asset.current_location_id=None
            set_status(db,asset,'IN_USE')
            asset.warehouse_id=None; asset.handover_date=when.date()
        else:
            if asset.warehouse_id: fail('Tài sản đã nằm trong kho')
            if db.scalar(select(m.Maintenance.id).where(m.Maintenance.asset_id==asset.id,m.Maintenance.end_at==None)): fail('Hoàn tất bảo trì trước khi thu hồi về kho')
            if asset.current_status=='RETIRED': fail('Tài sản đã ngừng sử dụng, không thể nhập lại kho')
            if db.scalar(select(m.Assignment.id).where(m.Assignment.asset_id==asset.id,m.Assignment.returned_at==None)):
                returned=return_asset(db,asset.id,Return(condition_in=payload.condition,note=payload.note),user,warehouse_flow=True); returned.returned_at=when
            current=db.scalar(select(m.LocationHistory).where(m.LocationHistory.asset_id==asset.id,m.LocationHistory.ended_at==None))
            if not current or current.location_id!=warehouse.location_id:
                location=move(db,asset.id,Move(location_id=warehouse.location_id,reason='Warehouse return',note=payload.note),user,warehouse_flow=True); location.created_at=when
            asset.warehouse_id=warehouse.id; asset.current_assignee_id=None; set_status(db,asset,'AVAILABLE')
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
    row=m.InventoryTransaction(number=next_number(db,'STK'),transaction_type=payload.transaction_type,warehouse_id=warehouse.id,asset_id=asset.id if asset else None,item_id=item.id if item else None,quantity=quantity,transaction_date=when,recipient_user_id=payload.recipient_user_id,recipient_location_id=payload.recipient_location_id,source_vendor=payload.source_vendor,condition=payload.condition,performed_by=user.id,note=payload.note)
    db.add(row); db.flush(); audit(db,user,payload.transaction_type.lower(),'inventory-transactions',row)
    if asset:
        emit(db,asset,'ISSUED' if issue else 'RETURNED',user,state_before,description=' · '.join(filter(None,[warehouse.name,payload.condition,payload.note])),when=when,source_ref='stock:'+str(row.id))
    return row
