# corp-analysis-web

태웅로직스 기업분석 리포트 및 웹서비스 (통계컨설팅 기말 프로젝트)

## 프로젝트 개요
- 분석 대상 : 태웅로직스 (물류·무역)
- TRACK1 : 국제환경·해상운임 분석 (KCCI 운임 예측)
- TRACK2 : 태웅로직스 수익성 분석
- 분석 결과를 비즈니스 사용자용 웹 대시보드로 제공

## 링크
- 배포 주소 : (배포 후 작성)
- 보고서 (Notion) : (링크 작성)

## 기술 스택
- 분석·전처리 : Python
- 웹 : React
- DB·인증 : Supabase
- 배포 : Vercel

## 폴더 구조
```
corp-analysis-web/
├── web/              # React 웹서비스
├── preprocessing/    # 데이터 전처리 (gdelt, gpr, dart)
├── analysis/         # 분석·가설 검증·모델링 (track1, track2)
├── db/               # ERD, 테이블 설명, RLS 보안 설정
└── data/processed/   # 전처리 완료 데이터 (Supabase 적재용)
```

## 데이터 흐름
원본 데이터 → `preprocessing/` → `data/processed/` → `analysis/` · Supabase → `web/` 대시보드

- 원본·중간 데이터는 용량 문제로 레포에 포함하지 않음 (`preprocessing/README.md` 참고)

## 팀원 및 역할
| 이름 | 역할 |
|---|---|
| 정혜민 (팀장) | Track1 |
| 김승범 | Track2 |
| 박수용 | Track1 |
| 이예진 | Track2 |

## 협업 규칙
### 커밋 메시지
`분류: 한 일` 형식으로 작성
- `기능:` 새 기능 추가
- `수정:` 버그 수정
- `데이터:` 전처리 코드·데이터 추가·변경
- `분석:` 통계 분석 추가·변경
- `문서:` README 등 문서
- `설정:` .gitignore, 패키지, 배포 설정

### 작업 방식
- `main`은 항상 동작하는 상태로 유지
- 각자 브랜치에서 작업 후 Pull Request로 병합
- `.env`(Supabase 키 등)는 절대 커밋하지 않음
