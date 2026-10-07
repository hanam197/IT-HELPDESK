import { useMemo, useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { Plus } from 'lucide-react';
import { canWrite, type Row } from './api';
import { Button } from './components/ui/button';
import type { EditorState } from './components/Editor';
import { CATALOG_CONFIG, type CatalogTab } from './network/config';
import { buildNetworkModel, EMPTY_IP_FILTERS, matchesQuery, type IpFilters } from './network/model';
import { useNetworkData } from './network/useNetwork';
import { IpTable, NetworkSearch, ResourceTable, SubnetTable } from './network/Tables';
import { IpDetail, NetworkHistory, NetworkOverview, SubnetPanel } from './network/Panels';
import { SwitchPorts } from './network/SwitchPorts';
import { NetworkTopology } from './network/Topology';
import './network.css';

export function NetworkWorkspace({ user, open }: { user: Row; open: (state: EditorState) => void }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [site, setSite] = useState('');
  const [catalog, setCatalog] = useState<CatalogTab>('ip-addresses');
  const [catalogQuery, setCatalogQuery] = useState('');
  const [ipFilters, setIpFilters] = useState<IpFilters>(EMPTY_IP_FILTERS);
  const [subnetId, setSubnetId] = useState<number | null>(null);
  const [ipId, setIpId] = useState<number | null>(null);
  const { data, error, isLoading } = useNetworkData();
  const model = useMemo(() => data ? buildNetworkModel(data, site) : null, [data, site]);
  if (location.pathname !== '/network'||location.search) return <Navigate replace to="/network"/>;
  if (isLoading) return <div className="loading">Đang tải không gian mạng…</div>;
  if (error) return <div className="error" role="alert">{error.message}</div>;
  if (!data || !model) return null;

  const writable = canWrite(user.role, 'ip-addresses');
  const visibleSubnets = model.subnets.filter(subnet=>matchesQuery({...subnet,vlan_name:model.vlansById.get(subnet.vlan_id)?.name,vlan_tag:String(model.vlansById.get(subnet.vlan_id)?.tag??'')},catalogQuery));
  const selectedSubnet = catalog==='subnets' ? visibleSubnets.find(subnet => subnet.id === subnetId) ?? visibleSubnets[0] : undefined;
  const selectedIp = model.ips.find(ip => ip.id === ipId);
  const edit = (resource: string, row?: Row) => open({ resource, initial: row, edit: !!row?.id });
  const selectSubnet = (subnet: Row) => {
    setSubnetId(subnet.id);
    setIpId(null);
    setIpFilters(EMPTY_IP_FILTERS);
  };
  const selectIp = (ip: Row) => setIpId(ip.id);
  const addIp = () => edit('ip-addresses', {
    assignment_type: 'Static',
    ...(selectedSubnet ? { subnet_id: selectedSubnet.id } : {}),
  });
  const ipTable = (rows: Row[]) => <IpTable
    rows={rows}
    filters={ipFilters} onFiltersChange={setIpFilters} selectedId={ipId} onSelect={selectIp}
    onAdd={writable ? addIp : undefined} onEdit={writable ? ip => edit('ip-addresses', ip) : undefined}
  />;
  const activeCatalog = catalog;
  const catalogConfig = CATALOG_CONFIG[activeCatalog];
  const catalogRows = { 'ip-addresses':model.ips,layout:[],subnets: model.subnets, vlans: model.vlans, devices: model.devices, 'switch-ports': model.ports }[activeCatalog];
  const catalogView = <section className="net-card net-list">
    {<div className="net-tabs" role="tablist" aria-label="Danh sách mạng">
      {(Object.keys(CATALOG_CONFIG) as CatalogTab[]).map(key=><button type="button" role="tab" aria-selected={activeCatalog===key} className={activeCatalog===key?'active':''} key={key} onClick={()=>{setCatalog(key);setCatalogQuery('');setSubnetId(null);setIpId(null);setIpFilters(EMPTY_IP_FILTERS)}}>{CATALOG_CONFIG[key].label}</button>)}
    </div>}
    {activeCatalog!=='ip-addresses'&&activeCatalog!=='layout'&&activeCatalog!=='switch-ports'&&<>    <div className="net-tools"><NetworkSearch value={catalogQuery} onChange={setCatalogQuery}
      placeholder={activeCatalog === 'subnets' || activeCatalog === 'vlans' ? 'Tìm subnet, VLAN, gateway…' : 'Tìm thiết bị, VLAN, cổng…'}/>
      {writable && activeCatalog !== 'devices' && <Button variant="outline" onClick={() => edit(catalogConfig.resource)}><Plus size={15}/>Thêm {catalogConfig.label}</Button>}
    </div>
</>}
    {activeCatalog==='ip-addresses' ? ipTable(model.ips)
      : activeCatalog==='layout' ? <NetworkTopology model={model} onPort={writable ? port => edit('switch-ports', port) : undefined} onIp={ip=>{setCatalog('ip-addresses');selectIp(ip)}}/>
      : activeCatalog==='switch-ports' ? <SwitchPorts model={model} onEdit={writable ? port=>edit('switch-ports',port) : undefined}/>
      : activeCatalog === 'subnets'
      ? <SubnetTable model={model} query={catalogQuery} selectedId={selectedSubnet?.id??null} onSelect={selectSubnet} onEdit={writable ? subnet => edit('subnets', subnet) : undefined}/>
      : <ResourceTable rows={catalogRows.filter(row => matchesQuery(row, catalogQuery))} columns={catalogConfig.columns}
        onRow={activeCatalog === 'devices' ? row => navigate(`/assets/${row.id}`) : writable ? row => edit(catalogConfig.resource, row) : undefined}/>
    }
  </section>;

  return <div className="net-workspace">
    <div className="page-heading"><div><h1>Mạng / IPAM</h1><p>Quản lý VLAN, subnet, địa chỉ IP và thiết bị mạng</p></div>
      <div className="heading-actions"><label className="net-site">Cơ sở<select value={site} onChange={event => {
        setSite(event.target.value); setSubnetId(null); setIpId(null);
      }}><option value="">Tất cả cơ sở</option>{model.sites.map(row => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label>
        {writable && <><Button onClick={addIp}><Plus size={16}/>Thêm IP</Button>
          <Button onClick={() => edit('subnets')}><Plus size={16}/>Thêm subnet</Button>
          <Button onClick={() => navigate('/warehouses')}><Plus size={16}/>Thêm thiết bị</Button></>}
      </div>
    </div>
    <div className={`net-layout ${selectedIp ? 'has-detail' : ''}`}><div className="net-main">
      <NetworkOverview model={model}/>
      {catalogView}
      {selectedSubnet&&<SubnetPanel subnet={selectedSubnet} model={model}
        onEdit={writable ? () => edit('subnets', selectedSubnet) : undefined}>
        {ipTable(model.ipsBySubnet.get(selectedSubnet.id) ?? [])}
        <Button variant="outline" onClick={()=>{setCatalog('ip-addresses');setSubnetId(null);setIpId(null);setIpFilters(EMPTY_IP_FILTERS)}}>Xem tất cả IP</Button>
      </SubnetPanel>}

      <details className="net-history-section"><summary>Lịch sử mạng</summary><NetworkHistory events={data.history}/></details>
    </div>
      {selectedIp && <IpDetail ip={selectedIp} model={model} history={data.history} onClose={() => setIpId(null)}
        onEdit={writable ? () => edit('ip-addresses', selectedIp) : undefined}
        />
      }
    </div>
  </div>;
}
