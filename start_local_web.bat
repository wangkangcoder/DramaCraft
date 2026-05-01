@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul

cd /d "%~dp0"

set "ROOT_DIR=%cd%"
set "BACKEND_DIR=%ROOT_DIR%\backend"
set "FRONTEND_DIR=%ROOT_DIR%\frontend"
set "FRONTEND_DIST=%FRONTEND_DIR%\dist\index.html"
set "APP_URL=http://127.0.0.1:8000/ai-screenplay-system/"
set "LOGIN_URL=http://127.0.0.1:8000/ai-screenplay-system/#/login?fresh=1"
set "DOCS_URL=http://127.0.0.1:8000/docs"
set "HEALTH_URL=http://127.0.0.1:8000/health"
set "LOG_DIR=%ROOT_DIR%\run_logs"
set "RUNTIME_DIR=%ROOT_DIR%\.localruntime"
set "BROWSER_PROFILE_DIR=%RUNTIME_DIR%\browser-profile"
set "WATCHER_SCRIPT=%ROOT_DIR%\watch_local_app.ps1"
set "BACKEND_LOG="
set "BACKEND_ERR="
set "BACKEND_PID_FILE=%LOG_DIR%\backend.pid"
set "BROWSER_PID_FILE=%LOG_DIR%\browser.pid"
set "WATCHER_PID_FILE=%LOG_DIR%\watcher.pid"
set "PYTHON_EXE="
set "NODE_HOME="
set "LOCAL_NODE_DIR=%ROOT_DIR%\.localtools\node-v20.20.2-win-x64"
set "BROWSER_EXE="
set "SKIP_FRONTEND_BUILD=1"
set "LOCAL_APP_SESSION_MODE_VALUE=0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

if exist "%ROOT_DIR%\.venv\Scripts\python.exe" (
  set "PYTHON_EXE=%ROOT_DIR%\.venv\Scripts\python.exe"
) else (
  set "PYTHON_EXE=python"
)

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>nul
if not exist "%RUNTIME_DIR%" mkdir "%RUNTIME_DIR%" >nul 2>nul

if defined STOP_ONLY goto :stop_only

echo ========================================================
echo Starting local web app without Docker
echo ========================================================
echo.

"%PYTHON_EXE%" --version >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python 3.10+ was not found.
  echo Install Python first, then run this file again.
  pause
  exit /b 1
)

call :prepare_log_paths

"%PYTHON_EXE%" -c "import uvicorn, fastapi, requests, openai, neo4j, pydantic_settings, zhipuai" >nul 2>nul
if errorlevel 1 (
  echo Installing backend dependencies...
  "%PYTHON_EXE%" -m pip install -r "%BACKEND_DIR%\requirements.txt"
  if errorlevel 1 (
    echo [ERROR] Backend dependency installation failed.
    pause
    exit /b 1
  )
)

if defined FORCE_FRONTEND_BUILD (
  echo Checking source file encoding...
  "%PYTHON_EXE%" "%ROOT_DIR%\scripts\check_mojibake.py"
  if errorlevel 1 (
    echo [ERROR] Source encoding check failed.
    echo Fix mojibake before rebuilding the frontend.
    pause
    exit /b 1
  )

  call :ensure_node
  if errorlevel 1 (
    echo [ERROR] Node.js was not found.
    echo Install Node.js 18+ or keep the portable Node folder under .localtools.
    pause
    exit /b 1
  )

  if not exist "%FRONTEND_DIR%\node_modules\.bin\vite.cmd" (
    echo Installing frontend dependencies...
    pushd "%FRONTEND_DIR%"
    call npm install
    set "NPM_EXIT=%ERRORLEVEL%"
    popd
    if not "!NPM_EXIT!"=="0" (
      echo [ERROR] Frontend dependency installation failed.
      pause
      exit /b 1
    )
  )

  echo Building the latest frontend bundle...
  pushd "%FRONTEND_DIR%"
  call npm run build
  set "BUILD_EXIT=%ERRORLEVEL%"
  if not "!BUILD_EXIT!"=="0" (
    echo Frontend build failed once. Retrying in 2 seconds...
    timeout /t 2 /nobreak >nul
    call npm run build
    set "BUILD_EXIT=%ERRORLEVEL%"
  )
  popd
  if not "!BUILD_EXIT!"=="0" (
    if exist "%FRONTEND_DIST%" (
      echo [WARN] Frontend build failed, but an existing dist bundle was found.
      echo [WARN] Continuing with the last successful frontend build.
    ) else (
      echo [ERROR] Frontend build failed and no existing frontend dist is available.
      pause
      exit /b 1
    )
  )
) else (
  if exist "%FRONTEND_DIST%" (
    echo Reusing the existing frontend dist bundle.
  ) else (
    echo [ERROR] The shared package is missing frontend\dist.
    echo This one-click startup no longer rebuilds the frontend on the recipient machine.
    echo Rebuild the frontend on the source machine and include the full frontend\dist folder before sharing.
    pause
    exit /b 1
  )
)

echo Stopping any previous local app instance...
call :stop_existing_instances
call :clear_browser_profile

if defined MANAGED_BROWSER (
  rem Keep the backend alive and let the watcher handle shutdown explicitly.
  set "LOCAL_APP_SESSION_MODE_VALUE=0"
)

echo Starting backend service...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$env:LOCAL_APP_SESSION_MODE = '%LOCAL_APP_SESSION_MODE_VALUE%'; $env:LOCAL_APP_STARTUP_GRACE_SECONDS = '90'; $env:LOCAL_APP_CLIENT_TIMEOUT_SECONDS = '45'; $env:LOCAL_APP_EMPTY_SHUTDOWN_SECONDS = '8'; $env:LOCAL_APP_BACKEND_PID_FILE = '%BACKEND_PID_FILE%'; $process = Start-Process -PassThru -WindowStyle Hidden -FilePath '%PYTHON_EXE%' -WorkingDirectory '%ROOT_DIR%' -ArgumentList 'backend\launch_local.py' -RedirectStandardOutput '%BACKEND_LOG%' -RedirectStandardError '%BACKEND_ERR%'; if (-not $process) { exit 1 }; for ($i = 0; $i -lt 3; $i++) { try { if (Test-Path -LiteralPath '%BACKEND_PID_FILE%') { Remove-Item -LiteralPath '%BACKEND_PID_FILE%' -Force -ErrorAction Stop }; [System.IO.File]::WriteAllText('%BACKEND_PID_FILE%', [string]$process.Id, [System.Text.Encoding]::ASCII); exit 0 } catch { Start-Sleep -Milliseconds 300 } }; exit 0"
if errorlevel 1 (
  echo [ERROR] Failed to launch the backend process.
  echo Check these files for details:
  echo   %BACKEND_LOG%
  echo   %BACKEND_ERR%
  pause
  exit /b 1
)

echo Waiting for the local service to become ready...
call :wait_for_health 60
if errorlevel 1 (
  echo [ERROR] The backend did not pass the health check in time.
  echo Check these files for details:
  echo   %BACKEND_LOG%
  echo   %BACKEND_ERR%
  pause
  exit /b 1
)

:open_browser
if defined NO_BROWSER goto :finish

if defined MANAGED_BROWSER (
  call :launch_managed_browser
  if errorlevel 1 (
    echo Managed browser mode could not be started.
    echo Falling back to the standard browser mode.
    call :open_default_browser "%LOGIN_URL%"
  )
  goto :finish
)

call :open_default_browser "%LOGIN_URL%"

:finish
echo.
echo Local app is ready:
echo   App:  %APP_URL%
echo   Docs: %DOCS_URL%
echo.
echo Default login:
echo   Username: admin
echo   Password: 123456
echo.
echo Logs:
echo   %BACKEND_LOG%
echo   %BACKEND_ERR%
if defined MANAGED_BROWSER (
  echo.
  echo Closing the dedicated app window will stop the local service.
)
echo.
echo If the browser did not open, visit the App URL manually.
endlocal
exit /b 0

:open_default_browser
set "TARGET_URL=%~1"
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Start-Process '%TARGET_URL%'; exit 0 } catch { exit 1 }" >nul 2>nul
if not errorlevel 1 exit /b 0
start "" "%TARGET_URL%" >nul 2>nul
if not errorlevel 1 exit /b 0
explorer "%TARGET_URL%" >nul 2>nul
if not errorlevel 1 exit /b 0
exit /b 1

:prepare_log_paths
set "RUN_ID="
for /f %%i in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "(Get-Date).ToString('yyyyMMdd-HHmmss')"') do set "RUN_ID=%%i"
if not defined RUN_ID set "RUN_ID=%RANDOM%"
set "BACKEND_LOG=%LOG_DIR%\backend-%RUN_ID%.log"
set "BACKEND_ERR=%LOG_DIR%\backend-%RUN_ID%.err.log"
exit /b 0

:stop_only
echo ========================================================
echo Stopping local web app
echo ========================================================
echo.
call :stop_existing_instances
call :clear_browser_profile
echo Local app has been stopped.
echo.
endlocal
exit /b 0

:launch_managed_browser
call :ensure_browser
if errorlevel 1 exit /b 1

if not exist "%WATCHER_SCRIPT%" (
  echo [ERROR] Managed browser watcher script is missing:
  echo   %WATCHER_SCRIPT%
  exit /b 1
)

if not exist "%BROWSER_PROFILE_DIR%" mkdir "%BROWSER_PROFILE_DIR%" >nul 2>nul

powershell -NoProfile -ExecutionPolicy Bypass -Command "$process = Start-Process -PassThru -FilePath '%BROWSER_EXE%' -ArgumentList @('--new-window','--app=%LOGIN_URL%','--user-data-dir=%BROWSER_PROFILE_DIR%'); if ($process) { Set-Content -Path '%BROWSER_PID_FILE%' -Value $process.Id -Encoding ascii; exit 0 } else { exit 1 }"
if errorlevel 1 exit /b 1

call :wait_for_managed_browser 10
if errorlevel 1 (
  del /q "%BROWSER_PID_FILE%" >nul 2>nul
  exit /b 1
)

set /p BACKEND_PID=<"%BACKEND_PID_FILE%"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$process = Start-Process -PassThru -WindowStyle Hidden -FilePath 'powershell.exe' -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File','%WATCHER_SCRIPT%','-BackendPid','%BACKEND_PID%','-BrowserProfileDir','%BROWSER_PROFILE_DIR%','-BrowserPidFile','%BROWSER_PID_FILE%','-BackendPidFile','%BACKEND_PID_FILE%','-WatcherPidFile','%WATCHER_PID_FILE%'); if ($process) { Set-Content -Path '%WATCHER_PID_FILE%' -Value $process.Id -Encoding ascii; exit 0 } else { exit 1 }"
exit /b 0

:stop_existing_instances
call :stop_process_from_pid_file "%WATCHER_PID_FILE%"
call :stop_process_from_pid_file "%BROWSER_PID_FILE%"
call :stop_process_from_pid_file "%BACKEND_PID_FILE%"
call :stop_managed_browser_processes
call :stop_backend_processes
call :wait_for_no_managed_browser 10
call :wait_for_no_backend 10
del /q "%WATCHER_PID_FILE%" >nul 2>nul
del /q "%BROWSER_PID_FILE%" >nul 2>nul
del /q "%BACKEND_PID_FILE%" >nul 2>nul
exit /b 0

:stop_process_from_pid_file
set "PID_FILE=%~1"
if not exist "%PID_FILE%" exit /b 0
powershell -NoProfile -ExecutionPolicy Bypass -Command "$pidText = Get-Content -LiteralPath '%PID_FILE%' -ErrorAction SilentlyContinue | Select-Object -First 1; $pidValue = 0; if ([int]::TryParse($pidText, [ref]$pidValue)) { $proc = Get-Process -Id $pidValue -ErrorAction SilentlyContinue; if ($proc) { Stop-Process -Id $pidValue -Force -ErrorAction SilentlyContinue } }" >nul 2>nul
del /q "%PID_FILE%" >nul 2>nul
exit /b 0

:stop_backend_processes
powershell -NoProfile -ExecutionPolicy Bypass -Command "$processes = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^python(\\.exe)?$' -and $_.CommandLine -like '*backend\launch_local.py*' }; foreach ($proc in $processes) { Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>nul
exit /b 0

:stop_managed_browser_processes
powershell -NoProfile -ExecutionPolicy Bypass -Command "$profile = [regex]::Escape('%BROWSER_PROFILE_DIR%'); $processes = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { ($_.Name -ieq 'msedge.exe' -or $_.Name -ieq 'chrome.exe') -and $_.CommandLine -match $profile }; foreach ($proc in $processes) { Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>nul
exit /b 0

:wait_for_no_backend
set "MAX_WAIT=%~1"
for /l %%i in (1,1,%MAX_WAIT%) do (
  call :check_backend_process
  if errorlevel 1 exit /b 0
  timeout /t 1 /nobreak >nul
)
exit /b 0

:wait_for_no_managed_browser
set "MAX_WAIT=%~1"
for /l %%i in (1,1,%MAX_WAIT%) do (
  call :check_managed_browser
  if errorlevel 1 exit /b 0
  timeout /t 1 /nobreak >nul
)
exit /b 0

:wait_for_health
set "MAX_WAIT=%~1"
for /l %%i in (1,1,%MAX_WAIT%) do (
  call :check_health
  if not errorlevel 1 exit /b 0
  timeout /t 1 /nobreak >nul
)
exit /b 1

:wait_for_managed_browser
set "MAX_WAIT=%~1"
for /l %%i in (1,1,%MAX_WAIT%) do (
  call :check_managed_browser
  if not errorlevel 1 exit /b 0
  timeout /t 1 /nobreak >nul
)
exit /b 1

:check_health
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $response = Invoke-WebRequest -UseBasicParsing -Uri '%HEALTH_URL%' -TimeoutSec 2; if ($response.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>nul
exit /b %ERRORLEVEL%

:check_backend_process
powershell -NoProfile -ExecutionPolicy Bypass -Command "$proc = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^python(\\.exe)?$' -and $_.CommandLine -like '*backend\launch_local.py*' } | Select-Object -First 1; if ($proc) { exit 0 } else { exit 1 }" >nul 2>nul
exit /b %ERRORLEVEL%

:check_managed_browser
powershell -NoProfile -ExecutionPolicy Bypass -Command "$profile = [regex]::Escape('%BROWSER_PROFILE_DIR%'); $proc = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { ($_.Name -ieq 'msedge.exe' -or $_.Name -ieq 'chrome.exe') -and $_.CommandLine -match $profile } | Select-Object -First 1; if ($proc) { exit 0 } else { exit 1 }" >nul 2>nul
exit /b %ERRORLEVEL%

:clear_browser_profile
if exist "%BROWSER_PROFILE_DIR%" (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Test-Path -LiteralPath '%BROWSER_PROFILE_DIR%') { Remove-Item -LiteralPath '%BROWSER_PROFILE_DIR%' -Recurse -Force -ErrorAction SilentlyContinue }" >nul 2>nul
)
exit /b 0

:ensure_node
if exist "%LOCAL_NODE_DIR%\node.exe" (
  set "NODE_HOME=%LOCAL_NODE_DIR%"
)
if defined NODE_HOME goto :node_ready
if exist "%ProgramFiles%\nodejs\node.exe" set "NODE_HOME=%ProgramFiles%\nodejs"
if not defined NODE_HOME if exist "%ProgramFiles(x86)%\nodejs\node.exe" set "NODE_HOME=%ProgramFiles(x86)%\nodejs"
if not defined NODE_HOME if exist "%LocalAppData%\Programs\nodejs\node.exe" set "NODE_HOME=%LocalAppData%\Programs\nodejs"

:node_ready
if defined NODE_HOME set "PATH=%NODE_HOME%;%PATH%"
where node >nul 2>nul
if errorlevel 1 exit /b 1
where npm >nul 2>nul
if errorlevel 1 exit /b 1
exit /b 0

:ensure_browser
if exist "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" (
  set "BROWSER_EXE=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
  exit /b 0
)
if exist "C:\Program Files\Microsoft\Edge\Application\msedge.exe" (
  set "BROWSER_EXE=C:\Program Files\Microsoft\Edge\Application\msedge.exe"
  exit /b 0
)
if exist "%LocalAppData%\Microsoft\Edge\Application\msedge.exe" (
  set "BROWSER_EXE=%LocalAppData%\Microsoft\Edge\Application\msedge.exe"
  exit /b 0
)
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
  set "BROWSER_EXE=C:\Program Files\Google\Chrome\Application\chrome.exe"
  exit /b 0
)
if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
  set "BROWSER_EXE=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
  exit /b 0
)
if exist "%LocalAppData%\Google\Chrome\Application\chrome.exe" (
  set "BROWSER_EXE=%LocalAppData%\Google\Chrome\Application\chrome.exe"
  exit /b 0
)
exit /b 1
