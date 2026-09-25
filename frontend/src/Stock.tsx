import { vi,eventLabels,statusLabels } from './i18n'
import { useQuery } from '@tanstack/react-query'
import { Link,useNavigate,useSearchParams } from 'react-router-dom'
import { ArrowDownToLine } from 'lucide-react'
import { api,type Row } from './api'
import { configs } from './config'
import { RecordList } from './components/RecordList'
import { HistoryRecords } from './History'
import { QuickStockIssue } from './Warehouse'

export function Stock({user}:{user:Row}){
 const [params,setParams]=useSearchParams();const navigate=useNavigate();const requested=params.get('tab');const tab=['assets','consumables','history'].includes(requested||'')?requested!:'consumables';const warehouse=params.get('warehouse')||''
 const {data:meta,error}=useQuery({queryKey:['meta'],queryFn:()=>api('/meta')})
 const update=(key:string,value:string)=>{const next=new URLSearchParams(params);value?next.set(key,value):next.delete(key);next.delete('q');setParams(next)}
 const filters=warehouse?{warehouse_id:Number(warehouse)}:{}
 return <div className="stock-page"><div className="page-heading"><div><h1>Tồn kho</h1><p>Tra cứu tài sản trong kho, vật tư và lịch sử nhập xuất.</p></div><div className="heading-actions"><QuickStockIssue user={user} warehouseId={Number(warehouse)}/><Link className="button button-outline" to={warehouse?'/warehouses/'+warehouse:'/warehouses'}><ArrowDownToLine size={16}/>Mở kho</Link></div></div>
 {error&&<p role="alert" className="error">{error.message}</p>}
 <div className="stock-page-toolbar"><label>Kho<select aria-label="Lọc theo kho" value={warehouse} onChange={e=>update('warehouse',e.target.value)}><option value="">Tất cả kho</option>{meta?.warehouses.map((w:Row)=><option key={w.id} value={w.id}>{w.code} · {w.name}</option>)}</select></label><p>{tab==='assets'?'Tài sản có số sê-ri hiện đang lưu trong kho.':tab==='consumables'?'Số lượng tồn, mức tối thiểu và vị trí kệ của vật tư.':'Toàn bộ lượt nhập xuất tại kho đã chọn.'}</p></div>
 <div className="view-tabs" role="tablist" aria-label="Các mục tồn kho">{[['assets','Assets'],['consumables','Consumables'],['history','History']].map(([key,name])=><button role="tab" aria-selected={tab===key} className={tab===key?'active':''} key={key} onClick={()=>update('tab',key)}>{vi(name)}</button>)}</div>
 <div role="tabpanel">{tab==='history'?<HistoryRecords key={'history'+warehouse} filters={filters} initialSearch={params.get('q')||''}/>:<RecordList key={tab+warehouse} resource={tab==='assets'?'assets':'inventory-items'} columns={tab==='assets'?['code','type_label','model','serial','status_label','warehouse_label','received_date']:configs['inventory-items'].columns} filters={filters} view={tab==='assets'?'in-stock':''} initialSearch={params.get('q')||''} renderActions={r=><QuickStockIssue user={user} compact {...(tab==='assets'?{asset:r}:{item:r})}/>} onRow={r=>navigate(`/${tab==='assets'?'assets':'inventory-items'}/${r.id}`)}/>}</div>
 </div>
}
