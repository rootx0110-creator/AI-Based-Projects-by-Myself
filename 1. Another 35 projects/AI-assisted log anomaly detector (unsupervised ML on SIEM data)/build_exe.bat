@echo off
REM ===========================================================================
REM  Build SentinelForge as a single Windows EXE using PyInstaller.
REM  Output: dist\SentinelForge.exe  (self-contained, runs the local web app)
REM ===========================================================================
setlocal

cd /d "%~dp0"

python -m PyInstaller --version >nul 2>nul
if errorlevel 1 (
  echo Installing PyInstaller ...
  pip install pyinstaller
)

echo Cleaning previous builds ...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo Building EXE ...
python -m PyInstaller --noconfirm --onefile --windowed --name SentinelForge ^
  --add-data "templates;templates" ^
  --add-data "static;static" ^
  --add-data "loganomaly;loganomaly" ^
  --hidden-import flask ^
  --hidden-import sklearn.ensemble ^
  --hidden-import sklearn.neighbors ^
  --hidden-import sklearn.svm ^
  --hidden-import sklearn.preprocessing ^
  launcher.py

if errorlevel 1 (
  echo.
  echo EXE build failed. See messages above.
  exit /b 1
)

echo.
echo Done. Run:  dist\SentinelForge.exe
echo Browser opens automatically at http://127.0.0.1:8600
endlocal