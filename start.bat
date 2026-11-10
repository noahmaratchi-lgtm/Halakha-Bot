@echo off
rem Double-click to run the Halakha Bot on Windows.
cd /d "%~dp0"
where py >nul 2>nul && (set PY=py) || (set PY=python)
if not exist .venv\Scripts\python.exe (
  echo Setting up for the first time, this takes a minute...
  if exist .venv rmdir /s /q .venv
  %PY% -m venv .venv || (echo. & echo Python is not installed. Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH". & pause & exit /b 1)
)
.venv\Scripts\python -m pip install -q -r requirements.txt
echo Starting... your browser will open at http://localhost:5000
echo Keep this window open while you use the bot. Close it to stop.
start "" cmd /c "timeout /t 20 >nul & start http://localhost:5000"
.venv\Scripts\python app.py
pause
