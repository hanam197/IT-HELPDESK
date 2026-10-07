import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Search } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Cell } from '../components/DataTable';
import type { Row } from '../api';
import { COLUMN_LABELS } from './config';
import { matchesQuery, type IpFilters, type NetworkModel } from './model';

export function NetworkSearch({ value, onChange, placeholder }: {
  value: string; onChange: (value: string) => void; placeholder: string;
}) {
  return <div className="net-search"><Search size={16}/><input
    aria-label={placeholder} placeholder={placeholder} value={value}
    onChange={event => onChange(event.target.value)}
  /></div>;
}
export function ResourceTable({ rows, columns, onRow }: {
  rows: Row[]; columns: readonly string[]; onRow?: (row: Row) => void;
}) {
  return <div className="net-table-wrap"><table className="net-table">
    <thead><tr>{columns.map(column => <th key={column}>{COLUMN_LABELS[column] ?? column}</th>)}</tr></thead>
    <tbody>{rows.map(row => <tr key={row.id} className={onRow ? 'interactive' : undefined}
      tabIndex={onRow ? 0 : undefined} onClick={() => onRow?.(row)}
      onKeyDown={event => { if (event.key === 'Enter') onRow?.(row); }}>
      {columns.map(column => <td key={column}><Cell name={column} value={row[column]}/></td>)}
    </tr>)}</tbody>
  </table>{!rows.length && <div className="net-empty">Chưa có dữ liệu phù hợp.</div>}</div>;
}
export function SubnetTable({ model, query, selectedId, onSelect, onEdit }: {
  model: NetworkModel; query: string; selectedId: number | null;
  onSelect: (subnet: Row) => void; onEdit?: (subnet: Row) => void;
}) {
  const rows = model.subnets.filter(subnet => matchesQuery({
    ...subnet, vlan_name: model.vlansById.get(subnet.vlan_id)?.name,
    vlan_tag: String(model.vlansById.get(subnet.vlan_id)?.tag ?? ''),
  }, query));
  return <div className="net-table-wrap"><table className="net-table">
    <thead><tr>{['VLAN', 'Tên', 'Subnet', 'Gateway', 'Đang dùng / Tổng', 'Sử dụng', ''].map((heading, index) => <th key={index}>{heading}</th>)}</tr></thead>
    <tbody>{rows.map(subnet => {
      const vlan = model.vlansById.get(subnet.vlan_id);
      const usage = model.subnetUsage(subnet);
      const percent = usage.total ? Math.round(usage.used / usage.total * 100) : 0;
      return <tr key={subnet.id} className={`interactive ${selectedId === subnet.id ? 'selected' : ''}`}
        tabIndex={0} onClick={() => onSelect(subnet)}
        onKeyDown={event => { if (event.key === 'Enter') onSelect(subnet); }}>
        <td>{vlan?.tag}</td><td>{vlan?.name}</td><td className="net-link">{subnet.cidr}</td>
        <td>{subnet.gateway || '—'}</td><td>{usage.used} / {usage.total.toLocaleString('vi-VN')}</td>
        <td><div className="net-progress"><i style={{ width: `${percent}%` }}/></div>{percent}%</td>
        <td>{onEdit && <button aria-label={`Sửa subnet ${subnet.cidr}`} onClick={event => {
          event.stopPropagation(); onEdit(subnet);
        }}>•••</button>}</td>
      </tr>;
    })}</tbody>
  </table>{!rows.length && <div className="net-empty">Chưa có subnet phù hợp. Thêm VLAN và subnet để bắt đầu.</div>}</div>;
}
export function IpTable({ rows, filters, onFiltersChange, selectedId, onSelect, onAdd, onEdit }: {
  rows: Row[];
  filters: IpFilters; onFiltersChange: (filters: IpFilters) => void;
  selectedId: number | null; onSelect: (row: Row) => void;
  onAdd?: () => void; onEdit?: (row: Row) => void;
}) {
  const [page, setPage] = useState(1);
  useEffect(() => { setPage(1); }, [rows, filters.query, filters.assignmentType]);
  const filtered = rows.filter(row => matchesQuery(row, filters.query)
    && (!filters.assignmentType || row.assignment_type === filters.assignmentType));
  const pages = Math.max(1, Math.ceil(filtered.length / 20));
  const currentPage = Math.min(page, pages);
  return <>
    <div className="net-tools">
      <NetworkSearch value={filters.query} onChange={query => onFiltersChange({ ...filters, query })}
        placeholder="Tìm IP, MAC, hostname, mã tài sản, trạm…"/>
      <select aria-label="Loại cấp phát" value={filters.assignmentType} onChange={event => onFiltersChange({ ...filters, assignmentType: event.target.value })}>
        <option value="">Tất cả loại</option><option>Static</option><option>DHCP</option>
      </select>
      {onAdd && <Button onClick={onAdd}><Plus size={15}/>Thêm IP</Button>}
    </div>
    <div className="net-table-wrap"><table className="net-table">
      <thead><tr>{['Địa chỉ IP', 'Hostname', 'Tài sản', 'MAC', 'Vị trí / Trạm', 'Loại', ''].map((heading, index) => <th key={index}>{heading}</th>)}</tr></thead>
      <tbody>{filtered.slice((currentPage - 1) * 20, currentPage * 20).map(row => <tr
        key={row.id} className={`interactive ${row.id === selectedId ? 'selected' : ''}`} tabIndex={0}
        onClick={() => onSelect(row)} onKeyDown={event => { if (event.key === 'Enter') onSelect(row); }}>
        <td className="net-link">{row.address}</td>
        <td>{row.hostname || '—'}</td><td>{row.asset_id
          ? <Link onClick={event => event.stopPropagation()} to={`/assets/${row.asset_id}`}>{row.asset_label}</Link> : '—'}</td>
        <td className="mono">{row.mac || '—'}</td><td>{row.location_label || '—'}</td><td>{row.assignment_type}</td>
        <td>{onEdit && <button aria-label={`Sửa ${row.address}`} onClick={event => {
          event.stopPropagation(); onEdit(row);
        }}>•••</button>}</td>
      </tr>)}</tbody>
    </table>{!filtered.length && <div className="net-empty">Chưa có địa chỉ IP phù hợp. Thêm IP để bắt đầu quản lý.</div>}</div>
    <div className="net-pagination"><span>{filtered.length} địa chỉ · Trang {currentPage} / {pages}</span>
      <Button size="sm" variant="outline" disabled={currentPage <= 1} onClick={() => setPage(currentPage - 1)}>Trước</Button>
      <Button size="sm" variant="outline" disabled={currentPage >= pages} onClick={() => setPage(currentPage + 1)}>Sau</Button>
    </div>
  </>;
}
