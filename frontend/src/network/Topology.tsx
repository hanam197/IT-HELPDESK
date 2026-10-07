import { useEffect, useMemo } from 'react';
import { Monitor, Server } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Background, Controls, Handle, MarkerType, MiniMap, Position, ReactFlow, useNodesState, type Edge, type Node, type NodeProps } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Button } from '../components/ui/button';
import type { Row } from '../api';
import type { NetworkModel } from './model';

type DeviceNode = Node<{
  asset: Row; ports: Row[]; ips: Row[]; network: boolean;
  onPort?: (port: Row) => void; onIp: (ip: Row) => void;
}, 'device'>;

function DeviceCard({ data }: NodeProps<DeviceNode>) {
  return <div className={`net-flow-device ${data.network ? 'network' : ''}`}>
    <Handle type="target" position={Position.Left} isConnectable={false}/>
    <div className="net-flow-device-title">{data.network ? <Server size={19}/> : <Monitor size={19}/>}
      <Link className="nodrag" to={`/assets/${data.asset.id}`}>{data.asset.code}</Link>
    </div>
    <span>{data.asset.type_label} · {data.asset.model || '—'}</span>
    <small>{data.asset.location_label || 'Chưa gắn vị trí'}</small>
    {data.ips.map(ip => <button className="net-physical-ip nodrag" key={ip.id} onClick={() => data.onIp(ip)}>{ip.address}</button>)}
    {data.network && <div className="net-flow-ports nodrag">{data.ports.map(port => <button key={port.id} disabled={!data.onPort} onClick={() => data.onPort?.(port)} title={port.connected_asset_id ? 'Sửa kết nối cổng' : 'Chưa ghi nhận thiết bị kết nối'}>{port.name}{!port.connected_asset_id && ' · Trống'}</button>)}
      {data.onPort && <Button size="sm" variant="outline" onClick={() => data.onPort?.({switch_id:data.asset.id})}>Thêm cổng</Button>}
    </div>}
    <Handle type="source" position={Position.Right} isConnectable={false}/>
  </div>;
}
const nodeTypes = { device: DeviceCard };

export function NetworkTopology({ model, onIp, onPort }: {
  model: NetworkModel; onIp: (ip: Row) => void; onPort?: (port: Row) => void;
}) {
  const graph = useMemo(() => {
    const assets = new Map(model.devices.map(asset => [asset.id, asset]));
    for (const port of model.ports) {
      for (const id of [port.switch_id, port.connected_asset_id]) {
        const asset = model.assetsById.get(id);
        if (asset) assets.set(asset.id, asset);
      }
    }
    const links = model.ports.filter(port => assets.has(port.switch_id) && assets.has(port.connected_asset_id));
    const incoming = new Set(links.map(port => port.connected_asset_id));
    const positions = new Map<number, {x:number;y:number}>();
    let nextRow = 0;
    // Place each device once, including disconnected components and cyclic legacy links.
    const place = (id:number, depth:number) => {
      if (positions.has(id)) return;
      const position = {x:depth * 360, y:nextRow * 260};
      positions.set(id, position);
      const children = links.filter(port => port.switch_id === id).map(port => port.connected_asset_id);
      const unplaced = children.filter(child => !positions.has(child));
      for (const child of unplaced) place(child, depth + 1);
      if (unplaced.length) {
        const rows = unplaced.map(child => positions.get(child)!.y);
        position.y = (Math.min(...rows) + Math.max(...rows)) / 2;
      } else nextRow++;
    };
    const ordered = [...assets.values()].sort((a,b) => Number(/router|firewall/i.test(b.type_label || '')) - Number(/router|firewall/i.test(a.type_label || '')));
    ordered.filter(asset => !incoming.has(asset.id)).forEach(asset => place(asset.id, 0));
    ordered.forEach(asset => place(asset.id, 0));
    const nodes:DeviceNode[] = [...assets.values()].map(asset => {
      const ports = model.ports.filter(port => port.switch_id === asset.id);
      return {id:String(asset.id),type:'device',position:positions.get(asset.id)!,data:{asset,ports,ips:model.ips.filter(ip=>ip.asset_id===asset.id),network:ports.length>0 || /router|switch|firewall|access point|^ap$|nvr/i.test(asset.type_label || ''),onPort,onIp}};
    });
    const edges:Edge[] = links.map(port => ({id:`port-${port.id}`,source:String(port.switch_id),target:String(port.connected_asset_id),type:'smoothstep',label:port.name,data:{port},markerEnd:{type:MarkerType.ArrowClosed},style:{stroke:'#3b82f6',strokeWidth:2},labelStyle:{fill:'#1d4ed8',fontWeight:600},labelBgStyle:{fill:'#eff6ff'},labelBgPadding:[8,4],labelBgBorderRadius:4}));
    return {nodes,edges};
  }, [model,onPort,onIp]);
  const [nodes,setNodes,onNodesChange] = useNodesState(graph.nodes);
  useEffect(() => {setNodes(graph.nodes)}, [graph,setNodes]);
  return <section className="net-topology" aria-label="Sơ đồ kết nối mạng">
    <header><div><h2>Kết nối vật lý</h2><p>Router → Switch → PC / thiết bị. Tên cổng hiển thị trên đường nối.</p></div></header>
    {!nodes.length ? <div className="net-empty">Thêm Router / Switch trong tài sản, sau đó ghi nhận cổng và thiết bị kết nối.</div> : <>
      <div className="net-flow-canvas">
        <ReactFlow nodes={nodes} edges={graph.edges} nodeTypes={nodeTypes} onNodesChange={onNodesChange}
          onEdgeClick={(_,edge) => {if(onPort && edge.data?.port) onPort(edge.data.port as Row)}}
          fitView fitViewOptions={{padding:0.2,maxZoom:1}} minZoom={0.1} maxZoom={2} nodesConnectable={false} edgesReconnectable={false} deleteKeyCode={null}>
          <Background gap={20} color="#dbe5f1"/><Controls showInteractive={false}/><MiniMap pannable zoomable nodeColor="#dbeafe"/>
        </ReactFlow>
      </div><p className="net-flow-hint">Kéo thiết bị để sắp xếp, kéo nền để di chuyển, cuộn để thu phóng.{onPort && ' Bấm cổng hoặc đường nối để sửa kết nối.'}</p>
    </>}
  </section>;
}
