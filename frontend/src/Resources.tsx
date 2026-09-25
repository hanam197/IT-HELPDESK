import { vi,eventLabels,statusLabels } from './i18n'
import { QuickStockIssue } from './Warehouse'
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate,useParams,useSearchParams,Link } from 'react-router-dom'
import { Plus,Download,BookOpen,ArrowUpRight,SlidersHorizontal } from 'lucide-react'
import type { SortingState } from '@tanstack/react-table'
import { api,canWrite,label,type Row } from './api'
import { configs } from './config'
import { DataTable,Badge } from './components/DataTable'
import { Button } from './components/ui/button'
import type { EditorState } from './components/Editor'
export function Resources({user,open,report=false}:{user:Row,open:(s:EditorState)=>void,report?:boolean}){
 const {resource:routeResource}=useParams();const [params]=useSearchParams();const [reportResource,setReportResource]=useState('assets');const resource=report?reportResource:routeResource!;const config=configs[resource];const navigate=useNavigate()
 const [q,setQ]=useState(params.get('q')||'');const [page,setPage]=useState(1);const [sorting,setSorting]=useState<SortingState>([]);const [filterValues,setFilterValues]=useState<Row>({});const [groupBy,setGroupBy]=useState('');const [showFilters,setShowFilters]=useState(false)
 const {data:meta}=useQuery({queryKey:['meta'],queryFn:()=>api('/meta')})
 const filters:Row={...filterValues};const group=resource==='assets'?'asset_status':resource==='maintenance'?'maintenance_status':resource==='articles'?'article_status':resource==='ip-addresses'?'ip_status':null
 for(const key of ['status','priority','category']){const value=params.get(key);if(value&&meta){const item=meta['master-data'].find((r:Row)=>(r.code===value||r.name===value||vi(r.name)===value)&&(key!=='status'||r.group===group));if(item)filters[key+'_id']=item.id}}
 if(params.get('type')&&meta){const item=meta['asset-types'].find((r:Row)=>r.name===params.get('type'));if(item)filters.type_id=item.id}
 if(params.get('user')&&resource==='assignments')filters.user_id=Number(params.get('user'))
 if(params.get('user')&&resource==='assets')filters.assigned_user=Number(params.get('user'))
 if(params.get('view')==='my')filters.technician_id=user.id
 if(params.get('view')==='unassigned')filters.technician_id=null
 if(params.get('view')==='active'&&resource==='assignments')filters.returned_at=null
 if(params.get('view')==='active'&&resource==='maintenance')filters.end_at=null
 const qs=new URLSearchParams({q,filters:JSON.stringify(filters),page:String(page),page_size:'20',sort:sorting[0]?.id||'id',direction:sorting[0]?.desc===false?'asc':'desc'})
 if(params.get('view'))qs.set('view',params.get('view')!)
 if(params.get('location'))qs.set('location',params.get('location')!)
 const {data,error,isLoading}=useQuery({queryKey:['list',resource,qs.toString()],queryFn:()=>api(`/${resource}?${qs}`),enabled:!!config})
 const {data:summary}=useQuery({queryKey:['report-summary',resource,qs.toString(),groupBy],queryFn:()=>api(`/reports/${resource}/summary?${qs}&group_by=${groupBy}`),enabled:report&&!!config})
 if(!config)return <div className="empty"><h1>Không tìm thấy trang</h1><Link to="/">Về tổng quan</Link></div>
 const rows=data?.items||[]
 const exportData=(format:string)=>{const query=new URLSearchParams(qs);query.set('format',format);window.location.href=`/api/reports/${resource}/export?${query}`}
 return <><div className="page-heading"><div><span className="eyebrow">{report?'THỐNG KÊ VÀ XUẤT DỮ LIỆU':resource==='assets'?'DANH SÁCH TÀI SẢN':'VẬN HÀNH CNTT'}</span><h1>{report?'Báo cáo':config.title}{!report&&data&&<span className="title-count">{data.total}</span>}</h1><p>{report?'Tra cứu dữ liệu vận hành và xuất báo cáo.':config.subtitle}</p></div><div className="heading-actions">{!report&&resource==='assets'&&<QuickStockIssue user={user}/>}{(report||resource!=='assets')&&<Button variant="outline" onClick={()=>exportData('csv')}><Download size={16}/>CSV</Button>}<Button variant="outline" onClick={()=>exportData('xlsx')}><Download size={16}/>XLSX</Button>{!report&&!['assets','inventory-items'].includes(resource)&&config.fields.length>0&&canWrite(user.role,resource)&&<Button onClick={()=>open({resource})}><Plus size={16}/>Tạo mới {resource==='assets'?'tài sản':'bản ghi'}</Button>}{!report&&resource==='assignments'&&canWrite(user.role,'operations')&&<Button onClick={()=>open({resource:'assets',operation:'assign'})}><Plus size={16}/>Cấp phát thiết bị</Button>}{!report&&resource==='location-history'&&canWrite(user.role,'operations')&&<Button onClick={()=>open({resource:'assets',operation:'move'})}><Plus size={16}/>Điều chuyển vị trí</Button>}</div></div>
 {report&&<div className="report-tabs">{['assets','assignments','ip-addresses','subnets','switch-ports','maintenance','articles','location-history'].filter(r=>configs[r]).map(r=><button className={resource===r?'active':''} key={r} onClick={()=>{setReportResource(r);setFilterValues({});setPage(1);setQ('');setSorting([])}}>{configs[r].title}</button>)}</div>}

 {report&&summary&&<><div className="report-metrics">{Object.entries(summary.totals).map(([name,value])=><div className="panel" key={name}><span>{vi(name)}</span><strong>{String(value)}</strong></div>)}<label>Nhóm theo<select value={groupBy} onChange={e=>setGroupBy(e.target.value)}><option value="">Tất cả bản ghi</option>{config.columns.filter(c=>c.endsWith('_label')||['department','assigned_to'].includes(c)).map(c=><option key={c} value={c}>{label(c.replace('_label',''))}</option>)}</select></label></div>{groupBy&&<div className="report-groups">{summary.groups.map((g:Row)=><span key={g.group}>{vi(g.group)}<strong>{g.count}</strong>{resource==='maintenance'&&<small>Chi phí: {g.cost}</small>}</span>)}</div>}</>}
 {showFilters&&<div className="filter-panel">{config.fields.filter(f=>f.ref&&f.type!=='multiselect').map(f=><label key={f.key}>{label(f.key.replace('_id',''))}<select value={filterValues[f.key]??''} onChange={e=>{const next={...filterValues};if(e.target.value)next[f.key]=Number(e.target.value);else delete next[f.key];setFilterValues(next);setPage(1)}}><option value="">Tất cả</option>{(meta?.[f.ref!]||[]).filter((r:Row)=>!f.group||r.group===f.group).map((r:Row)=><option key={r.id} value={r.id}>{f.ref==='master-data'?vi(r.name):r.name||r.code||r.number||r.cidr}</option>)}</select></label>)}{resource==='assignments'&&<label>Người phụ trách<select value={filterValues.user_id||''} onChange={e=>setFilterValues(e.target.value?{user_id:Number(e.target.value)}:{})}><option value="">Tất cả người dùng</option>{meta?.users.map((r:Row)=><option key={r.id} value={r.id}>{r.name}</option>)}</select></label>}<Button variant="ghost" onClick={()=>{setFilterValues({});navigate('/'+(report?'reports':resource));setQ('');setPage(1)}}>Đặt lại bộ lọc</Button></div>}
 {error&&<div className="error">{error.message}</div>}{isLoading?<div className="loading">Đang tải dữ liệu…</div>:resource==='articles'&&!report?<><div className="kb-search"><input placeholder="Tìm bài viết kiến thức…" value={q} onChange={e=>{setQ(e.target.value);setPage(1)}}/></div><div className="article-grid">{rows.map((r:Row)=><Link to={'/articles/'+r.id} className="article-card" key={r.id}><div className="article-icon"><BookOpen size={23}/></div><Badge>{r.category_label}</Badge><h2>{r.title}</h2><p>{r.summary}</p><footer><span>{r.number}</span><ArrowUpRight size={18}/></footer></Link>)}</div><div className="pagination"><Button variant="outline" disabled={page===1} onClick={()=>setPage(page-1)}>Trước</Button><span>Trang {page}</span><Button variant="outline" disabled={page*20>=data.total} onClick={()=>setPage(page+1)}>Sau</Button></div></>:<DataTable rows={rows} columns={config.columns} renderActions={!report&&resource==='assets'?r=><QuickStockIssue user={user} asset={r} compact/>:undefined} onRow={r=>navigate(`/${resource}/${r.id}`)} q={q} setQ={s=>{setQ(s);setPage(1)}} total={data?.total} page={page} setPage={setPage} sorting={sorting} setSorting={setSorting} toolbar={<Button variant="outline" size="sm" onClick={()=>setShowFilters(!showFilters)}><SlidersHorizontal size={15}/>Bộ lọc {Object.keys(filters).length>0&&`(${Object.keys(filters).length})`}</Button>}/>}
 </>
}
