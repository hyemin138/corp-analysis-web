# 테스트 및 자료 검증 결과

검증일: 2026-11-17 / 실행 환경: Linux Python 3.13 (실제 Windows 3.12 구동은 이 실행에서 확인하지 않음)

| 항목 | 결과 | 검증 방법 / 한계 |
| --- | --- | --- |
| 수집기 가상 데이터·HTTP 테스트 | **21 / 21 통과** | 최초 버전 `tests/test_collector.py`에서 목(mock) API 및 가상 XML 사용 |
| P0/P1/P2 기본 오프라인 검사 | **8 / 8 통과** | `tests/test_smoke.py` 사용 |
| 전체 테스트 | **29 / 29 통과** | `python -m unittest discover -s tests -v` |
| 분기 행수 | **26** | 공개 선별·진단 CSV 재집계 |
| 변수 정의 | **23** | `docs/evidence/variable_dictionary.csv` 대조 |
| 셀별 결정 | **598** | 26 × 23, 중복 여부 검사 |
| 값이 남아 있는 셀 | **543** | 보류·결측을 비우는 선별 CSV 확인 |
| Q4 검토 계산값 | **70** | 2021~2025 Q4 × 14계정, `연간 - 9개월` Decimal 계산 재대조 |
| 공시 출처 | **29** | 원문 접수번호 중복 및 기록된 SHA256 형식 검사 |
| 엑셀/CSV 값 비교 | **1,196셀 일치** | 선별·진단 시트 각 26 × 23 값, 저장된 Excel 값과 CSV 대응 확인 |

**검사 결과:** `tools/verify_snapshot.py` → `status=PASS`.

> 위 테스트는 수집기 내부 동작 및 **2026-11-12 인계본 스냅샷의 정합성**을 검증한 것입니다. 29건 원본 공시 ZIP의 SHA-256을 이번 실행환경에서 다시 계산하거나, 모든 연결·별도 회계적 정의를 독립 검수한 것은 아닙니다. OpenDART API 실통신과 Windows 3.12 전체 재실행은 별도 확인필요.

참고 출처: 최초 수집기 ZIP의 `tests/test_collector.py`; 최종 인계 ZIP의 `qa/handoff_summary.json`, `qa/quarterly_cell_decisions.csv`, `qa/feedback_20261112/q4_source_review.csv`, `Track2_B_검토및인계.xlsx`.
