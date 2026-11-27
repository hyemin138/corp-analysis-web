# 재현 범위와 명령

## 실행·코드·데이터·브라우저

내부 ZIP은 `C_DASHBOARD_README.md`의 Python 명령으로 동결 빌드를 실행할 수 있습니다. 소스 검사는 Node 24와 `npm ci` 이후 진행합니다.

```powershell
npm test
npm run test:data
npm run test:browser
npm run build
```

`test:data`와 `test:browser`에는 포함된 내부 JSON과 `data/LOCAL_IMPORT.json`이 필요합니다. 브라우저 검사에는 Google Chrome이 필요합니다. 별도 DB, API, 연구 모델 학습, 원자료 재수집은 필요하지 않습니다. 데이터 검사26개는 저장 스냅샷의 정합성 검사이며 외부 원자료 재조회가 아닙니다.

## 자료 없이 공개 소스 검사

공개 Git의 같은 커밋에서 `npm ci`, `npm test`, `npm run build`를 실행할 수 있습니다. 자료가 없는 화면은 오류를 숨기지 않고 복구 안내를 표시합니다. 이 검사를 실자료 화면 검증으로 해석하지 않습니다.

## 기존 독립 QA와 패키지 생성

내부 `qa/v2/vera`와 `qa/v2/editor`는 실제 독립 검수 보고서와 계산/화면 증거입니다. 일부 감사 스크립트는 검수 당시 원 CSV·로컬 경로·도구에 의존하므로 ZIP만으로 모든 원문 감사가 재실행된다고 보장하지 않습니다. 앱 소스·자료 검사와 그 범위를 구분합니다.

`scripts/package_v2.py`는 관리자의 Git 작업폴더, 독립 검수 종결 결정, 원자료 보호목록, 소스/빌드 동결 기록이 있을 때만 사용하는 인계 생성 도구입니다. Git이 없는 추출 ZIP에서 이를 실행하는 절차가 아닙니다. ZIP의 무결성은 외부 `TAEWOONG_C_DASHBOARD_V2_FINAL_VERIFICATION.json`, `.zip.sha256` 및 내부 `qa/v2/FILE_MANIFEST.csv`로 확인합니다.

선택 실행검사 `scripts/smoke_bundle.mjs`는 Playwright가 설치된 개발 폴더에서 localhost 주소와 결과 파일 경로를 받아 네 영역·핵심 수치·콘솔을 검사합니다. 이는 전체26개 브라우저 회귀의 대체가 아닙니다.
