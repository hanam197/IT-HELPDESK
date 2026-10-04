import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import * as Dialog from '@radix-ui/react-dialog'
import { Link } from 'react-router-dom'
import { ArrowDownToLine, ArrowUpFromLine, X, Warehouse, UserRound, Package, CalendarDays } from 'lucide-react'
import { api, formatDate, type Row } from '../api'
import { Cell } from './DataTable'
import { RecordList } from './RecordList'
import { Button } from './ui/button'

const columns=['number','transaction_type','asset_label','quantity','warehouse_label','recipient_user_label','transaction_date','performed_by_label']
const labels={number:'Chứng từ',transaction_type:'Giao dịch',asset_label:'Hàng hóa',quantity:'Số lượng',warehouse_label:'Kho',recipient_user_label:'Người / Trạm nhận',transaction_date:'Thời gian',performed_by_label:'Người thực hiện'}
export function StockHistory({filters={},initialSearch='',meta}:{filters?:Row,initialSearch?:string,meta?:Row}){
 const [type,setType]=useState('');const [selected,setSelected]=useState<Row|null>(null)
 const {data:detail,error}=useQuery({queryKey:['stock-transaction',selected?.id],queryFn:()=>api('/inventory-transactions/'+selected!.id),enabled:!!selected})
 const name=(id:number,resource:string,fallback:string)=>meta?.[resource]?.find((r:Row)=>r.id===id)?.name||fallback||'—'
 const rowItem=(row:Row)=>row.asset_id?meta?.assets.find((a:Row)=>a.id===row.asset_id):meta?.['inventory-items'].find((i:Row)=>i.id===row.item_id)
 const cell=(row:Row,key:string)=>{
  const item=rowItem(row),receive=row.transaction_type==='RECEIVE',Icon=receive?ArrowDownToLine:ArrowUpFromLine
  if(key==='number')return <span className="inventory-document"><strong className="mono">{row.number}</strong><small>#{row.id}</small></span>
  if(key==='transaction_type')return <span className={'stock-movement-badge '+(receive?'receive':'issue')}><Icon size={13}/>{receive?'Nhập / Thu hồi':'Xuất kho'}</span>
  if(key==='asset_label')return <span className="inventory-product"><strong>{item?.model||item?.name||row.asset_label||row.item_label||'—'}</strong><small>{item?.code||row.asset_label||row.item_label}{item?.serial?` · S/N: ${item.serial}`:''}</small></span>
  if(key==='quantity')return <span className={'inventory-movement-quantity '+(receive?'receive':'issue')}>{receive?'+':'−'}{Number(row.quantity).toLocaleString('vi-VN')} <small>{row.asset_id?'thiết bị':item?.unit||''}</small></span>
  if(key==='warehouse_label')return name(row.warehouse_id,'warehouses',row.warehouse_label)
  if(key==='recipient_user_label')return <span className="inventory-product"><strong>{name(row.recipient_user_id,'users',row.recipient_user_label)}</strong><small>{row.recipient_location_label||''}</small></span>
  if(key==='performed_by_label')return name(row.performed_by,'users',row.performed_by_label)
  return <Cell name={key} value={row[key]}/>
 }
 const current=detail||selected;const currentItem=current?rowItem(current):null;const receive=current?.transaction_type==='RECEIVE'
 return <>
  <div className="inventory-section-intro"><div><h2>Lịch sử nhập xuất</h2><p>Chứng từ, hàng hóa và người thực hiện trong từng giao dịch.</p></div><span className="inventory-readonly">Lịch sử được lưu tự động</span></div>
  <RecordList resource="inventory-transactions" columns={columns} columnLabels={labels} renderCell={cell} filters={{...filters,...(type?{transaction_type:type}:{})}} initialSearch={initialSearch} onRow={setSelected} toolbar={<select aria-label="Lọc loại giao dịch" value={type} onChange={e=>setType(e.target.value)}><option value="">Tất cả giao dịch</option><option value="RECEIVE">Nhập / Thu hồi</option><option value="ISSUE">Xuất kho</option></select>}/>
  {current&&<Dialog.Root open onOpenChange={open=>{if(!open)setSelected(null)}}><Dialog.Portal><Dialog.Overlay className="modal-overlay"/><Dialog.Content className="editor quick-maintenance-dialog inventory-history-dialog" aria-describedby="inventory-history-description"><header className="editor-heading"><div><span className="eyebrow">CHỨNG TỪ KHO</span><Dialog.Title>{current.number}</Dialog.Title><p id="inventory-history-description">{receive?'Nhập / Thu hồi':'Xuất kho'} · {formatDate(current.transaction_date)}</p></div><Button variant="ghost" size="icon" aria-label="Đóng" onClick={()=>setSelected(null)}><X size={20}/></Button></header><div className="quick-maintenance-body">{error&&<p role="alert" className="error">{error.message}</p>}
   <div className="inventory-history-product"><span><Package size={26}/></span><div><strong>{currentItem?.model||currentItem?.name||current.asset_label||current.item_label}</strong><p className="mono">{currentItem?.code||current.asset_label||current.item_label}</p>{currentItem?.serial&&<small>S/N: {currentItem.serial}</small>}</div><span className={'inventory-movement-quantity '+(receive?'receive':'issue')}>{receive?'+':'−'}{Number(current.quantity).toLocaleString('vi-VN')}<small>{current.asset_id?'thiết bị':currentItem?.unit||''}</small></span></div>
   <div className="inventory-history-info"><section><h3><Warehouse size={16}/>{receive?'Kho nhận':'Kho xuất'}</h3><p>{name(current.warehouse_id,'warehouses',current.warehouse_label)}</p></section><section><h3><UserRound size={16}/>Người / Trạm nhận</h3><p>{current.recipient_user_label?name(current.recipient_user_id,'users',current.recipient_user_label):receive?'Nhập về kho':'—'}</p>{current.recipient_location_label&&<small>{current.recipient_location_label}</small>}</section><section><h3><UserRound size={16}/>Người thực hiện</h3><p>{name(current.performed_by,'users',current.performed_by_label)}</p></section><section><h3><CalendarDays size={16}/>Thời gian giao dịch</h3><p>{formatDate(current.transaction_date)}</p></section></div>
   {current.source_vendor&&<div className="inventory-history-text"><h3>Nhà cung cấp</h3><p>{current.source_vendor}</p></div>}<div className="inventory-history-text"><h3>Tình trạng bàn giao</h3><p>{current.condition||'Chưa ghi nhận'}</p></div><div className="inventory-history-text"><h3>Ghi chú / Nguyên nhân</h3><p>{current.note||'Không có ghi chú'}</p></div>
  </div><footer className="editor-footer"><Link className="button button-outline" to={`/${current.asset_id?'assets':'inventory-items'}/${current.asset_id||current.item_id}`}>Xem {current.asset_id?'thiết bị':'vật tư'}</Link><Button onClick={()=>setSelected(null)}>Đóng</Button></footer></Dialog.Content></Dialog.Portal></Dialog.Root>}
 </>
}
