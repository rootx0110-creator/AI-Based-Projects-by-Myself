@echo off
REM Build the Red Team Engagement Report Generator as a single exe (no console).
setlocal
cd /d "%~dp0"

python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --name "RedTeamReportGenerator" ^
  main.py

echo.
echo Done. Binary: dist\RedTeamReportGenerator.exe
endlocal