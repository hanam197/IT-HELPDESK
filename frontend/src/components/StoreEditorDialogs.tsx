import * as Dialog from '@radix-ui/react-dialog'
import { X, Check, LoaderCircle, Warehouse, Monitor, MapPin } from 'lucide-react'
import { deviceName } from '../deviceName'
import type { ReactNode } from 'react'
import { type Row } from '../api'
import { statusLabels, vi } from '../i18n'
import { Button } from './ui/button'

type Props = { values: Row; meta?: Row; pending: boolean; error?: string; onChange: (patch: Row) => void; onSubmit: () => void; onClose: () => void }
function StoreDialog({ title, description, children, ...props }: Props & { title: string; description: string; children: ReactNode }) {
 return <Dialog.Root open onOpenChange={open=>{if(!open&&!props.pending)props.onClose()}}><Dialog.Portal><Dialog.Overlay className="modal-overlay"/><Dialog.Content className="editor quick-maintenance-dialog store-editor-dialog" aria-describedby="store-editor-description"><header className="editor-heading"><div><span className="eyebrow">IT STORE</span><Dialog.Title>{title}</Dialog.Title><p id="store-editor-description">{description}</p></div><Button variant="ghost" size="icon" aria-label="Đóng" disabled={props.pending} onClick={props.onClose}><X size={20}/></Button></header><form onSubmit={e=>{e.preventDefault();props.onSubmit()}}><div className="quick-maintenance-body">{children}{props.error&&<div role="alert" className="error">{props.error}</div>}</div><footer className="editor-footer"><Button type="button" variant="outline" disabled={props.pending} onClick={props.onClose}>Hủy</Button><Button type="submit" disabled={props.pending||!props.meta}>{props.pending?<LoaderCircle className="spin" size={16}/>:<Check size={16}/>} {title==='Nhập thiết bị'?'Xác nhận nhập kho':title==='Thêm kho'?'Thêm kho':'Lưu thay đổi'}</Button></footer></form></Dialog.Content></Dialog.Portal></Dialog.Root>
}
export function AssetReceiptDialog(props: Props) {
 const {values,meta,pending,onChange}=props
 const input=(key:string,name:string,placeholder:string,required=false,type='text')=><label><span>{name}{required&&<b> *</b>}</span><input required={required} type={type} disabled={pending} value={values[key]||''} placeholder={placeholder} onChange={e=>onChange({[key]:e.target.value})}/></label>
 return <StoreDialog {...props} title="Nhập thiết bị" description="Tiếp nhận thiết bị hoặc linh kiện mới vào kho.">
  <div className="store-form-notice"><Monitor size={20}/><span>{deviceName(values,meta)||'Tên và mã thiết bị được tạo tự động.'}<small>Tên thiết bị = Loại tài sản + Model + S/N.</small></span></div>
  <div className="form-grid quick-maintenance-grid">
   <label><span>Loại tài sản<b> *</b></span><select required disabled={pending||!meta} value={values.type_id||''} onChange={e=>onChange({type_id:e.target.value})}><option value="">Chọn loại tài sản</option>{meta?.['asset-types'].map((row:Row)=><option key={row.id} value={row.id}>{row.name}</option>)}</select></label>
   <label><span>Kho tiếp nhận<b> *</b></span><select required disabled={pending||!meta} value={values.warehouse_id||''} onChange={e=>onChange({warehouse_id:e.target.value})}><option value="">Chọn kho</option>{meta?.warehouses.map((row:Row)=><option key={row.id} value={row.id}>{row.name}</option>)}</select></label>
   {input('model','Model','Ví dụ: Dell Latitude 5530',true)}{input('serial','S/N','Số sê-ri trên thiết bị',true)}
   {input('brand','Hãng','Ví dụ: Dell, HP, Lenovo')}{input('received_date','Ngày nhập','',false,'date')}
  </div>
  <details className="quick-maintenance-extra"><summary>Thông tin bổ sung</summary><div className="form-grid quick-maintenance-grid">
   <label><span>Trạng thái<b> *</b></span><select required disabled={pending||!meta} value={values.status_id||''} onChange={e=>onChange({status_id:e.target.value})}>{!values.status_id&&<option value="">Chọn trạng thái</option>}{meta?.['master-data'].filter((row:Row)=>row.group==='asset_status'&&statusLabels[String(row.code).toUpperCase()]).map((row:Row)=><option key={row.id} value={row.id}>{statusLabels[String(row.code).toUpperCase()]||vi(row.name)}</option>)}</select></label>
   <label><span>Ảnh tài sản</span><input type="file" disabled={pending} accept="image/jpeg,image/png,image/webp" onChange={e=>onChange({photo_upload:e.target.files?.[0]})}/><small className="field-help">JPG, PNG hoặc WebP · tối đa 5 MB</small></label>
   <label className="wide"><span>Mô tả</span><textarea rows={2} disabled={pending} value={values.description||''} onChange={e=>onChange({description:e.target.value})}/></label>
  </div></details>
 </StoreDialog>
}
export function WarehouseEditorDialog(props: Props & { initial: Row; edit: boolean }) {
 const {values,meta,pending,onChange,edit,initial}=props
 const sites:Row[]=(meta?.locations||[]).filter((row:Row)=>row.kind==='site')
 const location=meta?.locations.find((row:Row)=>row.id===Number(values.location_id))
 return <StoreDialog {...props} title={edit?'Sửa kho':'Thêm kho'} description="Kho lưu thiết bị, linh kiện và vật tư IT tại một cơ sở.">
  <div className="store-form-notice"><Warehouse size={21}/><span>{edit?initial.code:'Mã kho được tạo tự động khi lưu.'}<small>{edit?'Mã nhận diện kho.':'Chỉ cần nhập tên kho và chọn cơ sở.'}</small></span></div>
  <div className="form-grid quick-maintenance-grid">
   <label><span>Tên kho<b> *</b></span><input autoFocus required maxLength={120} disabled={pending} value={values.name||''} placeholder="Ví dụ: IT Store Quận 7" onChange={e=>onChange({name:e.target.value})}/></label>
   {edit?<div className="store-fixed-location"><span>Cơ sở / Vị trí kho</span><p><MapPin size={15}/>{location?.path||location?.name||initial.location_label||'—'}</p><small>Vị trí được giữ cố định sau khi tạo kho.</small></div>:<label><span>Cơ sở<b> *</b></span><select required disabled={pending||!meta} value={values.location_id||''} onChange={e=>onChange({location_id:e.target.value})}><option value="">Chọn cơ sở</option>{sites.filter(row=>row.active).map(row=><option key={row.id} value={row.id}>{row.name}</option>)}</select>{meta&&!sites.some(row=>row.active)&&<small className="field-help">Thêm cơ sở đang hoạt động trước khi tạo kho.</small>}</label>}
   <label className="wide"><span>Mô tả</span><textarea rows={2} disabled={pending} placeholder="Ghi chú về kho (không bắt buộc)…" value={values.description||''} onChange={e=>onChange({description:e.target.value})}/></label>
  </div>
 </StoreDialog>
}
