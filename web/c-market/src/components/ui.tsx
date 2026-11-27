import type {ReactNode} from 'react';
import {Download,Info} from 'lucide-react';
import {exportCsv,fmt,signed} from '../domain';
import type {Row} from '../data/provider';
import type {Observation} from '../analysis';
import './ui.css';
export function Panel({title,sub,actions,children,className=''}:{title:string;sub?:string;actions?:ReactNode;children:ReactNode;className?:string}){
 return <section className={`panel ${className}`}><header className="panel-head"><div><h2>{title}</h2>{sub&&<p>{sub}</p>}</div>{actions}</header>{children}</section>;
}
export function Notice({children}:{children:ReactNode}){return <div className="notice"><Info size={16}/><div>{children}</div></div>}
export function Empty({text='선택 조건에서 비교 가능한 관측값이 없습니다.'}:{text?:string}){return <div className="empty">{text}</div>}
export function Export({rows,name,label='CSV'}:{rows:Row[];name:string;label?:string}){return <button className="button" disabled={!rows.length} onClick={()=>exportCsv(name+'.csv',rows)}><Download size={15}/>{label}</button>}
export function Stat({label,value,unit='',sub=''}:{label:string;value:string;unit?:string;sub?:string}){return <div className="stat"><span>{label}</span><strong>{value}<small>{unit}</small></strong><p>{sub}</p></div>}
export function InterpretationPanel({items,availability}:{items:Observation[];availability?:{reason:string;partial:string;completeDate:string;onComplete:()=>void}}){
 return <Panel title="주요 관찰과 점검 질문" sub="선택한 값과 고정된 규칙으로 작성합니다. 원인을 추정하거나 위험등급을 만들지 않습니다." className="interpretation">
  {availability&&<Notice><strong>대표 시장 상태가 미배정된 이유</strong><p>{availability.reason}</p><p>확인 가능한 부분 운임축: {availability.partial}. 전체 시장 대표상태를 대신하지 않습니다.</p><button className="text-button" onClick={availability.onComplete}>마지막 완전입력일 {availability.completeDate}로 이동</button></Notice>}
  <div className="observations">{items.map(x=><article key={x.id} data-testid={x.id}><div className="observation-title"><span>{x.title}</span></div><p>{x.text}</p><p className="check-question">점검 질문 · {x.question}</p><details><summary>계산 근거와 한계</summary><dl><dt>근거 ID</dt><dd>{x.id}</dd><dt>출처</dt><dd>{x.source}</dd><dt>계산식</dt><dd>{x.formula}</dd><dt>실제값</dt><dd>{fmt(x.value,4)} {x.value!==null?x.unit:''}</dd><dt>기준 날짜</dt><dd>{x.dates.join(' / ')||'미확보'}</dd><dt>표시 조건</dt><dd>{x.condition}</dd><dt>한계</dt><dd>{x.limitation}</dd></dl></details></article>)}</div>
 </Panel>;
}
export function CheckQuestions({items}:{items:string[]}){return <div className="reading check-questions"><h3>추가 점검 질문</h3><ul>{items.map(x=><li key={x}>{x}</li>)}</ul><small>질문은 확인할 항목이며, 원인이나 미래 결과가 입증됐다는 뜻이 아닙니다.</small></div>}
export function ComparisonValue({a,b,digits=2}:{a:unknown;b:unknown;digits?:number}){return <><td>{fmt(a,digits)}</td><td>{fmt(b,digits)}</td><td>{typeof a==='number'&&typeof b==='number'?signed(b-a,digits):'—'}</td></>}
