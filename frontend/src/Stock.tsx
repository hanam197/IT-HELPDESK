import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link,useNavigate,useSearchParams } from 'react-router-dom'
import { Warehouse,Monitor,Package,History,Check,TriangleAlert,Layers } from 'lucide-react'
import { api,type Row } from './api'
import { RecordList } from './components/RecordList'
import { Badge,Cell } from './components/DataTable'
import { StockHistory } from './components/StockHistory'
import { QuickStockIssue } from './Warehouse'

export function Stock({user}:{user:Row}){
 const [params,setParams]=useSearchParams();const navigate=useNavigate();const requested=params.get('tab');const tab=['assets','consumables','history'].includes(requested||'')?requested!:'consumables';const warehouse=params.get('warehouse')||''
 const [status,setStatus]=useState('')
 const {data:meta,error}=useQuery({queryKey:['meta'],queryFn:()=>api('/meta')})
 const update=(key:string,value:string)=>{const next=new URLSearchParams(params);value?next.set(key,value):next.delete(key);next.delete('q');setStatus('');setParams(next)}
 const filters=warehouse?{warehouse_id:Number(warehouse)}:{}
 const assets:Row[]=(meta?.assets||[]).filter((r:Row)=>r.warehouse_id&&(!warehouse||r.warehouse_id===Number(warehouse)))
 const items:Row[]=(meta?.['inventory-items']||[]).filter((r:Row)=>!warehouse||r.warehouse_id===Number(warehouse))
 const lowItems=items.filter(r=>Number(r.quantity)<Number(r.minimum_stock))
 const statuses:Row[]=(meta?.['master-data']||[]).filter((r:Row)=>r.group==='asset_status'&&['available','maintenance','retired'].includes(r.code))
 const cell=(row:Row,key:string)=>{
  if(key==='model'||key==='name'){const Icon=key==='model'?Monitor:Package;return <span className="inventory-stock-product"><span className="inventory-stock-icon">{key==='model'&&row.photo_url?<img src={row.photo_url} alt=""/>:<Icon size={21}/>}</span><span className="inventory-product"><strong>{row[key]||row.code}</strong><small className="mono">{row.code}</small></span></span>}
  if(key==='quantity')return <span className="inventory-product"><strong className={Number(row.quantity)<Number(row.minimum_stock)||Number(row.quantity)===0?'inventory-low':''}>{Number(row.quantity).toLocaleString('vi-VN')} <small>{row.unit}</small></strong>{Number(row.quantity)<Number(row.minimum_stock)&&<span className="inventory-low-label"><TriangleAlert size={11}/>Cần bổ sung</span>}</span>
  if(key==='minimum_stock')return <span>{Number(row.minimum_stock).toLocaleString('vi-VN')} <small className="muted">{row.unit}</small></span>
  if(key==='warehouse_label')return meta?.warehouses.find((w:Row)=>w.id===row.warehouse_id)?.name||row.warehouse_label||'—'
  if(key==='status_label')return <Badge>{row.current_status||row.status_label}</Badge>
  return <Cell name={key} value={row[key]}/>
 }
 return <div className="stock-page inventory-workspace">
  <div className="page-heading"><div><span className="eyebrow">IT STORE · QUẢN LÝ TỒN</span><h1>Tồn kho</h1><p>Kiểm tra hàng sẵn sàng, theo dõi vật tư và tra cứu chứng từ.</p></div><div className="heading-actions"><QuickStockIssue user={user} warehouseId={Number(warehouse)}/><Link className="button button-outline" to={warehouse?'/warehouses/'+warehouse:'/warehouses'}><Warehouse size={16}/>Mở IT Store</Link></div></div>
  {error&&<p role="alert" className="error">{error.message}</p>}
  <div className="inventory-dashboard-overview"><section className="inventory-scope-bar"><div className="inventory-warehouse-filter"><span><Warehouse size={25}/></span><label>Kho đang theo dõi<select aria-label="Lọc theo kho" value={warehouse} onChange={e=>update('warehouse',e.target.value)}><option value="">Tất cả kho</option>{meta?.warehouses.map((w:Row)=><option key={w.id} value={w.id}>{w.name}</option>)}</select></label></div><div className="inventory-scope-copy"><strong>Tồn hiện tại</strong><span>Thiết bị, linh kiện và vật tư đang lưu trong kho</span></div></section>
  <div className="inventory-summary-cards">{[{name:'Thiết bị & linh kiện',value:assets.length,icon:Layers,tone:'blue',caption:'Đang lưu trong kho'},{name:'Sẵn sàng cấp phát',value:assets.filter(r=>r.current_status==='AVAILABLE').length,icon:Check,tone:'green',caption:'Có thể xuất ngay'},{name:'Loại vật tư',value:items.length,icon:Package,tone:'purple',caption:'Quản lý theo số lượng'},{name:'Cần bổ sung',value:lowItems.length,icon:TriangleAlert,tone:'orange',caption:'Dưới mức tồn tối thiểu'}].map(metric=><article className={'inventory-summary-card '+metric.tone} key={metric.name}><span className="inventory-summary-icon"><metric.icon size={21}/></span><div><span>{metric.name}</span><strong>{metric.value}</strong><small>{metric.caption}</small></div></article>)}</div></div>
  <section className="inventory-content panel"><div className="inventory-tabs" role="tablist" aria-label="Các mục tồn kho">{[{key:'assets',name:'Thiết bị & linh kiện',icon:Monitor,count:assets.length},{key:'consumables',name:'Vật tư',icon:Package,count:items.length},{key:'history',name:'Lịch sử nhập xuất',icon:History}].map(t=><button role="tab" aria-selected={tab===t.key} aria-controls="inventory-panel" id={'inventory-tab-'+t.key} className={tab===t.key?'active':''} key={t.key} onClick={()=>update('tab',t.key)}><t.icon size={17}/>{t.name}{t.count!==undefined&&<span>{t.count}</span>}</button>)}</div>
   <div id="inventory-panel" role="tabpanel" aria-labelledby={'inventory-tab-'+tab}>
    {tab==='history'?<StockHistory key={'history'+warehouse} meta={meta} filters={filters} initialSearch={params.get('q')||''}/>:<>
     <div className="inventory-section-intro"><div><h2>{tab==='assets'?'Thiết bị trong kho':'Vật tư trong kho'}</h2><p>{tab==='assets'?'Theo dõi từng thiết bị theo số sê-ri và tình trạng.':'Số lượng hiện có, mức tồn tối thiểu và kệ lưu trữ.'}</p></div>{tab==='consumables'&&lowItems.length>0&&<span className="inventory-low-summary"><TriangleAlert size={14}/>{lowItems.length} loại cần bổ sung</span>}</div>
     <RecordList pageSize={6} key={tab+warehouse} resource={tab==='assets'?'assets':'inventory-items'} columns={tab==='assets'?['model','type_label','serial','status_label','warehouse_label','received_date']:['name','category','quantity','minimum_stock','warehouse_label','bin_shelf']} columnLabels={{model:'Thiết bị / Mã',name:'Vật tư / Mã',quantity:'Tồn hiện tại',minimum_stock:'Tồn tối thiểu',warehouse_label:'Kho',bin_shelf:'Kệ / Ngăn'}} renderCell={cell} filters={{...filters,...(tab==='assets'&&status?{status_id:Number(status)}:{})}} view={tab==='assets'?'in-stock':''} initialSearch={params.get('q')||''} toolbar={tab==='assets'?<select aria-label="Lọc tình trạng tồn kho" value={status} onChange={e=>setStatus(e.target.value)}><option value="">Tất cả tình trạng</option>{statuses.map(s=><option key={s.id} value={s.id}>{s.code==='available'?'Sẵn sàng':s.code==='maintenance'?'Đang bảo trì':'Ngừng sử dụng'}</option>)}</select>:undefined} renderActions={r=><QuickStockIssue user={user} compact {...(tab==='assets'?{asset:r}:{item:r})}/>} onRow={r=>navigate(`/${tab==='assets'?'assets':'inventory-items'}/${r.id}`)}/>
    </>}
   </div>
  </section>
 </div>
}
