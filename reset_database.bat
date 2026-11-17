@echo off
setlocal
cd /d "%~dp0"
title Reset database
rem Starts the app on a fresh, empty database with the fresh migrations of 2026-11-16.
rem The old database is kept as a backup in the instance folder. Run this once.

netstat -ano | findstr ":8000" | findstr "LISTENING" >nul
if not errorlevel 1 (
  echo The app is still running. Close it first, then run this again.
  pause
  exit /b 1
)

echo This makes a NEW EMPTY database for Imtiaz Weaving.
echo The old database is kept as a backup in the instance folder.
echo Registration, the secret key, seed data and client documents are kept.
echo.
choice /c YN /n /m "Press Y to continue, or N to stop: "
if errorlevel 2 (
  echo Nothing was changed.
  pause
  exit /b 1
)

for /f %%d in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set STAMP=%%d
if exist instance\db.sqlite3 (
  copy /y instance\db.sqlite3 "instance\db_old_%STAMP%.sqlite3" >nul
  if errorlevel 1 (
    echo The backup could not be made, so nothing was changed. Close any program using the database, then try again.
    pause
    exit /b 1
  )
  del /q instance\db.sqlite3
  echo Old database saved as instance\db_old_%STAMP%.sqlite3
)

rem Old migration files, replaced by one 0001_initial.py in each app.
if exist "billing\migrations\0002_invoice_fbr_dated_invoice_fbr_environment_and_more.py" del /q "billing\migrations\0002_invoice_fbr_dated_invoice_fbr_environment_and_more.py"
if exist "billing\migrations\0003_invoice_seller_strn.py" del /q "billing\migrations\0003_invoice_seller_strn.py"
if exist "billing\migrations\0004_invoice_invoice_ref_no_invoice_invoice_type_and_more.py" del /q "billing\migrations\0004_invoice_invoice_ref_no_invoice_invoice_type_and_more.py"
if exist "billing\migrations\0005_invoice_seller_ntn.py" del /q "billing\migrations\0005_invoice_seller_ntn.py"
if exist "billing\migrations\0006_invoice_issued_offline.py" del /q "billing\migrations\0006_invoice_issued_offline.py"
if exist "billing\migrations\0007_add_kg_selling.py" del /q "billing\migrations\0007_add_kg_selling.py"
if exist "billing\migrations\0008_pack_lines_and_last_number.py" del /q "billing\migrations\0008_pack_lines_and_last_number.py"
if exist "billing\migrations\0009_metre_selling.py" del /q "billing\migrations\0009_metre_selling.py"
if exist "billing\migrations\0010_invoice_line_quality.py" del /q "billing\migrations\0010_invoice_line_quality.py"
if exist "billing\migrations\0011_remove_pack_selling.py" del /q "billing\migrations\0011_remove_pack_selling.py"
if exist "billing\migrations\0012_remove_job_no.py" del /q "billing\migrations\0012_remove_job_no.py"
if exist "core\migrations\0002_remove_invoice_counter.py" del /q "core\migrations\0002_remove_invoice_counter.py"
if exist "core\migrations\0003_company_sandbox_scenarios_product_fed_percent_and_more.py" del /q "core\migrations\0003_company_sandbox_scenarios_product_fed_percent_and_more.py"
if exist "core\migrations\0004_company_fbr_mode_customer_fbr_checked_at_and_more.py" del /q "core\migrations\0004_company_fbr_mode_customer_fbr_checked_at_and_more.py"
if exist "core\migrations\0005_company_ntn_and_cnic.py" del /q "core\migrations\0005_company_ntn_and_cnic.py"
if exist "core\migrations\0006_pack_lines_and_last_number.py" del /q "core\migrations\0006_pack_lines_and_last_number.py"
if exist "core\migrations\0007_demo_and_registration.py" del /q "core\migrations\0007_demo_and_registration.py"
if exist "core\migrations\0008_product_redesign.py" del /q "core\migrations\0008_product_redesign.py"
if exist "core\migrations\0009_fixed_unregistered_buyer.py" del /q "core\migrations\0009_fixed_unregistered_buyer.py"
if exist "fbr\migrations\0002_alter_fbrcredential_environment.py" del /q "fbr\migrations\0002_alter_fbrcredential_environment.py"
for %%a in (billing core fbr) do if exist "%%a\migrations\__pycache__" rmdir /s /q "%%a\migrations\__pycache__"

echo.
echo Done. Now run start.bat and finish the setup screen again.
echo Then set the last invoice number under Company, and run add_seed_data.bat.
pause
