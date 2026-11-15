# preprocessing
원본 데이터를 분석·DB 적재용으로 가공하는 전처리 코드

## 폴더 구성
- `gdelt/` : GDELT 국제뉴스 데이터 전처리 (2022~2026)
- `gpr/` : 지정학 데이터 전처리
- `dart/` : DART 분기 재무 데이터 전처리

## 데이터 흐름
data/raw/ (원본) → data/interim/ (중간 결과) → data/processed/ (최종, Supabase 적재)

- `raw/`, `interim/`은 용량 문제로 GitHub에 올리지 않음 (.gitignore 처리)
- 각자 로컬에서 원본을 받아 `data/raw/`에 넣고 전처리 코드를 실행하면 `interim/`, `processed/`가 생성됨
- 원본 다운로드 방법은 각 하위 폴더 README 참고
- `processed/`만 레포에 포함

## 실행 방법
각 하위 폴더의 README 참고
