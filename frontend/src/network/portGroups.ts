import type { Row } from '../api';
export const PORT_GROUPS = [
  {key:'normal',label:'Cổng thường',field:'port_count',prefix:'Gi'},
  {key:'uplink',label:'Uplink',field:'uplink_port_count',prefix:'Uplink'},
  {key:'sfp',label:'Cổng quang SFP',field:'sfp_port_count',prefix:'SFP'},
] as const;
export function canonicalPortName(name:string) {
  const match=/^(Gi|Uplink|SFP)0*(\d+)$/i.exec(name);
  if(!match)return name;
  const group=PORT_GROUPS.find(group=>group.prefix.toLowerCase()===match[1].toLowerCase())!;
  return `${group.prefix}${String(Number(match[2])).padStart(2,'0')}`;
}
export function declaredPortGroups(asset?:Row) {
  return PORT_GROUPS.map(group=>({...group,names:Array.from({length:asset?.[group.field]||0},(_,index)=>`${group.prefix}${String(index+1).padStart(2,'0')}`)}));
}
