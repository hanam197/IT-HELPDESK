import * as Dialog from '@radix-ui/react-dialog'
import { Building2, Users, Monitor, MapPin, X, Plus, LoaderCircle, ChevronRight } from 'lucide-react'
import type { Row } from '../api'
import { Button } from './ui/button'

const kinds = [
  { code: 'site', name: 'Cơ sở', hint: 'Nhà máy, văn phòng', icon: Building2 },
  { code: 'team', name: 'Bộ phận', hint: 'Thuộc một cơ sở', icon: Users },
  { code: 'station', name: 'Trạm', hint: 'Điểm đặt thiết bị', icon: Monitor },
]

export function LocationCreateDialog({ values, meta, pending, error, onChange, onSubmit, onClose }: {
  values: Row; meta?: Row; pending: boolean; error?: string;
  onChange: (patch: Row) => void; onSubmit: () => void; onClose: () => void;
}) {
  const kind = values.kind || 'station'
  const parentKind = kind === 'team' ? 'site' : 'team'
  const parentLabel = kind === 'team' ? 'Cơ sở' : 'Bộ phận'
  const parents: Row[] = (meta?.locations || []).filter((row: Row) => row.kind === parentKind)
  const parent = parents.find(row => row.id === Number(values.parent_id))
  const input = (key: string, name: string, placeholder: string, wide = false) => (
    <label className={wide ? 'wide' : ''}><span>{name}</span><input disabled={pending} value={values[key] || ''} placeholder={placeholder} onChange={e => onChange({ [key]: e.target.value })}/></label>
  )
  return <Dialog.Root open onOpenChange={open => { if (!open && !pending) onClose() }}>
    <Dialog.Portal><Dialog.Overlay className="modal-overlay"/>
      <Dialog.Content className="editor quick-maintenance-dialog location-create-dialog" aria-describedby="location-create-description">
        <header className="editor-heading"><div><span className="eyebrow">CẤU TRÚC VỊ TRÍ</span><Dialog.Title>Thêm vị trí</Dialog.Title><p id="location-create-description">Tổ chức theo Cơ sở → Bộ phận → Trạm.</p></div><Button variant="ghost" size="icon" aria-label="Đóng" disabled={pending} onClick={onClose}><X size={20}/></Button></header>
        <form onSubmit={e => { e.preventDefault(); onSubmit() }}>
          <div className="quick-maintenance-body">
            <fieldset className="location-kind-picker" disabled={pending}><legend>Cấp vị trí <b>*</b></legend><div>{kinds.map(({ code, name, hint, icon: Icon }) => <label className={kind === code ? 'selected' : ''} key={code}><input type="radio" name="location-kind" value={code} checked={kind === code} onChange={() => onChange({ kind: code, parent_id: '' })}/><Icon size={22}/><span><strong>{name}</strong><small>{hint}</small></span></label>)}</div></fieldset>
            <div className="form-grid quick-maintenance-grid">
              <label className={kind === 'site' ? 'wide' : ''}><span>Tên vị trí<b> *</b></span><input required maxLength={100} autoFocus disabled={pending} value={values.name || ''} placeholder={kind === 'site' ? 'Ví dụ: Nhà máy Quận 7' : kind === 'team' ? 'Ví dụ: Bộ phận sản xuất' : 'Ví dụ: Trạm đóng gói 01'} onChange={e => onChange({ name: e.target.value })}/></label>
              {kind !== 'site' && <label><span>{parentLabel}<b> *</b></span><select required disabled={pending || !meta} value={values.parent_id || ''} onChange={e => onChange({ parent_id: e.target.value })}><option value="">Chọn {parentLabel.toLowerCase()}</option>{parents.map(row => <option key={row.id} value={row.id}>{row.path || row.name}</option>)}</select>{meta && !parents.length && <small className="field-help">Tạo {parentLabel.toLowerCase()} trước để thêm {kind === 'team' ? 'bộ phận' : 'trạm'}.</small>}</label>}
              {input('physical_location', 'Vị trí thực tế', 'Ví dụ: Tòa D, tầng 1, khu B', true)}
            </div>
            <div className="location-path-preview"><MapPin size={16}/><span>{parent && <>{parent.path || parent.name}<ChevronRight size={13}/></>}<strong>{values.name || 'Vị trí mới'}</strong></span></div>
            <label className="location-active-toggle"><span><strong>Hoạt động</strong><small>Vị trí sẵn sàng để sử dụng.</small></span><input type="checkbox" disabled={pending} checked={!!values.active} onChange={e => onChange({ active: e.target.checked })}/></label>
            {error && <div className="error" role="alert">{error}</div>}
          </div>
          <footer className="editor-footer"><Button type="button" variant="outline" disabled={pending} onClick={onClose}>Hủy</Button><Button type="submit" disabled={pending || !meta}>{pending ? <LoaderCircle className="spin" size={16}/> : <Plus size={16}/>}Thêm vị trí</Button></footer>
        </form>
      </Dialog.Content>
    </Dialog.Portal>
  </Dialog.Root>
}
