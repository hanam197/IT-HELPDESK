import { useQuery } from '@tanstack/react-query'
import { Navigate,useNavigate,useParams,useSearchParams } from 'react-router-dom'
import { api,type Row } from './api'
import { configs } from './config'
import { RecordList } from './components/RecordList'

export function historyLink(resource:string,id?:number){
 if(id)return `/${resource}/${id}`
 if(resource==='inventory-transactions')return '/inventory?tab=history'
 if(['asset-operations','location-history','assignments'].includes(resource))return '/assets'
 return '/'+resource
}
export function HistoryRecords({filters={},initialSearch=''}:{filters?:Row,initialSearch?:string}){
 const navigate=useNavigate()
 return <RecordList resource="inventory-transactions" columns={configs['inventory-transactions'].columns} filters={filters} initialSearch={initialSearch} onRow={row=>navigate('/inventory-transactions/'+row.id)}/>
}
/** Preserve bookmarks without retaining a standalone History module. */
export function LegacyHistoryRedirect(){
 const [params]=useSearchParams();const {resource,id}=useParams()
 const {data}=useQuery({queryKey:['legacy-history',resource,id],queryFn:()=>api('/'+resource+'/'+id),enabled:!!resource&&!!id})
 if(resource&&id){
  if(resource==='inventory-transactions')return <Navigate replace to={'/inventory-transactions/'+id}/>
  if(data?.asset_id)return <Navigate replace to={'/assets/'+data.asset_id+'?tab=history'}/>
  if(!data)return <div className="loading">Đang mở bản ghi…</div>
  return <Navigate replace to={'/'+resource+'/'+id}/>
 }
 if(params.get('asset'))return <Navigate replace to={'/assets/'+params.get('asset')+'?tab=history'}/>
 if(params.get('tab')==='stock')return <Navigate replace to={'/inventory?tab=history'+(params.get('warehouse')?'&warehouse='+params.get('warehouse'):'')}/>
 return <Navigate replace to="/assets"/>
}
