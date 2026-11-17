@echo off
setlocal
cd /d "%~dp0"
rem Adds the sandbox test products, test buyer and one saved test invoice per assigned scenario,
rem from instance\seed_sandbox.json. Nothing is sent to FBR. Enter the scenarios under FBR setup first.
if not exist venv\Scripts\python.exe (
  echo Run start.bat first, then run this again.
  pause
  exit /b 1
)
venv\Scripts\python.exe manage.py add_seed_data --file instance\seed_sandbox.json
pause
