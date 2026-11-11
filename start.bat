@echo off
rem Double-click to run the Halakha Bot on Windows.
rem Each start it fetches the newest version from GitHub (your api_key file and settings are kept).
cd /d "%~dp0"

echo Checking for updates...
set "UPD=%TEMP%\halakha_bot_update"
if exist "%UPD%" rmdir /s /q "%UPD%"
mkdir "%UPD%"
curl.exe -fsSL --max-time 60 -o "%UPD%\latest.zip" https://github.com/noahmaratchi-lgtm/Halakha-Bot/archive/refs/heads/main.zip
if errorlevel 1 (
  echo Could not check for updates - starting the version you have.
) else (
  tar -xf "%UPD%\latest.zip" -C "%UPD%"
  for /d %%D in ("%UPD%\*") do (
    if exist "%%D\start.bat" move /y "%%D\start.bat" "%~dp0start.new" >nul
    xcopy /e /y /q "%%D\*" "%~dp0" >nul
  )
  echo Up to date.
)
rmdir /s /q "%UPD%" 2>nul

where py >nul 2>nul && (set PY=py) || (set PY=python)
if not exist .venv\Scripts\python.exe (
  echo Setting up for the first time, this takes a minute...
  if exist .venv rmdir /s /q .venv
  %PY% -m venv .venv || (echo. & echo Python is not installed. Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH". & pause & exit /b 1)
)
.venv\Scripts\python -m pip install -q --disable-pip-version-check -r requirements.txt
echo Starting... your browser will open at http://localhost:5000
echo Keep this window open while you use the bot. Close it to stop.
start "" cmd /c "timeout /t 15 >nul & start http://localhost:5000"
.venv\Scripts\python app.py

rem Swap in the newer start.bat after the bot stops. This is one line on purpose:
rem cmd reads the whole line before the file is replaced, then exits.
if exist start.new (copy /y start.new start.bat >nul & del start.new & pause & exit /b)
pause
