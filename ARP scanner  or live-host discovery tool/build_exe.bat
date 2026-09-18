@echo off
REM Build standalone executables with PyInstaller.
REM Requires: python with PyInstaller installed (pip install pyinstaller).
REM
REM   dist\arpscan.exe     GUI app (double-click this one)
REM   dist\arpscan-cli.exe console CLI (for terminals / scripting)

echo === Building GUI app (dist\arpscan.exe) ===
python -m PyInstaller arpscan.spec --noconfirm --clean
if errorlevel 1 (
    echo GUI build failed.
    exit /b 1
)

echo.
echo === Building console CLI (dist\arpscan-cli.exe) ===
python -m PyInstaller arpscan_cli.spec --noconfirm
if errorlevel 1 (
    echo CLI build failed.
    exit /b 1
)

echo.
echo Done. Double-click dist\arpscan.exe to run the app.