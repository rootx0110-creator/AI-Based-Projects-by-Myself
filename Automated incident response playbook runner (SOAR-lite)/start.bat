@echo off
setlocal
cd /d "%~dp0"
echo ============================================
echo   SOAR-Lite - Incident Response Playbook Runner
echo   Starting at http://127.0.0.1:8787
echo   Press Ctrl+C to stop the server.
echo ============================================
set SOAR_NO_OPEN=1
powershell -NoProfile -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:8787'"
node server.js
pause