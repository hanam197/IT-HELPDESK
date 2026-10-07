import { test, expect, type Page } from '@playwright/test';

async function setup(page:Page,empty=false,role='ADMIN') {
  await page.route('**/api/auth/me',route=>route.fulfill({json:{id:1,name:'Quản trị viên',role}}));
  await page.route('**/api/dashboard*',route=>{
    const days=Number(new URL(route.request().url()).searchParams.get('days')||30);
    const daily=Array.from({length:days},(_,index)=>{
      const date=new Date(Date.UTC(2026,9,7-days+1+index)).toISOString().slice(0,10);
      const received=empty?0:index%3;const issued=empty?0:1;const returned=empty?0:index%2;
      return {date,received,issued,returned,other:0,total:received+issued+returned};
    });
    route.fulfill({json:{stats:empty?{}:{'Total assets':120,'Active assets':78,'Available assets':24,'Assets in warehouse':18,'Assets under repair':12,'Retired assets':4,'Disposed assets':2,'Low stock items':3,'Phiếu bảo trì đang mở':5},analytics:{days,daily,total:daily.reduce((sum,day)=>sum+day.total,0),previous_total:empty?0:20},asset_type:empty?{}:{PC:42,Laptop:36,Switch:18,'Access Point':12,Printer:12},asset_location:empty?{}:{'Q7 / Office':70,'Q7 / Factory':30,'IT Store':18,'Chưa có vị trí':2},attention:empty?[]:[{id:1,resource:'maintenance',title:'MT-2026-01',subtitle:'Phiếu bảo trì đang mở'}],operations:empty?[]:[{id:1,asset_id:1,asset_label:'PC-Q7-01',operation_type:'ISSUED',operation_date:'2026-10-07T03:00:00Z'}]}});
  });
}

test('analytical dashboard shows real chart categories, period controls and drilldowns',async({page})=>{
  await setup(page);await page.goto('/');
  await expect(page.getByRole('heading',{name:'Tổng quan',exact:true})).toBeVisible();
  await expect(page.locator('.dash-kpis .dash-kpi')).toHaveCount(4);
  await expect(page.locator('.dash-kpis')).toContainText('120');
  await expect(page.getByRole('img',{name:'Phân bổ trạng thái của 120 tài sản'})).toBeVisible();
  await expect(page.locator('.dash-status-legend a').first()).toHaveAttribute('href','/assets?status=in_use');
  await expect(page.locator('.dash-chart-bars>button')).toHaveCount(10);
  await page.locator('.dash-chart-bars>button').first().focus();
  await expect(page.locator('.dash-chart-readout')).toContainText('Cấp phát:');
  await page.getByLabel('Khoảng thời gian phân tích').selectOption('7');
  await expect(page.locator('.dash-chart-bars>button')).toHaveCount(7);
  await page.getByLabel('Khoảng thời gian phân tích').selectOption('90');
  await expect(page.locator('.dash-chart-bars>button')).toHaveCount(13);
  await expect(page.locator('.dash-distribution-bars').first().getByRole('link',{name:'PC 42'})).toHaveAttribute('href','/assets?type=PC');
  await page.screenshot({path:'/tmp/helpdesk-dashboard-analytics-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  await page.screenshot({path:'/tmp/helpdesk-dashboard-analytics-mobile.png',fullPage:true});
});

test('empty dashboard and viewer permissions remain clear',async({page})=>{
  await setup(page,true,'VIEWER');await page.goto('/');
  await expect(page.locator('.dash-chart-readout')).toContainText('Chưa có hoạt động');
  await expect(page.locator('.dash-trend-summary')).toContainText('Chưa có hoạt động ở kỳ trước');
  await expect(page.getByRole('button',{name:'Bảo trì nhanh',exact:true})).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Điều chuyển tài sản',exact:true})).toHaveCount(0);
  await expect(page.getByRole('img',{name:'Phân bổ trạng thái của 0 tài sản'})).toBeVisible();
});
