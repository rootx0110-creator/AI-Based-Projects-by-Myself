@echo off
setlocal
REM ============================================================
REM  Build the Windows Event Log Intrusion Timeline Tool (.exe)
REM  Output: dist\IntrusionTimelineTool.exe
REM ============================================================
set PY=py -3
where py >nul 2>nul
if errorlevel 1 set PY=python

echo [1/3] Installing PyInstaller...
%PY% -m pip install --quiet --upgrade pyinstaller
if errorlevel 1 goto :err

echo [2/3] Building single-file executable...
%PY% -m PyInstaller --noconfirm --clean WECT.spec
if errorlevel 1 goto :err

echo [3/3] Done!
echo.
echo  Executable: dist\IntrusionTimelineTool.exe
goto :eof

:err
echo.
echo  BUILD FAILED. Scroll up for details.
exit /b 1