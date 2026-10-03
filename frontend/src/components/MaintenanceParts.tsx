import { Link } from 'react-router-dom'
import { X,Package } from 'lucide-react'
import type { Row } from '../api'
import { Button } from './ui/button'
export function MaintenanceParts({ids,meta,assetId,onChange,disabled=false,records=[],hideEmpty=false,lockedIds=[]}:{ids:number[],meta?:Row,assetId?:number,onChange?:(ids:number[])=>void,disabled?:boolean,records?:Row[],hideEmpty?:boolean,lockedIds?:number[]}){
 const selected=ids.map(id=>records.find(r=>r.id===id)||meta?.assets.find((r:Row)=>r.id===id)||{id,code:`#${id}`})
 const options=(meta?.assets||[]).filter((r:Row)=>r.id!==assetId&&!ids.includes(r.id)&&r.warehouse_id&&r.current_status==='AVAILABLE'&&['linh kiện','component','components'].includes((meta?.['asset-types'].find((t:Row)=>t.id===r.type_id)?.name||'').trim().toLocaleLowerCase()))
 return <div className="maintenance-parts-picker">
  {onChange&&<select aria-label="Chọn linh kiện trong kho" value="" disabled={disabled||!meta} onChange={e=>{if(e.target.value)onChange([...ids,Number(e.target.value)])}}><option value="">{options.length?'Chọn linh kiện để xuất kho…':'Không có linh kiện sẵn sàng trong kho'}</option>{options.map((r:Row)=><option key={r.id} value={r.id}>{r.code} · {r.model||r.name} · {r.warehouse_label||meta?.warehouses.find((w:Row)=>w.id===r.warehouse_id)?.name}</option>)}</select>}
  <div className="maintenance-selected-parts">{selected.length?selected.map(r=><div className="maintenance-part" key={r.id}><Package size={17}/><Link to={'/assets/'+r.id}><strong>{r.model||r.code}</strong><span>{[r.code,r.serial].filter(Boolean).join(' · ')}</span></Link>{onChange&&!lockedIds.includes(r.id)&&<Button type="button" variant="ghost" size="icon" disabled={disabled} aria-label={'Bỏ linh kiện '+r.code} onClick={()=>onChange(ids.filter(id=>id!==r.id))}><X size={14}/></Button>}</div>):!hideEmpty&&<div className="maintenance-parts-empty">Chưa chọn linh kiện</div>}</div>
 </div>
}
