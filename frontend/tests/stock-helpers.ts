import type { APIRequestContext } from '@playwright/test'
import { readFileSync } from 'node:fs'
const template=readFileSync(new URL('../../[Template]BBBANGIAONHANTHIEtBI.pdf',import.meta.url))
export const handoverInfo={sender_name:'IT Administrator',sender_department:'IT Helpdesk',recipient_department:'Operations',place:'Văn phòng',purpose:'Cấp mới',city:'TP.HCM'}
export function postStock(request:APIRequestContext,data:any){
 const headers={'X-Requested-With':'Helpdesk'}
 if(data.transaction_type==='ISSUE'&&data.recipient_user_id)return request.post('/api/inventory/issue-with-handover',{headers,multipart:{payload:JSON.stringify(data),handover_info:JSON.stringify(handoverInfo),file:{name:'signed.pdf',mimeType:'application/pdf',buffer:template}}})
 return request.post('/api/inventory/transactions',{headers,data})
}
