# C 데이터 공급 협의 초안

이 문서는 현재 파일 어댑터의 소비 요구사항이다. 팀의 정식 API·PK·FK·DB 구조 확정안이 아니다. 인증·RLS·페이지네이션·엔드포인트·권한은 DB/전체 웹 담당자와 공동 결정해야 한다. 프런트에 service_role 키를 넣지 않는다.

현재 입력 버전은 `c-market-desk/1.0`, 공급 함수는 `MarketDataProvider.load(AbortSignal?) → Promise<MarketData>`다. 타입 정의는 src/data/provider.ts를 따른다. 메모리 입력 묶음은 다음과 같다.

|묶음|현재 행 단위·기간|필수 내용|
|---|---|---|
|routes|KCCI 발표일,201회|date,KCCI,13항로 지수|
|china|지표×관측일,790행|series,observed_date,원/정제 지수,등록·정렬 날짜|
|features|KCCI 발표일,201회|운임 변화·변동성,통항 mean7/trend84/pct28,관측창·가용성|
|states|KCCI 발표일,201회|대표 level×direction,별도 volatility,primary_eligible,split,미배정 사유|
|runs / transitions|원구간 / 원전환|기존run_id·경계날짜·관측 횟수·기간 정의|
|transit|경로×관측일,7064행|portid,date,n_container,0과결측 구분|
|targets|KCCI 발표일,201회|KNEI,KMDI,EUMED 및 기존특성|
|predictions|모형×원점×목표·평가구분,2660행|model_id,target,origin,명목28일일자·실제대응일,실제/예측로그변화,수준,actual_available,phase,방향,구간,훈련성숙일|
|metrics|모형×표본/목표|n,MAE,RMSE,방향정확도,구간유효표본과포함률|
|thresholds / meta|고정규칙/스냅샷정보|v4.1임계값·표본범위·각지표최신일·후향평가/빈티지제한|

전체 열·타입은 내부 ZIP의 DATA_MAPPING.md와 원 SOURCE_MANIFEST.json을 따른다. 숫자는 number, 결측은 null, actual_available는 boolean이다. 날짜는 YYYY-MM-DD지만 발표일·관측일·집계시작/종료·예측원점·명목목표·실제대응일은 별개 의미다. raw_*는 문자열이며 transitions.raw_change도 숫자로 간주하지 않는다.

운임 지수는 포인트, 수익률은 열별 % 또는100×ln 단위, 통항은 척/일 및 정의된7일평균이다. EUMED=(2×KNEI+KMDI)/3. features의 주간 통항은 발표일−7일~−1일이며 관측창을 API에서도 반환해야 한다. 제품단가·회사계약운임과 혼합하지 않는다.

필터 요구는 시장날짜/기간·지표·항로·경로·빈도·상태·모형·예측원점·평가연도다. 화면은 공급된 표본을 로컬 필터링한다. 시점 이하 관측을 선택하며 미래값 backfill을 하지 않는다. 예측 평가는 actual_available===true 및 EUMED_H28의 두 탐색적 평가 phase만 사용한다.

실제 API 연결 시201행 고정 검사를 메타 기반으로 개정하고 새 날짜의 라벨·구간·가용성·성숙타깃 규칙을 재검증해야 한다. 날짜만 늘리거나 기존 임계값을 재학습하지 않는다. 현 자료의 publicationVintageVerified=false를 실제 최초공개시각 검증으로 바꾸지 않는다.
