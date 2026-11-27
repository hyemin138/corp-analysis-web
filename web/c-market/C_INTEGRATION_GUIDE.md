# 팀 저장소 통합 안내

기준은 origin/main `d166d2d7ee5866d83b613194e78a97f3457d521f`다. 기본 브랜치는 main이며 작업 브랜치는 feat/c-market-dashboard다. 접근 계정 psy5965에 push 권한이 확인됐다. main 직접 커밋·push·병합·배포는 하지 않는다.

검사 당시 추적 파일은 루트 README·.gitignore와 analysis/db/preprocessing/web README6개뿐이었다. React·Supabase·Vercel 방향만 문서로 정해졌고 공통 웹 셸·라우터·API·DB 스키마·PR 템플릿은 없었다. 기존 열려 있는 PR #1은 feature/track2-dart-collector로 별도 작업이어서 건드리지 않았다. README의 `분류: 한 일` 커밋 규칙을 따른다.

따라서 C 코드를 `web/c-market` 독립 Vite 패키지로 추가했다. web 루트나 다른 트랙을 덮어쓰지 않았다. 현 로컬 URL5174는 단독 검수본5173과 분리했다. 향후 팀의 React 셸이 생기면 C 라우트를 연결하고 스타일 범위·공통 내비게이션·선택 보존 정책을 협의해야 한다. 현재 존재하지 않는 공통 화면과의 호환성이 검증됐다고 주장하지 않는다.

안전한 병합 순서: 내부 데이터 ZIP 전달 → 로컬 import와 테스트 → 팀원 C 화면 검토 → 호스트 라우터/스타일/인증 협의 → provider 변환 → 필요 시 별도 통합 PR. 현재 PR을 병합하더라도 원 README의 Vercel Root Directory=web만으로 이 하위 앱이 자동 배포되지는 않는다. 배포 구성은 변경하지 않았다.

`public/data`, `data`, `qa`, `dist`, node_modules는 의도적으로 추적 제외다. 데이터 import 후 `git status --ignored`로 제외를 확인한다. 원자료 공개 권한 확인 전 force-add를 하지 않는다. 미확정 API 계약을 Supabase 스키마로 구현하지 않는다.
