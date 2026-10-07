export type CatalogTab = 'ip-addresses' | 'layout' | 'subnets' | 'vlans' | 'devices' | 'switch-ports';
export const CATALOG_CONFIG = {
  "ip-addresses": {label:"Địa chỉ IP",resource:"ip-addresses",columns:[]},
  subnets: { label: 'Subnets', resource: 'subnets', columns: [] },
  vlans: { label: 'VLANs', resource: 'vlans', columns: ['tag', 'name', 'site_label', 'description'] },
  devices: { label: 'Thiết bị mạng', resource: 'assets', columns: ['code', 'type_label', 'model', 'serial', 'location_label'] },
  'switch-ports': { label: 'Cổng switch', resource: 'switch-ports', columns: ['switch_label', 'name', 'connected_asset_label'] },
  layout: {label:"Sơ đồ mạng",resource:"",columns:[]},
} as const;
export const COLUMN_LABELS: Record<string, string> = {
  tag: 'VLAN', name: 'Tên', site_label: 'Cơ sở', description: 'Mô tả',
  code: 'Mã tài sản', type_label: 'Loại', model: 'Model', serial: 'S/N',
  location_label: 'Vị trí', switch_label: 'Thiết bị nguồn', native_vlan_label: 'VLAN gốc',
  tagged_vlans_label: 'Tagged VLAN', connected_asset_label: 'Thiết bị kết nối',
  asset_label: 'Tài sản', mac: 'MAC', hostname: 'Hostname',
};
