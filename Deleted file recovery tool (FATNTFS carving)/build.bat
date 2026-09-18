@echo off
setlocal
title Deleted File Recovery - Build
cd /d "%~dp0"

echo ============================================
echo  Deleted File Recovery Tool - EXE Builder
echo ============================================
echo.

where pyinstaller >nul 2>nul
if errorlevel 1 (
    echo [1/3] pyinstaller not found - installing...
    pip install pyinstaller
) else (
    echo [1/3] pyinstaller found
)

echo [2/3] Building executable (one-file windowed)...
pyinstaller --clean --noconfirm DeletedFileRecovery.spec

if errorlevel 1 (
    echo.
    echo BUILD FAILED - see error above.
    pause
    exit /b 1
)

echo [3/3] Build complete!
echo.
echo Output: %~dp0dist\DeletedFileRecovery.exe
echo.
echo TIP: right-click the EXE and select "Run as administrator"
echo      for full raw-disk recovery access.
echo.
pause
endlocal