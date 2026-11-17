@echo off
setlocal
cd /d "%~dp0"
title Make delivery folder
rem Makes D:\Imtiaz_Weaving_Delivery with only what the client's computer needs:
rem the app, its start, stop and backup files, and the real database with its keys.
rem Test files, documents, old databases and the reset and test-data files stay here.

set "OUT=D:\Imtiaz_Weaving_Delivery"

netstat -ano | findstr ":8000" | findstr "LISTENING" >nul
if not errorlevel 1 (
  echo The app is still running. Close it first, then run this again.
  echo The database must not be copied while the app is using it.
  pause
  exit /b 1
)

if not exist instance\db.sqlite3 (
  echo instance\db.sqlite3 was not found, so nothing was made.
  pause
  exit /b 1
)
if not exist instance\fbr_key.txt (
  echo instance\fbr_key.txt was not found. Without it the saved FBR tokens can't be read. Nothing was made.
  pause
  exit /b 1
)

if exist "%OUT%" (
  echo %OUT% already exists. It will be deleted and made again.
  choice /c YN /n /m "Press Y to continue, or N to stop: "
  if errorlevel 2 (
    echo Nothing was changed.
    pause
    exit /b 1
  )
  rmdir /s /q "%OUT%"
  if exist "%OUT%" (
    echo %OUT% could not be deleted. Close any window or program using it, then try again.
    pause
    exit /b 1
  )
)
mkdir "%OUT%"

echo Copying the app...
for %%d in (billing config core fbr licensing templates static) do (
  robocopy "%%d" "%OUT%\%%d" /E /XD __pycache__ /XF tests.py *.pyc /NFL /NDL /NJH /NJS /NP >nul
  if errorlevel 8 goto copy_failed
)
for %%f in (manage.py requirements.txt start.bat start_app.vbs stop_app.vbs backup.bat) do (
  copy /y "%%f" "%OUT%\" >nul
  if errorlevel 1 goto copy_failed
)

echo Copying the database and keys...
mkdir "%OUT%\instance"
for %%f in (db.sqlite3 fbr_key.txt secret_key.txt licence.json) do (
  if exist "instance\%%f" (
    copy /y "instance\%%f" "%OUT%\instance\" >nul
    if errorlevel 1 goto copy_failed
  )
)

for %%f in (manage.py start.bat instance\db.sqlite3 instance\fbr_key.txt core\models.py billing\models.py fbr\payload.py) do (
  if not exist "%OUT%\%%f" (
    echo %%f is missing from the delivery folder.
    goto copy_failed
  )
)

echo.
echo Done: %OUT%
echo Copy this folder to a USB drive and keep it private.
echo It holds client records, the FBR tokens and the key to read them.
echo.
echo On the client's computer:
echo  1. Copy the folder to the computer, for example D:\Imtiaz_Weaving.
echo  2. Run start.bat. The first run needs internet and Python 3.12 or newer.
echo  3. Add that computer's IP in IRIS before sending any invoice from it.
echo  4. From then on, make real invoices only on the client's computer.
pause
exit /b 0

:copy_failed
echo.
echo The delivery folder is not complete. Don't use it. See the message above, then run this again.
pause
exit /b 1
