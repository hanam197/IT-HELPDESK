import type { Row } from '../api';

export interface NetworkData {
  vlans: Row[];
  subnets: Row[];
  'ip-addresses': Row[];
  'switch-ports': Row[];
  locations: Row[];
  assets: Row[];
  devices: Row[];
  history: Row[];
}
export interface Usage {
  used: number;
  available: number;
  total: number;
}
export interface IpFilters {
  query: string;
  assignmentType: string;
}
export const EMPTY_IP_FILTERS: IpFilters = { query: '', assignmentType: '' };
export const indexRows = (rows: Row[]) => new Map<number, Row>(rows.map(row => [row.id, row]));
const normalize = (value: string) => value.toLocaleLowerCase('vi-VN').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replaceAll('đ', 'd');
export function matchesQuery(row: Row, query: string): boolean {
  const term = normalize(query.trim());
  return !term || Object.values(row).some(value => typeof value === 'string' && normalize(value).includes(term));
}
export function calculateUsage(ips: Row[], total: number): Usage {
  const used = ips.length;
  return { used, total, available: Math.max(0, total - used) };
}

// Build indexes once per response; all views use the same relationships and site scope.
export function buildNetworkModel(data: NetworkData, site: string) {
  const assetsById = indexRows(data.assets);
  const subnetsById = indexRows(data.subnets);
  const vlansById = indexRows(data.vlans);
  const locationsById = indexRows(data.locations);
  const ipsBySubnet = new Map<number, Row[]>();
  for (const ip of data['ip-addresses']) {
    const rows = ipsBySubnet.get(ip.subnet_id) ?? [];
    rows.push(ip);
    ipsBySubnet.set(ip.subnet_id, rows);
  }
  const rootSite = (id: number | null) => {
    const visited = new Set<number>();
    let location = id == null ? undefined : locationsById.get(id);
    while (location && !visited.has(location.id)) {
      if (location.kind === 'site') return location.id;
      visited.add(location.id);
      location = locationsById.get(location.parent_id);
    }
    return null;
  };
  const matchesSite = (row: Row) => {
    const siteId = row.site_id ?? subnetsById.get(row.subnet_id)?.site_id ?? rootSite(row.location_id);
    return !site || String(siteId) === site;
  };
  const ips = data['ip-addresses'].filter(matchesSite);
  const subnets = data.subnets.filter(matchesSite);
  const vlans = data.vlans.filter(matchesSite);
  const devices = data.devices.filter(matchesSite);
  const ports = data['switch-ports'].filter(port => matchesSite(assetsById.get(port.switch_id) ?? {}));
  const subnetUsage = (subnet: Row) => calculateUsage(ipsBySubnet.get(subnet.id) ?? [], subnet.total_ips);
  const usage = calculateUsage(ips, subnets.reduce((total, subnet) => total + subnet.total_ips, 0));
  return {
    assetsById, subnetsById, vlansById, ipsBySubnet, subnetUsage, usage,
    ips, subnets, vlans, devices, ports,
    sites: data.locations.filter(location => location.kind === 'site'),
  };
}
export type NetworkModel = ReturnType<typeof buildNetworkModel>;
