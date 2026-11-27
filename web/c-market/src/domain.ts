import type { MarketData, Row } from './data/provider';
export type Point = { date: string; value: number | null };
export const LEVELS: Record<string,string> = { low:'저운임', middle:'중운임', high:'고운임' };
export const DIRECTIONS: Record<string,string> = { falling:'하락', sideways:'횡보', rising:'상승' };
export const VOLS: Record<string,string> = { low:'낮음', middle:'보통', high:'높음' };
export const STATES = Object.keys(LEVELS).flatMap(l => Object.keys(DIRECTIONS).map(d=>`${l}|${d}`));
export const MODEL_LABELS: Record<string,string> = { NAIVE:'Naive', RIDGE:'Ridge', RIDGE_SCFI:'Ridge + SCFI', RIDGE_CCFI:'Ridge + CCFI', RIDGE_BRENT:'Ridge + Brent', ARIMA:'ARIMA', ETS:'ETS', MOMENTUM:'모멘텀', RIDGE_BOTH:'Ridge + SCFI·CCFI', RIDGE_FX:'Ridge + 환율', RIDGE_FX_BRENT:'Ridge + 환율·Brent' };
export const ROUTES: Record<string,string> = { KCCI:'KCCI 종합', KNEI:'유럽 · KNEI', KMDI:'지중해 · KMDI', KUWI:'미 서안 · KUWI', KUEI:'미 동안 · KUEI', KMEI:'중동 · KMEI', KAUI:'호주 · KAUI', KLEI:'중남미 동안 · KLEI', KLWI:'중남미 서안 · KLWI', KSAI:'남아프리카 · KSAI', KWAI:'서아프리카 · KWAI', KCI:'중국 · KCI', KJI:'일본 · KJI', KSEI:'동남아 · KSEI', EUMED:'유럽·지중해 합성 · EUMED' };
export const PORTS: Record<string,{name:string; id:string;color:string}> = { suez:{name:'수에즈운하',id:'chokepoint1',color:'#2465dd'},panama:{name:'파나마운하',id:'chokepoint2',color:'#0e9690'},bab:{name:'바브엘만데브',id:'chokepoint4',color:'#e29a33'},cape:{name:'희망봉',id:'chokepoint7',color:'#8b65cc'} };
export const COLORS=['#2563d8','#0c9693','#e79829','#8d69cf','#e46e75','#769f34','#5e85b0','#c66fba','#827652','#3fadb4','#9e7c64','#6e76b6','#c98742','#87a7a3','#243956'];
export const fmt = (v: unknown, digits=0) => v===null||v===undefined||v===''||!Number.isFinite(Number(v)) ? '—' : new Intl.NumberFormat('ko-KR',{minimumFractionDigits:digits,maximumFractionDigits:digits}).format(Number(v));
export const signed = (v: unknown, digits=2) => v===null||v===undefined||v===''||!Number.isFinite(Number(v)) ? '—' : `${Number(v)>0?'+':''}${fmt(v,digits)}`;
export const change = (v: number|null|undefined,b:number|null|undefined) => v==null||b==null||b===0 ? null : 100*(v/b-1);
export const shiftDate = (date:string, days:number) => { const d=new Date(date+'T12:00:00Z'); d.setUTCDate(d.getUTCDate()+days); return d.toISOString().slice(0,10); };
export const inRange = <T extends Row>(rows:T[],start:string,end:string,key='date') => rows.filter(x=>x[key]>=start&&x[key]<=end);
export const atDate = <T extends Row>(rows:T[],date:string,key='date'):T|null => { const v=rows.filter(x=>x[key]<=date); return v.length?v[v.length-1]:null; };
export const stateName=(state:string|null|undefined) => { if(!state)return '전체 시장 미배정'; const [l,d]=state.split('|'); return `${LEVELS[l]??l} · ${DIRECTIONS[d]??d}`; };
export function explainMissing(reason:string|null|undefined):string {
 if(reason==='2022_warmup_not_fitted')return '2022년 초기 관측: 상태 기준 적용 대상이 아닙니다.';
 if(reason?.startsWith('missing:')){const names:Record<string,string>={cape_suez_log_ratio:'희망봉/수에즈 통항 비율',panama_change_4_release:'파나마 4발표 통항 변화'};const keys=reason.slice(8).split(',');return '필수 통항 파생값 미확보: '+keys.map(k=>names[k]??'일부 필수 관측').join(', ');}
 return '시장 상태 판정에 필요한 입력이 충분하지 않습니다.';
}
export const isNumber=(n:unknown):n is number=>typeof n==='number'&&Number.isFinite(n);
export function series(data:MarketData,key:string):Point[] {
 if(key==='SCFI'||key==='CCFI')return data.china.filter(x=>x.series===key).map(x=>({date:x.observed_date,value:x.index_points}));
 if(key==='EUMED')return data.targets.map(x=>({date:x.date,value:x.EUMED}));
 return data.routes.map(x=>({date:x.date,value:x[key]??null}));
}
export function relative(points:Point[]):Point[] {const base=points.find(x=>isNumber(x.value))?.value;return points.map(x=>({...x,value:change(x.value,base)}));}
export function selectedMetrics(data:MarketData,key:string,date:string,start:string) {
 const all=series(data,key).filter(x=>x.date<=date); const now=all.at(-1),prev=all.at(-2),base=all.find(x=>x.date>=start);const returns=all.slice(-9).flatMap((x,i,arr)=>i>0&&x.value&&arr[i-1].value?[Math.log(x.value/arr[i-1].value!)]:[]);
 const mean=returns.reduce((a,b)=>a+b,0)/(returns.length||1);const volatility=returns.length===8?Math.sqrt(returns.reduce((a,b)=>a+(b-mean)**2,0)/7):null;
 return {now,prev,weekly:change(now?.value,prev?.value),period:change(now?.value,base?.value),base,volatility};
}
export function evaluationRows(data:MarketData,models?:string[],start?:string,end?:string):Row[] {
 return data.predictions.filter(x=>x.actual_available===true&&x.target==='EUMED_H28'&&['EXPLORATORY_2025','EXPLORATORY_2026'].includes(x.phase)&&(!models||models.includes(x.model_id))&&(!start||x.origin>=start)&&(!end||x.origin<=end));
}
export function metrics(rows:Row[]) {
 const valid=rows.filter(x=>x.actual_available===true&&isNumber(x.actual_y)&&isNumber(x.prediction)); const n=valid.length;
 const correct=valid.filter(x=>(x.prediction>0)===(x.actual_y>0)).length;
 const interval=valid.filter(x=>isNumber(x.interval80_lower)&&isNumber(x.interval80_upper));
 return {n,mae:n?valid.reduce((a,x)=>a+Math.abs(x.prediction-x.actual_y),0)/n:null,rmse:n?Math.sqrt(valid.reduce((a,x)=>a+(x.prediction-x.actual_y)**2,0)/n):null,accuracy:n?100*correct/n:null,intervalN:interval.length,coverage:interval.length?100*interval.filter(x=>x.actual_y>=x.interval80_lower&&x.actual_y<=x.interval80_upper).length/interval.length:null};
}
export const quantile=(xs:number[],p:number)=>{const a=[...xs].sort((a,b)=>a-b);if(!a.length)return null;const i=(a.length-1)*p;return a[Math.floor(i)]+(a[Math.ceil(i)]-a[Math.floor(i)])*(i%1);};
export function exportCsv(name:string, rows:Row[]) {if(!rows.length)return;const keys=Object.keys(rows[0]);const quote=(x:any)=>`"${String(x??'').replaceAll('"','""')}"`;const blob=new Blob(['\ufeff'+[keys.map(quote).join(','),...rows.map(x=>keys.map(k=>quote(x[k])).join(','))].join('\r\n')],{type:'text/csv;charset=utf-8'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
