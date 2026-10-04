import { ArrowRightLeft, CornerDownLeft, Wrench } from 'lucide-react'
import { canWrite, type Row } from '../api'
import { QuickStockIssue } from '../Warehouse'
import type { EditorState } from './Editor'
import { Button } from './ui/button'

export function AssetRowActions({ user, asset, meta, open }: {
  user: Row; asset: Row; meta?: Row; open: (state: EditorState) => void
}) {
  const type = asset.asset_type || meta?.['asset-types']?.find((t: Row) => t.id === asset.type_id)
  const active = !['RETIRED', 'DISPOSED'].includes(asset.current_status)
  const operation = (name: string) => open({ resource: 'assets', operation: name, initial: { asset_id: asset.id } })
  return <div className="asset-row-actions" aria-label="Thao tác tài sản">
    {active && <>
      <QuickStockIssue user={user} asset={asset} compact iconOnly/>
      {(asset.warehouse_id ? canWrite(user.role, 'warehouses') : canWrite(user.role, 'operations') && type?.track_location) && <Button variant="outline" size="icon" className="row-action row-action-move" title={asset.warehouse_id ? "Điều chuyển kho" : "Điều chuyển vị trí"} aria-label={asset.warehouse_id ? "Điều chuyển kho" : "Điều chuyển vị trí"} onClick={() => operation(asset.warehouse_id ? 'warehouse-move' : 'move')}><ArrowRightLeft size={16}/></Button>}
      {!asset.warehouse_id && canWrite(user.role, 'warehouses') && <Button variant="outline" size="icon" className="row-action row-action-return" title="Thu hồi về kho" aria-label="Thu hồi về kho" disabled={!meta?.warehouses?.length} onClick={() => operation('return')}><CornerDownLeft size={16}/></Button>}
      {type?.track_maintenance && canWrite(user.role, 'maintenance') && <Button variant="outline" size="icon" className="row-action row-action-maintenance" title="Bảo trì nhanh" aria-label="Bảo trì nhanh" onClick={() => open({ resource: 'maintenance', initial: { asset_id: asset.id, technician_id: user.id } })}><Wrench size={16}/></Button>}
    </>}
  </div>
}
