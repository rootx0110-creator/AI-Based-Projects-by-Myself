@echo off
REM ============================================================
REM  Build standalone STRIDEForge.exe (single file, no install)
REM  1) installs deps   2) runs PyInstaller   3) outputs dist\
REM ============================================================
cd /d "%~dp0"
echo [1/2] Installing dependencies...
python -m pip install -r requirements.txt pyinstaller --quiet
if errorlevel 1 ( echo Install failed & pause & exit /b 1 )

echo [2/2] Building executable with PyInstaller...
pyinstaller --noconfirm --clean --onefile --name STRIDEForge ^
  --add-data "templates;templates" ^
  --add-data "static;static" ^
  app.py
if errorlevel 1 ( echo Build failed & pause & exit /b 1 )

echo.
echo  Build complete: dist\STRIDEForge.exe
echo  Run it - it starts the bundled web server and opens your browser.
pause