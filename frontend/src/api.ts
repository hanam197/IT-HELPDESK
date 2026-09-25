import { fieldLabels,vi } from './i18n'
import { QueryClient } from '@tanstack/react-query'
export const queryClient = new QueryClient({defaultOptions:{queries:{retry:1,staleTime:20000}}})
export type Row = Record<string, any>
export async function api<T=any>(path:string, options:RequestInit={}):Promise<T>{
 const response=await fetch('/api'+path,{...options,headers:{...(options.body instanceof FormData?{}:{'Content-Type':'application/json'}),'X-Requested-With':'Helpdesk',...options.headers}})
 if(!response.ok){if(response.status===401&&!path.startsWith('/auth/login'))queryClient.setQueryData(['me'],null);const data=await response.json().catch(()=>({detail:'Không thể thực hiện yêu cầu'}));throw new Error(typeof data.detail==='string'?vi(data.detail):Array.isArray(data.detail)?data.detail.map((e:Row)=>`${label(String(e.loc?.at(-1)||'record').replace('_id',''))}: ${e.type==='missing'?'Vui lòng nhập thông tin':e.type==='extra_forbidden'?'Không được phép thay đổi trường này':e.type==='string_too_short'?`Cần ít nhất ${e.ctx?.min_length} ký tự`:'Giá trị không hợp lệ'}`).join(' · '):'Không thể thực hiện yêu cầu')}
 return response.json()
}
export const label=(s:string)=>fieldLabels[s]||vi(s.replaceAll('_',' ').replaceAll('-',' ').replace(/\b\w/g,c=>c.toUpperCase()))
export const formatDate=(s:any)=>s?new Date(s).toLocaleString('vi-VN',{day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'}):'—'
export function canWrite(role:string,resource:string){return role==='ADMIN'||role==='IT_MANAGER'&&!['users','master-data','asset-types','locations'].includes(resource)||role==='IT_SUPPORT'&&['tickets','maintenance','articles','ticket-articles','operations'].includes(resource)}
