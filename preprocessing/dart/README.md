# 태웅로직스 DART 재무데이터 수집·검증 파이프라인

> **통계컨설팅 기말 프로젝트 · Track 2 B (김승범)**  
> 팀 저장소 위치: `corp-analysis-web/preprocessing/dart/`

태웅로직스의 공시자료를 **수집 → 원본 해시 검증 → 표 추출 → 연결(CFS) 재무주석 정제 → 품질검사**하는 Python 도구입니다. Track 2의 수익성 분석을 위한 **데이터 준비·진단**이 목적이며, 운임 예측(Track 1)이나 최종 예측 모델은 이 폴더의 범위가 아닙니다.

## 2026-11-12 최종 인계 자료 추가 (이번 공개 패키지)

최초 수집기와 2026-11-12 최종 인계본을 비교해 **단위 테스트·계정정의·표준화된 결과 CSV·원문 출처 목록·검토 근거**를 보완했습니다. 수집·정제 스크립트 4개는 인계 ZIP의 파일과 SHA-256이 동일하여 원본 코드를 변경하지 않았습니다.

| 공개 자료 | 경로 | 목적 |
| --- | --- | --- |
| 최종 분기선별 CSV | [`examples/B_quarterly_screened.csv`](examples/B_quarterly_screened.csv) | 보류를 제외한 26분기 분석 후보 |
| 최종 분기진단 CSV | [`examples/B_quarterly_diagnostic.csv`](examples/B_quarterly_diagnostic.csv) | 보류·계산수치도 설명용으로 기록 |
| 연간 진단 CSV | [`examples/B_annual_diagnostic.csv`](examples/B_annual_diagnostic.csv) | TEU·사업부문·운송매입(연간만) |
| 공시 출처 목록 | [`docs/evidence/source_catalog.csv`](docs/evidence/source_catalog.csv) | 29건 접수번호·원문 URL·해시 |
| 계정 사전 | [`docs/evidence/variable_dictionary.csv`](docs/evidence/variable_dictionary.csv) | 23지표 정의·단위·결합 기준 |
| 셀별 판정 | [`docs/evidence/quarterly_cell_decisions.csv`](docs/evidence/quarterly_cell_decisions.csv) | 598개 셀의 사용·보류 사유 |
| 원문 검토·Q4 근거 | [`docs/evidence/feedback_20261112/`](docs/evidence/feedback_20261112) | Q4 70개 복원 및 기타 2개 검토 근거 |
| 최종 이슈 목록 | [`docs/review_register.csv`](docs/review_register.csv) | 13개 주의/보류 항목 |
| 인계본 검사기 | [`tools/verify_snapshot.py`](tools/verify_snapshot.py) | CSV·엑셀·결정값 검산(원본 독립 검증은 아님) |

**검산 요약:** 26분기 × 23지표 = 598개 판단 셀, 선별본 비공백 543개, 2026-11-12 피드백 후 72개 복원(Q4 70개 + 기타 2개), 출처 29건. 본 패키지는 **최종 결과물의 사용 제한을 함께 기록하는 인계 스냅샷**이며 모든 값이 과거 예측시점에 사용 가능하다는 의미는 아닙니다.

수집기 테스트와 인계본 오프라인 검사는 다음과 같이 실행합니다.

```bat
py -3.12 -m unittest discover -s tests -v
py -3.12 tools\verify_snapshot.py
```

자세한 테스트 결과는 [TEST_RESULTS.md](docs/TEST_RESULTS.md) 참고.

## 주요 범위 및 결과

| 항목 | 내용 |
| --- | --- |
| 분석 대상 | 태웅로직스 연결재무제표 및 사업보고서 주석 |
| 목표 기간 | 2020년 1분기 ~ 2026년 2분기 (26개 분기) |
| 수집 방식 | OpenDART API, 정기공시 목록 및 공시서류 원본 XML/ZIP |
| 주요 지표 | 판관비 세부, 대손상각비, 매출채권·충당금, 채권 경과기간, 연간 부문·TEU·운송매입 |
| 데이터 품질 | SHA-256 원본 검사, 계정·단위·연결 범위 검사, 합계 대조, 미확인값 보류 |
| 공개 결과 예시 | [`examples/Track2_B_검토및인계.xlsx`](examples/Track2_B_%EA%B2%80%ED%86%A0%EB%B0%8F%EC%9D%B8%EA%B3%84.xlsx) (6개 시트) |

이번에 첨부한 최종 인계본의 분기선별 시트는 **26개 분기 × 23개 분석 지표 = 598개 칸**이며, 그중 **543개 칸에 값**이 있습니다. 이는 업로드된 엑셀의 **셀 존재 여부**를 재계산한 결과로, **543개 모두가 원문·시점 검증을 완료했다는 뜻은 아닙니다.** 상세 보류 사항은 [품질 검토 요약](docs/QUALITY_REVIEW.md)과 [검토 목록 CSV](docs/review_register.csv)를 확인하세요.

## 폴더 구조

```text
preprocessing/dart/
├── collector.py               # OpenDART 목록·원문 수집, 상태관리, SHA-256, 표 추출
├── refine_track2_b.py         # P0: 판관비·대손·매출채권 정규화 및 분기 값
├── refine_track2_b_p1.py      # P1: 연간 부문·TEU·운송매입 정규화
├── complete_track2_b.py       # P2: 채권 경과기간·충당금 비율 및 QA
├── START_WINDOWS.bat          # Windows 수집기 메뉴 (P0~P2는 CMD 명령 사용)
├── .env.example               # 비밀키 없는 입력 양식
├── .gitignore                 # 실제 키·원본·캐시·DB 등 업로드 차단
├── configs/
│   ├── accounts.json          # 계정 사전
│   └── reconcile_template.csv  # 표별 합계 검산용 빈 템플릿
├── tests/
│   ├── test_smoke.py
│   └── test_collector.py          # 인터넷·실제 API 키 없이 실행하는 단위 검사
├── examples/
│   ├── Track2_B_검토및인계.xlsx  # 2026-11-12 기준 인계 스냅샷
│   └── B_*.csv                # 최종 분기·연간 인계본
├── tools/verify_snapshot.py   # 최종 인계본 정합성 검산
└── docs/
    ├── evidence/             # 29건 출처·셀별 판정·2026-11-12 검토 근거
    ├── TEST_RESULTS.md       # 테스트 실행 기록
    ├── QUALITY_REVIEW.md      # 검증 및 사용 제한
    ├── DATA_PIPELINE.md       # 처리 단계와 생성물
    ├── SOURCES.md             # 공식 자료 출처
    └── review_register.csv    # 인계본에서 추린 미해결·주의 항목 13건
```

## 실행 환경

- **Python 3.10 이상** (Windows 기준 Python 3.12 권장)
- 핵심 수집·정제 스크립트는 **Python 표준 라이브러리만 사용**: `pip install`이나 `requirements.txt`가 필요하지 않습니다.
- DART API 키는 **실제 수집에만 필요**하며 `.env`를 Git에 올리면 안 됩니다.

Windows CMD에서 `preprocessing/dart` 폴더로 이동한 뒤 아래 순서대로 실행합니다.

```bat
copy .env.example .env
notepad .env
py -3.12 collector.py init
py -3.12 collector.py discover --freeze 20261110
py -3.12 collector.py collect --pilot --dry-run
py -3.12 collector.py collect --pilot
py -3.12 collector.py validate
py -3.12 collector.py extract
```

파일럿 결과의 **공시, 표, 연결/별도 구분, 단위, 공시 버전**을 확인한 후에만 전체 수집을 수행합니다.

```bat
py -3.12 collector.py collect --all --dry-run
py -3.12 collector.py collect --all
py -3.12 collector.py validate
py -3.12 collector.py extract
py -3.12 refine_track2_b.py --verify-raw
py -3.12 refine_track2_b_p1.py --verify-raw
py -3.12 complete_track2_b.py --verify-raw
```

- 파일럿·전체 수집 명령은 **외부 DART API를 실제 호출할 수 있으므로**, 대상 기간과 호출량을 먼저 확인합니다.
- **기본 동결일은 2026-11-10**입니다. `discover`의 목록 기간과 회계분기 범위는 다릅니다. 대상 회계 기간은 코드상 **2020Q1~2026Q2**로 제한됩니다.
- 수집이 중단되면 `collector.py status` / `collector.py resume` / `collector.py retry`를 이용합니다. 기존 원본을 다시 가져오지 않도록 요청 상태와 해시를 관리합니다.
- 구체적인 각 단계의 데이터 경로는 [DATA_PIPELINE.md](docs/DATA_PIPELINE.md)에 정리했습니다.

## 오프라인 테스트

```bat
py -3.12 -m unittest discover -s tests -v
```

인터넷 및 DART API 키 없이 파서·수치 변환·원본 해시·기본 분기 처리 함수를 점검합니다. **이 테스트는 실제 DART 원문 전체 수집 및 재생성 성공을 보증하지 않습니다.**

## 인계 엑셀과 코드의 관계

[`examples/Track2_B_검토및인계.xlsx`](examples/Track2_B_%EA%B2%80%ED%86%A0%EB%B0%8F%EC%9D%B8%EA%B3%84.xlsx)은 당시 추출·검토·추가 원문 대조를 거친 **분석용 결과 스냅샷**입니다. 원본 수집기에 더해 **별도의 인계본 재구성·피드백 반영 작업**이 이루어졌으며, 관련 결과 CSV와 일부 검토 증빙은 `examples/`, `docs/evidence/`에 추가했습니다. 다만 DART 원본 ZIP·전체 중간 추출 결과·검토용 HTML은 공개용 묶음에 포함하지 않았습니다. 따라서 위 네 Python 파일만으로 **동일한 최종 Excel 파일을 그대로 재생성할 수 있다고 주장하지 않습니다.** 인계본 전체를 감사·재현하려면 별도 보관된 원본·추가 검토 기록이 필요합니다(확인필요).

## 데이터 해석 유의사항

- **당기·전기, 3개월·누적, 연결·별도, 금액 단위**가 섞이지 않도록 합니다.
- **2021~2025년 Q4 일부 판관비**는 연간 수치에서 9개월 누적을 차감한 **검토된 계산값**이며, 분기공시 직접값과 다릅니다.
- **2020Q1·2020Q4·2023Q4**의 채권 경과기간 비율은 원문 합계·범위 불일치 이슈로 사용이 보류되었습니다.
- **매출채권 경과기간**을 곧바로 **연체기간**으로 단정하지 않고, **충당금 비율**을 명시적 **ECL 확정률**로 대체하지 않습니다.
- 결측·비공시·원문 보류값은 자동으로 0을 채우지 않습니다.
- 모델 입력 시 **공시 공개일/기준시점(as-of)** 검증과 Track 2의 다른 담당자 재무본표와의 교차 검증이 추가로 필요합니다.

## 출처

데이터: [금융감독원 DART](https://dart.fss.or.kr/) 및 [OpenDART](https://opendart.fss.or.kr/)의 태웅로직스 정기공시. API별 공식 설명서와 취급 주의사항은 [SOURCES.md](docs/SOURCES.md)에 정리했습니다.
