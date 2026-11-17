# 파이프라인 구조와 입력·출력

## 단계별 흐름

```text
OpenDART 정기공시 목록/원문
  │
  ▼
collector.py (discover → collect → validate → extract)
  ├─ state.sqlite3 / state/*            # 요청 상태·공시 목록 (공개 제외)
  ├─ data/raw/*                         # 원본 bytes + SHA256 메타 (공개 제외)
  └─ data/interim/tables.json           # 추출된 표/문맥/위치 (공개 제외)
               │
               ├── refine_track2_b.py     → reports/p0_full/
               │       판관비/대손상각비/채권, 분기 및 원문 버전
               ├── refine_track2_b_p1.py  → reports/p1_annual/
               │       연간 TEU/사업부문/운송 매입
               └── complete_track2_b.py   → reports/b_remaining/
                       매출채권 경과기간/충당금 비율 및 검토 이력
               │
               ▼
         사람의 QA·계정 정의 검토·표 재구성
               │
               ▼
        Track2_B_검토및인계.xlsx (공개용 스냅샷)
               │
               ▼
            Track 2 수익성 진단 / 팀 데이터베이스
```

## 핵심 구현 특징

- 목록 API에서 공시 접수번호·접수일과 정정 공시 버전을 구분합니다.
- 수집 시 SQLite ledger로 요청 상태를 관리하고 원본 바이트의 SHA-256을 저장하며 재실행 시 검증합니다.
- XML/HTML 표의 `rowspan`과 `colspan`을 격자 좌표로 확장해 계정 위치를 추적합니다.
- 표의 원래 금액 단위와 `value_kind`(단독 분기·누적·연간·잔액)를 구분합니다.
- 계정·기간·원문 근거가 불충분하면 `REVIEW_REQUIRED` 또는 `HOLD`로 기록하고 임의 대체하지 않습니다.
- P0, P1, P2는 모두 `collector.py`의 파서/입출력 도우미를 사용합니다.

## 재현에 필요한 비공개 원본

이전 실행의 `state.sqlite3`와 `data/raw/`를 **서로 짝이 맞는 상태로** 보관해야 같은 스냅샷을 검증할 수 있습니다. 상태 DB만으로는 원본 ZIP의 해시 검증을 다시 진행할 수 없습니다. GitHub에는 상태 DB와 원본 전체 파일을 넣지 않습니다.

최종 Excel 인계 파일은 별도 수동 검토와 피드백 반영 스크립트를 통해 정리한 결과입니다. 이러한 후속 작업의 **검토 증빙 일부와 최종 CSV는** `docs/evidence/`, `examples/`에 있으나 **전체 중간 추출값·원문 HTML·엑셀 생성 스크립트 실행환경은** 공개 묶음에 없어, **최종 XLSX의 완전한 재현 절차는 포함하지 않았습니다(확인필요).**

## 선택 작업: 표의 합계 검산

`configs/reconcile_template.csv`를 복사한 후 실제 `table_id`, 열 번호, 합계 행, 세부행(세미콜론으로 구분)과 허용 오차를 입력합니다. 좌표는 격자 기준 **0부터 시작**합니다.

```bat
py -3.12 collector.py reconcile configs\my_checks.csv
```

비어 있는 템플릿은 검산에 사용할 수 없으며, 공시 원문의 실제 좌표를 입력해야 합니다.

## 공개 인계 스냅샷 구성

- `examples/B_quarterly_screened.csv`: 보류 제외 26분기 단위 선별본
- `examples/B_quarterly_diagnostic.csv`: 원자료·보류값 설명용
- `examples/B_annual_diagnostic.csv`: 2020–2025년 연간 진단 자료
- `docs/evidence/`: 공시 목록, 변수 정의, 셀별 판단, Q4 복원 근거 및 검증 결과
- `tools/verify_snapshot.py`: 위 CSV와 Excel 일부를 실제로 검산하는 도구 (원본 DART 재검증 아님)

최종 결과의 **완전 재생성**에는 별도 인계 ZIP의 `original_outputs/P0·P1·P2`, `source/tables.json`, `source/official_20261112/`, 수동 피드백 코드·원본 공시 ZIP 등이 필요합니다. GitHub 공개 패키지에는 **복원 과정을 검증할 수 있는 대표 근거만** 담았습니다.
