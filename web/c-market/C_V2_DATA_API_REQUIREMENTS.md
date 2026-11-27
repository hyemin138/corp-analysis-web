# V2 공급 어댑터 협의

현재계약은기존MarketDataProvider.load(signal)→MarketData와c-market-desk/1.0 로컬스냅샷이다. src/data/provider.ts의10배열·thresholds/meta를유지한다. DB테이블/PK/FK/엔드포인트/인증방식확정안은아니다. 상세기존열은C_DATA_API_REQUIREMENTS.md를참조한다.

신규분석은원데이터에서클라이언트계산한다. 필수입력은 routes(date,KCCI,13항로),targets(date,KNEI,KMDI,EUMED),states(date,primary_eligible,representative_regime,volatility_state와원run/transition정보),features(발표일·실제관측창·변화/변동·4경로mean7/base28/pct28),transit(portid,실제관측일,n_container),predictions(모형/원점/목표/실제대응일/actual_available/prediction/actual_y/구간/실제발표간격/훈련타깃성숙·v4_state_basis)이다.

자료형: 날짜YYYY-MM-DD·숫자number·결측null·가용성boolean. raw_*는문자열이다. 발표일/관측일/집계창/예측원점/생성일/명목목표/실제대응일은다른의미다. 빈티지미검증을배포시각으로대체하지않는다.

현재 소비 함수는 각 계열 안에서 날짜 오름차순인 관측 배열을 전제로 한다. 새 API 어댑터도 지표·경로별 날짜 순서를 보존하거나 명시적으로 정렬해야 한다. 이는 DB 저장 순서나 정식 API 엔드포인트를 강제하는 뜻이 아니다.

파생출력:RouteComparison(공통시작/끝/실값/변화율/방향/미계산사유/정규화점),Observation(근거ID/지표/공식/값/날짜/조건/질문/한계),StateComparison(완전동일상태검증/A/B/차이),ReliabilityScore(실제값n/MAE/방향/구간n/포함률/폭/오차사례). 타입과계산은analysis.ts가정의한다. 이를별도영구테이블로만들지는ERD담당자가판단한다.

필터는시장기간/관측일/항로/운임/경로와빈도,별도의비교상태/A/B,별도의예측모형/연도/원점이다. 현재고정201행스키마검사는새API전환때메타·가용성·성숙규칙과함께재검토해야한다. 최초공개정보가확인되기전에는실시간과거이용가능자료라고표현하지않는다.
