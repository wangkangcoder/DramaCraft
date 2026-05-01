@echo off
setlocal
chcp 65001 >nul

cd /d "%~dp0"

set "STOP_ONLY=1"
call "%~dp0start_local_web.bat"
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
  echo.
  echo Stop failed. Please read the message above and try again.
  pause
)

endlocal
exit /b %EXIT_CODE%
