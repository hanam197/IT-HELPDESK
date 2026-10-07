import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { Activity, AlertCircle, ArrowRight, ArrowUpRight, Boxes, Monitor, PackageCheck, Wrench } from 'lucide-react';
import { api, canWrite, formatDate, type Row } from './api';
import { eventLabels, statusLabels, vi } from './i18n';
import { Button } from './components/ui/button';
import type { EditorState } from './components/Editor';
import './dashboard.css';

const COLORS=['#2563eb','#10b981','#f59e0b','#64748b','#cbd5e1'];
const SERIES=[{key:'received',label:'Nhập tài sản',color:'#2563eb'},{key:'issued',label:'Cấp phát',color:'#10b981'},{key:'returned',label:'Thu hồi',color:'#f59e0b'},{key:'other',label:'Thao tác khác',color:'#94a3b8'}];
const shortDate=(value:string)=>value.slice(8,10)+'/'+value.slice(5,7);
const number=(value:number)=>value.toLocaleString('vi-VN');

function ActivityChart({analytics,days}: {analytics:Row;days:number}) {
  const [active,setActive]=useState<number|null>(null);
  const groups=useMemo(()=>{
    const daily:Row[]=analytics.daily||[]; const size=days>30?7:days>14?3:1;const result:Row[]=[];
    for(let start=0;start<daily.length;start+=size){
      const rows=daily.slice(start,start+size);
      const group:Row={date:rows[0].date,end:rows.at(-1)!.date,total:0,received:0,issued:0,returned:0,other:0};
      for(const row of rows)for(const key of ['total','received','issued','returned','other'])group[key]+=Number(row[key]||0);
      result.push(group);
    } return result;
  },[analytics,days]);
  const max=Math.max(1,...groups.map(group=>group.total));
  const selected=active===null?null:groups[active];
  return <>
    <div className="dash-series">{SERIES.map(series=><span key={series.key}><i style={{background:series.color}}/>{series.label}</span>)}</div>
    <div className="dash-activity-plot" aria-label="Biểu đồ hoạt động tài sản"><div className="dash-chart-axis"><span>{max}</span><span>{Math.round(max/2)}</span><span>0</span></div>
      <div className="dash-chart-bars">{groups.map((group,index)=><button key={group.date} className={active===index?'active':''} aria-label={`${shortDate(group.date)}${group.end!==group.date?` – ${shortDate(group.end)}`:''}: ${group.total} thao tác`} onMouseEnter={()=>setActive(index)} onFocus={()=>setActive(index)} onClick={()=>setActive(index)} title={SERIES.map(series=>`${series.label}: ${group[series.key]}`).join(' · ')}>
        <div className="dash-bar-track"><div className="dash-bar-stack" style={{height:`${group.total/max*100}%`}}>{SERIES.map(series=><i key={series.key} style={{background:series.color,height:`${group.total?group[series.key]/group.total*100:0}%`}}/>)}</div></div>
        <span>{groups.length<=10||index%Math.ceil(groups.length/6)===0||index===groups.length-1?shortDate(group.date):'\u00a0'}</span>
      </button>)}</div>
    </div>
    <div className="dash-chart-readout" aria-live="polite">{selected?<><strong>{shortDate(selected.date)}{selected.end!==selected.date?` – ${shortDate(selected.end)}`:''}</strong><span>{SERIES.map(series=>`${series.label}: ${selected[series.key]}`).join(' · ')}</span></>:<span>{analytics.total?'Di chuột hoặc chọn cột để xem số liệu.':'Chưa có hoạt động trong khoảng thời gian này.'}</span>}</div>
  </>;
}

export function Dashboard({open,user}: {open:(state:EditorState)=>void;user:Row}) {
  const [days,setDays]=useState(30);
  const {data,error,isLoading}=useQuery({queryKey:['dashboard',days],queryFn:()=>api(`/dashboard?days=${days}`)});
  const navigate=useNavigate();
  if(isLoading)return <div className="loading">Đang tải dữ liệu phân tích…</div>;
  if(error)return <div role="alert" className="error">{error.message}</div>;
  if(!data)return null;
  const stats=data.stats||{};
  const total=Number(stats['Total assets']||0);
  const analytics=data.analytics||{total:0,previous_total:0,daily:[]};
  const states=[{code:'IN_USE',count:Number(stats['Active assets']||0)},{code:'AVAILABLE',count:Number(stats['Available assets']||0)},{code:'MAINTENANCE',count:Number(stats['Assets under repair']||0)},{code:'RETIRED',count:Number(stats['Retired assets']||0)},{code:'DISPOSED',count:Number(stats['Disposed assets']||0)}];
  let offset=0;
  const stops=states.map((state,index)=>{const start=offset;offset+=total?state.count/total*100:0;return `${COLORS[index]} ${start}% ${offset}%`});
  const distribution=(values:Row)=>Object.entries(values||{}).map(([name,value])=>({name,count:Number(value)})).sort((a,b)=>b.count-a.count);
  const types=distribution(data.asset_type);
  const locations=distribution(data.asset_location);
  const attention:Row[]=data.attention||[];
  const change=analytics.previous_total?(analytics.total-analytics.previous_total)/analytics.previous_total*100:null;
  return <div className="dash-analytics">
    <div className="page-heading"><div><span className="eyebrow">PHÂN TÍCH VẬN HÀNH CNTT</span><h1>Tổng quan</h1><p>Theo dõi tài sản, hoạt động cấp phát và các vấn đề cần xử lý.</p></div><Button variant="outline" onClick={()=>navigate('/reports')}>Xem báo cáo<ArrowUpRight size={15}/></Button></div>
    <div className="dash-kpis">{[
      {label:'Tổng tài sản',value:total,detail:'Toàn bộ tài sản đang được quản lý',icon:Monitor,path:'/assets'},
      {label:'Đang sử dụng',value:Number(stats['Active assets']||0),detail:`${total?Math.round(Number(stats['Active assets']||0)/total*100):0}% tổng tài sản`,icon:Activity,path:'/assets?status=in_use'},
      {label:'Tài sản trong kho',value:Number(stats['Assets in warehouse']||0),detail:'Thiết bị đang lưu trong kho',icon:Boxes,path:'/inventory?tab=assets'},
      {label:'Đang bảo trì',value:Number(stats['Assets under repair']||0),detail:`${Number(stats['Phiếu bảo trì đang mở']||0)} phiếu đang mở`,icon:Wrench,path:'/assets?status=maintenance'},
    ].map(metric=><Link className="dash-kpi" to={metric.path} key={metric.label}><div><span>{metric.label}</span><metric.icon size={19}/></div><strong>{number(metric.value)}</strong><small>{metric.detail}<ArrowUpRight size={13}/></small></Link>)}</div>
    <div className="dash-analysis-row">
      <section className="dash-panel dash-trend"><header><div><h2>Hoạt động tài sản</h2><p>Nhập, cấp phát, thu hồi và các thao tác khác</p></div><select aria-label="Khoảng thời gian phân tích" value={days} onChange={event=>setDays(Number(event.target.value))}><option value={7}>7 ngày gần nhất</option><option value={30}>30 ngày gần nhất</option><option value={90}>90 ngày gần nhất</option></select></header>
        <div className="dash-trend-summary"><strong>{number(analytics.total)}</strong><span>thao tác trong {days} ngày</span><small>{change===null?'Chưa có hoạt động ở kỳ trước':`${change>=0?'+':''}${Math.round(change)}% so với ${days} ngày trước`}</small></div>
        <ActivityChart key={days} analytics={analytics} days={days}/>
      </section>
      <section className="dash-panel"><header><div><h2>Trạng thái tài sản</h2><p>Phân bổ tại thời điểm hiện tại</p></div></header>
        <div className="dash-donut-area"><div className="dash-donut" role="img" aria-label={`Phân bổ trạng thái của ${total} tài sản`} style={{background:total?`conic-gradient(${stops.join(',')})`:'#e2e8f0'}}><div><strong>{number(total)}</strong><span>Tài sản</span></div></div></div>
        <div className="dash-status-legend">{states.map((state,index)=><Link to={`/assets?status=${state.code.toLowerCase()}`} key={state.code}><i style={{background:COLORS[index]}}/><span>{statusLabels[state.code]}</span><strong>{number(state.count)}</strong><small>{total?Math.round(state.count/total*100):0}%</small></Link>)}</div>
      </section>
    </div>
    <div className="dash-distribution-row">{[{title:'Tài sản theo loại',subtitle:'Các nhóm thiết bị được quản lý',rows:types,path:(name:string)=>`/assets?type=${encodeURIComponent(name)}`,color:'#2563eb'},
      {title:'Phân bổ theo vị trí',subtitle:'5 vị trí có nhiều tài sản nhất',rows:locations.slice(0,5),path:(name:string)=>`/assets?location=${encodeURIComponent(name==='Unassigned'?'Unassigned':name)}`,color:'#10b981'}].map(chart=><section className="dash-panel" key={chart.title}><header><div><h2>{chart.title}</h2><p>{chart.subtitle}</p></div></header><div className="dash-distribution-bars">{chart.rows.slice(0,8).map(row=><Link to={chart.path(row.name)} key={row.name} title={row.name}><span>{row.name==='Unassigned'?'Chưa gán vị trí':vi(row.name)}</span><div><i style={{width:`${row.count/Math.max(1,...chart.rows.map(item=>item.count))*100}%`,background:chart.color}}/></div><strong>{number(row.count)}</strong></Link>)}</div>{!chart.rows.length&&<p className="dash-empty">Chưa có dữ liệu để hiển thị.</p>}{chart.title==='Tài sản theo loại'&&types.length>8&&<Link className="dash-text-link" to="/assets">Xem tất cả {types.length} loại tài sản →</Link>}</section>)}</div>
    <div className="dash-detail-row"><section className="dash-panel"><header><div><h2>Hoạt động gần đây</h2><p>Những thay đổi mới nhất của tài sản</p></div><Link to="/assets">Xem tài sản<ArrowUpRight size={14}/></Link></header><div className="dash-recent-list">{(data.operations||[]).slice(0,5).map((row:Row)=><Link to={`/assets/${row.asset_id}`} key={row.id}><span className="dash-event-symbol"><PackageCheck size={17}/></span><div><strong>{eventLabels[row.operation_type]||row.operation_type}</strong><small>{row.asset_label||row.asset_id}</small></div><time>{formatDate(row.operation_date)}</time></Link>)}{!data.operations?.length&&<p className="dash-empty">Chưa có thao tác tài sản.</p>}</div></section>
      <section className="dash-panel"><header><div><h2>Cần chú ý</h2><p>Các vấn đề đang cần xử lý</p></div><span className="dash-alert-count">{attention.length}</span></header>{Number(stats['Low stock items']||0)>0&&<Link className="dash-stock-alert" to="/inventory?tab=consumables"><Boxes size={16}/>{stats['Low stock items']} vật tư dưới mức tồn tối thiểu<ArrowRight size={15}/></Link>}<div className="dash-attention-list">{attention.slice(0,4).map((row,index)=><Link to={`/${row.resource}/${row.id}`} key={index}><AlertCircle size={17}/><div><strong>{row.title}</strong><small>{row.subtitle}</small></div><ArrowRight size={14}/></Link>)}{!attention.length&&<p className="dash-empty">Không có mục nào cần xử lý.</p>}</div></section>
    </div>
    <div className="dash-actions"><Link to="/warehouses"><Boxes size={16}/>Mở kho thiết bị</Link>{canWrite(user.role,'operations')&&<button onClick={()=>open({resource:'assets',operation:'move'})}><ArrowRight size={16}/>Điều chuyển tài sản</button>}{canWrite(user.role,'maintenance')&&<button onClick={()=>open({resource:'maintenance'})}><Wrench size={16}/>Bảo trì nhanh</button>}</div>
  </div>;
}
