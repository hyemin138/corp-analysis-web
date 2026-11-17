@echo off
chcp 65001 >nul
cd /d "%~dp0"
py -3.12 --version >nul 2>&1
if errorlevel 1 (
  echo Python 3.12가 필요합니다. 설치 시 Python Launcher도 선택하세요.
  pause
  exit /b 1
)
:menu
cls
echo 태웅로직스 TRACK2 B 수집기
echo 1. 초기화 및 API 키 파일 열기
echo 2. 공시 목록 수집
echo 3. 파일럿 수집 계획만 확인
echo 4. 파일럿 수집 (2025 사업, 2026 반기)
echo 5. 직전 수집 계획 이어받기
echo 6. 상태 확인
echo 7. 원본 검증 및 후보 표 추출
echo 8. 검수값 CSV 내보내기
echo 9. README 열기
echo 0. 종료
set /p action=번호: 
if "%action%"=="0" exit /b 0
if "%action%"=="1" (
 py -3.12 collector.py init
 if not exist .env copy .env.example .env >nul
 notepad .env
)
if "%action%"=="2" py -3.12 collector.py discover --freeze 20261110
if "%action%"=="3" py -3.12 collector.py collect --pilot --dry-run
if "%action%"=="4" py -3.12 collector.py collect --pilot
if "%action%"=="5" py -3.12 collector.py resume
if "%action%"=="6" py -3.12 collector.py status
if "%action%"=="7" (
 py -3.12 collector.py validate
 if not errorlevel 1 py -3.12 collector.py extract
)
if "%action%"=="8" py -3.12 collector.py export
if "%action%"=="9" notepad README.md
pause
goto menu
