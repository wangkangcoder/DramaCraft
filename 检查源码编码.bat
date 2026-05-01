@echo off
setlocal
chcp 65001 >nul

cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

if exist "%~dp0.venv\Scripts\python.exe" (
  "%~dp0.venv\Scripts\python.exe" "%~dp0scripts\check_mojibake.py"
) else (
  python "%~dp0scripts\check_mojibake.py"
)

set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" pause
endlocal
exit /b %EXIT_CODE%
