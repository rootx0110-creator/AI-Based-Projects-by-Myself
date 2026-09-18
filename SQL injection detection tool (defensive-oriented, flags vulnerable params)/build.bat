@echo off
REM ============================================================
REM  SQLInspect - build a standalone Windows exe with PyInstaller
REM ============================================================
setlocal
cd /d "%~dp0"

echo [1/3] Ensuring dependencies...
pip install -r requirements.txt
pip install pyinstaller

echo [2/3] Building static bundle (PyInstaller with --add-data)...
pyinstaller --noconfirm --clean --onefile ^
  --name SQLInspect ^
  --add-data "templates;templates" ^
  --add-data "static;static" ^
  --add-data "core;core" ^
  --add-data "reports;reports" ^
  app.py

if errorlevel 1 (
  echo BUILD FAILED
  exit /b 1
)

echo [3/3] Done. Executable: dist\SQLInspect.exe
echo       Run it, then open http://127.0.0.1:5000
endlocal
pause