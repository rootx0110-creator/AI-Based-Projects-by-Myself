@echo off
rem ============================================================
rem  Beacon Detection Lab - rebuild the Windows executables
rem  Requires: Python 3.9+ and pip (one-time pyinstaller download)
rem ============================================================
cd /d "%~dp0"

python -m pip install --upgrade pyinstaller || goto :err
python -m py_compile launcher.py dashboard.py analyzer.py || goto :err

pyinstaller --noconfirm --clean --onefile --windowed --name BeaconDetectionLab launcher.py || goto :err
pyinstaller --noconfirm --clean --onefile --name beacon-analyzer analyzer.py || goto :err

echo.
echo Build OK. Executables are in dist\
echo   BeaconDetectionLab.exe  - double-click: dashboard UI + browser
echo   beacon-analyzer.exe     - CLI: beacon-analyzer.exe access.log -o report.html
pause
exit /b 0

:err
echo.
echo Build FAILED.
pause
exit /b 1
