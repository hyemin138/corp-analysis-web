import {Chart,baseOption} from './Chart';
import {fmt} from '../domain';
import {Empty} from './ui';
import {useRef} from 'react';
export interface PlotPoint {date:string;value:number|null;observation_start?:string;observation_end?:string}
export interface PlotSeries {name:string;color:string;points:PlotPoint[]}
const escape=(x:unknown)=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]!));
export function TimeSeries({series,unit,label,selectedDate,onDate,group,height=300,range}:{series:PlotSeries[];unit:string;label:string;selectedDate?:string;onDate?:(s:string)=>void;group?:string;height?:number;range?:[string,string]}){
 const cursorDate=useRef<string|null>(null);
 const tooltip=(items:any[])=>{
  if(group&&cursorDate.current){
   const date=cursorDate.current;
   return `<b>동기 커서 ${date}</b>`+series.map(s=>{const point=s.points.find(x=>x.date===date);return `<div><b>${escape(s.name)}</b>: ${!point?'해당일 관측 없음':point.value===null?'미확보':fmt(point.value,2)+' '+escape(unit)}${point?.observation_start?`<br/><small>관측창 ${escape(point.observation_start)} ~ ${escape(point.observation_end)}</small>`:''}</div>`;}).join('');
  }
  return items.map(x=>{const v=x.value;return `<div><b>${escape(x.seriesName)}</b> · ${escape(v[0])} : ${fmt(v[1],2)} ${v[1]===null?'':escape(unit)}${v[2]?`<br/><small>관측창 ${escape(v[2])} ~ ${escape(v[3])}</small>`:''}</div>`;}).join('');
 };
 if(!series.some(x=>x.points.some(p=>p.value!==null)))return <Empty/>;
 return <Chart label={label} height={height} group={group} onCursorDate={t=>{cursorDate.current=t===null?null:new Date(t).toISOString().slice(0,10);}}
  onAxisDate={onDate?(t)=>{const dates=series.flatMap(s=>s.points.map(p=>p.date));if(dates.length)onDate(dates.reduce((a,b)=>Math.abs(Date.parse(a)-t)<=Math.abs(Date.parse(b)-t)?a:b));}:undefined}
  option={{...baseOption,axisPointer:group?{triggerOn:'none'}:undefined,tooltip:{...baseOption.tooltip,triggerOn:group?'none':'mousemove|click',axisPointer:{type:'line'},formatter:tooltip},
   xAxis:{...baseOption.xAxis,min:range?Date.parse(range[0]):undefined,max:range?Date.parse(range[1]):undefined,axisPointer:{show:true,snap:false}},yAxis:{...baseOption.yAxis,name:unit,nameGap:24},
   series:series.map((s,i)=>({type:'line',name:s.name,showSymbol:false,connectNulls:false,lineStyle:{width:2.4},emphasis:{focus:'series'},itemStyle:{color:s.color},
    data:s.points.map(x=>[x.date,x.value,x.observation_start??null,x.observation_end??null]),
    markLine:i===0&&selectedDate?{silent:true,symbol:'none',label:{show:false},lineStyle:{type:'dashed',color:'#9aaac0'},data:[{xAxis:selectedDate}]}:undefined}))}}/>;
}
