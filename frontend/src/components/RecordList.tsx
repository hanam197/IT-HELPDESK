import { useState } from 'react'
import { keepPreviousData,useQuery } from '@tanstack/react-query'
import { Download } from 'lucide-react'
import type { SortingState } from '@tanstack/react-table'
import { api,type Row } from '../api'
import { DataTable } from './DataTable'
import { Button } from './ui/button'

/** Shared, server-paginated inventory and history table. Exports use identical filters. */
export function RecordList({resource,columns,filters={},view='',initialSearch='',onRow,renderActions}:{resource:string,columns:string[],filters?:Row,view?:string,initialSearch?:string,onRow?:(row:Row)=>void,renderActions?:(row:Row)=>React.ReactNode}){
 const [q,setQ]=useState(initialSearch);const [page,setPage]=useState(1);const [sorting,setSorting]=useState<SortingState>([])
 const query=new URLSearchParams({q,filters:JSON.stringify(filters),view,page:String(page),page_size:'20',sort:sorting[0]?.id||'id',direction:sorting[0]?.desc===false?'asc':'desc'})
 const {data,error,isLoading}=useQuery({queryKey:['records',resource,query.toString()],queryFn:()=>api(`/${resource}?${query}`),placeholderData:keepPreviousData})
 const exportRows=()=>{const params=new URLSearchParams(query);params.set('format','xlsx');window.location.href=`/api/reports/${resource}/export?${params}`}
 return <section className="record-list" aria-label="Bản ghi">{error&&<p className="error" role="alert">{error.message}</p>}{isLoading?<div className="loading">Đang tải dữ liệu…</div>:<DataTable rows={data?.items||[]} columns={columns} q={q} setQ={value=>{setQ(value);setPage(1)}} total={data?.total||0} page={page} setPage={setPage} sorting={sorting} setSorting={value=>{setSorting(value);setPage(1)}} onRow={onRow} renderActions={renderActions} toolbar={<Button variant="outline" size="sm" onClick={exportRows}><Download size={15}/>XLSX</Button>}/>}</section>
}
