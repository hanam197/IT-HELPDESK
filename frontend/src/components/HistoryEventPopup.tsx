import type { ReactNode } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import { Link } from 'react-router-dom'
import { Package,UserRound,Undo2,ArrowRightLeft,Wrench,CalendarDays,MapPin,Warehouse,ArrowRight,FileText,Tag,CircleCheck,TriangleAlert,X,Building2,Layers,Monitor,Truck } from 'lucide-react'
import { formatDate,type Row } from '../api'
import { vi,statusLabels } from '../i18n'
import { Badge } from './DataTable'
import { Button } from './ui/button'
const variants:Record<string,{title:string,icon:typeof Package,tone:string}>={
 RECEIVED:{title:'Nhập tài sản',icon:Package,tone:'green'},
 ISSUED:{title:'Cấp phát',icon:UserRound,tone:'blue'},
 RETURNED:{title:'Thu hồi',icon:Undo2,tone:'purple'},
 MOVED:{title:'Điều chuyển vị trí',icon:ArrowRightLeft,tone:'orange'},
 MAINTENANCE:{title:'Bảo trì / Sửa chữa',icon:Wrench,tone:'red'},
}
export const hasEventPopup=(type:string)=>!!variants[type]
const text=(value:any):string=>typeof value==='object'&&value?value.name||'—':value===null||value===undefined||value===''?'—':String(value)
function Info({icon:Icon,label,children}:{icon:typeof Package,label:string,children:ReactNode}){return <div className="event-info"><span className="event-info-icon"><Icon size={19}/></span><div><small>{label}</small><div>{children}</div></div></div>}
function Status({value}:{value:any}){return value?<Badge>{statusLabels[value]||vi(value)}</Badge>:<span className="muted">Chưa ghi nhận</span>}
function Place({value}:{value:any}){const name=text(value);const parts=name.split(/\s*[›>]\s*|\s+\/\s+/);return <div className="event-place">{parts.map((part,i)=>{const Icon=parts.length===1?MapPin:i===0?Building2:i===parts.length-1?Monitor:Layers;return <div key={i}><Icon size={18}/><span>{part}</span></div>})}</div>}
function Custody({state}:{state:Row}){return <div className="event-card"><Info icon={UserRound} label="Người sử dụng">{text(state.current_assignee)}</Info><Info icon={MapPin} label="Vị trí">{text(state.current_location)}</Info></div>}
function Transition({before,after}:{before:Row,after:Row}){return <div className="event-status-transition"><div><small>Trạng thái trước</small><Status value={before.current_status}/></div><ArrowRight size={22}/><div><small>Trạng thái sau</small><Status value={after.current_status}/></div></div>}
export function HistoryEventPopup({event}:{event:Row}){
 const config=variants[event.event_type],Icon=config.icon,before=event.before_state||{},after=event.after_state||{},repair=after.maintenance||before.maintenance||{},stock=event.stock||{},maintenance=event.event_type==='MAINTENANCE'
 return <Dialog.Content aria-describedby={undefined} className={'lifecycle-event-dialog event-popup event-tone-'+config.tone+(maintenance?' event-popup-wide':'')}>
  <header><span className="event-hero-icon"><Icon size={29}/></span><div className="event-heading"><Dialog.Title>{config.title}</Dialog.Title></div><Dialog.Close asChild><Button variant="ghost" size="icon" aria-label="Đóng chi tiết sự kiện"><X size={20}/></Button></Dialog.Close></header>
  <div className="lifecycle-event-body">
   <div className="event-meta"><Info icon={CalendarDays} label="Thời gian sự kiện">{formatDate(event.occurred_at)}</Info><Info icon={UserRound} label="Người thực hiện">{event.performed_by||'Chưa ghi nhận'}</Info></div>
   {event.event_type==='RECEIVED'&&<>
    <div className="event-two-col"><Info icon={Truck} label="Nguồn cung cấp">{text(stock.source_vendor)}</Info><Info icon={Tag} label="Trạng thái khi nhập"><Status value={after.current_status}/></Info></div>
    <section><h3>Thông tin thiết bị tại thời điểm nhập</h3><dl className="event-device-card">{[['Model',after.model],['S/N',after.serial],['Loại',after.type_label||event.asset_type_label],['Hãng',after.brand]].map(([label,value])=><div key={label}><dt>{label}</dt><dd>{text(value)}</dd></div>)}</dl></section>
    <section><Info icon={Warehouse} label="Vị trí sau khi nhập">{text(after.current_location)}</Info></section>
   </>}
   {event.event_type==='ISSUED'&&<>
    <section><Info icon={Warehouse} label="Từ (Nguồn)">{text(before.current_location)}</Info></section>
    <section><h3>Đến (Người nhận / Trạm)</h3><Custody state={after}/></section>
    <section className="event-status-line"><span>Trạng thái sau cấp phát</span><Status value={after.current_status}/></section>
   </>}
   {event.event_type==='RETURNED'&&<>
    <section><h3>Từ (Nguồn)</h3><Custody state={before}/></section>
    <section><h3>Về (Kho nhận)</h3><div className="event-card"><Info icon={Warehouse} label="Vị trí kho">{text(after.current_location)}</Info></div></section>
    <section className="event-status-line"><span>Tình trạng khi thu hồi</span><Status value={after.current_status}/></section>
   </>}
   {event.event_type==='MOVED'&&<>
    <section className="event-route"><div><h3>Từ (Vị trí cũ)</h3><Place value={before.current_location}/></div><ArrowRight size={25}/><div><h3>Đến (Vị trí mới)</h3><Place value={after.current_location}/></div></section>
    <section className="event-status-line"><span>Trạng thái</span><Status value={after.current_status}/></section>
   </>}
   {maintenance&&<>
    <div className="event-two-col event-repair-meta"><Info icon={CalendarDays} label="Thời gian xử lý">{repair.start_at?formatDate(repair.start_at):'Chưa ghi nhận'}<span className="event-time-arrow"> → </span>{repair.end_at?formatDate(repair.end_at):'Chưa kết thúc'}</Info><Info icon={UserRound} label="Người xử lý">{text(repair.technician)}</Info></div>
    <section className="event-two-col"><Info icon={TriangleAlert} label="Vấn đề">{text(repair.problem)}</Info><Info icon={Tag} label="Nhóm vấn đề">{vi(text(repair.issue_category))}</Info></section>
    <section className="event-repair-content"><Info icon={FileText} label="Nguyên nhân / Chẩn đoán">{text(repair.diagnosis)}</Info><Info icon={Wrench} label="Cách xử lý">{text(repair.action_taken)}</Info><Info icon={CircleCheck} label="Kết quả xử lý"><Badge>{repair.status||'Chưa ghi nhận'}</Badge></Info></section>
    <Transition before={before} after={after}/>
    {(repair.parts_replaced||repair.vendor||repair.cost!=null)&&<section className="event-two-col">{repair.parts_replaced&&<Info icon={Package} label="Linh kiện thay thế">{repair.parts_replaced}</Info>}{repair.vendor&&<Info icon={Truck} label="Nhà cung cấp">{repair.vendor}</Info>}{repair.cost!=null&&<Info icon={FileText} label="Chi phí">{new Intl.NumberFormat('vi-VN').format(Number(repair.cost))}</Info>}</section>}
   </>}
   {!maintenance&&after.maintenance&&<section><h3>Phiếu bảo trì liên quan</h3><div className="event-card"><Info icon={TriangleAlert} label="Vấn đề">{text(repair.problem)}</Info><Info icon={FileText} label="Nguyên nhân / Chẩn đoán">{text(repair.diagnosis)}</Info><Info icon={Wrench} label="Cách xử lý">{text(repair.action_taken)}</Info><Info icon={CircleCheck} label="Kết quả xử lý">{repair.resolution_outcome?vi(repair.resolution_outcome):vi(text(repair.status))}</Info></div></section>}
   {!maintenance&&event.event_type!=='RECEIVED'&&before.current_status!==after.current_status&&<Transition before={before} after={after}/>}
   <section className="event-note"><h3>{maintenance?'Ghi chú':'Nội dung ghi nhận'}</h3><p>{maintenance?text(repair.note):text(stock.note||event.description)}</p></section>
   {maintenance&&event.description&&<p className="event-summary">{event.description}</p>}
  </div>
  <footer><span className="event-reference">{event.reference||'Sự kiện #'+event.id}</span>{event.resource==='maintenance'&&event.record_id&&<Link className="button button-outline" to={'/maintenance/'+event.record_id}>Mở phiếu bảo trì</Link>}<Dialog.Close asChild><Button variant="outline">Đóng</Button></Dialog.Close></footer>
 </Dialog.Content>
}
