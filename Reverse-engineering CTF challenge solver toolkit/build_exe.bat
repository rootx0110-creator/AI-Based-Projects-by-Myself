@echo off
setlocal
chcp 65001 >nul
title RE Toolkit - build .exe

echo.
echo ============================================================
echo   Building RE_Toolkit.exe with PyInstaller
echo ============================================================
echo.

python -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [1/3] Installing pyinstaller ...
    python -m pip install pyinstaller
) else (
    echo [1/3] pyinstaller already installed.
)

echo [2/3] Checking customtkinter ...
python -m pip show customtkinter >nul 2>&1
if errorlevel 1 (
    echo       Installing customtkinter ...
    python -m pip install customtkinter
)

echo [3/3] Running PyInstaller ...
python -m PyInstaller --noconfirm --clean RE_Toolkit.spec
if errorlevel 1 (
    echo.
    echo BUILD FAILED.
    exit /b 1
)

echo.
echo Done. Your executable is at:
echo     dist\RE_Toolkit.exe
echo.
pause