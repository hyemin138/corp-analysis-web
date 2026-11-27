import type {MarketData} from './data/provider';
import {evaluationRows,MODEL_LABELS,PORTS,ROUTES,shiftDate,STATES} from './domain.ts';
export type View='market'|'context'|'compare'|'forecast';
export interface Preferences {
 view:View;start:string;end:string;date:string;index:string;contextIndex:string;freightKeys:string[];routeKeys:string[];portKeys:string[];
 frequency:'daily'|'weekly';transitMode:'level'|'percent';compareState:string;aDate:string;bDate:string;
 model:string;year:string;origin:string;
}
export const isDate=(s:unknown):s is string=>typeof s==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&Number.isFinite(Date.parse(s))&&new Date(s+'T12:00:00Z').toISOString().slice(0,10)===s;
export function initialPreferences(d:MarketData,saved:Partial<Preferences>={}):Preferences{
 const min=d.routes[0].date,max=Object.values(d.meta.seriesLatest).concat(d.meta.lastFreightDate).sort().at(-1) as string;
 const valid=(v:unknown):v is string=>isDate(v)&&v>=min&&v<=max;
 const end=valid(saved.end)?saved.end:d.meta.lastFreightDate;
 const start=valid(saved.start)&&saved.start<=end?saved.start:shiftDate(end,-365)<min?min:shiftDate(end,-365);
 const date=valid(saved.date)&&saved.date>=start&&saved.date<=end?saved.date:end;
 const state=STATES.includes(saved.compareState??'')?saved.compareState!:d.states.find(x=>x.date===d.meta.lastCompleteDate)!.representative_regime;
 const matches=d.states.filter(x=>x.primary_eligible===true&&x.representative_regime===state);
 const pick=(a:unknown,defs:string[],allowed:string[])=>Array.isArray(a)?[...new Set(a.filter(x=>typeof x==='string'&&allowed.includes(x)))]:defs;
 const year=['ALL','2025','2026'].includes(saved.year??'')?saved.year!:'ALL';
 const rows=evaluationRows(d).filter(x=>year==='ALL'||x.origin.startsWith(year));
 return {view:['market','context','compare','forecast'].includes(saved.view??'')?saved.view!:'market',start,end,date,
 index:['KCCI','SCFI','CCFI'].includes(saved.index??'')?saved.index!:'KCCI',contextIndex:Object.keys(ROUTES).includes(saved.contextIndex??'')?saved.contextIndex!:'KCCI',
 freightKeys:pick(saved.freightKeys,['KCCI','SCFI','CCFI'],Object.keys(ROUTES).concat(['SCFI','CCFI'])),
 routeKeys:pick(saved.routeKeys,['KNEI','KMDI','KUWI'],Object.keys(ROUTES).filter(k=>k!=='KCCI')),
 portKeys:pick(saved.portKeys,['suez','cape'],Object.keys(PORTS)),frequency:saved.frequency==='daily'?'daily':'weekly',transitMode:saved.transitMode==='percent'?'percent':'level',
 compareState:state,aDate:matches.some(x=>x.date===saved.aDate)?saved.aDate!:matches.at(-1)!.date,bDate:matches.some(x=>x.date===saved.bDate)?saved.bDate!:matches[0].date,
 model:Object.keys(MODEL_LABELS).includes(saved.model??'')?saved.model!:'RIDGE',year,origin:rows.some(x=>x.origin===saved.origin)?saved.origin!:rows.at(-1)!.origin};
}
export interface PageProps {data:MarketData;p:Preferences;update:(patch:Partial<Preferences>)=>void;focus:(date:string)=>void}
