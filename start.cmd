@echo off
cd /d "%~dp0"
echo.
echo  [music-library] http://127.0.0.1:8765  ^(stop: Ctrl+C^)
echo.
start "" "http://127.0.0.1:8765"
".venv\Scripts\python.exe" tools\web\app.py
if errorlevel 1 pause
