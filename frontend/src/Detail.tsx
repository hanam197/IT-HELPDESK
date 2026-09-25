import { AssetDetail } from './AssetDetail'
import { Link,useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import ReactMarkdown from 'react-markdown'
import { ArrowLeft,Pencil,Building2 } from 'lucide-react'
import { api,canWrite,label,type Row } from './api'
import { configs } from './config'
import { Badge,Cell } from './components/DataTable'
import { Button } from './components/ui/button'
import type { EditorState } from './components/Editor'
import { QuickStockIssue } from './Warehouse'
import { historyLink } from './History'

export function Detail({user,open}:{user:Row,open:(s:EditorState)=>void}){
 const {resource='',id}=useParams()
 const {data,error,isLoading}=useQuery({queryKey:['detail',resource,id],queryFn:()=>api(`/${resource}/${id}${resource==='assets'?'/detail':''}`)})
 if(isLoading)return <div className="loading">Đang tải bản ghi…</div>
 if(error)return <div className="error">{error.message}</div>
 if(!data)return null
 if(resource==='assets')return <AssetDetail data={data} user={user} open={open}/>
 const back=resource==='inventory-items'?'/inventory?tab=consumables':historyLink(resource)
 const backLabel=resource==='inventory-items'||resource==='inventory-transactions'?'Tồn kho':configs[resource]?.title||label(resource)
 return <><Link className="back-link" to={back}><ArrowLeft size={15}/>Quay lại {backLabel}</Link>
 <div className="page-heading"><div><span className="eyebrow">{data.code||data.number||label(resource)}</span><h1>{data.name||data.title||data.number||data.address||data.problem||label(resource)+' #'+id}</h1><div className="detail-subtitle">{data.status_label&&<Badge>{data.status_label}</Badge>}</div></div><div className="heading-actions">{resource==='inventory-items'&&<QuickStockIssue user={user} item={data}/>} {canWrite(user.role,resource)&&configs[resource]?.fields.length>0&&<Button variant="outline" onClick={()=>open({resource,initial:data,edit:true})}><Pencil size={15}/>Sửa thông tin</Button>}</div></div>
 <div className="detail-layout"><section className="record-overview">{resource==='articles'?<div className="panel markdown"><p className="article-summary">{data.summary}</p>{['problem','symptoms','cause','resolution','commands','notes'].map(k=>data[k]&&<section key={k}><h2>{label(k)}</h2><ReactMarkdown>{data[k]}</ReactMarkdown></section>)}</div>:<GenericOverview data={data}/>}</section><aside><section className="panel"><div className="panel-heading"><h2>Bản ghi liên quan</h2></div><div className="linked-records">{data.asset_id&&<Link to={'/assets/'+data.asset_id+'?tab=history'}><span className="asset-tag">Tài sản</span>{data.asset_label}<span>Xem lịch sử tài sản →</span></Link>}{data.item_id&&<Link to={'/inventory-items/'+data.item_id}>{data.item_label} →</Link>}{data.warehouse_id&&<Link to={'/inventory?warehouse='+data.warehouse_id}>{data.warehouse_label||'Tồn kho'} →</Link>}{!data.asset_id&&!data.item_id&&!data.warehouse_id&&<p className="muted">Không có bản ghi liên quan.</p>}</div></section></aside></div>
 {resource==='audit-logs'&&<section className="panel audit-detail"><h2>Chi tiết thay đổi</h2><div><section><h3>Trước</h3><pre>{JSON.stringify(data.old_value,null,2)}</pre></section><section><h3>Sau</h3><pre>{JSON.stringify(data.new_value,null,2)}</pre></section></div></section>}
 </>
}
function OverviewSection({title,icon,fields,data}:{title:string,icon:React.ReactNode,fields:string[],data:Row}){return <section className="panel overview-section"><header>{icon}<h2>{title}</h2></header><dl>{fields.filter(key=>data[key]!==undefined).map(key=><div key={key} className={['description','notes','problem','diagnosis','action_taken'].includes(key)?'wide':''}><dt>{label(key.replace('_label',''))}</dt><dd><Cell name={key} value={data[key]}/></dd></div>)}</dl></section>}
function GenericOverview({data}:{data:Row}){
 const hidden=new Set(['password_hash','archived','id','photo','ticket_label','allow_ticket'])
 const fields=Object.keys(data).filter(k=>!hidden.has(k)&&!Array.isArray(data[k])&&typeof data[k]!=='object'&&!k.endsWith('_id'))
 return <OverviewSection title="Thông tin bản ghi" icon={<Building2 size={17}/>} data={data} fields={fields}/>
}
