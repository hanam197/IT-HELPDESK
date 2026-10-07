import { test, expect, type Page } from '@playwright/test';

async function setup(page: Page, role = 'ADMIN') {
  const asset = { id: 1, code: 'SW-Q7-01', type_label: 'Switch', model: 'Switch 24P', location_id: 3, location_label: 'Q7 / Kho / QC-10' };
  const ips = Array.from({ length: 25 }, (_, index) => ({
    id: index + 1, address: `192.168.20.${index + 1}`, subnet_id: 1,
    status_id: index === 0 ? 2 : 1, interface_id: index === 0 ? 1 : null,
    assignment_type: 'Static', vlan_label: 'WAREHOUSE',
    ...(index === 0 ? { asset_id: 1, asset_label: asset.code, hostname: 'switch-q7', mac: 'AA:BB:CC:DD:EE:01', location_label: asset.location_label } : {}),
  }));
  const data = {
    assets: [asset], devices: [asset],
    locations: [{ id: 1, name: 'Q7', kind: 'site' }, { id: 2, kind: 'team', parent_id: 1 }, { id: 3, kind: 'station', parent_id: 2 }],
    statuses: [{ id: 1, code: 'available' }, { id: 2, code: 'used' }, { id: 3, code: 'reserved' }],
    subnets: [{ id: 1, cidr: '192.168.20.0/24', gateway: '192.168.20.254', vlan_id: 1, site_id: 1, total_ips: 254 }],
    vlans: [{ id: 1, tag: 20, name: 'WAREHOUSE', site_id: 1, site_label: 'Q7' }],
    interfaces: [{ id: 1, name: 'eth0', mac: 'AA:BB:CC:DD:EE:01', asset_id: 1 }],
    'switch-ports': [] as Record<string, unknown>[], 'ip-addresses': ips, history: [],
  };
  const writes: Record<string, unknown>[] = [];
  await page.route('**/api/auth/me', route => route.fulfill({ json: { id: 1, name: 'Quản trị viên', role, department: 'IT' } }));
  await page.route('**/api/dashboard', route => route.fulfill({ json: { attention: [] } }));
  await page.route('**/api/network/workspace', route => route.fulfill({ json: data }));
  await page.route(/\/api\/ip-addresses\/\d+$/, async route => {
    const payload = route.request().postDataJSON(); writes.push(payload);
    const row = ips.find(row => row.id === Number(route.request().url().split('/').at(-1)))!;
    Object.assign(row, payload, payload.interface_id ? {
      asset_id: 1, asset_label: asset.code, location_label: asset.location_label,
    } : { asset_id: undefined, asset_label: undefined, location_label: undefined });
    await route.fulfill({ json: row });
  });
  return {data,writes};
}

test('no workspace submenu and no sidebar submenu', async ({ page }) => {
  await setup(page);
  await page.goto('/network');
  await expect(page.getByRole('navigation', { name: 'Module mạng' })).toHaveCount(0);
  await expect(page.locator('.subnav a[href^="/network"]')).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'Mạng / IPAM', exact: true })).toBeVisible();
  for (const old of ['overview', 'subnets', 'ip-addresses', 'devices', 'history', 'interfaces', 'assignment', 'search', 'import', 'conflicts']) {
    await page.goto(`/network/${old}`);
    await expect(page).toHaveURL(/\/network(?:\?tab=[^/]+)?$/);
  }
  await expect(page.getByRole('combobox', { name: 'Trạng thái IP' })).toHaveCount(0);
  await expect(page.getByRole('columnheader', { name: 'Trạng thái' })).toHaveCount(0);
  await expect(page.locator('.net-stats')).toContainText('25 / 254');
  await expect(page.locator('.net-stats')).toContainText('Chưa sử dụng');
});

test('independent subnet/IP filtering and pagination', async ({ page }) => {
  await setup(page);
  await page.goto('/network');
  await page.getByRole('tab',{name:'Subnets',exact:true}).click();
  await expect(page.locator('.net-subnet tbody tr')).toHaveCount(20);
  const search = page.getByRole('textbox', { name: 'Tìm subnet, VLAN, gateway…' });
  await search.fill('warehouse');
  await page.locator('.net-list tbody tr').first().click();
  const detail = page.locator('.net-subnet');
  await expect(detail.locator('tbody tr')).toHaveCount(20);
  await expect(search).toHaveValue('warehouse');
  await detail.getByRole('button', { name: 'Sau', exact: true }).click();
  await expect(detail.locator('tbody tr')).toHaveCount(5);
  await expect(detail.locator('tbody tr').first()).toContainText('192.168.20.21');
  await detail.getByRole('textbox', { name: 'Tìm IP, MAC, hostname, mã tài sản, trạm…' }).fill('QC-10');
  await expect(detail.locator('tbody tr')).toHaveCount(1);
  await expect(page.locator('.net-list tbody tr')).toHaveCount(1);
  await detail.locator('tbody tr').first().press('Enter');
  await expect(page.locator('.net-detail')).toContainText('SW-Q7-01');
});

test('add IP form has direct MAC and hostname, no status or interface selector', async ({ page }) => {
  await setup(page);
  await page.route('**/api/meta', route=>route.fulfill({json:{assets:[],subnets:[{id:1,cidr:'192.168.20.0/24'}],'master-data':[]}}));
  await page.goto('/network');
  await page.getByRole('button',{name:'Thêm IP',exact:true}).first().click();
  const dialog=page.getByRole('dialog');
  await expect(dialog).toBeVisible();
  await expect(dialog.getByLabel('MAC', {exact:true})).toBeVisible();
  await expect(dialog.getByLabel('Tên máy', {exact:true})).toBeVisible();
  await expect(dialog.getByLabel('Trạng thái', {exact:true})).toHaveCount(0);
  await expect(dialog.getByLabel('Giao diện mạng', {exact:true})).toHaveCount(0);
  await page.keyboard.press('Escape');
  await expect(dialog).toHaveCount(0);
});

test('mobile viewer can inspect IP without mutation controls', async ({ page }) => {
  await setup(page, 'VIEWER');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/network');
  await page.locator('.net-list tbody tr').first().click();
  await expect(page.locator('.net-detail')).toContainText('SW-Q7-01');
  await expect(page.getByRole('button', { name: /Gán IP|Thu hồi IP|Thêm IP|Sửa/ })).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'Xem tài sản', exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});


test('catalog tabs stay inside the table card', async ({page})=>{
  await setup(page);
  await page.goto('/network');
  await expect(page.getByRole('tab',{name:'Subnets',exact:true})).toBeVisible();
  await page.getByRole('tab',{name:'VLANs',exact:true}).click();
  await expect(page.locator('.net-list').first()).toContainText('WAREHOUSE');
  await page.getByRole('tab',{name:'Thiết bị mạng',exact:true}).click();
  await expect(page.locator('.net-list').first()).toContainText('SW-Q7-01');
  await page.getByRole('tab',{name:'Cổng switch',exact:true}).click();
  await expect(page.locator('.net-list').first()).toContainText('Chưa có dữ liệu phù hợp');
  await page.locator('.net-history-section > summary').click();
  await expect(page.getByRole('heading',{name:'Lịch sử mạng'})).toBeVisible();
});


test('IP tab precedes Subnets and search controls match button height',async({page})=>{
  await setup(page);
  await page.goto('/network');
  const tabs=page.getByRole('tablist',{name:'Danh sách mạng'}).getByRole('tab');
  await expect(tabs.nth(0)).toHaveText('Địa chỉ IP');
  await expect(tabs.nth(1)).toHaveText('Subnets');
  await expect(tabs.nth(0)).toHaveAttribute('aria-selected','true');
  await expect(page.locator('.net-list tbody tr')).toHaveCount(20);
  const search=await page.locator('.net-list .net-search').boundingBox();
  const button=await page.locator('.net-list').getByRole('button',{name:'Thêm IP',exact:true}).boundingBox();
  expect(Math.abs(search!.height-button!.height)).toBeLessThanOrEqual(1);
  for(const card of await page.locator('.net-stats > .net-card').all())expect((await card.boundingBox())!.height).toBeLessThanOrEqual(160);
});

test('React Flow shows physical router/switch/PC links and IP details',async({page})=>{
  const {data}=await setup(page);
  data.assets.push({...data.assets[0],id:2,code:'PC-Q7-02',type_label:'PC'});
  data.assets.push({...data.assets[0],id:3,code:'RTR-Q7',type_label:'Router'});
  data.assets.push({...data.assets[0],id:4,code:'SW-Q7-02',type_label:'Switch'});
  data.devices.push(data.assets[2],data.assets[3]);
  data['switch-ports'].push({id:1,switch_id:1,name:'Gi1',connected_asset_id:4},{id:2,switch_id:3,name:'ether2',connected_asset_id:1},{id:3,switch_id:4,name:'Gi8',connected_asset_id:2});
  await page.goto('/network');
  await page.getByRole('tab',{name:'Sơ đồ mạng',exact:true}).click();
  await expect(page.locator('.react-flow__node')).toHaveCount(4);
  await expect(page.locator('.react-flow__edge')).toHaveCount(3);
  await expect(page.locator('.react-flow__edge[data-id="port-2"]')).toContainText('ether2');
  await expect(page.getByRole('button',{name:'VLAN / Subnet',exact:true})).toHaveCount(0);
  await expect(page.locator('.react-flow__node[data-id="2"]').getByRole('link')).toHaveAttribute('href','/assets/2');
  await page.screenshot({path:'/tmp/ipam-react-flow-desktop.png',fullPage:true});
  const router=page.locator('.react-flow__node[data-id="3"]');
  const before=await router.boundingBox();
  await page.mouse.move(before!.x+5,before!.y+8);
  await page.mouse.down();
  await page.mouse.move(before!.x+65,before!.y+48,{steps:10});
  await page.mouse.up();
  await expect.poll(async()=> (await router.boundingBox())?.x).not.toBe(before?.x);
  await page.locator('.react-flow__node[data-id="1"]').getByRole('button',{name:'192.168.20.1',exact:true}).click();
  await expect(page.locator('.net-detail')).toContainText('192.168.20.1');
  await page.getByRole('tab',{name:'Sơ đồ mạng',exact:true}).click();
  await page.setViewportSize({width:390,height:844});
  await expect(page.locator('.react-flow')).toBeVisible();
  await page.screenshot({path:'/tmp/ipam-react-flow-mobile.png',fullPage:true});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
});

test('port mapping filters devices and generates Gi01 through Gi24',async({page})=>{
  await setup(page);
  const types=[{id:1,name:'Switch',track_network:true},{id:2,name:'Router',track_network:true},{id:3,name:'Access Point',track_network:true},{id:4,name:'PC',track_network:true},{id:5,name:'Linh kiện',track_network:false}];
  const assets=types.map((type,index)=>({id:index+1,type_id:type.id,code:['SW-24','RTR-01','AP-01','PC-01','RAM-01'][index],model:type.name,port_count:index===0?24:2,uplink_port_count:index===0?2:0,sfp_port_count:index===0?2:0}));
  await page.route('**/api/meta',route=>route.fulfill({json:{'asset-types':types,assets,'switch-ports':[{id:99,switch_id:1,name:'Gi1',connected_asset_id:4}]}}));
  const writes:Record<string,unknown>[]=[];
  await page.route('**/api/switch-ports',async route=>{const payload=route.request().postDataJSON();writes.push(payload);await route.fulfill({json:{id:100,...payload}})});
  await page.goto('/network');
  await page.getByRole('tab',{name:'Cổng switch',exact:true}).click();
  await page.getByRole('button',{name:'Thêm Cổng switch',exact:true}).click();
  const dialog=page.getByRole('dialog');
  const source=dialog.getByLabel('Thiết bị nguồn (Router / Switch / AP)');
  await expect(source.locator('option')).toHaveCount(4);
  await expect(source).not.toContainText('PC-01');
  await source.selectOption('1');
  const port=dialog.getByLabel('Tên cổng');
  await expect(port.locator('option')).toHaveCount(29);
  await expect(port.locator('optgroup')).toHaveCount(3);
  await expect(port.locator('option[value="SFP02"]')).toHaveText('SFP02');
  await expect(port.locator('option[value="Gi01"]')).toHaveAttribute('disabled','');
  await expect(port.locator('option[value="Gi24"]')).toHaveText('Gi24');
  const target=dialog.getByLabel('Thiết bị kết nối');
  await expect(target).toContainText('PC-01');
  await expect(target).not.toContainText('RAM-01');
  await expect(target).not.toContainText('SW-24');
  await expect(dialog.locator('select')).toHaveCount(3);
  await port.selectOption('Gi24');await target.selectOption('4');
  await dialog.getByRole('button',{name:'Lưu kết nối'}).click();
  await expect(dialog).toHaveCount(0);
  expect(writes).toEqual([{switch_id:1,name:'Gi24',connected_asset_id:4}]);
});

test('network asset receipt asks for port count',async({page})=>{
  await setup(page);
  await page.route('**/api/meta',route=>route.fulfill({json:{'asset-types':[{id:1,name:'Switch'},{id:2,name:'Laptop'}],warehouses:[{id:1,name:'IT Store'}],locations:[],assets:[],'inventory-items':[],'master-data':[{id:1,group:'asset_status',code:'available'}]}}));
  await page.goto('/network');
  await page.getByRole('button',{name:'Thêm thiết bị',exact:true}).click();
  await page.getByRole('button',{name:'Nhập thiết bị',exact:true}).click();
  const dialog=page.getByRole('dialog');
  await dialog.getByLabel('Loại tài sản').selectOption('1');
  await expect(dialog.getByLabel('Số cổng mạng')).toBeVisible();
  await dialog.getByLabel('Số cổng mạng').fill('24');
  await dialog.getByLabel('Số cổng uplink').fill('2');
  await dialog.getByLabel('Số cổng quang SFP').fill('2');
  await dialog.getByLabel('Loại tài sản').selectOption('2');
  await expect(dialog.getByLabel('Số cổng mạng')).toHaveCount(0);
  await expect(dialog.getByLabel('Số cổng uplink')).toHaveCount(0);
  await expect(dialog.getByLabel('Số cổng quang SFP')).toHaveCount(0);
});

test('switch port workspace groups devices, filters connections and pages large switches',async({page})=>{
  const {data}=await setup(page);
  Object.assign(data.assets[0],{port_count:64});
  const second={...data.assets[0],id:2,code:'SW-Q7-02',port_count:24};
  const pc={...data.assets[0],id:3,code:'PC-Q7-03',type_label:'PC'};
  data.assets.push(second,pc);data.devices.push(second);
  data['switch-ports'].push({id:1,switch_id:1,name:'Gi1',connected_asset_id:3});
  await page.goto('/network');
  await page.getByRole('tab',{name:'Cổng switch',exact:true}).click();
  const chooser=page.getByRole('complementary',{name:'Chọn thiết bị nguồn'});
  await expect(chooser.getByRole('button')).toHaveCount(2);
  await expect(page.locator('.net-port-device-heading')).toContainText('SW-Q7-01');
  await expect(page.locator('.net-port-tile')).toHaveCount(48);
  await page.getByRole('button',{name:'Trang cổng tiếp'}).click();
  await expect(page.locator('.net-port-tile')).toHaveCount(16);
  await expect(page.locator('.net-port-grid')).toContainText('Gi64');
  await page.getByLabel('Lọc kết nối cổng').selectOption('connected');
  await expect(page.locator('.net-port-tile')).toHaveCount(1);
  await page.getByRole('button',{name:'Gi01 · PC-Q7-03',exact:true}).click();
  await expect(page.getByRole('region',{name:'Chi tiết kết nối cổng'})).toContainText('PC-Q7-03');
  await page.getByLabel('Lọc kết nối cổng').selectOption('empty');
  await expect(page.locator('.net-port-tile.connected')).toHaveCount(0);
  await expect(page.getByLabel('Tìm cổng, thiết bị, IP, MAC trong switch…')).toHaveCount(0);
  await page.getByRole('button',{name:'Tổng cổng: 64',exact:true}).click();
  await expect(page.locator('.net-port-tile')).toHaveCount(48);
  await chooser.getByRole('button').filter({hasText:'SW-Q7-02'}).click();
  await expect(page.locator('.net-port-tile')).toHaveCount(24);
  await page.getByLabel('Tìm switch, thiết bị kết nối, IP, MAC…').fill('PC-Q7-03');
  await expect(chooser.getByRole('button')).toHaveCount(1);
  await expect(page.locator('.net-port-tile')).toHaveCount(1);
  await page.getByLabel('Tìm switch, thiết bị kết nối, IP, MAC…').fill('');
  await page.getByLabel('Lọc kết nối cổng').selectOption('all');
  await page.screenshot({path:'/tmp/ipam-switch-ports-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  await page.screenshot({path:'/tmp/ipam-switch-ports-mobile.png',fullPage:true});
});

test('viewer can inspect switch ports without mapping actions',async({page})=>{
  const {data}=await setup(page,'VIEWER');
  Object.assign(data.assets[0],{port_count:24});
  await page.goto('/network');
  await page.getByRole('tab',{name:'Cổng switch',exact:true}).click();
  await page.getByRole('button',{name:'Gi01 · Cổng trống',exact:true}).click();
  await expect(page.getByRole('region',{name:'Chi tiết kết nối cổng'})).toBeVisible();
  await expect(page.getByRole('button',{name:'Gán thiết bị',exact:true})).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Thêm Cổng switch',exact:true})).toHaveCount(0);
});

test('switch groups normal uplink and SFP ports with clickable totals and device shortcut',async({page})=>{
  const {data}=await setup(page);
  Object.assign(data.assets[0],{port_count:24,uplink_port_count:2,sfp_port_count:2});
  const pc={...data.assets[0],id:2,code:'PC-Q7-02',type_label:'PC'};
  data.assets.push(pc);
  data['switch-ports'].push({id:1,switch_id:1,name:'SFP01',connected_asset_id:2});
  await page.goto('/network');
  await page.getByRole('tab',{name:'Cổng switch',exact:true}).click();
  await expect(page.getByRole('region',{name:'Cổng thường',exact:true}).locator('.net-port-tile')).toHaveCount(24);
  await expect(page.getByRole('region',{name:'Uplink',exact:true}).locator('.net-port-tile')).toHaveCount(2);
  await expect(page.getByRole('region',{name:'Cổng quang SFP',exact:true}).locator('.net-port-tile')).toHaveCount(2);
  await expect(page.getByRole('button',{name:'Tổng cổng: 28',exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Đã kết nối: 1',exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Còn trống: 27',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Đã kết nối: 1',exact:true}).click();
  await expect(page.locator('.net-port-tile')).toHaveCount(1);
  await page.getByRole('button',{name:'Còn trống: 27',exact:true}).click();
  await expect(page.locator('.net-port-tile')).toHaveCount(27);
  await page.getByRole('button',{name:'Tổng cổng: 28',exact:true}).click();
  await page.getByRole('button',{name:'SFP01 · PC-Q7-02',exact:true}).click();
  await expect(page.locator('.net-port-connection')).toHaveCount(0);
  await expect(page.getByRole('link',{name:'Mở thiết bị PC-Q7-02 tại SFP01',exact:true})).toHaveAttribute('href','/assets/2');
  await page.screenshot({path:'/tmp/ipam-grouped-ports-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  await page.screenshot({path:'/tmp/ipam-grouped-ports-mobile.png',fullPage:true});
  await page.getByRole('link',{name:'Mở thiết bị PC-Q7-02 tại SFP01',exact:true}).click();
  await expect(page).toHaveURL(/\/assets\/2$/);
});

test('device selector scrolls horizontally and leaves full width for port simulation',async({page})=>{
  const {data}=await setup(page);
  for(let id=2;id<=25;id++){
    const asset={...data.assets[0],id,code:`SW-Q7-${String(id).padStart(2,'0')}`,port_count:24};
    data.assets.push(asset);data.devices.push(asset);
  }
  await page.goto('/network');
  await page.getByRole('tab',{name:'Cổng switch',exact:true}).click();
  const strip=page.getByRole('complementary',{name:'Chọn thiết bị nguồn'});
  expect(await strip.evaluate(element=>element.scrollWidth>element.clientWidth)).toBe(true);
  await page.getByRole('button',{name:'Cuộn thiết bị sang phải',exact:true}).click();
  await expect.poll(()=>strip.evaluate(element=>element.scrollLeft)).toBeGreaterThan(0);
  const main=await page.locator('.net-port-main').boundingBox();
  const layout=await page.locator('.net-port-layout').boundingBox();
  expect(Math.abs(main!.width-layout!.width)).toBeLessThan(2);
  await strip.getByRole('button').filter({hasText:'SW-Q7-25'}).click();
  await expect(page.locator('.net-port-device-heading')).toContainText('SW-Q7-25');
  await expect(page.locator('.net-port-tile')).toHaveCount(24);
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
});
