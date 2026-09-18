@echo off
setlocal
title ThreatIntel Feed Aggregator

if not exist data mkdir data
if not exist reports mkdir reports

echo.
echo  ============================================================
echo    ThreatIntel Feed Aggregator  -  IOC ingestion + blocklist
echo  ============================================================
echo.

python -m pip install -r requirements.txt
if errorlevel 1 goto :fail

python app.py
goto :end

:fail
echo.
echo  ERROR: failed to install dependencies. Run manually:
echo     python -m pip install -r requirements.txt
echo     python app.py
pause

:end
endlocal