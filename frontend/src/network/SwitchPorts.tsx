import { useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ChevronLeft, ChevronRight, Plus, Server } from 'lucide-react';
import { Button } from '../components/ui/button';
import type { Row } from '../api';
import { canonicalPortName, declaredPortGroups, PORT_GROUPS } from './portGroups';
import { DeviceVisual, PortJack } from './DeviceVisual';
import { NetworkSearch } from './Tables';
import { matchesQuery, type NetworkModel } from './model';

type PortSlot = { group:string; key:string; name:string; row?:Row; target?:Row; ips:Row[] };

export function SwitchPorts({model,onEdit}: {model:NetworkModel;onEdit?: (port:Row)=>void}) {
  const deviceStrip=useRef<HTMLElement>(null);
  const [deviceQuery,setDeviceQuery] = useState('');
  const [deviceId,setDeviceId] = useState<number|null>(null);
  const [slotKey,setSlotKey] = useState<string|null>(null);
  const [filter,setFilter] = useState('all');
  const [page,setPage] = useState(1);
  const devices = useMemo(() => {
    const owners = new Map(model.devices.filter(asset => /^(router|switch|ap|access point)$/i.test(String(asset.type_label || '').trim())).map(asset=>[asset.id,asset]));
    const portsByDevice=new Map<number,Row[]>();
    for (const port of model.ports) {
      const rows=portsByDevice.get(port.switch_id)||[];rows.push(port);portsByDevice.set(port.switch_id,rows);
      const asset=model.assetsById.get(port.switch_id);
      if(asset && /^(router|switch|ap|access point)$/i.test(String(asset.type_label || '').trim()))owners.set(asset.id,asset);
    }
    const ipsByAsset=new Map<number,Row[]>();
    for(const ip of model.ips)if(ip.asset_id){const ips=ipsByAsset.get(ip.asset_id)||[];ips.push(ip);ipsByAsset.set(ip.asset_id,ips)}
    return [...owners.values()].sort((a,b)=>String(a.code).localeCompare(String(b.code),'vi',{numeric:true})).map(asset=>{
      const rows=portsByDevice.get(asset.id)||[];
      const indexedPorts=new Map(rows.map(row=>[canonicalPortName(row.name),row]));
      const slot=(name:string,group:string,row?:Row):PortSlot=>({group,key:row?`record-${row.id}`:`empty-${name}`,name,row,target:model.assetsById.get(row?.connected_asset_id),ips:ipsByAsset.get(row?.connected_asset_id)||[]});
      const slots:PortSlot[]=declaredPortGroups(asset).flatMap(group=>group.names.map(name=>slot(name,group.key,indexedPorts.get(name))));
      const mapped=new Set(slots.map(port=>port.row?.id));
      slots.push(...rows.filter(row=>!mapped.has(row.id)).sort((a,b)=>a.name.localeCompare(b.name,'vi',{numeric:true})).map(row=>slot(row.name,PORT_GROUPS.find(group=>canonicalPortName(row.name).startsWith(group.prefix))?.key||'normal',row)));
      const connected=slots.filter(port=>port.target).length;
      return {asset,slots,connected};
    });
  },[model]);
  const matchesPort=(port:PortSlot,query:string)=>matchesQuery({...(port.target||{}),port_name:port.name,addresses:port.ips.map(ip=>[ip.address,ip.mac,ip.hostname].filter(Boolean).join(' ')).join(' ')},query);
  const visibleDevices=devices.filter(device=>matchesQuery(device.asset,deviceQuery)||device.slots.some(port=>matchesPort(port,deviceQuery)));
  const selected=visibleDevices.find(device=>device.asset.id===deviceId)||visibleDevices[0];
  const slots=selected?.slots||[];
  const filtered=slots.filter(port=>(matchesQuery(selected!.asset,deviceQuery)||matchesPort(port,deviceQuery))&&(filter==='all'||(filter==='connected'?!!port.target:!port.target)));
  const pages=Math.max(1,Math.ceil(filtered.length/48));
  const currentPage=Math.min(page,pages);
  const selectedPort=filtered.find(port=>port.key===slotKey);
  const reset=()=>{setSlotKey(null);setPage(1)};
  return <section className="net-port-workspace" aria-label="Quản lý cổng thiết bị mạng">
    <div className="net-port-toolbar net-tools"><NetworkSearch value={deviceQuery} onChange={value=>{setDeviceQuery(value);reset()}} placeholder="Tìm switch, thiết bị kết nối, IP, MAC…"/>
      {onEdit&&<Button variant="outline" onClick={()=>onEdit(selected?{switch_id:selected.asset.id}:{})}><Plus size={15}/>Thêm Cổng switch</Button>}
    </div>
    <div className="net-port-layout">
      <div className="net-port-device-strip"><span className="net-port-list-heading">ROUTER / SWITCH / AP</span>
        <button className="net-port-strip-arrow" aria-label="Cuộn thiết bị sang trái" onClick={()=>deviceStrip.current?.scrollBy({left:-300,behavior:'smooth'})}><ChevronLeft size={16}/></button>
        <aside ref={deviceStrip} className="net-port-device-list" aria-label="Chọn thiết bị nguồn">
          {visibleDevices.map(device=><button key={device.asset.id} className={`net-port-device-option ${selected?.asset.id===device.asset.id?'active':''}`} aria-pressed={selected?.asset.id===device.asset.id} title={`${device.asset.code} · ${device.asset.location_label||'Chưa gắn vị trí'}`} onFocus={event=>event.currentTarget.scrollIntoView({block:'nearest',inline:'nearest'})} onClick={()=>{setDeviceId(device.asset.id);setFilter('all');reset()}}>
            <Server size={15}/><div className="net-port-strip-device-info"><strong>{device.asset.code}</strong><small title={device.asset.location_label}>{device.asset.location_label||'Chưa gắn vị trí'}</small></div>
          </button>)}
          {!visibleDevices.length&&<span className="net-port-strip-empty">Không tìm thấy thiết bị phù hợp.</span>}
        </aside>
        <button className="net-port-strip-arrow" aria-label="Cuộn thiết bị sang phải" onClick={()=>deviceStrip.current?.scrollBy({left:300,behavior:'smooth'})}><ChevronRight size={16}/></button>
      </div>
      <div className="net-port-main">{selected?<>
        <div className="net-port-compact-heading"><header className="net-port-device-heading"><div className="net-port-device-identity"><Link to={`/assets/${selected.asset.id}`} aria-label={`Mở thiết bị nguồn ${selected.asset.code}`}><DeviceVisual asset={selected.asset}/></Link><div><h2>{selected.asset.code}</h2><p>{selected.asset.model} · {selected.asset.location_label||'Chưa gắn vị trí'}</p></div></div></header>
        <div className="net-port-stat-cards" aria-label="Thống kê cổng">
          {[{key:'all',label:'Tổng cổng',count:slots.length},
            {key:'connected',label:'Đã kết nối',count:selected.connected},
            {key:'empty',label:'Còn trống',count:slots.length-selected.connected}].map(stat=><button key={stat.key} className={`net-port-stat ${stat.key} ${filter===stat.key?'active':''}`} aria-pressed={filter===stat.key} aria-label={`${stat.label}: ${stat.count}`} onClick={()=>{setFilter(stat.key);reset()}}>
              <span>{stat.label}</span><strong>{stat.count}</strong>
            </button>)}
        </div></div>
        <div className="net-port-utilization"><div><span>{selected.connected}/{slots.length} cổng đã kết nối</span><strong>{slots.length?Math.round(selected.connected/slots.length*100):0}%</strong></div><div className="net-port-utilization-track" role="progressbar" aria-label="Tỷ lệ cổng đã kết nối" aria-valuemin={0} aria-valuemax={slots.length||1} aria-valuenow={selected.connected}><i style={{width:`${slots.length?selected.connected/slots.length*100:0}%`}}/></div></div>
        {!PORT_GROUPS.some(group=>selected.asset[group.field])&&<p className="net-port-note">Thống kê hiện tính trên các cổng đã ghi nhận. Bổ sung số cổng trong form sửa tài sản để xem đầy đủ cổng trống.</p>}
        <div className="net-port-filter-row"><div className="net-rack-legend"><span><i className="connected"/>Đã kết nối</span><span><i/>Cổng trống</span><span><i className="selected"/>Đang chọn</span></div><select aria-label="Lọc kết nối cổng" value={filter} onChange={event=>{setFilter(event.target.value);reset()}}><option value="all">Tất cả cổng</option><option value="connected">Đã kết nối</option><option value="empty">Cổng trống</option></select></div>
        <div className="net-switch-face"><div className="net-switch-face-title"><span>MÔ PHỎNG CỔNG</span><span>{selected.asset.code}</span></div>
        <div className="net-port-clusters">{PORT_GROUPS.map(group=>{
          const ports=filtered.slice((currentPage-1)*48,currentPage*48).filter(port=>port.group===group.key);
          const total=slots.filter(port=>port.group===group.key).length;
          return total>0&&<section className={`net-port-cluster ${group.key}`} key={group.key} aria-label={group.label}><header><strong>{group.label}</strong><span>{total} cổng</span></header>
            <div className="net-port-grid" aria-label={`${group.label} của ${selected.asset.code}`}>{ports.map(port=><div className="net-port-slot" key={port.key}>
              <button className={`net-port-tile ${port.target?'connected':'empty'} ${selectedPort?.key===port.key?'selected':''}`} aria-pressed={selectedPort?.key===port.key} aria-label={`${port.name} · ${port.target?.code||'Cổng trống'}`} onClick={()=>setSlotKey(port.key)}>
                <div><strong>{port.name}</strong><i/></div><PortJack optical={group.key==='sfp'}/><span title={port.target?.code}>{port.target?.code||'Cổng trống'}</span>
              </button>{port.target&&<Link className="net-port-device-shortcut" to={`/assets/${port.target.id}`} aria-label={`Mở thiết bị ${port.target.code} tại ${port.name}`} title={`Mở ${port.target.code}`}><DeviceVisual asset={port.target}/></Link>}
            </div>)}</div>{!ports.length&&<p className="net-port-cluster-empty">Không có cổng trong bộ lọc hoặc trang này.</p>}
          </section>;
        })}</div></div>
        {!filtered.length&&<div className="net-empty">{slots.length?'Không có cổng phù hợp với bộ lọc.':'Chưa có dữ liệu phù hợp. Khai báo số cổng hoặc thêm kết nối để bắt đầu.'}</div>}
        {pages>1&&<div className="net-port-pagination"><Button variant="outline" size="sm" aria-label="Trang cổng trước" disabled={currentPage===1} onClick={()=>setPage(currentPage-1)}><ChevronLeft size={15}/></Button><Button variant="outline" size="sm" aria-label="Trang cổng tiếp" disabled={currentPage===pages} onClick={()=>setPage(currentPage+1)}><ChevronRight size={15}/></Button></div>}
        {selectedPort&&<section className="net-port-inspector" aria-label="Chi tiết kết nối cổng"><div className="net-port-inspector-title"><div><h3>{selected.asset.code} / {selectedPort.name}</h3><p>{selectedPort.target?'Đã ghi nhận kết nối vật lý':'Cổng chưa ghi nhận thiết bị kết nối'}</p></div>{onEdit&&<Button onClick={()=>onEdit(selectedPort.row||{switch_id:selected.asset.id,name:selectedPort.name})}>{selectedPort.target?'Sửa kết nối':'Gán thiết bị'}</Button>}</div>
          <div className="net-port-path"><div className="net-port-path-device"><DeviceVisual asset={selected.asset}/><strong>{selected.asset.code}</strong><small>Thiết bị nguồn</small></div><div className={`net-port-path-wire ${selectedPort.target?'connected':''}`}><span>{selectedPort.name}</span><i/></div><div className="net-port-path-device">{selectedPort.target?<Link to={`/assets/${selectedPort.target.id}`} aria-label={`Mở thiết bị ${selectedPort.target.code}`}><DeviceVisual asset={selectedPort.target}/></Link>:<DeviceVisual/>}<strong>{selectedPort.target?.code||'Chưa kết nối'}</strong><small>{selectedPort.target?.type_label||'Chọn thiết bị để gán cổng'}</small></div></div>

        </section>}
      </>:<div className="net-empty">Chưa có Router, Switch hoặc AP phù hợp để quản lý cổng.</div>}</div>
    </div>
  </section>;
}
