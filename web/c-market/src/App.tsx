import {useEffect,useState} from 'react';
import {Anchor,ArrowRight,BarChart3,CalendarDays,ChartNoAxesCombined,Layers,LoaderCircle,RotateCcw,Ship,TriangleAlert} from 'lucide-react';
import {createDataProvider,type MarketData} from './data/provider';
import {initialPreferences,isDate,type Preferences,type View} from './state';
import {interpretMarket} from './analysis';
import {atDate,explainMissing,LEVELS,DIRECTIONS,VOLS,shiftDate} from './domain';
import {InterpretationPanel,Notice} from './components/ui';
import {MarketPage} from './pages/MarketPage';
import {ContextPage} from './pages/ContextPage';
import {ComparePage} from './pages/ComparePage';
import {ForecastPage} from './pages/ForecastPage';

const NAV=[
 {id:'market',title:'시장 변화',en:'Market & route divergence',icon:ChartNoAxesCombined,question:'운임은 어떻게 변했고, 어느 항로가 달랐는가?'},
 {id:'context',title:'운임·통항 탐색',en:'Freight & maritime context',icon:Anchor,question:'같은 기간에 운임과 해상 통항은 어떻게 움직였는가?'},
 {id:'compare',title:'같은 상태 비교',en:'Compare historical contexts',icon:Layers,question:'같은 시장 상태라도 실제 환경은 무엇이 달랐는가?'},
 {id:'forecast',title:'예측 신뢰도',en:'Forecast errors & uncertainty',icon:BarChart3,question:'예측은 언제 틀렸으며, 무엇을 신뢰할 수 있는가?'},
] as const;
function readSaved():Partial<Preferences>{try{return JSON.parse(localStorage.getItem('c-market-v2')||'{}');}catch{return {};}}
export default function App(){
 const[data,setData]=useState<MarketData|null>(null),[p,setP]=useState<Preferences|null>(null),[error,setError]=useState(''),[message,setMessage]=useState('');
 useEffect(()=>{const ac=new AbortController();createDataProvider().load(ac.signal).then(d=>{setData(d);setP(initialPreferences(d,readSaved()));}).catch(e=>{if(e.name!=='AbortError')setError('스냅샷을 불러오지 못했습니다. '+e.message);});return()=>ac.abort();},[]);
 useEffect(()=>{if(p)localStorage.setItem('c-market-v2',JSON.stringify(p));},[p]);
 useEffect(()=>{if(p?.view)window.scrollTo({top:0,left:0,behavior:'auto'});},[p?.view]);
 if(error)return <main className="load-screen"><TriangleAlert size={35}/><h1>자료를 불러오지 못했습니다</h1><p>{error}</p><p>데이터를 임의 생성하지 않습니다. 내부 인계 ZIP과 C_DASHBOARD_README.md의 data:import 안내를 확인하세요.</p><button className="button primary" onClick={()=>location.reload()}>다시 불러오기</button></main>;
 if(!data||!p)return <main className="load-screen"><LoaderCircle className="spin" size={35}/><h1>C Market Desk</h1><p>보관된 연구 스냅샷을 불러오는 중입니다.</p></main>;
 const d=data,min=d.routes[0].date,max=[d.meta.lastFreightDate,...Object.values(d.meta.seriesLatest)].sort().at(-1) as string;
 const update=(patch:Partial<Preferences>)=>{setMessage('');setP(old=>old?{...old,...patch}:old);};
 const focus=(date:string)=>{if(!isDate(date)||date<min||date>max){setMessage(`자료 탐색 범위는 ${min} ~ ${max}입니다.`);return;}setP(old=>old?{...old,date,start:date<old.start?date:old.start,end:date>old.end?date:old.end}:old);setMessage('');};
 const period=(key:'start'|'end',value:string)=>{if(!isDate(value)||value<min||value>max){setMessage(`유효한 날짜와 자료 범위 ${min}~${max}를 확인하세요.`);return;}const start=key==='start'?value:p.start,end=key==='end'?value:p.end;if(start>end){setMessage('기간 시작일은 종료일 이후일 수 없습니다.');return;}update({start,end,date:p.date<start?start:p.date>end?end:p.date});};
 const preset=(days:number|null)=>{const end=p.end;const start=days===null?min:shiftDate(end,-days)<min?min:shiftDate(end,-days);update({start,date:p.date<start?start:p.date});};
 const nav=NAV.find(x=>x.id===p.view)!;
 const props={data:d,p,update,focus};
 const observations=interpretMarket(d,p.date,p.start,p.end,p.routeKeys,p.portKeys);
 const selectedState=atDate(d.states,p.date);
 const availability=selectedState&&!selectedState.primary_eligible?{reason:explainMissing(selectedState.missing_reason),partial:`${LEVELS[selectedState.level_state]??'수준 미확인'} · ${DIRECTIONS[selectedState.direction_state]??'방향 미확인'} · 변동성 ${VOLS[selectedState.volatility_state]??'미확인'}`,completeDate:d.meta.lastCompleteDate,onComplete:()=>focus(d.meta.lastCompleteDate)}:undefined;
 const insights=<InterpretationPanel items={p.view==='context'?observations.filter(x=>['OBS-STATE','OBS-TRANSIT'].includes(x.id)):observations} availability={availability}/>;
 return <div className="app-shell">
  <aside className="sidebar"><a className="brand" href="#" onClick={e=>{e.preventDefault();update({view:'market'});}}><span><Ship size={25}/></span><div>C MARKET<small>TAEWOONG RESEARCH / V2</small></div></a><p className="nav-label">관찰에서 비교와 검증으로</p><nav aria-label="C 분석 영역">{NAV.map((x,i)=><button key={x.id} className={p.view===x.id?'nav-item active':'nav-item'} onClick={()=>update({view:x.id as View})}><x.icon size={21}/><div>{x.title}<small>{x.en}</small></div><span>{String(i+1).padStart(2,'0')}</span></button>)}</nav><div className="side-note"><span className="status-dot"/>로컬 연구 스냅샷<p>관측·해석·예측 검증을 구분합니다.<br/>실시간 시장 데이터가 아닙니다.</p><small>C v4.1 / Forecast v5.1</small></div></aside>
  <div className="workspace"><header className="topbar"><span>국제 물류시장 <b>/</b> {nav.title}</span><span className="research-badge">연구용 · 후향 스냅샷</span></header><main>
   <div className="page-title"><div><span className="eyebrow">C MARKET INTELLIGENCE</span><h1>{nav.title}</h1><p>{nav.question}</p></div><button className="button" onClick={()=>{setP({...initialPreferences(d),view:p.view});setMessage('');window.scrollTo({top:0,behavior:'auto'});}}><RotateCcw size={15}/>필터 초기화</button></div>
   <div className="snapshot-strip"><span>스냅샷 최신 KCCI {d.meta.lastFreightDate}</span><span>SCFI {d.meta.seriesLatest.SCFI} · CCFI {d.meta.seriesLatest.CCFI}</span><span>통항 {d.meta.lastTransitDate}</span><span>마지막 완전입력 {d.meta.lastCompleteDate}</span><span>오늘 {new Date().toLocaleDateString('sv-SE')} · 별도 날짜</span></div>
   {(p.view==='market'||p.view==='context')&&<section className="filterbar" aria-label="공통 시장 탐색 필터"><CalendarDays size={18}/><label>기간<input type="date" aria-label="기간 시작일" min={min} max={max} value={p.start} onChange={e=>period('start',e.target.value)}/></label><span>—</span><input type="date" aria-label="기간 종료일" min={min} max={max} value={p.end} onChange={e=>period('end',e.target.value)}/><div className="presets">{[[null,'전체'],[365,'1년'],[180,'6개월'],[90,'3개월']].map(([days,label])=><button key={String(label)} onClick={()=>preset(days as number|null)}>{label}</button>)}</div><label className="focus-control">관측 선택일<input type="date" aria-label="관측 선택일" min={min} max={max} value={p.date} onChange={e=>focus(e.target.value)}/></label><button className="button" onClick={()=>focus(d.meta.lastCompleteDate)}>완전입력일</button></section>}
   {message&&<div role="alert"><Notice>{message}</Notice></div>}
   {p.view==='context'&&insights}
   {p.view==='market'&&<MarketPage {...props} insights={insights}/>}{p.view==='context'&&<ContextPage {...props}/>}{p.view==='compare'&&<ComparePage {...props}/>}{p.view==='forecast'&&<ForecastPage {...props}/>}
   <div className="next-step">{p.view==='market'?<><span>항로 간 차이를 확인했다면,같은 기간의 해상 환경을 함께 읽어보세요.</span><button className="text-button" onClick={()=>update({view:'context'})}>운임·통항으로<ArrowRight size={14}/></button></>:p.view==='context'?<><span>같은 상태의 과거에도 비슷한 환경이었을까요?</span><button className="text-button" onClick={()=>update({view:'compare'})}>과거 상태 비교<ArrowRight size={14}/></button></>:p.view==='compare'?<><span>관측 환경이 같아 보여도 미래 운임을 정확히 알 수 있는 것은 아닙니다.</span><button className="text-button" onClick={()=>update({view:'forecast'})}>예측 신뢰도 읽기<ArrowRight size={14}/></button></>:<span>모델의 오차와 불확실성을 시장 점검 정보로 사용하고,확정 전망으로 해석하지 않습니다.</span>}</div>
   <footer className="page-footer"><span>기존 v4.1 상태·v5.1 예측 결과 보존 · 데이터 최초공개 빈티지 미검증</span><span>연구 CONDITIONAL_REVIEW · 회사 이익의 인과모형 아님</span></footer>
  </main></div>
 </div>;
}
