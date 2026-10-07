import { Camera, Laptop, Monitor, Printer, Server, Wifi } from 'lucide-react';
import type { Row } from '../api';

export function DeviceVisual({asset}: {asset?:Row}) {
  if(asset?.photo_url)return <img className="net-device-photo" src={asset.photo_url} alt={`Thiết bị ${asset.code}`}/>;
  const kind=String(asset?.type_label||'').toLowerCase();
  if(/switch|router/.test(kind))return <svg className="net-device-visual" viewBox="0 0 160 72" aria-hidden="true">
    {/router/.test(kind)&&<path d="M28 34V8M132 34V8" stroke="#64748b" strokeWidth="5" strokeLinecap="round"/>}
    <rect x="6" y="30" width="148" height="34" rx="5" fill="#e2e8f0" stroke="#94a3b8"/>
    <rect x="12" y="36" width="136" height="22" rx="3" fill="#334155"/>
    {[0,1,2,3,4,5].map(index=><g key={index}><rect x={23+index*17} y="40" width="12" height="12" rx="1" fill="#0f172a" stroke="#94a3b8"/><path d={`M${26+index*17} 41v3m3-3v3m3-3v3`} stroke="#fbbf24" strokeWidth="1"/></g>)}
    <circle cx="137" cy="43" r="2" fill="#60a5fa"/><circle cx="137" cy="50" r="2" fill="#94a3b8"/>
    <path d="M17 66h9m108 0h9" stroke="#94a3b8" strokeWidth="3" strokeLinecap="round"/>
  </svg>;
  if(/access point|^ap$/.test(kind))return <div className="net-device-ap" aria-hidden="true"><Wifi size={26}/><i/></div>;
  const Icon=/printer|máy in/.test(kind)?Printer:/camera/.test(kind)?Camera:/laptop/.test(kind)?Laptop:/nvr|server/.test(kind)?Server:Monitor;
  return <Icon className="net-device-icon" size={58} strokeWidth={1.3} aria-hidden="true"/>;
}

export function PortJack({optical=false}: {optical?:boolean}) {
  if(optical)return <svg className="net-port-jack" viewBox="0 0 64 48" aria-hidden="true"><rect className="net-jack-frame" x="2" y="8" width="60" height="32" rx="3"/><rect x="8" y="14" width="48" height="20" rx="2" fill="#020617"/><rect x="14" y="18" width="14" height="12" rx="2" fill="#334155" stroke="#94a3b8"/><rect x="36" y="18" width="14" height="12" rx="2" fill="#334155" stroke="#94a3b8"/><path d="M10 12h44" stroke="#94a3b8"/></svg>;
  return <svg className="net-port-jack" viewBox="0 0 64 48" aria-hidden="true">
    <rect className="net-jack-frame" x="2" y="2" width="60" height="44" rx="4"/>
    <path className="net-jack-socket" d="M10 9h44v23H42v7H22v-7H10z"/>
    {Array.from({length:8},(_,index)=><path className="net-jack-contact" key={index} d={`M${15+index*5} 10v9`}/>)}
    <path d="M26 36h12" stroke="#64748b" strokeWidth="2"/>
  </svg>;
}
