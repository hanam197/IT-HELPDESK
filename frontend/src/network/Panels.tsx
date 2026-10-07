import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRightLeft, ChevronRight, History, Layers, MapPin, Monitor, Network, Router, Server, Wifi, X } from 'lucide-react';
import { Button } from '../components/ui/button';
import { formatDate, type Row } from '../api';
import type { NetworkModel } from './model';

export function NetworkOverview({ model }: { model: NetworkModel }) {
  const { used, total, available } = model.usage;
  const percent = total ? Math.round(used / total * 100) : 0;
  return <div className="net-stats">
    <section className="net-card"><h3>Sử dụng IP</h3><div className="net-usage">
      <div className="net-donut" style={{ background: total
        ? `conic-gradient(#0866f5 0 ${used / total * 100}%, #20b866 ${used / total * 100}% 100%)` : '#e7edf5' }}><span>{percent}%</span></div>
      <div><strong>{used} / {total.toLocaleString('vi-VN')}</strong><small>Địa chỉ đang sử dụng</small>
        {[['used', 'Đang dùng', used], ['available', 'Chưa sử dụng', available]].map(([code, label, count]) => <div className="net-legend" key={code}><i className={String(code)}/>{label}<b>{Number(count).toLocaleString('vi-VN')}</b></div>)}
      </div>
    </div></section>
    <section className="net-card"><h3><Layers size={16}/>Subnets</h3><strong className="net-number">{model.subnets.length}</strong><small>Tổng số subnet</small><div className="net-summary-footer"><span>IPv4 <b>{model.subnets.filter(subnet=>!subnet.cidr.includes(':')).length}</b></span><span>IPv6 <b>{model.subnets.filter(subnet=>subnet.cidr.includes(':')).length}</b></span></div></section>
    <section className="net-card"><h3><Network size={16}/>VLANs</h3><strong className="net-number">{model.vlans.length}</strong><small>Tổng số VLAN</small><div className="net-summary-footer"><span>Cơ sở <b>{new Set(model.vlans.map(vlan=>vlan.site_id)).size}</b></span><span>Subnets <b>{model.subnets.length}</b></span></div></section>
    <section className="net-card"><h3><Server size={16}/>Thiết bị mạng</h3><strong className="net-number">{model.devices.length}</strong><small>Tổng thiết bị mạng</small>
      <div className="net-device-breakdown">{[
        { label:'Access Points', icon:Wifi, pattern:/access point|^ap$|bộ phát/i },
        { label:'Switches', icon:Server, pattern:/switch/i },
        { label:'Routers', icon:Router, pattern:/router|định tuyến/i },
        { label:'NVR', icon:Monitor, pattern:/nvr/i },
      ].map(group=><div key={group.label}><group.icon size={16}/><span>{group.label}</span><b>{model.devices.filter(device=>group.pattern.test(device.type_label||'')).length}</b></div>)}</div>
    </section>
  </div>;
}
export function SubnetPanel({ subnet, model, onEdit, children }: {
  subnet: Row; model: NetworkModel; onEdit?: () => void; children: ReactNode;
}) {
  const vlan = model.vlansById.get(subnet.vlan_id);
  const usage = model.subnetUsage(subnet);
  const metrics = [
    ['Gateway', subnet.gateway || '—'],
    ['DHCP Range', subnet.dhcp_start ? `${subnet.dhcp_start} → ${subnet.dhcp_end}` : 'Chưa cấu hình'],
    ['Tổng IP', usage.total], ['Đang dùng', usage.used], ['Chưa sử dụng', usage.available],
  ];
  const metricIcons = [Network, ArrowRightLeft, Layers, Monitor, Server];
  return <section className="net-card net-subnet">
    <div className="net-subnet-head"><div>
      <small>Mạng / IPAM <ChevronRight size={12}/> VLAN {vlan?.tag} <ChevronRight size={12}/> {subnet.cidr}</small>
      <h2>{vlan?.name}<span className="net-vlan-tag">VLAN {vlan?.tag}</span></h2><p>{subnet.cidr}</p>
    </div>{onEdit && <Button variant="outline" onClick={onEdit}>Sửa subnet</Button>}</div>
    <div className="net-subnet-metrics">{metrics.map(([label, value], index) => { const Icon=metricIcons[index]; return <div key={label}><Icon size={19}/><small>{label}</small><strong>{value}</strong></div>; })}</div>
    {children}
  </section>;
}
function DetailBlock({ title, icon, values }: { title: string; icon: ReactNode; values: Record<string, ReactNode> }) {
  return <section className="net-detail-block"><h3>{icon}{title}</h3><dl>{Object.entries(values).map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value ?? '—'}</dd></div>)}</dl></section>;
}
export function IpDetail({ ip, model, history, onClose, onEdit }: {
  ip: Row; model: NetworkModel; history: Row[]; onClose: () => void;
  onEdit?: () => void;
}) {
  const asset = model.assetsById.get(ip.asset_id);
  const subnet = model.subnetsById.get(ip.subnet_id);
  const events = history.filter(event => event.object_type === 'ip-addresses' && event.object_id === ip.id).slice(0, 5);
  return <aside className="net-card net-detail">
    <div className="net-detail-title"><h2>{ip.address}</h2><button aria-label="Đóng chi tiết IP" onClick={onClose}><X size={18}/></button></div>
    <div className="net-detail-badges"><span className="net-badge">{ip.assignment_type}</span></div>
    <DetailBlock title="Mạng" icon={<Network size={17}/>} values={{ VLAN: ip.vlan_label, Subnet: subnet?.cidr, Gateway: subnet?.gateway }}/>
    <DetailBlock title="Thiết bị" icon={<Monitor size={17}/>} values={{
      Hostname: ip.hostname, 'Địa chỉ MAC': ip.mac,
      'Tài sản': ip.asset_id ? <Link to={`/assets/${ip.asset_id}`}>{ip.asset_label}</Link> : undefined,
      'Loại thiết bị': asset?.type_label, Hãng: asset?.brand, Model: asset?.model, 'Số sê-ri': asset?.serial,
    }}/>
    <DetailBlock title="Vị trí" icon={<MapPin size={17}/>} values={{ 'Vị trí / Trạm': ip.location_label }}/>
    <DetailBlock title="Kết nối" icon={<ArrowRightLeft size={17}/>} values={{ Switch: ip.switch_label, Port: ip.port, VLAN: ip.vlan_label }}/>
    <DetailBlock title="Cấp phát" icon={<Wifi size={17}/>} values={{ Loại: ip.assignment_type }}/>
    <h3>Ghi chú</h3><p className="net-note">{ip.description || 'Chưa có ghi chú'}</p>
    <h3><History size={16}/>Lịch sử <a href="#network-history">Xem tất cả</a></h3>
    <div className="net-mini-history">{events.map(event => <div key={event.id}><small>{formatDate(event.created_at)}</small><span>{event.event} · {event.actor}</span></div>)}
      {!events.length && <small>Chưa có lịch sử.</small>}
    </div>
    <footer>
      {onEdit && <Button onClick={onEdit}>Sửa</Button>}
      {ip.asset_id && <Link className="net-view-asset" to={`/assets/${ip.asset_id}`}>Xem tài sản</Link>}
    </footer>
  </aside>;
}
export function NetworkHistory({ events }: { events: Row[] }) {
  return <section id="network-history" className="net-card"><h2>Lịch sử mạng</h2><p>500 thay đổi gần nhất: gán, thu hồi IP và cập nhật IP / VLAN / thiết bị.</p>
    <div className="net-history">{events.filter(event=>event.object_type!=='interfaces').map(event => <article key={event.id}><History size={16}/><div>
      <strong>{event.event} · {event.object_type} #{event.object_id}</strong><small>{formatDate(event.created_at)} · {event.actor}</small>
      <details><summary>Xem thay đổi</summary><pre>{JSON.stringify({ truoc: publicSnapshot(event.old_value), sau: publicSnapshot(event.new_value) }, null, 2)}</pre></details>
    </div></article>)}{!events.length && <div className="net-empty">Chưa có lịch sử.</div>}</div>
  </section>;
}

function publicSnapshot(snapshot: Row | null) { return snapshot ? Object.fromEntries(Object.entries(snapshot).filter(([key]) => !['status_id', 'interface_id'].includes(key))) : null; }
