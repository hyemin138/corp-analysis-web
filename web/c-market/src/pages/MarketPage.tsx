import {useState} from 'react';
import type {ReactNode} from 'react';
import type {PageProps} from '../state';
import {routeDivergence,kcciPeriodComparison,FLAT_BAND} from '../analysis';
import {COLORS,ROUTES,series,inRange,relative,selectedMetrics,fmt,signed,change} from '../domain';
import {Panel,Stat,Notice,Export,Empty} from '../components/ui';
import {TimeSeries} from '../components/TimeSeries';
import {Chart} from '../components/Chart';

export function MarketPage({data:d,p,update,focus,insights}:PageProps&{insights:ReactNode}){
 const [mode,setMode]=useState<'level'|'percent'>('percent');
 const current=selectedMetrics(d,p.index,p.date,p.start),a=routeDivergence(d,p.routeKeys,p.start,p.end);
 const reference=kcciPeriodComparison(d,a),kc=reference.change,opposite=reference.opposite;
 const toggle=(key:string,field:'routeKeys'|'freightKeys')=>update({[field]:p[field].includes(key)?p[field].filter(x=>x!==key):[...p[field],key]});
 return <>
  <div className="stats"><Stat label={`${p.index} · 선택일 이하 최신 관측`} value={fmt(current.now?.value,2)} unit="pt" sub={current.now?.date}/><Stat label="직전 발표 대비" value={signed(current.weekly)} unit={current.weekly===null?'':'%'} sub={`비교 ${current.prev?.date??'미확보'}`}/><Stat label="최근 8회 변동성" value={fmt(current.volatility,4)} sub="1발표 ln변화 표준편차 · 비연율화"/></div>
  {insights}
  <Panel title="국제운임의 흐름" sub="출발지·항로·기준이 다른 지수입니다. 상대변화도 동일 계약운임을 뜻하지 않습니다." actions={<div className="segmented"><button className={mode==='percent'?'active':''} onClick={()=>setMode('percent')}>기간 변화율</button><button className={mode==='level'?'active':''} onClick={()=>setMode('level')}>원지수</button></div>}>
   <div className="control-row"><label>선택일 KPI<select aria-label="KPI 지표" value={p.index} onChange={e=>update({index:e.target.value})}>{['KCCI','SCFI','CCFI'].map(x=><option key={x}>{x}</option>)}</select></label><div className="chips">{['KCCI','SCFI','CCFI'].map(x=><button key={x} className={p.freightKeys.includes(x)?'chip active':'chip'} onClick={()=>toggle(x,'freightKeys')}>{x}</button>)}</div><Export name="freight_period" rows={p.freightKeys.flatMap(key=>inRange(series(d,key),p.start,p.end).map(x=>({series:key,...x})))}/></div>
   <TimeSeries label="국제운임 흐름" selectedDate={p.date} onDate={focus} unit={mode==='percent'?'% · 각 지표 첫 유효 관측 대비':'지수 pt'} series={p.freightKeys.map((key,i)=>{const points=inRange(series(d,key),p.start,p.end);return {name:key,color:COLORS[i],points:mode==='percent'?relative(points):points};})}/>
   <p className="caption">{p.freightKeys.map(key=>{const s=inRange(series(d,key),p.start,p.end);return `${key} 기준 ${s.find(x=>x.value!==null)?.date??'없음'}`;}).join(' · ')}. 지표별 기준일이 다를 수 있습니다. 선택일 오른쪽은 이후의 회고 관측입니다.</p>
  </Panel>
  <Panel title="종합지수가 가리는 항로별 차이" sub="선택 항로의 공통 관측일로만 기준100과 기간 변화율을 계산합니다." actions={<button className="button" onClick={()=>update({routeKeys:Object.keys(ROUTES).filter(k=>!['KCCI','EUMED'].includes(k))})}>전체 13항로</button>}>
   <div className="chips routes">{Object.entries(ROUTES).filter(([k])=>k!=='KCCI').map(([key,name])=><button key={key} className={p.routeKeys.includes(key)?'chip active':'chip'} onClick={()=>toggle(key,'routeKeys')}>{name}</button>)}</div>
   <div className="analysis-band"><div><small>공통 비교기간</small><b>{a.baseDate??'없음'} → {a.endDate??'없음'}</b></div><div><small>최대–최소 격차 · 선택{p.routeKeys.length}개</small><b data-testid="route-spread">{fmt(a.spread,2)} {a.spread===null?'':'%p'}</b></div><div><small>기간 방향 · ±{FLAT_BAND}% 내 횡보</small><b>상승 {a.counts.rising} / 횡보 {a.counts.sideways} / 하락 {a.counts.falling}</b></div></div>
   {a.status!=='OK'&&<Notice>{a.status==='NO_SELECTION'?'비교할 항로를 선택하세요.':a.status==='ONE_OBSERVATION'?'공통 관측이1회뿐이어서 기간 변화와 격차를 계산하지 않습니다.':'공통 유효 기준일이 없어 서로 다른 시작일을 같은 기준일로 표시하지 않습니다.'}</Notice>}
   {a.rows.some(x=>x.reason)&&<Notice>{a.rows.filter(x=>x.reason).map(x=>`${x.name}: ${x.reason}`).join(' / ')}</Notice>}
   <TimeSeries label="항로 기준100 비교" selectedDate={p.date} onDate={focus} unit="공통 기준일=100" series={a.rows.map((x,i)=>({name:x.name,color:COLORS[i%COLORS.length],points:x.points}))}/>
   <div className="split"><div>{a.ranked.length?<Chart label="항로 변화율 순위" height={Math.max(230,a.rows.length*30)} option={{tooltip:{trigger:'axis',confine:true,valueFormatter:(v:number)=>fmt(v,2)+'%'},grid:{left:122,right:35,top:15,bottom:30},xAxis:{type:'value',name:'%'},yAxis:{type:'category',inverse:true,data:a.ranked.map(x=>x.name)},series:[{type:'bar',barMaxWidth:18,data:a.ranked.map(x=>({value:x.change,itemStyle:{color:x.change!>=0?'#2763cc':'#15978f'}}))}]}}/>:<Empty/>}</div><div className="reading" data-testid="kcci-period-comparison"><h3>KCCI와 다른 방향의 항로</h3><p>{reference.performed?`같은 기준일의 KCCI 변화 ${signed(kc)}%. 상승과 하락이 반대인 항로는 ${opposite.length}개입니다.`:'KCCI 변화 — · 공통 기간 관측이 부족하여 방향 비교 미실시.'}</p><p>{reference.performed?(opposite.map(x=>x.name).join(', ')||'비교 가능한 반대 방향 항로 없음'):'공통 유효 관측이 2회 이상일 때 비교합니다.'}</p><small>±1% 횡보는 이 기간의 표시 규칙이며 C v4 상태 방향 임계값을 바꾸지 않습니다. EUMED는 (2×KNEI+KMDI)/3 시장 대리지표입니다.</small></div></div>
   <details className="detail-block"><summary>항로별 실제값·기간 변화와 CSV</summary><div className="control-row"><Export name="route_divergence" rows={a.rows.map(({points,...x})=>x)}/></div><div className="table-wrap"><table><thead><tr><th>항로</th><th>공통 기준일</th><th>기준값</th><th>끝 발표일</th><th>끝값</th><th>변화율 %</th><th>제한</th></tr></thead><tbody>{a.rows.map(x=><tr key={x.key}><td>{x.name}</td><td>{x.baseDate??'—'}</td><td>{fmt(x.base,2)}</td><td>{x.endDate??'—'}</td><td>{fmt(x.end,2)}</td><td>{signed(x.change)}</td><td>{x.reason??'비교 가능'}</td></tr>)}</tbody></table></div></details>
  </Panel>
 </>;
}
