@echo off
setlocal
chcp 65001 >nul

cd /d "%~dp0"

rem Use the system default browser so the latest local page opens in the user's browser.
call "%~dp0start_local_web.bat"
set "EXIT_CODE=%ERRORLEVEL%"

if "%EXIT_CODE%"=="0" (
  echo.
  echo The local app launch has completed.
  echo If the browser did not open automatically, visit:
  echo   http://127.0.0.1:8000/ai-screenplay-system/#/login?fresh=1
  echo.
  if not defined NO_SUCCESS_PAUSE pause
) else (
  echo.
  echo Start failed. Please read the message above and try again.
  pause
)

endlocal
exit /b %EXIT_CODE%
