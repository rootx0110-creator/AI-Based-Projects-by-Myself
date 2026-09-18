@echo off
REM ============================================================
REM  Launch Wireless Network Auditor in LIVE (real) mode.
REM  Requires Npcap (https://npcap.com) and a Wi-Fi adapter.
REM  ONLY use against your own lab access point.
REM ============================================================
setlocal
cd /d "%~dp0"

set AUDITOR_ENGINE=live
REM Leave blank to auto-detect the Wi-Fi adapter, or set a name:
REM   set AUDITOR_IFACE=Wi-Fi
set AUDITOR_IFACE=

if exist "dist\WirelessNetworkAuditor.exe" (
  start "" "dist\WirelessNetworkAuditor.exe"
) else (
  python app.py
)
endlocal
