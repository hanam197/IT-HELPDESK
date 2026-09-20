import { QueryClient } from '@tanstack/react-query'
export const queryClient = new QueryClient({defaultOptions:{queries:{retry:1,staleTime:20000}}})
export type Row = Record<string, any>
export async function api<T=any>(path:string, options:RequestInit={}):Promise<T>{
 const response=await fetch('/api'+path,{...options,headers:{...(options.body instanceof FormData?{}:{'Content-Type':'application/json'}),'X-Requested-With':'Helpdesk',...options.headers}})
 if(!response.ok){if(response.status===401&&!path.startsWith('/auth/login'))queryClient.setQueryData(['me'],null);const data=await response.json().catch(()=>({detail:'Request failed'}));throw new Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail))}
 return response.json()
}
export const label=(s:string)=>s.replaceAll('_',' ').replaceAll('-',' ').replace(/\b\w/g,c=>c.toUpperCase())
export const formatDate=(s:any)=>s?new Date(s).toLocaleString('en-GB',{day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'}):'—'
export function canWrite(role:string,resource:string){return role==='ADMIN'||role==='IT_MANAGER'&&!['users','master-data','asset-types','locations'].includes(resource)||role==='IT_SUPPORT'&&['tickets','maintenance','articles','ticket-articles','operations'].includes(resource)}
