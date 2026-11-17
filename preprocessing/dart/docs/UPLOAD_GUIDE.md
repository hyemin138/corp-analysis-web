# 팀 공용 GitHub에 반영하는 방법

이 패키지는 팀 저장소 루트에 상대 경로 `preprocessing/dart/`가 생기도록 구성되어 있습니다.
해당 폴더 내용만 업로드하고 `main`에 직접 넣기보다 개인 브랜치에서 PR을 생성하세요.

1. 팀 저장소를 Clone하거나 웹에서 개인 브랜치 `feature/track2-dart-collector`를 만듭니다.
2. 이 압축을 풀어 저장소의 `preprocessing/dart/` 경로를 유지합니다.
3. 업로드 전 `git status` 또는 GitHub 변경 파일 목록을 확인합니다. **.env, data/raw, state.sqlite3는 없어야 합니다.**
4. 커밋: `데이터: Track2 DART 수집·정제·검증 코드 및 인계 자료 추가`
5. PR 설명에는 수정 범위(Track2 B), offline 테스트 결과, 원본 검증의 제한을 적습니다.

팀 저장소 루트의 README나 .gitignore를 덮어쓰지 않도록, 수집기 전용 README·.gitignore를 하위 폴더 안에 넣었습니다.
