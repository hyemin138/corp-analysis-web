import type {PageProps} from '../state';
import {transitSeries} from '../analysis';
import {atDate,COLORS,PORTS,ROUTES,STATES,series,inRange,relative,fmt,signed,stateName,VOLS} from '../domain';
import {Panel,Notice,Empty,Export} from '../components/ui';
import {TimeSeries} from '../components/TimeSeries';
import {Chart,baseOption} from '../components/Chart';
import {plotTime,plotDate} from '../calendar';

export function ContextPage({data:d,p,update,focus}:PageProps){
 const f=atDate(d.features,p.date),s=atDate(d.states,p.date),fare=inRange(series(d,p.contextIndex),p.start,p.end);
 const ports=p.portKeys.map(key=>{const points=transitSeries(d,key,p.start,p.end,p.frequency),first=points.find(x=>x.value!==null);return {key,...PORTS[key],points,zero:first?.value===0};});
 const rangeStates=d.states.filter(x=>x.date>=p.start&&x.date<=p.end);
 const cursorDates=[...new Set([...fare.map(x=>x.date),...ports.flatMap(x=>x.points.map(v=>v.date))])].sort();
 return <>
  {p.date===p.origin&&<Notice>선택일 {p.date}은 저장 예측 원점과 같은 날짜입니다. 이 화면은 회고 환경이며, 원점 당일의 일별 통항 관측이나 최초 공개시각 미검증 자료를 원점 당시 사용 가능 정보로 간주하지 않습니다.</Notice>}
  <Panel title="운임과 통항을 같은 기간에서 읽기" sub="커서와 날짜 선택은 연동하고, 서로 다른 단위는 별도 축에 표시합니다." >
   <div className="control-row"><label>운임계열<select aria-label="통합 탐색 운임" value={p.contextIndex} onChange={e=>update({contextIndex:e.target.value})}>{Object.entries(ROUTES).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label><div className="segmented"><button className={p.frequency==='weekly'?'active':''} onClick={()=>update({frequency:'weekly'})}>주간 7일평균</button><button className={p.frequency==='daily'?'active':''} onClick={()=>update({frequency:'daily'})}>일별 척수</button></div><div className="segmented"><button className={p.transitMode==='level'?'active':''} onClick={()=>update({transitMode:'level'})}>원단위</button><button className={p.transitMode==='percent'?'active':''} onClick={()=>update({transitMode:'percent'})}>기간 변화율</button></div></div>
   <TimeSeries label="동기 운임 차트" group="c-v2-context" cursorDates={cursorDates} range={[p.start,p.end]} selectedDate={p.date} onDate={focus} unit={p.transitMode==='level'?'지수 pt':'% · 운임 첫 관측 대비'} series={[{name:ROUTES[p.contextIndex],color:COLORS[0],points:p.transitMode==='level'?fare:relative(fare)}]}/>
   <div className="chips transit-chips">{Object.entries(PORTS).map(([key,v])=><button key={key} className={p.portKeys.includes(key)?'chip active':'chip'} onClick={()=>update({portKeys:p.portKeys.includes(key)?p.portKeys.filter(x=>x!==key):[...p.portKeys,key]})}>{v.name}</button>)}</div>
   {p.transitMode==='percent'&&ports.some(x=>x.zero)&&<Notice>{ports.filter(x=>x.zero).map(x=>x.name).join(', ')}의 기간 첫 유효 관측은0척입니다. 분모가0이므로 변화율을 계산하지 않습니다. 다음 비영값으로 대체하지 않으며 원단위에서0을 확인할 수 있습니다.</Notice>}
   <TimeSeries label="동기 통항 차트" group="c-v2-context" cursorDates={cursorDates} range={[p.start,p.end]} selectedDate={p.date} onDate={focus} unit={p.transitMode==='level'?(p.frequency==='weekly'?'척/일 · 직전7일평균':'컨테이너선 척/일'):'% · 경로별 첫 관측 대비'} series={ports.map(x=>({name:x.name,color:x.color,points:p.transitMode==='level'?x.points:relative(x.points).map((v,i)=>({...x.points[i],value:v.value}))}))}/>
   <p className="caption">{p.frequency==='weekly'?'통항 x축=KCCI 발표일, 값=직전7일. 커서는 가까운 실제 발표일로 맞춥니다.':'통항 x축=실제 일별 관측일. 커서는 두 차트 실제 날짜의 합집합에서 가까운 날짜로 맞춥니다.'} 같은 날짜의 레코드가 없으면 '해당일 관측 없음', 값이 결측이면 '미확보'입니다. 보간·값 대체는 하지 않으며 주간 관측창은 따로 표시합니다. 운임 첫 관측 {fare.find(x=>x.value!==null)?.date??'없음'}; {ports.map(x=>`${x.name} 기준 ${x.points.find(v=>v.value!==null)?.date??'없음'}`).join(' · ')}. 선택일 이후와 원점 당일의 일별 값도 회고 관측이며 당시 이용 가능 정보가 아닙니다.</p>
   <div className="control-row"><Export name="freight_transit_freight" label="운임 CSV" rows={fare.map(x=>({series:p.contextIndex,...x}))}/><Export name="freight_transit_observations" label="통항 CSV" rows={ports.flatMap(x=>x.points.map(v=>({route:x.key,...v,frequency:p.frequency})))}/></div>
  </Panel>
  <Panel title="그 시점의 시장 상태와 통항환경" sub={`${p.date} 선택 · 상태/특징표 실제 발표 ${s?.date??'없음'}`}>
   <div className="selected-state"><strong>{s?.primary_eligible?stateName(s.representative_regime):'전체 시장 미배정'}</strong><span>변동성 {VOLS[s?.volatility_state]??'미확인'}</span><button className="button" disabled={!s?.primary_eligible} onClick={()=>{const peers=d.states.filter(x=>x.primary_eligible&&x.representative_regime===s!.representative_regime&&x.date!==s!.date);update({view:'compare',compareState:s!.representative_regime,aDate:s!.date,bDate:peers[0]?.date??s!.date});}}>같은 상태의 다른 날짜 비교</button></div>
   <div className="table-wrap"><table><thead><tr><th>경로</th><th>7일 평균 척/일</th><th>28일 전 창 대비 %</th><th>관측창</th></tr></thead><tbody>{Object.entries(PORTS).map(([key,v])=><tr key={key}><td>{v.name}</td><td>{fmt(f?.[key+'_mean7'],2)}</td><td>{signed(f?.[key+'_pct28'])}</td><td>{f?.observation_start??'—'} ~ {f?.observation_end??'—'}{f?.[key+'_mean7']===null?' · 미확보':''}</td></tr>)}</tbody></table></div>
   {s&&!s.primary_eligible&&<Notice>대표상태 미배정 관측입니다. 통항·파생자료가 부족한 상태를 정상 관측이나0척으로 표시하지 않습니다. <button className="text-button" onClick={()=>focus(d.meta.lastCompleteDate)}>마지막 완전입력일 {d.meta.lastCompleteDate}로 이동</button></Notice>}
   <Chart label="시장 상태 타임라인" height={290} onAxisDate={t=>{const a=rangeStates.filter(x=>x.primary_eligible);if(a.length)focus(a.reduce((x,y)=>Math.abs(plotTime(x.date)-t)<Math.abs(plotTime(y.date)-t)?x:y).date);}} onClick={e=>{if(e.value?.[0])focus(typeof e.value[0]==='number'?plotDate(e.value[0]):String(e.value[0]));}} option={{...baseOption,grid:{...baseOption.grid,left:120},xAxis:{...baseOption.xAxis,min:plotTime(p.start),max:plotTime(p.end)},legend:{show:false},tooltip:{trigger:'item',confine:true,formatter:(v:any)=>`${plotDate(v.value[0])} · ${stateName(v.value[2])}`},yAxis:{type:'category',data:STATES.map(stateName),axisLabel:{fontSize:11}},series:[{type:'scatter',symbolSize:11,data:rangeStates.filter(x=>x.primary_eligible).map(x=>({value:[plotTime(x.date),STATES.indexOf(x.representative_regime),x.representative_regime],itemStyle:{color:COLORS[STATES.indexOf(x.representative_regime)]}}))}]}}/>
   <p className="caption">타임라인의 점을 선택하면 공통 날짜가 바뀝니다. 미배정 발표는 점이 없습니다. 62구간·53전환은 유효 발표 간 규칙 라벨 결과이며 구조변화점 수가 아닙니다.</p>
  </Panel>
  <Notice>PortWatch는 최종 관측 {d.meta.lastTransitDate}까지의 보관 자료입니다. 관측일과 최초 공개시각은 다릅니다. 최초 공개 빈티지는 미검증이며 수에즈 감소분이 모두 희망봉으로 이동했다거나 통항 변화가 운임의 원인이라고 판단하지 않습니다.</Notice>
 </>;
}
