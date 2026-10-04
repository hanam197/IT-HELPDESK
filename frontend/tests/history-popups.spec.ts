import { postStock } from './stock-helpers'
import {test,expect} from '@playwright/test'
test('five event popups keep table history and show historical data on desktop and mobile',async({page})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message))
 await page.goto('/')
 await page.getByLabel('Tên đăng nhập',{exact:true}).fill('admin')
 await page.getByLabel('Mật khẩu',{exact:true}).fill('WarehouseTest2026!')
 await page.getByRole('button',{name:'Đăng nhập',exact:true}).click()
 await expect(page.getByRole('heading',{name:'Tổng quan',exact:true})).toBeVisible()
 const headers={'X-Requested-With':'Helpdesk'},meta=await (await page.request.get('/api/meta')).json()
 const post=async(path:string,data:any)=>{const r=path==='/inventory/transactions'?await postStock(page.request,data):await page.request.post('/api'+path,{headers,data});expect(r.ok(),await r.text()).toBeTruthy();return r.json()}
 const asset=await post('/assets/register',{model:'POPUP-HISTORY',brand:'Test Brand',serial:'HIST-'+Date.now(),type_id:meta['asset-types'].find((r:any)=>r.name==='Laptop').id,warehouse_id:meta.warehouses[0].id})
 const stations=meta.locations.filter((r:any)=>r.kind==='station'&&r.active&&!meta.warehouses.some((w:any)=>w.location_id===r.id))
 await post('/inventory/transactions',{transaction_type:'ISSUE',asset_id:asset.id,warehouse_id:asset.warehouse_id,recipient_user_id:4,recipient_location_id:stations[0].id})
 await post('/assets/'+asset.id+'/move',{location_id:stations[1].id})
 const md=(group:string,code:string)=>meta['master-data'].find((r:any)=>r.group===group&&r.code===code).id
 await post('/maintenance',{asset_id:asset.id,type_id:md('maintenance_type','network'),status_id:md('maintenance_status','completed'),resolution_outcome:'FIXED',problem:'Mất kết nối tại trạm',diagnosis:'Cáp mạng lỏng',action_taken:'Cắm lại cáp và kiểm tra kết nối thành công',technician_id:3,note:'Kiểm tra tại chỗ'})
 await post('/inventory/transactions',{transaction_type:'RECEIVE',asset_id:asset.id,warehouse_id:asset.warehouse_id,return_status:'AVAILABLE',reason:'Đổi thiết bị cho trạm',note:'Thiết bị hoạt động bình thường'})
 // Later edits must not replace the asset model saved with receipt history.
 expect((await page.request.patch('/api/assets/'+asset.id,{headers,data:{model:'RENAMED-LATER'}})).ok()).toBeTruthy()
 await page.goto('/assets/'+asset.id+'?tab=history')
 const table=page.locator('.asset-lifecycle table'),dialog=page.getByRole('dialog')
 await expect(table).toBeVisible()
 for(const [type,title] of [['RECEIVED','Nhập tài sản','green'],['ISSUED','Cấp phát','blue'],['RETURNED','Thu hồi','purple'],['MOVED','Điều chuyển vị trí','orange'],['MAINTENANCE','Sửa chữa / bảo trì','red']]){
  await page.getByLabel('Loại sự kiện',{exact:true}).selectOption(type)
  await table.locator('tbody tr').first().focus();await page.keyboard.press('Enter')
  await expect(dialog.getByRole('heading',{name:title,exact:true})).toBeVisible()
  await expect(dialog).toContainText('Người thực hiện')
  await expect(dialog).not.toContainText('undefined')
  if(type==='RECEIVED'){await expect(dialog).toContainText('POPUP-HISTORY');await expect(dialog).not.toContainText('RENAMED-LATER')}
  if(type==='MOVED'){await expect(dialog).toContainText(stations[0].name);await expect(dialog).toContainText(stations[1].name)}
  if(type==='MAINTENANCE'){await expect(dialog).toContainText('Cáp mạng lỏng');await expect(dialog).toContainText('Cắm lại cáp và kiểm tra kết nối thành công');await expect(dialog.getByRole('link',{name:'Mở phiếu bảo trì'})).toBeVisible()}
  await page.screenshot({path:'/tmp/history-popup-'+type+'.png'})
  await page.setViewportSize({width:390,height:844})
  const bounds=await dialog.boundingBox();expect(bounds!.x).toBeGreaterThanOrEqual(0);expect(bounds!.x+bounds!.width).toBeLessThanOrEqual(390)
  expect(await dialog.evaluate(el=>el.scrollWidth<=el.clientWidth)).toBeTruthy()
  await page.screenshot({path:'/tmp/history-popup-mobile-'+type+'.png'})
  await page.keyboard.press('Escape');await expect(dialog).not.toBeVisible()
  await page.setViewportSize({width:1440,height:1050})
 }
 expect(errors).toEqual([])
})
