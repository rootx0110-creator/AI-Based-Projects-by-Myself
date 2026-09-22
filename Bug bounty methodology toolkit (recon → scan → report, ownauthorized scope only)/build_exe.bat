@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo  Building BBMToolkit.exe (PyInstaller, one file)
echo ============================================================
python -m pip install --upgrade pyinstaller
if errorlevel 1 (
  echo  [FAIL] pip install pyinstaller failed
  exit /b 1
)
python -m PyInstaller --noconfirm --onefile --windowed ^
  --name BBMToolkit ^
  --add-data "static;static" ^
  --collect-all certifi ^
  app.py
if errorlevel 1 (
  echo  [FAIL] pyinstaller build failed
  exit /b 1
)
echo.
echo  [OK] dist\BBMToolkit.exe is ready.
echo  Run it, then open http://127.0.0.1:8765 in your browser.
endlocal
