# 자료 출처와 공시 이용 범위

## 공식 데이터 출처

- [금융감독원 전자공시시스템(DART)](https://dart.fss.or.kr/): 태웅로직스 정기보고서 및 연결재무제표 주석
- [OpenDART](https://opendart.fss.or.kr/): API 이용 및 인증 안내
- [공시검색 API 설명](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019001): 정기공시 검색 및 접수번호
- [고유번호 API 설명](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019018): 회사의 DART 고유번호 조회
- [공시서류 원본파일 API 설명](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019003): XML 원본 ZIP 수집

## 데이터 처리 원칙

1. 연결(CFS) 주석의 계정 정의와 기간을 분리해 보관하고 별도(OFS) 값과 혼합하지 않습니다.
2. 접수번호와 공시일을 보존하되, 실제 시점별 예측에 쓰려면 **공시가 언제 사용 가능해졌는지** 다시 검토합니다.
3. 분기 비용(`flow`)과 기간말 잔액(`stock`), 연간 물동량(TEU)을 혼합하거나 연간 값을 임의 분기화하지 않습니다.
4. 누락·불일치·공시 버전 간 차이를 임의로 수정하지 않고 기록합니다.

실제 공시 원문·수집 시점·재배포 가능 범위는 [OpenDART 이용약관](https://opendart.fss.or.kr/)과 각 자료의 이용조건을 확인해야 합니다(확인필요). 코드 예시에 API 키 또는 응답에 포함된 비밀정보가 남지 않도록 해야 합니다.

## 이번 최종 인계 출처 추적

정기·정정공시 29건의 접수번호·공시일·원문 URL·SHA256: [`evidence/source_catalog.csv`](evidence/source_catalog.csv). 공시별 수치와 사용 판단은 [`evidence/quarterly_cell_decisions.csv`](evidence/quarterly_cell_decisions.csv)의 `source_url`, `source_value_ids`, `decision` 열에 기록. 자료 정리 기준은 사용자 제공 `Track2_B_handoff_20261112_reviewed(2).zip` (2026-11-12 검토본). 이 공개용 ZIP은 원본 공시 ZIP·DART HTML 전체를 재배포하지 않음.
