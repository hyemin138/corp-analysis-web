# C 모듈 구조

`src/App.tsx`는6개 탭과 공통 날짜·기간 상태를 소유한다. 브라우저 localStorage의 `c-market-filters`에 선택을 보존하고 범위 밖·손상된 선택은 복구한다. 예측 화면은 시장 날짜 필터와 별도로 원점·연도 필터를 사용한다.

`src/domain.ts`는 시점 이하 관측 선택, 변화율, 결측 처리, 상태 명칭, 엄격한 actual_available 평가와 내보내기 함수를 제공한다. 원래 수치 계산을 이식했고 새 통계모형은 없다. 기준값0은 변화율null이며 다음 비영값으로 바꾸지 않는다.

`src/components/Chart.tsx`는 모듈형 ECharts·ResizeObserver·해제 시 dispose·축 날짜 선택을 관리한다. `src/styles.css`는 이 독립 문서의 전체 레이아웃을 담당한다. 호스트 앱의 전역 CSS에 그대로 합치기 전 스타일 범위를 분리해야 한다.

`src/data/provider.ts`의 `MarketDataProvider.load(signal)`가 유일한 공급 경계다. 현재 LocalSnapshotProvider는 BASE_URL 하위 JSON을 읽는다. 데이터 없음·잘못된 형식은 명시적으로 안내한다. 미래 공급자는 동일한 메모리 구조를 반환하거나 별도 변환 계층을 둘 수 있다.

`scripts/import_snapshot.py`는 외부에 업로드하지 않고 로컬 내부 ZIP의10개 원자료 SHA·핵심 구조를 확인한다. `public/data/market.json`은 원 JSON과 byte 동일하다. 생성시각을 관측일로 사용하지 않는다.

각 폴더는 C 전용이다. 현재 팀 main에는 공통 라우터·인증 코드·Supabase SDK·DB 스키마가 없었다. 이를 임의 작성하지 않았으며 현재 C 모듈은 로그인이나 DB를 요구하지 않는 로컬 연구 시연용이다.
