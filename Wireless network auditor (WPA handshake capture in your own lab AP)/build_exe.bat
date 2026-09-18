@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo  Building Wireless Network Auditor executable (.exe)
echo ============================================================
echo.

python -m PyInstaller --onefile --windowed --clean --noconfirm ^
  --name WirelessNetworkAuditor ^
  --collect-all scapy ^
  --add-data "templates;templates" ^
  --add-data "static;static" ^
  app.py

echo.
echo ============================================================
if exist "dist\WirelessNetworkAuditor.exe" (
  echo  BUILD OK - dist\WirelessNetworkAuditor.exe
  echo  The exe opens the app in your browser and keeps running
  echo  in the background. Close it from Task Manager (or Ctrl+C
  echo  if you build the console variant) when done.
) else (
  echo  BUILD FAILED - see messages above.
)
echo ============================================================
pause