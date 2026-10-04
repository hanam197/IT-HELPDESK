import type { Row } from './api'
export const deviceName=(asset:Row|undefined,meta?:Row)=>asset?[meta?.['asset-types']?.find((type:Row)=>type.id===Number(asset.type_id))?.name||asset.type_label,asset.model,String(asset.serial||'').trim().toUpperCase()].filter(Boolean).map(value=>String(value).trim()).join(' - '):''
