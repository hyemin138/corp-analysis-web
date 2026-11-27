import type {PageProps} from '../state';
import {sameStateComparison} from '../analysis';
import {STATES,stateName,fmt,signed,VOLS} from '../domain';
import {Panel,Notice,ComparisonValue,Export,CheckQuestions} from '../components/ui';

export function ComparePage({data:d,p,update,focus}:PageProps){
 const dates=d.states.filter(x=>x.primary_eligible===true&&x.representative_regime===p.compareState),c=sameStateComparison(d,p.aDate,p.bDate);
 const selectState=(state:string)=>{const a=d.states.filter(x=>x.primary_eligible===true&&x.representative_regime===state);update({compareState:state,aDate:a.at(-1)!.date,bDate:a[0].date});};
 return <>
  <Panel title="같은 상태라면 시장환경도 같았을까" sub="동일 대표상태의 완전입력 관측에서만 비교일A/B를 선택합니다.">
   <div className="control-row"><label>설명용 시장 상태<select aria-label="비교 시장 상태" value={p.compareState} onChange={e=>selectState(e.target.value)}>{STATES.map(x=><option key={x} value={x}>{stateName(x)} · {d.states.filter(s=>s.primary_eligible&&s.representative_regime===x).length}회</option>)}</select></label><label>비교일A<select aria-label="비교일A" value={p.aDate} onChange={e=>update({aDate:e.target.value})}>{dates.map(x=><option key={x.date}>{x.date}</option>)}</select></label><label>비교일B<select aria-label="비교일B" value={p.bDate} onChange={e=>update({bDate:e.target.value})}>{dates.map(x=><option key={x.date}>{x.date}</option>)}</select></label></div>
   <div className="comparison-story"><div><small>공통점</small><h3>{c.reason}</h3><p>변동성은 별도 축입니다. A: {VOLS[c.a?.volatility_state]??'미확인'} / B: {VOLS[c.b?.volatility_state]??'미확인'}.</p></div><div><small>실제 차이점과 해석 한계</small>{c.contrasts.map(x=><p key={x}>{x}</p>)}<p>미확보 값의 차이는 계산하지 않습니다. 같은 상태여도 미래 운임이나 기업 수익성이 비슷하다고 예측할 수 없습니다.</p></div></div>
   {p.aDate===p.bDate&&<Notice>같은 날짜를 선택했습니다. 과거 환경의 차이를 보려면 다른 날짜를 선택하세요.</Notice>}
   <div className="table-wrap"><table data-testid="state-comparison"><thead><tr><th>지표</th><th>A · {p.aDate}</th><th>B · {p.bDate}</th><th>B−A</th><th>단위</th></tr></thead><tbody>{c.pairs.map(x=><tr key={x.metric}><td>{x.metric}</td><ComparisonValue a={x.a} b={x.b} digits={x.metric==='8회 변동성'?4:2}/><td>{x.unit}</td></tr>)}</tbody></table></div>
   <p className="caption">A 통항창 {c.af?.observation_start??'—'}~{c.af?.observation_end??'—'} / B 통항창 {c.bf?.observation_start??'—'}~{c.bf?.observation_end??'—'}. 0과 미확보를 구분하며 최초 공개시각은 미검증입니다.</p>
   <CheckQuestions items={[`같은 ${stateName(p.compareState)} 상태인데, A ${p.aDate}와 B ${p.bDate}의 변동성·통항 차이는 어떤 시장 점검을 요구하는가?`,'실제 계약의 노선·기간 구성이 달랐는지 내부 자료로 확인할 수 있는가?','미래 운임을 유사하다고 가정하기 전에 두 날짜의 관측창과 자료 가용성을 확인했는가?']}/>
   <div className="control-row"><button className="button" onClick={()=>{focus(p.aDate);update({view:'context'});}}>A의 운임·통항 탐색</button><button className="button" onClick={()=>{focus(p.bDate);update({view:'context'});}}>B의 운임·통항 탐색</button><Export name="same_state_comparison" rows={c.pairs.map(x=>({...x,a_date:p.aDate,b_date:p.bDate,state:p.compareState}))}/></div>
  </Panel>
  <Panel title="항로의 움직임도 같았는가" sub="각 날짜까지 실제4번째 이전 발표 대비 단순 변화율입니다. 두 기간의 실제 시작일도 확인하세요.">
   <div className="table-wrap"><table><thead><tr><th>항로</th><th>A 기준발표</th><th>A 변화 %</th><th>B 기준발표</th><th>B 변화 %</th><th>B−A %p</th></tr></thead><tbody>{c.routeRows.map(x=><tr key={x.key}><td>{x.name}</td><td>{x.a.baseDate??'—'}</td><td>{signed(x.a.value)}</td><td>{x.b.baseDate??'—'}</td><td>{signed(x.b.value)}</td><td>{x.a.value!==null&&x.b.value!==null?signed(x.b.value-x.a.value):'—'}</td></tr>)}</tbody></table></div>
  </Panel>
  <details className="detail-block"><summary>상태 표본·원구간·전환 연구 근거와 CSV</summary><p>완전입력192회=개발151+2026설명41. 규칙 임계값은 기존v4.1이며9대표상태·62연속구간·53유효 라벨전환을 보존합니다. 시장의 자연체제나 위험등급이 아닙니다.</p><div className="state-counts">{STATES.map(s=><button key={s} className={s===p.compareState?'active':''} onClick={()=>selectState(s)}>{stateName(s)}<b>{d.states.filter(x=>x.primary_eligible&&x.representative_regime===s).length}회</b></button>)}</div><div className="control-row"><Export name="original_regime_runs" rows={d.runs}/><Export name="original_regime_transitions" rows={d.transitions}/><Export name="same_state_dates" rows={dates}/></div><div className="table-wrap runs"><table><thead><tr><th>원구간ID</th><th>상태</th><th>시작</th><th>끝</th><th>관측수</th><th>달력범위 일</th><th>시작사유</th></tr></thead><tbody>{d.runs.map(x=><tr key={x.run_id}><td>{x.run_id}</td><td>{stateName(x.state)}</td><td><button className="text-button" onClick={()=>{focus(x.start);update({view:'context'});}}>{x.start}</button></td><td>{x.end}</td><td>{x.observed_n}</td><td>{x.calendar_span_days}</td><td>{x.start_reason}</td></tr>)}</tbody></table></div><p>달력범위는 끝−시작이며 관측횟수·다음발표까지 interval_coverage와 다릅니다. 표본 끝과 공백으로 중도절단될 수 있습니다.</p></details>
 </>;
}
