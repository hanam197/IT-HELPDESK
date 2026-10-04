import type { APIRequestContext, Locator } from '@playwright/test'
import { readFileSync } from 'node:fs'
const template=readFileSync(new URL('../../[Template]BBBANGIAONHANTHIEtBI.pdf',import.meta.url))
export const handoverInfo={sender_name:'IT Administrator',sender_department:'IT Helpdesk',recipient_department:'Operations',place:'Văn phòng',purpose:'Cấp mới',city:'TP.HCM'}
export function postStock(request:APIRequestContext,data:any){
 const headers={'X-Requested-With':'Helpdesk'}
 if(data.transaction_type==='ISSUE'&&data.recipient_user_id||data.transaction_type==='RECEIVE'&&data.asset_id)return request.post('/api/inventory/movement-with-document',{headers,multipart:{payload:JSON.stringify(data),handover_info:JSON.stringify(handoverInfo),file:{name:'signed.pdf',mimeType:'application/pdf',buffer:template}}})
 return request.post('/api/inventory/transactions',{headers,data})
}

export async function attachReturnDocument(dialog:Locator){
 const sender=dialog.getByRole('textbox',{name:/^Người giao/})
 if(await sender.isVisible())await sender.fill('Người giao kiểm thử')
 await dialog.getByLabel('Biên bản thu hồi đã ký',{exact:true}).setInputFiles({name:'thu-hoi-da-ky.pdf',mimeType:'application/pdf',buffer:template})
}
