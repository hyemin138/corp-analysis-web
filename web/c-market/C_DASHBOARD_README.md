# C 외부 시장 대시보드

React + TypeScript + Vite + ECharts의 독립 C 모듈이다. 팀 저장소 main에는 실행 가능한 React 셸이 없었으므로 `web/c-market` 안에만 구성했다. 기존 `web/README.md`, A/B·DB·전처리 파일은 변경하지 않았다. 운영 배포나 Supabase 연결은 하지 않았다.

6개 화면: 국제운임 현황, KCCI 항로 비교, 설명용 시장 상태, 해상 통항환경, EUMED 28일 후향 예측 검증, 날짜별 종합 탐색. 날짜·기간·계열 선택, 확대·툴팁·범례, CSV 내보내기와 화면 간 날짜 연동을 제공한다.

## 실행

Node 24에서 검증했다. 이 폴더에서 실행한다.

```powershell
npm ci
# 팀 내부 ZIP을 별도 폴더에 풀어 놓은 뒤, 실제 경로로 바꾼다.
py -3.13 -B scripts/import_snapshot.py --from-app "C:\team-data\TAEWOONG_C_DASHBOARD_APP"
npm run dev
```

개발: http://127.0.0.1:5174 . 프로덕션 확인: `npm run build` 후 `npm run preview`, http://127.0.0.1:4174 . 서버가 켜져 있는 동안만 접속 가능하다. `python`이 실행 가능한 환경이라면 `npm run data:import -- --from-app "경로"`도 사용할 수 있다.

내부 데이터 ZIP은 `TAEWOONG_C_DASHBOARD_APP_FINAL.zip`이다. 원자료10개 SHA를 검증하고 완전입력192·구간62·전환53·평가80원점 조건을 검사한 뒤 화면 JSON을 그대로 복사한다. 재수집·모형학습·값 보정은 없다.

## 공개 저장소와 내부 데이터의 분리

연구 인계 원본은 팀 내부용이며 외부 재배포 권한이 확인되지 않았다. 따라서 `public/data/`, `data/`, 스크린샷·로컬 QA 산출물·dist는 Git에서 제외한다. 원자료나 전체 마스터를 커밋하지 않는다. 데이터 없는 클론은 앱이 실행되지만 가져오기 안내를 표시하며, 숫자를 임의 생성하지 않는다. 위 내부 ZIP을 전달받아야 실제 연구 화면을 사용할 수 있다. GitHub만으로 실자료가 제공된다는 뜻은 아니다.

```powershell
npm test              # 데이터 없이 실행 가능한 코드 검사
npm run test:data     # 내부 스냅샷 가져온 후18개 데이터/지표 검사
npm run test:browser  # 내부 스냅샷 + 설치된 Google Chrome 필요
npm run build
```

아키텍처·연결 방식은 C_DASHBOARD_ARCHITECTURE.md와 C_INTEGRATION_GUIDE.md, 팀 DB 협의 항목은 C_DATA_API_REQUIREMENTS.md를 따른다. 검증 범위와 연구 한계는 C_QA_REPORT.md 및 C_RESEARCH_LIMITATIONS.md에 구분했다.
