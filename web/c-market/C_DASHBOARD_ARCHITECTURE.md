# C V2 구조

App.tsx는4영역과공유선택을소유한다. state.ts는타입·저장선택복원·실제달력날짜검증을담는다. pages/MarketPage,ContextPage,ComparePage,ForecastPage로분리했다. styles.css는현재독립문서전용이므로호스트셸합류시범위화가필요하다.

analysis.ts는공통기준100/격차,해석규칙,같은상태비교,통항원집계투영,예측실패/구간폭을담는다. domain.ts의기존관측선택·메트릭·라벨·CSV를재사용한다. ui.tsx는공통패널/관찰근거,TimeSeries.tsx는단위·관측창툴팁,Chart.tsx는ECharts생명주기·클릭·연결그룹을담는다.

데이터경계는 MarketDataProvider.load(signal)로보존했다. 현재로컬JSON을읽으며runtime배열·스키마검사와복구안내가있다. 원JSON수치·임계·모형은변경하지않았다. researchEvidence.json은기존연구통계의최소추출값과입력SHA다. 새모형/새API/DB는없다.

공통기간·관측일은시장2영역에서만노출한다. 비교A/B·상태와예측연도/모형/원점은별도의의미있는선택으로보존한다. localStorage키는c-market-v2이며V1선택을삭제하지않는다.
