import { vi,eventLabels,statusLabels } from './i18n'
import { LocationPath } from './components/LocationPath'
import { useState } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import { Link,useNavigate,useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Monitor,Package,MapPin,CalendarDays,FileText,Camera,Printer,Pencil,ArrowRightLeft,CornerDownLeft,UserPlus,Wrench,Trash2,Download,X,ArrowDownToLine } from 'lucide-react'
import { api,canWrite,formatDate,label,type Row } from './api'
import { configs } from './config'
import { Badge,Cell,DataTable } from './components/DataTable'
import { Button } from './components/ui/button'
import type { EditorState } from './components/Editor'
import { QuickStockIssue,StockDialog } from './Warehouse'

export function AssetDetail({data,user,open}:{data:Row,user:Row,open:(s:EditorState)=>void}){
 const [params,setParams]=useSearchParams();const tab=['Overview','Network','History'].find(t=>t.toLowerCase()===params.get('tab'))||'Overview'
 const [receive,setReceive]=useState(false);const [assignStock,setAssignStock]=useState(false);const navigate=useNavigate()
 const {data:meta}=useQuery({queryKey:['meta'],queryFn:()=>api('/meta')})
 const writable=canWrite(user.role,'assets'),ops=canWrite(user.role,'operations'),at=data.asset_type||{},retired=data.current_status==='RETIRED'
 const edit=(fieldKeys?:string[])=>open({resource:'assets',initial:data,edit:true,fieldKeys})
 const operation=(name:string)=>open({resource:'assets',operation:name,initial:{asset_id:data.id}})
 const cardEdit=(keys:string[])=>writable?<Button size="sm" variant="outline" onClick={()=>edit(keys)}><Pencil size={14}/>Sửa</Button>:undefined
 return <div className="asset-workspace">
 <div className="page-heading asset-detail-heading"><div className="asset-heading-identity"><span className="asset-type-icon"><Monitor size={36}/></span><div><div className="asset-title-line"><h1>{data.model||data.code}</h1><Badge>{data.status_label}</Badge></div><div className="detail-subtitle"><span className="mono">{data.code}</span><span>{data.type_label}</span><span><MapPin size={14}/><LocationPath value={data.location_label||'Chưa có vị trí'}/></span></div></div></div><div className="asset-command-bar heading-actions" aria-label="Thao tác tài sản"> {!retired&&<><QuickStockIssue user={user} asset={data}/>{ops&&!data.warehouse_id&&<>
 {at.track_location&&<Button variant="outline" onClick={()=>operation('move')}><MapPin size={15}/>Điều chuyển vị trí</Button>}
 {(data.assignment_id||data.current_status==='IN_USE')&&<><Button variant="outline" onClick={()=>operation('return')}><CornerDownLeft size={15}/>Thu hồi</Button>{data.current_assignee_id&&data.current_status==='IN_USE'&&<Button variant="outline" onClick={()=>operation('reassign')}><ArrowRightLeft size={15}/>Chuyển người phụ trách</Button>}</>}
 {canWrite(user.role,'warehouses')&&<Button variant="outline" disabled={!meta?.warehouses.length} onClick={()=>setReceive(true)}><ArrowDownToLine size={15}/>Thu hồi về kho</Button>}
 </>}{at.track_maintenance&&canWrite(user.role,'maintenance')&&<Button variant="outline" onClick={()=>open({resource:'maintenance',initial:{asset_id:data.id,technician_id:user.id}})}><Wrench size={15}/>Bảo trì</Button>}
 {ops&&<Button variant="outline" className="retire-action" onClick={()=>operation('retire')}><Trash2 size={15}/>Ngừng sử dụng</Button>}</>}<Button variant="outline" onClick={()=>window.print()}><Printer size={16}/>In nhãn</Button>{writable&&<Button variant="outline" onClick={()=>edit()}><Pencil size={16}/>Sửa thông tin</Button>}</div></div>
 <div className="view-tabs" role="tablist" aria-label="Các mục tài sản">{['Overview','Network','History'].map(t=><button key={t} role="tab" aria-selected={tab===t} className={tab===t?'active':''} onClick={()=>setParams({tab:t.toLowerCase()})}>{vi(t)}</button>)}</div>
 <div className={'asset-detail-grid'+(tab!=='Overview'?' asset-detail-full-width':'')}><section className="asset-detail-main" role="tabpanel">
 {tab==='Overview'?<div className="asset-overview-grid">
 <AssetCard title="Thông tin tài sản" icon={<Package size={19}/>} action={cardEdit(['type_id','status_id','brand','model','serial'])}><AssetFields data={data} fields={['code','type_label','status_label','brand','model','serial']}/></AssetCard>
 <AssetCard title="Vị trí và người phụ trách" icon={<MapPin size={19}/>}><AssetFields data={data} fields={['location_label']}/><div className="asset-assignee"><div><span>Người phụ trách</span><strong>{data.assigned_to||'—'}</strong></div>{ops&&at.allow_assignment&&!data.assignment_id&&['AVAILABLE','IN_USE'].includes(data.current_status)&&<Button size="sm" disabled={!!data.warehouse_id&&!canWrite(user.role,'warehouses')} onClick={()=>data.warehouse_id?setAssignStock(true):operation('assign')}><UserPlus size={15}/>Cấp phát</Button>}</div><div className="location-chain">{(data.location_label||'Chưa có vị trí').split(' / ').map((part:string,i:number)=><div key={i}><Monitor size={19}/><strong>{part}</strong><small>{vi(['Site','Team','Station'][i]||'Location')}</small></div>)}</div></AssetCard>
 <AssetCard title="Nhập và bàn giao" icon={<CalendarDays size={19}/>} action={cardEdit(['received_date'])}><AssetFields data={data} fields={['received_date','handover_date','received_by','handed_over_by']}/></AssetCard>
 <AssetCard title="Thông tin bổ sung" icon={<FileText size={19}/>} action={cardEdit(['description'])}><AssetFields data={data} fields={['description','created_at','updated_at']}/></AssetCard>
 </div>:tab==='Network'?<div className="detail-tables">{['interfaces','ip-addresses','connected_ports',...(at.has_ports?['switch-ports']:[])].map(key=>{const resource=key==='connected_ports'?'switch-ports':key;return <section key={key}><div className="section-title"><h2>{key==='connected_ports'?'Cổng switch kết nối':configs[resource].title}</h2>{key!=='connected_ports'&&canWrite(user.role,resource)&&<Button size="sm" variant="outline" onClick={()=>open({resource,initial:resource==='switch-ports'?{switch_id:data.id}:{asset_id:data.id}})}>Thêm bản ghi</Button>}</div><DataTable rows={data[key]||[]} columns={configs[resource].columns} onRow={r=>navigate('/'+resource+'/'+r.id)}/></section>})}</div>:<AssetLifecycle events={data.lifecycle||[]}/>}
 </section>{tab==='Overview'&&<aside className="asset-detail-aside">
 <AssetCard title="Ảnh tài sản" icon={<Camera size={19}/>} action={writable?<Button size="sm" variant="outline" onClick={()=>edit(['photo_upload'])}><Camera size={14}/>{data.photo?'Thay ảnh':'Tải ảnh lên'}</Button>:undefined}><div className="asset-photo-frame">{data.photo?<img src={`/api/assets/${data.id}/photo`} alt={data.model}/>:<div className="photo-empty"><Camera size={32}/><span>Chưa có ảnh</span></div>}</div></AssetCard>
 <AssetCard title="Nhãn tài sản" icon={<Package size={19}/>}><div className="qr-label"><img src={`/api/assets/${data.id}/qr`} alt={'Mã QR của '+data.code}/><strong>{data.code}</strong><small>{data.model}</small></div><div className="label-actions"><Button size="sm" variant="outline" onClick={()=>window.print()}><Printer size={14}/>In nhãn</Button><a className="button button-outline" href={`/api/assets/${data.id}/qr`} download={data.code+'.png'}><Download size={14}/>Tải mã QR</a></div></AssetCard>
 </aside>}</div>
 {assignStock&&meta&&<StockDialog warehouseId={data.warehouse_id} mode="ISSUE" meta={meta} asset={data} onClose={()=>setAssignStock(false)}/>}
 {receive&&meta&&<StockDialog warehouseId={meta.warehouses[0]?.id||0} mode="RECEIVE" meta={meta} asset={data} onClose={()=>setReceive(false)}/>}
 </div>
}
function AssetCard({title,icon,action,children}:{title:string,icon:React.ReactNode,action?:React.ReactNode,children:React.ReactNode}){return <section className="panel asset-card"><header>{icon}<h2>{vi(title)}</h2>{action}</header><div className="asset-card-body">{children}</div></section>}
function AssetFields({data,fields}:{data:Row,fields:string[]}){return <dl className="asset-fields">{fields.map(key=><div className={['description','location_label','assigned_to','warehouse_label'].includes(key)?'wide':''} key={key}><dt>{key==='handed_over_by'?'Người bàn giao':label(key.replace('_label',''))}</dt><dd><Cell name={key} value={data[key]}/></dd></div>)}</dl>}
function AssetLifecycle({events}:{events:Row[]}){
 const [category,setCategory]=useState('');const [selected,setSelected]=useState<Row|null>(null)
 const filtered=events.filter(e=>!category||e.event_type===category)
 const displayValue=(value:unknown)=>value===null||value===undefined||value===''?'—':typeof value==='object'?('name' in value?String((value as Row).name):Object.entries(value).map(([key,v])=>`${label(key)}: ${vi(String(v??'—'))}`).join(' · ')):statusLabels[String(value)]||vi(String(value))
 return <section className="panel asset-lifecycle"><header><div><h2>Lịch sử tài sản</h2><p>Chọn một sự kiện để xem chi tiết và các thay đổi.</p></div><span className="count-pill">{filtered.length} sự kiện</span></header>
 <DataTable key={category} rows={filtered} columns={['occurred_at','event_type','performed_by','description']} onRow={setSelected} toolbar={<select className="lifecycle-category-select" aria-label="Loại sự kiện" value={category} onChange={e=>setCategory(e.target.value)}><option value="">Tất cả sự kiện</option>{Object.entries(eventLabels).map(([code,name])=><option key={code} value={code}>{name}</option>)}</select>}/>
 <Dialog.Root open={!!selected} onOpenChange={open=>{if(!open)setSelected(null)}}><Dialog.Portal><Dialog.Overlay className="modal-overlay"/><Dialog.Content className="lifecycle-event-dialog">
 <header><div><span className="eyebrow">CHI TIẾT SỰ KIỆN</span><Dialog.Title>{selected?.title}</Dialog.Title><Dialog.Description>Sự kiện đã lưu trong vòng đời tài sản.</Dialog.Description></div><Dialog.Close asChild><Button variant="ghost" size="icon" aria-label="Đóng chi tiết sự kiện"><X size={20}/></Button></Dialog.Close></header>
 {selected&&<div className="lifecycle-event-body"><dl className="asset-fields"><div><dt>Thời gian</dt><dd>{formatDate(selected.occurred_at)}</dd></div><div><dt>Phân loại</dt><dd>{eventLabels[selected.event_type]||selected.event_type}</dd></div><div><dt>Người thực hiện</dt><dd>{selected.performed_by||'Chưa ghi nhận'}</dd></div><div><dt>Mã sự kiện</dt><dd>{selected.reference||selected.id}</dd></div></dl><section><h3>Mô tả</h3><p className="event-description">{selected.description||'Không có mô tả bổ sung.'}</p></section>
 <section><h3>Trạng thái trước và sau thao tác</h3><div className="table-scroll"><table className="event-changes-table"><thead><tr><th>Thông tin</th><th>Trước</th><th>Sau</th></tr></thead><tbody>{['current_status','current_location','current_assignee'].map(key=><tr key={key}><th scope="row">{label(key)}</th><td>{displayValue(selected.before_state?.[key])}</td><td>{displayValue(selected.after_state?.[key])}</td></tr>)}</tbody></table></div></section><section><h3>Các thay đổi</h3>{selected.changes?.length?<div className="table-scroll"><table className="event-changes-table"><thead><tr><th>Trường dữ liệu</th><th>Trước</th><th>Sau</th></tr></thead><tbody>{selected.changes.map((change:Row)=><tr key={change.field}><th scope="row">{label(change.field.replace('_id',''))}</th><td>{displayValue(change.before)}</td><td>{displayValue(change.after)}</td></tr>)}</tbody></table></div>:<p className="muted">Sự kiện không ghi nhận thay đổi trường dữ liệu.</p>}</section>
 </div>}<footer>{selected?.resource==='maintenance'&&<Link className="button button-outline" to={'/maintenance/'+selected.record_id}>Mở phiếu bảo trì</Link>}<Dialog.Close asChild><Button variant="outline">Đóng</Button></Dialog.Close></footer>
 </Dialog.Content></Dialog.Portal></Dialog.Root></section>
}
