import {useEffect,useRef} from 'react';
import * as echarts from 'echarts/core';
import {LineChart,BarChart,ScatterChart,BoxplotChart,CustomChart} from 'echarts/charts';
import {GridComponent,TooltipComponent,LegendComponent,DataZoomComponent,MarkLineComponent,MarkAreaComponent,TitleComponent,ToolboxComponent,AriaComponent} from 'echarts/components';
import {CanvasRenderer} from 'echarts/renderers';

echarts.use([LineChart,BarChart,ScatterChart,BoxplotChart,CustomChart,GridComponent,TooltipComponent,LegendComponent,DataZoomComponent,MarkLineComponent,MarkAreaComponent,TitleComponent,ToolboxComponent,AriaComponent,CanvasRenderer]);
interface Peer {chart:echarts.ECharts;notify:(t:number|null)=>void}
const groups=new Map<string,Set<Peer>>();
let linking=false;

// Synchronize time values, never dataIndex: daily and weekly arrays have different lengths.
function moveCursor(peers:Set<Peer>,timestamp:number|null){
 if(linking)return;
 linking=true;
 try{for(const peer of peers){
  if(peer.chart.isDisposed())continue;
  peer.notify(timestamp);
  if(timestamp===null){
   peer.chart.dispatchAction({type:'hideTip'}, {silent:true});
   peer.chart.dispatchAction({type:'updateAxisPointer',currTrigger:'leave'}, {silent:true});
   continue;
  }
  const x=peer.chart.convertToPixel({xAxisIndex:0},timestamp);
  const y=Math.max(65,(peer.chart.getHeight()-20)/2);
  if(typeof x==='number'&&Number.isFinite(x)&&peer.chart.containPixel('grid',[x,y])){
   peer.chart.dispatchAction({type:'updateAxisPointer',currTrigger:'mousemove',x,y},{silent:true});
   peer.chart.dispatchAction({type:'showTip',x,y},{silent:true});
  }
 }}finally{linking=false;}
}

export function Chart({option,height=330,onClick,onAxisDate,onCursorDate,label,group}:{option:any;height?:number;onClick?:(e:any)=>void;onAxisDate?:(timestamp:number)=>void;onCursorDate?:(timestamp:number|null)=>void;label:string;group?:string}){
 const el=useRef<HTMLDivElement>(null),instance=useRef<echarts.ECharts|null>(null);
 const axisHandler=useRef<((e:any)=>void)|null>(null),cursorCallback=useRef(onCursorDate);
 cursorCallback.current=onCursorDate;
 useEffect(()=>{
  if(!el.current)return;
  const c=echarts.init(el.current);instance.current=c;
  const ro=new ResizeObserver(()=>c.resize());ro.observe(el.current);
  let peer:Peer|undefined;
  if(group){
   const peers=groups.get(group)??new Set<Peer>();groups.set(group,peers);
   peer={chart:c,notify:t=>cursorCallback.current?.(t)};peers.add(peer);
   c.getZr().on('mousemove',(event:any)=>{
    if(linking||!c.containPixel('grid',[event.offsetX,event.offsetY]))return;
    const timestamp=c.convertFromPixel({xAxisIndex:0},event.offsetX);
    if(typeof timestamp==='number'&&Number.isFinite(timestamp))moveCursor(peers,Math.round(timestamp/86400000)*86400000);
   });
   c.getZr().on('globalout',()=>moveCursor(peers,null));
   c.on('datazoom',(event:any)=>{
    if(linking)return;
    const zoom=event.batch?.[0]??event;
    if(typeof zoom.start!=='number'||typeof zoom.end!=='number')return;
    linking=true;
    try{for(const other of peers)if(other.chart!==c&&!other.chart.isDisposed())other.chart.dispatchAction({type:'dataZoom',start:zoom.start,end:zoom.end},{silent:true});}
    finally{linking=false;}
   });
  }
  return()=>{ro.disconnect();if(group&&peer){groups.get(group)?.delete(peer);if(!groups.get(group)?.size)groups.delete(group);}c.dispose();instance.current=null;};
 },[group]);
 useEffect(()=>{
  const c=instance.current;if(!c)return;
  c.setOption({animationDuration:250,textStyle:{fontFamily:'"Segoe UI", "Malgun Gothic", sans-serif',fontSize:12},...option,aria:{enabled:true,label:{description:label}}},true);
  c.off('click');if(onClick)c.on('click',onClick);
  const zr=c.getZr();if(axisHandler.current)zr.off('click',axisHandler.current);
  axisHandler.current=onAxisDate?(e:any)=>{if(c.containPixel('grid',[e.offsetX,e.offsetY])){const t=c.convertFromPixel({xAxisIndex:0},e.offsetX);if(typeof t==='number'&&Number.isFinite(t))onAxisDate(t);}}:null;
  if(axisHandler.current)zr.on('click',axisHandler.current);
 },[option,onClick,onAxisDate,label]);
 return <div ref={el} className="chart" role="img" data-testid={label} aria-label={label} style={{height}}/>;
}
export const baseOption={tooltip:{trigger:'axis',confine:true,backgroundColor:'#fff',borderColor:'#dbe2ec',textStyle:{color:'#263c58',fontSize:12}},legend:{top:0,type:'scroll',icon:'roundRect',itemWidth:12,itemHeight:4,textStyle:{color:'#56687e'}},grid:{left:58,right:26,top:48,bottom:64},xAxis:{type:'time',boundaryGap:['2%','3%'],axisLine:{lineStyle:{color:'#cdd7e5'}},axisLabel:{color:'#5c708b',hideOverlap:true,formatter:(v:number)=>{const d=new Date(v);return `${d.getUTCFullYear()}-${String(d.getUTCMonth()+1).padStart(2,'0')}-${String(d.getUTCDate()).padStart(2,'0')}`;}},splitLine:{show:false}},yAxis:{type:'value',scale:true,axisLabel:{color:'#5c708b'},splitLine:{lineStyle:{color:'#edf1f6'}}},dataZoom:[{type:'inside',filterMode:'none'},{type:'slider',bottom:5,height:17,borderColor:'transparent',fillerColor:'rgba(39,99,214,.12)',handleSize:18}],toolbox:{right:15,top:20,feature:{saveAsImage:{title:'차트 PNG 저장',name:'C_Market_Desk',pixelRatio:2}}}};
