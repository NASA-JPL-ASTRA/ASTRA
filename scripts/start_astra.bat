@echo off
REM ASTRA one-click start: Whisper API + Backend (Frontend optional)
REM Usage: scripts\start_astra.bat
REM        set ASTRA_BACKEND_PATH=C:\path\to\ASTRA-dev-feature1\backend
REM        scripts\start_astra.bat

cd /d "%~dp0\.."

REM Backend path: prefer env var, then try common locations
if "%ASTRA_BACKEND_PATH%"=="" (
  if exist "..\ASTRA-dev-feature1\backend" (
    set ASTRA_BACKEND_PATH=..\ASTRA-dev-feature1\backend
  ) else if exist "%USERPROFILE%\Desktop\ASTRA-dev-feature1\backend" (
    set ASTRA_BACKEND_PATH=%USERPROFILE%\Desktop\ASTRA-dev-feature1\backend
  )
)

echo === ASTRA One-Click Start ===
echo Whisper: %CD%
echo Backend: %ASTRA_BACKEND_PATH%
echo.

REM Clear task queue if requested
if not "%CLEAR_QUEUE_ON_START%"=="" (
  del /f WhisperServiceAPI.db 2>nul
  echo Cleared task queue (removed WhisperServiceAPI.db)
)

echo [1/2] Starting Whisper API (port 8001)...
start "Whisper API" cmd /c "set PORT=8001 && set FILTER_HALLUCINATION=false && python start.py"

timeout /t 3 /nobreak >nul

if exist "%ASTRA_BACKEND_PATH%" (
  echo [2/2] Starting ASTRA Backend (port 8000)...
  start "ASTRA Backend" cmd /c "cd /d %ASTRA_BACKEND_PATH% && set WHISPER_API_URL=http://127.0.0.1:8001 && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
) else (
  echo [2/2] Skipping Backend (not found: %ASTRA_BACKEND_PATH%)
)

echo.
echo ==========================================
echo Services starting...
echo   - Whisper API: http://127.0.0.1:8001
echo   - ASTRA Backend: http://127.0.0.1:8000
echo.
echo Run realtime demo:
echo   python realtime_demo.py --backend-url http://127.0.0.1:8000
echo.
if not "%ASTRA_BACKEND_PATH%"=="" (
  for %%F in ("%ASTRA_BACKEND_PATH%\..\frontend") do (
    if exist "%%~fF" (
      echo Or start Frontend (in another terminal):
      echo   cd %%~fF ^&^& npm run dev
    )
  )
)
echo ==========================================
echo.
echo Press any key to close this window (services will keep running in background)
pause >nul
