@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo.
  echo [ERROR] .venv not found. Run setup first:
  echo   python -m venv .venv
  echo   pip install -r requirements.txt
  echo.
  pause
  exit /b 1
)

netstat -ano | findstr /R /C:":8765 .*LISTENING" >nul 2>&1
if not errorlevel 1 (
  echo.
  echo [music-library] Port 8765 is already in use.
  echo If the UI looks outdated, press Ctrl+C in the old window, then run this again.
  echo.
  start "" "http://127.0.0.1:8765"
  pause
  exit /b 0
)

echo.
echo [music-library] http://127.0.0.1:8765  (stop: Ctrl+C)
echo.

rem Open browser after server starts (fixed 2s delay)
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:8765/"

".venv\Scripts\python.exe" tools\web\app.py
if errorlevel 1 pause
