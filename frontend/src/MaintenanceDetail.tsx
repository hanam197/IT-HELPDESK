import { useState,useEffect,type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useMutation,useQuery } from '@tanstack/react-query'
import { Save,Wrench,Check,ArrowDownToLine,Trash2,MoreVertical,CalendarDays,UserRound,Tag,Clock3,Monitor,TriangleAlert,Settings,Layers,FileText,ArrowRight,History } from 'lucide-react'
import { api,canWrite,queryClient,formatDate,type Row } from './api'
import { statusLabels,vi } from './i18n'
import { Badge } from './components/DataTable'
import { Button } from './components/ui/button'
import type { EditorState } from './components/Editor'
import { MaintenanceParts } from './components/MaintenanceParts'
import { StockDialog } from './Warehouse'

function duration(start?:string,end?:string){
 if(!start||!end)return '—'
 const minutes=Math.floor((new Date(end).getTime()-new Date(start).getTime())/60000)
 if(!Number.isFinite(minutes)||minutes<0)return '—'
 if(minutes===0)return 'Dưới 1 phút'
 const hours=Math.floor(minutes/60),rest=minutes%60
 return [hours?`${hours} giờ`:'',rest?`${rest} phút`:''].filter(Boolean).join(' ')
}
function AssetPhoto({asset}:{asset?:Row}){return <span className="maintenance-asset-photo">{asset?.photo_url?<img src={asset.photo_url} alt={asset.model||'Thiết bị'}/>:<Monitor size={32}/>}</span>}
function InfoRows({rows}:{rows:[string,ReactNode][]}){return <dl className="maintenance-info-rows">{rows.map(([name,value])=><div key={name}><dt>{name}</dt><dd>{value||'—'}</dd></div>)}</dl>}
function Step({title,icon:Icon,tone,children}:{title:string,icon:typeof Wrench,tone:string,children:ReactNode}){return <section className={'maintenance-step panel step-'+tone}><header><span className="maintenance-step-icon"><Icon size={23}/></span><div><h2>{title}</h2></div></header><div className="maintenance-step-body">{children}</div></section>}
export function MaintenanceDetail({data,user,open}:{data:Row,user:Row,open:(s:EditorState)=>void}){
 const [receive,setReceive]=useState(false),[actions,setActions]=useState(false)
 const {data:meta}=useQuery({queryKey:['meta'],queryFn:()=>api('/meta')})
 const {data:asset,error:assetError}=useQuery({queryKey:['maintenance-asset',data.asset_id],queryFn:()=>api(`/assets/${data.asset_id}`)})
 const writable=canWrite(user.role,'maintenance'),active=!data.end_at
 const operational=!['RETIRED','DISPOSED'].includes(data.asset_current_status)
 const stop=useMutation({mutationFn:()=>api(`/maintenance/${data.id}/stop-asset`,{method:'POST'}),onSuccess:()=>{queryClient.invalidateQueries();setActions(false)}})
 const completeStatus=meta?.['master-data'].find((r:Row)=>r.group==='maintenance_status'&&r.code==='completed')
 const fields=['problem','diagnosis','action_taken','note','resolution_outcome','type_id','technician_id']
 const initialDraft=(row:Row)=>Object.fromEntries(fields.map(key=>[key,row[key]??'']))
 const [draft,setDraft]=useState<Row>(()=>initialDraft(data))
 const [formError,setFormError]=useState('')
 const dirty=fields.some(key=>String(draft[key])!==String(data[key]??''))
 useEffect(()=>{if(!dirty)return;const warn=(e:BeforeUnloadEvent)=>{e.preventDefault();e.returnValue=''};window.addEventListener('beforeunload',warn);return()=>window.removeEventListener('beforeunload',warn)},[dirty])
 const save=useMutation({mutationFn:(complete:boolean)=>api(`/maintenance/${data.id}`,{method:'PATCH',body:JSON.stringify({...draft,type_id:Number(draft.type_id),technician_id:Number(draft.technician_id),resolution_outcome:draft.resolution_outcome||null,...(complete?{status_id:completeStatus.id}:{})})}),onSuccess:async(row:Row)=>{setDraft(initialDraft(row));setFormError('');await queryClient.invalidateQueries()}})
 const change=(key:string,value:string)=>{setDraft(current=>({...current,[key]:value}));setFormError('')}
 const submit=(complete:boolean)=>{
  if(!draft.problem.trim()){setFormError('Vui lòng nhập vấn đề');return}
  if(complete&&(!draft.diagnosis.trim()||!draft.action_taken.trim()||!draft.resolution_outcome)){setFormError('Vui lòng nhập nguyên nhân, cách xử lý và chọn kết quả trước khi hoàn tất');return}
  save.mutate(complete)
 }
 const editable=writable&&active&&!save.isPending
 const textField=(key:string,name:string)=>active&&writable?<textarea aria-label={name} value={draft[key]} disabled={!editable} onChange={e=>change(key,e.target.value)} rows={3}/>:<div className="maintenance-content-box">{data[key]||'—'}</div>
 const processed=duration(data.start_at,data.end_at),category=vi(data.issue_category_label||'—')
 const saveParts=useMutation({mutationFn:(ids:number[])=>api(`/maintenance/${data.id}`,{method:'PATCH',body:JSON.stringify({replacement_asset_ids:ids})}),onSuccess:()=>queryClient.invalidateQueries()})
 const parts=String(data.parts_replaced||'').split('\n').map((s:string)=>s.trim()).filter(Boolean)
 return <div className="maintenance-workspace maintenance-inline">
 <header className="maintenance-page-header">
  <AssetPhoto asset={asset}/><div className="maintenance-page-identity"><div className="maintenance-title-line"><h1>{data.number}</h1><Badge>{active?'Mới':'Hoàn tất'}</Badge></div><div className="maintenance-header-meta"><span><CalendarDays size={16}/>{formatDate(data.start_at)}<ArrowRight size={14}/>{data.end_at?formatDate(data.end_at):'Chưa hoàn tất'}</span>{data.end_at&&<span><Clock3 size={16}/>{processed}</span>}<span><UserRound size={16}/>{active&&writable?<select aria-label="Người xử lý" disabled={!editable} value={draft.technician_id} onChange={e=>change('technician_id',e.target.value)}>{meta?.users.map((r:Row)=><option key={r.id} value={r.id}>{r.name}</option>)}</select>:data.technician_label||'Chưa phân công'}</span><span><Tag size={16}/>{active&&writable?<select aria-label="Nhóm vấn đề" disabled={!editable} value={draft.type_id} onChange={e=>change('type_id',e.target.value)}>{meta?.['master-data'].filter((r:Row)=>r.group==='maintenance_type').map((r:Row)=><option key={r.id} value={r.id}>{vi(r.name)}</option>)}</select>:category}</span></div></div>
  <div className="maintenance-page-actions">{writable&&active&&<Button variant="outline" disabled={!dirty||save.isPending||saveParts.isPending} onClick={()=>submit(false)}><Save size={15}/>Lưu thay đổi</Button>}{writable&&active&&operational&&<Button disabled={!completeStatus||save.isPending||saveParts.isPending} onClick={()=>submit(true)}><Check size={15}/>Hoàn tất</Button>}
   <div className="maintenance-menu-wrap"><Button variant="outline" size="icon" aria-label="Thao tác khác" aria-expanded={actions} aria-controls="maintenance-actions" onClick={()=>setActions(!actions)}><MoreVertical size={19}/></Button>{actions&&<><button className="maintenance-menu-dismiss" aria-label="Đóng menu thao tác" onClick={()=>setActions(false)}/><div id="maintenance-actions" className="maintenance-actions-menu" onKeyDown={e=>{if(e.key==='Escape'){setActions(false);e.currentTarget.parentElement?.querySelector<HTMLButtonElement>('[aria-controls]')?.focus()}}}>
   {writable&&active&&['IN_USE','AVAILABLE'].includes(data.asset_current_status)&&<Button variant="ghost" disabled={stop.isPending} onClick={()=>stop.mutate()}><Wrench size={15}/>Dừng thiết bị để sửa</Button>}
   {active&&operational&&!data.asset_warehouse_id&&canWrite(user.role,'warehouses')&&<Button variant="ghost" disabled={!asset||!meta?.warehouses.length} onClick={()=>{setActions(false);setReceive(true)}}><ArrowDownToLine size={15}/>Thu hồi về kho</Button>}
   {active&&operational&&canWrite(user.role,'operations')&&<Button variant="ghost" className="maintenance-menu-danger" onClick={()=>{setActions(false);open({resource:'assets',operation:'retire',initial:{asset_id:data.asset_id}})}}><Trash2 size={15}/>Ngừng sử dụng</Button>}
   <Link to={'/assets/'+data.asset_id+'?tab=history'} onClick={()=>setActions(false)}><History size={15}/>Lịch sử tài sản</Link>
   </div></>}</div>
  </div>
 </header>
 {(formError||save.error||stop.error)&&<p className="error" role="alert">{formError||save.error?.message||stop.error?.message}</p>}
 <div className="maintenance-detail-layout"><section className="maintenance-steps">
  <Step title="Vấn đề" icon={TriangleAlert} tone="red">{textField('problem','Vấn đề')}</Step>
  <Step title="Nguyên nhân" icon={Settings} tone="blue">{textField('diagnosis','Nguyên nhân')}</Step>
  <Step title="Cách xử lý" icon={Wrench} tone="blue">{textField('action_taken','Cách xử lý')}</Step>
  <Step title="Kết quả xử lý" icon={Check} tone="green"><fieldset className="maintenance-outcomes" aria-label="Kết quả xử lý" disabled={!editable}>{[{value:'FIXED',label:'Đã khắc phục'},{value:'UNREPAIRABLE',label:'Không khắc phục được'}].map(result=><label key={result.value} className={draft.resolution_outcome===result.value?'selected':''}><input type="radio" name="resolution_outcome" value={result.value} checked={draft.resolution_outcome===result.value} onChange={()=>change('resolution_outcome',result.value)}/><span>{result.label}</span></label>)}{!active&&!data.resolution_outcome&&<span className="muted">Chưa ghi nhận kết quả trên phiếu cũ</span>}</fieldset></Step>
  <Step title="Linh kiện thay thế" icon={Layers} tone="purple"><MaintenanceParts lockedIds={data.replacement_asset_ids||[]} hideEmpty={parts.length>0} ids={data.replacement_asset_ids||[]} records={data.replacement_assets||[]} meta={meta} assetId={data.asset_id} disabled={saveParts.isPending||save.isPending} onChange={editable&&canWrite(user.role,'warehouses')?ids=>saveParts.mutate(ids):undefined}/>{saveParts.error&&<p className="error" role="alert">{saveParts.error.message}</p>}{parts.length>0&&<div className="maintenance-legacy-parts">{parts.map((part:string,i:number)=><div key={i}>{part}</div>)}</div>}</Step>
  <section className="panel maintenance-note"><h2><FileText size={16}/>Ghi chú</h2><div className="maintenance-note-body">{textField('note','Ghi chú')}</div></section>
 </section><aside className="maintenance-sidebar">
  <section className="panel maintenance-side-card"><header><h2>Thông tin thiết bị</h2></header>{assetError?<p className="error">Không tải được thông tin thiết bị.</p>:asset?<><Link className="maintenance-device-summary" to={'/assets/'+data.asset_id}><AssetPhoto asset={asset}/><div><div><strong>{asset.model||asset.code}</strong><Badge>{statusLabels[asset.current_status]||asset.status_label}</Badge></div><p>{[asset.code,asset.type_label,asset.brand].filter(Boolean).join(' · ')}</p></div></Link><InfoRows rows={[
   ['S/N',asset.serial],['Vị trí hiện tại',asset.location_label],['Người sử dụng',asset.assigned_to],...(asset.warehouse_label?[['Kho',asset.warehouse_label] as [string,ReactNode]]:[])
  ]}/></>:<p className="maintenance-loading">Đang tải thiết bị…</p>}<Link className="maintenance-history-link" to={'/assets/'+data.asset_id+'?tab=history'}><History size={15}/>Xem lịch sử tài sản<ArrowRight size={14}/></Link></section>

 </aside></div>
 {receive&&meta&&asset&&<StockDialog warehouseId={meta.warehouses[0]?.id||0} mode="RECEIVE" meta={meta} asset={asset} onClose={()=>setReceive(false)}/>}
 </div>
}
