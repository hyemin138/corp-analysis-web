# 팀 통합 V2

동일feat/c-market-dashboard·Draft PR #2를갱신한다. 시작HEAD49e13b5이고기존main d166d2d였다. main직접push·병합·자동병합·배포는하지않는다. 최신원격상태·최종커밋은 C_V2_FINAL_REPORT.md에기록한다.

수정범위는web/c-market뿐이다. 팀main에는아직실제호스트셸/공통라우터/API/DB스키마가없었고다른트랙·공통설정을대체하지않았다. V1독립앱/원자료와Git기준소스를보존했다.

V2는4영역으로재편했다. 메뉴를팀호스트에연결할때 App의view와공통스타일/인증정책을협의하고provider만API어댑터로교체한다. 현재정식API/PK/FK/Supabase구조는확정하지않았다. Vercel루트설정이나환경변수는변경하지않는다.

팀원은내부ZIP으로실자료를가져오고 C_V2_TEAM_INTEGRATION_GUIDE.md를따른다. public/data·data·qa·dist·node_modules는Git제외이며src/data공급자와연구통계참조는추적한다. 불필요한기능과테스트는C전용범위에서정리했고회귀대응표를남겼다.
