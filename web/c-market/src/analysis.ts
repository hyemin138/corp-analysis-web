import type {MarketData,Row} from './data/provider';
import {atDate,change,evaluationRows,isNumber,metrics,PORTS,ROUTES,series,shiftDate,signed,fmt,stateName,VOLS} from './domain.ts';

export const FLAT_BAND=1; // Period simple-return display only; never replaces v4 direction thresholds.
export type PeriodDirection='rising'|'sideways'|'falling'|'unavailable';
export const periodDirection=(value:number|null):PeriodDirection=>{if(value===null)return 'unavailable';const rounded=Math.round(value*1e9)/1e9;return rounded>FLAT_BAND?'rising':rounded< -FLAT_BAND?'falling':'sideways';};
export interface RouteComparison {
 key:string;name:string;baseDate:string|null;endDate:string|null;base:number|null;end:number|null;
 change:number|null;direction:PeriodDirection;points:{date:string;value:number|null}[];reason:string|null;
}
export function routeDivergence(data:MarketData,keys:string[],start:string,end:string){
 const unique=[...new Set(keys)];
 const all=unique.map(key=>({key,points:series(data,key).filter(x=>x.date>=start&&x.date<=end)}));
 const dates=all.length?all[0].points.filter(x=>isNumber(x.value)).map(x=>x.date).filter(date=>all.every(a=>a.points.some(x=>x.date===date&&isNumber(x.value)))):[];
 const first=dates[0]??null,last=dates.at(-1)??null;
 const rows:RouteComparison[]=all.map(a=>{
  const base=a.points.find(x=>x.date===first)?.value??null,endValue=a.points.find(x=>x.date===last)?.value??null;
  const reason=!first?'공통 유효 관측일 없음':dates.length<2?'공통 관측 1회: 기간 변화 비교 불가':base===0?'공통 기준값 0: 정규화·변화율 계산 불가':null;
  const delta=reason?null:change(endValue,base);
  return {key:a.key,name:ROUTES[a.key]??a.key,baseDate:first,endDate:last,base,end:endValue,change:delta,direction:periodDirection(delta),reason,
   points:a.points.filter(x=>first!==null&&last!==null&&x.date>=first&&x.date<=last).map(x=>({date:x.date,value:base===null||base===0||x.value===null?null:100*x.value/base}))};
 });
 const valid=rows.filter(x=>x.change!==null),ranked=[...valid].sort((a,b)=>b.change!-a.change!||a.key.localeCompare(b.key));
 return {rows,baseDate:first,endDate:last,commonN:dates.length,ranked,spread:valid.length>=2?ranked[0].change!-ranked.at(-1)!.change!:null,
  counts:{rising:valid.filter(x=>x.direction==='rising').length,sideways:valid.filter(x=>x.direction==='sideways').length,falling:valid.filter(x=>x.direction==='falling').length},
  status:!unique.length?'NO_SELECTION':!dates.length?'NO_COMMON_DATE':dates.length<2?'ONE_OBSERVATION':'OK'};
}
export function fourReleaseChange(data:MarketData,key:string,date:string){
 const a=series(data,key).filter(x=>x.date<=date),last=a.at(-1),base=a.at(-5);
 return {date:last?.date??null,baseDate:base?.date??null,value:change(last?.value,base?.value)};
}
export function kcciPeriodComparison(data:MarketData,analysis:ReturnType<typeof routeDivergence>){
 const points=series(data,'KCCI'),base=points.find(x=>x.date===analysis.baseDate),end=points.find(x=>x.date===analysis.endDate);
 const delta=analysis.status==='OK'&&analysis.commonN>=2?change(end?.value,base?.value):null;
 const direction=periodDirection(delta);
 return {change:delta,performed:delta!==null,opposite:analysis.rows.filter(x=>x.direction!=='unavailable'&&x.direction!=='sideways'&&direction!=='sideways'&&direction!=='unavailable'&&x.direction!==direction)};
}
export function transitSeries(data:MarketData,key:string,start:string,end:string,frequency:'daily'|'weekly'){
 return frequency==='daily'?data.transit.filter(x=>x.portid===PORTS[key].id&&x.date>=start&&x.date<=end).map(x=>({date:x.date,value:x.n_container as number|null,observation_start:x.date,observation_end:x.date})):
 data.features.filter(x=>x.date>=start&&x.date<=end).map(x=>({date:x.date,value:x[key+'_mean7'] as number|null,observation_start:x.observation_start as string,observation_end:x.observation_end as string}));
}
export interface Observation {id:string;title:string;text:string;value:number|null;unit:string;source:string;formula:string;dates:string[];condition:string;question:string;limitation:string}
export function interpretMarket(data:MarketData,date:string,start:string,end:string,routeKeys:string[],portKeys:string[]):Observation[]{
 const state=atDate(data.states,date),f=atDate(data.features,date),k=series(data,'KCCI').filter(x=>x.date<=date),now=k.at(-1),prev=k.at(-2);
 const route=routeDivergence(data,routeKeys,start,end),ports=portKeys.map(key=>({key,pct:f?.[key+'_pct28']})).filter(x=>isNumber(x.pct)).sort((a,b)=>Math.abs(b.pct)-Math.abs(a.pct));
 const top=ports[0],log4=isNumber(f?.change_4_release)?100*f.change_4_release:null;
 return [
  {id:'OBS-KCCI',title:'선택 시점의 운임',value:now?.value??null,unit:'pt',text:now?`${now.date} KCCI ${now.value?.toLocaleString('ko-KR')}pt, 직전 발표 대비 ${signed(change(now.value,prev?.value))}%.`:'선택일 이전 운임 관측이 없습니다.',source:'routes / kcci_routes_weekly.csv',formula:'100 × (선택일 이하 최신 / 직전 발표 − 1)',dates:[now?.date,prev?.date].filter(Boolean) as string[],condition:'발표일≤선택일; 직전값0·결측이면 변화율 미표시',question:'시장 지수와 실제 판매·매입 계약운임의 조정 시점은 같은가?',limitation:'KCCI는 회사 계약운임·이익이 아니다.'},
  {id:'OBS-STATE',title:'방향과 변동성',value:log4,unit:'100ln',text:state?`${state.primary_eligible?stateName(state.representative_regime):'전체 시장 미배정'} · 4발표 변화 ${signed(log4)} 100ln · 변동성 ${VOLS[state.volatility_state]??'미확인'}.`:'판정 가능한 상태가 없습니다.',source:'states + features / 기존 C v4.1',formula:'기존 change_4_release×100; volatility_8_release와 고정 임계값 보존',dates:[state?.date,f?.date].filter(Boolean) as string[],condition:'대표상태는 primary_eligible=true만 사용; 부분 운임축과 구분',question:'선택 시점이 안정된 운임 변화인가, 변동이 큰 구간인가?',limitation:'9상태는 설명용 규칙이며 자연 군집·위험등급이 아니다.'},
  {id:'OBS-ROUTES',title:'항로 간 변화 격차',value:route.spread,unit:'%p',text:route.spread===null?'공통 기준으로 비교할 항로가 부족합니다.':`${route.baseDate}→${route.endDate}, 선택 ${route.rows.length}개 중 비교 가능 ${route.ranked.length}개. 최대·최소 변화율 격차 ${fmt(route.spread,2)}%p.`,source:'routes + targets / KCCI 항로·EUMED',formula:'max(100×(끝/공통시작−1)) − min(동일식)',dates:[route.baseDate,route.endDate].filter(Boolean) as string[],condition:'모든 선택계열의 공통 숫자 관측일; 0기준은 제외 사유 표시',question:'종합지수가 가리는 노선별 변화가 있는가?',limitation:'선택 항로에 따라 격차가 달라진다. 화물·회사 비중 가중치가 아니다.'},
  {id:'OBS-TRANSIT',title:'통항환경의 관측 변화',value:top?.pct??null,unit:'%',text:!portKeys.length?'통항 경로를 선택하지 않았습니다. 경로를 선택하면 관측 변화를 표시합니다.':top?`${f!.date} 특징표에서 선택 경로 중 절대 변화가 가장 큰 ${PORTS[top.key].name}: 28일 전 비교창 대비 ${signed(top.pct)}%.`:'선택일에 비교 가능한 주간 통항 변화가 없습니다. 값을 0으로 대체하지 않습니다.',source:'features / 기존 PortWatch 주간 집계',formula:'100×(직전7일 평균 / 기존 base28 − 1); 경로간 절대변화 최대',dates:[f?.date,f?.observation_start,f?.observation_end].filter(Boolean) as string[],condition:'특징표 발표일≤선택일; 실제 관측창을 별도 표시',question:'운임과 통항 변화가 같은 시기에 보이는가? 다른 설명도 가능한가?',limitation:'최초공개시각 미검증. 감소분의 우회나 운임 원인을 확정하지 않는다.'},
 ];
}
export function sameStateComparison(data:MarketData,aDate:string,bDate:string){
 const a=data.states.find(x=>x.date===aDate),b=data.states.find(x=>x.date===bDate);
 const valid=Boolean(a?.primary_eligible===true&&b?.primary_eligible===true&&a.representative_regime===b.representative_regime);
 const af=data.features.find(x=>x.date===aDate),bf=data.features.find(x=>x.date===bDate);
 const pairs=[{metric:'KCCI',unit:'pt',a:a?.KCCI??null,b:b?.KCCI??null},
  {metric:'8회 변동성',unit:'비연율화 log SD',a:af?.volatility_8_release??null,b:bf?.volatility_8_release??null},
  ...Object.entries(PORTS).map(([key,p])=>({metric:p.name,unit:'척/일 · 직전7일',a:af?.[key+'_mean7']??null,b:bf?.[key+'_mean7']??null}))]
  .map(x=>({...x,difference:isNumber(x.a)&&isNumber(x.b)?x.b-x.a:null}));
 const portDifference=[...pairs.slice(2)].filter(x=>x.difference!==null).sort((x,y)=>Math.abs(y.difference!)-Math.abs(x.difference!))[0];
 const contrasts=valid?[`KCCI는 A ${fmt(a!.KCCI)}pt, B ${fmt(b!.KCCI)}pt로 B−A ${signed(b!.KCCI-a!.KCCI)}pt입니다.`,
  `변동성 범주는 A ${VOLS[a!.volatility_state]??'미확인'}, B ${VOLS[b!.volatility_state]??'미확인'}입니다.`,
  portDifference?`통항 일평균의 절대 차이가 가장 큰 경로는 ${portDifference.metric}입니다. A ${fmt(portDifference.a,2)}, B ${fmt(portDifference.b,2)}, B−A ${signed(portDifference.difference)}척/일입니다.`:'비교 가능한 통항 값이 없어 차이를 요약하지 않습니다.']:[];
 return {valid,a,b,af,bf,pairs,contrasts,reason:valid?`두 날짜 모두 ${stateName(a!.representative_regime)}의 동일 수준·방향 기준을 충족한다.`:'두 날짜가 같은 완전입력 대표상태인지 확인하세요.',
  routeRows:Object.keys(ROUTES).filter(k=>k!=='KCCI').map(key=>({key,name:ROUTES[key],a:fourReleaseChange(data,key,aDate),b:fourReleaseChange(data,key,bDate)}))};
}
export function reliabilityRows(data:MarketData,model:string,year:string){
 return evaluationRows(data,[model]).filter(x=>year==='ALL'||x.origin.startsWith(year));
}
export function reliabilityScore(rows:Row[]){
 const z=metrics(rows),valid=rows.filter(x=>x.actual_available===true&&isNumber(x.actual_y)&&isNumber(x.prediction));
 const intervals=valid.filter(x=>isNumber(x.interval80_lower)&&isNumber(x.interval80_upper)&&x.interval80_upper>=x.interval80_lower);
 const total=valid.reduce((s,x)=>s+Math.abs(x.actual_y-x.prediction),0);
 const failures=valid.map<Row & {computed_abs_error:number;computed_direction_correct:boolean}>(x=>({...x,computed_abs_error:Math.abs(x.actual_y-x.prediction),computed_direction_correct:(x.prediction>0)===(x.actual_y>0)})).sort((a,b)=>b.computed_abs_error-a.computed_abs_error||a.origin.localeCompare(b.origin));
 return {...z,intervalN:intervals.length,coverage:intervals.length?100*intervals.filter(x=>x.actual_y>=x.interval80_lower&&x.actual_y<=x.interval80_upper).length/intervals.length:null,meanWidth:intervals.length?intervals.reduce((s,x)=>s+x.interval80_upper-x.interval80_lower,0)/intervals.length:null,
  failures,top5Share:total?100*failures.slice(0,5).reduce((s,x)=>s+x.computed_abs_error,0)/total:null};
}
export function originContext(data:MarketData,row:Row){
 const f=atDate(data.features,row.origin),s=atDate(data.states,row.origin);
 return {feature:f,state:s,lastObservation:f?.date??null,windowEnd:f?.observation_end??null,
  noFutureObservation:Boolean(f&&f.date<=row.origin&&f.observation_end<row.origin),publicationVerified:false,
  narrative:'원점 이하 관측의 회고 표시 · 당시 최초 공개시각 미검증'};
}
export const surroundingPeriod=(date:string)=>({start:shiftDate(date,-84),end:date,date});
