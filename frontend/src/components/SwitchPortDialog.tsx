import * as Dialog from '@radix-ui/react-dialog';
import { X, Check, LoaderCircle } from 'lucide-react';
import type { Row } from '../api';
import { canonicalPortName, declaredPortGroups } from '../network/portGroups';
import { Button } from './ui/button';

export const supportsPorts = (type?: Row) => ['router','switch','ap','access point'].includes(String(type?.name || '').trim().toLowerCase());
export function SwitchPortDialog({values,initial,meta,pending,error,onChange,onSubmit,onClose}: {
  values:Row;initial:Row;meta?:Row;pending:boolean;error?:string;
  onChange:(patch:Row)=>void;onSubmit:()=>void;onClose:()=>void;
}) {
  const typeOf=(asset:Row)=>meta?.['asset-types'].find((type:Row)=>type.id===asset.type_id);
  const sources=(meta?.assets || []).filter((asset:Row)=>supportsPorts(typeOf(asset)));
  const source=sources.find((asset:Row)=>asset.id===Number(values.switch_id));
  const targets=(meta?.assets || []).filter((asset:Row)=>asset.id!==Number(values.switch_id)&&typeOf(asset)?.track_network);
  const groups=declaredPortGroups(source);
  const names=groups.flatMap(group=>group.names);
  const occupied=(meta?.['switch-ports'] || []).filter((port:Row)=>port.switch_id===Number(values.switch_id)&&port.id!==initial.id);
  const current=String(values.name || '');
  const legacy=current && !names.includes(current) && Number(values.switch_id)===initial.switch_id;
  return <Dialog.Root open onOpenChange={open=>{if(!open&&!pending)onClose()}}><Dialog.Portal><Dialog.Overlay className="modal-overlay"/><Dialog.Content className="editor" aria-describedby="port-description">
    <header className="editor-heading"><div><span className="eyebrow">KẾT NỐI VẬT LÝ</span><Dialog.Title>{initial.id?'Sửa kết nối cổng':'Thêm kết nối cổng'}</Dialog.Title><p id="port-description">Chọn thiết bị nguồn, cổng và thiết bị kết nối.</p></div><Button variant="ghost" size="icon" aria-label="Đóng" disabled={pending} onClick={onClose}><X size={20}/></Button></header>
    <form onSubmit={event=>{event.preventDefault();onSubmit()}}><div className="form-grid">
      <label className="wide"><span>Thiết bị nguồn (Router / Switch / AP)<b> *</b></span><select required disabled={pending||!meta} value={values.switch_id||''} onChange={event=>onChange({switch_id:event.target.value,name:'',connected_asset_id:''})}><option value="">Chọn thiết bị nguồn</option>{sources.map((asset:Row)=><option key={asset.id} value={asset.id}>{asset.code} · {asset.model}</option>)}</select></label>
      <label><span>Tên cổng<b> *</b></span>{names.length?<select required disabled={pending} value={current} onChange={event=>onChange({name:event.target.value})}><option value="">Chọn cổng</option>{legacy&&<option value={current}>{current}</option>}{groups.filter(group=>group.names.length).map(group=><optgroup label={group.label} key={group.key}>{group.names.map(name=>{
        const used=occupied.some((port:Row)=>canonicalPortName(port.name)===name);
        return <option key={name} value={name} disabled={used}>{name}{used?' · Đã ghi nhận':''}</option>;
      })}</optgroup>)}</select>:<><input required disabled={pending||!source} value={current} maxLength={40} placeholder="Ví dụ: Gi01" onChange={event=>onChange({name:event.target.value})}/>{source&&<small>Thiết bị chưa khai báo số cổng. Có thể cập nhật trong form sửa tài sản.</small>}</>}</label>
      <label><span>Thiết bị kết nối</span><select disabled={pending||!meta} value={values.connected_asset_id||''} onChange={event=>onChange({connected_asset_id:event.target.value})}><option value="">Chưa kết nối</option>{targets.map((asset:Row)=><option key={asset.id} value={asset.id}>{asset.code} · {asset.model}</option>)}</select></label>
    </div>{error&&<div role="alert" className="error">{error}</div>}<footer className="editor-footer"><Button type="button" variant="outline" disabled={pending} onClick={onClose}>Hủy</Button><Button type="submit" disabled={pending||!meta}>{pending?<LoaderCircle className="spin" size={16}/>:<Check size={16}/>}Lưu kết nối</Button></footer></form>
  </Dialog.Content></Dialog.Portal></Dialog.Root>;
}
