@echo off
title Web App Fuzzer - Input Validation Testing
setlocal
cd /d "%~dp0"

echo.
echo  ============================================================
echo   Web App Fuzzer - Input Validation Testing  v1.0.0
echo  ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo  [ERROR] Python was not found.
  echo  Install it from https://python.org and try again.
  pause
  exit /b 1
)

echo  [1/2] Checking dependencies...
pip show flask >nul 2>nul
if errorlevel 1 (
  echo        Installing dependencies - first run only...
  python -m pip install -r requirements.txt
)
pip show requests >nul 2>nul
if errorlevel 1 (
  echo        Installing dependencies - first run only...
  python -m pip install -r requirements.txt
)

echo  [2/2] Starting server...
echo.
echo  ----- Opening http://127.0.0.1:5000 in your browser... -----
echo.

timeout /t 3 /nobreak >nul
start "" http://127.0.0.1:5000

python app.py

pause