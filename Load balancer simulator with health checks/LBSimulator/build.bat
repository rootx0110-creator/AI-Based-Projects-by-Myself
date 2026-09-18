@echo off
REM LBSimulator Build Script
REM Creates a standalone .exe with PyInstaller

setlocal enabledelayedexpansion

echo ============================================
echo  LBSimulator Build Script
echo ============================================
echo.

REM 1. Create virtual environment
if not exist "venv" (
    echo [1/4] Creating virtual environment...
    python -m venv venv
) else (
    echo [1/4] Virtual environment already exists.
)

REM 2. Activate and install dependencies
echo [2/4] Installing dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt -q

REM 3. Ensure icon exists
if not exist "assets\icon.ico" (
    echo [3/4] WARNING: assets\icon.ico not found. Using default icon.
) else (
    echo [3/4] Icon found: assets\icon.ico
)

REM 4. Run PyInstaller
echo [4/4] Building with PyInstaller...
echo.

pyinstaller build.spec

echo.
echo ============================================
echo  Build Complete!
echo ============================================
echo.
echo Output: dist\LBSimulator.exe
echo.

if exist "dist\LBSimulator.exe" (
    echo ✅ LBSimulator.exe created successfully.
    dir dist\LBSimulator.exe
) else (
    echo ❌ Build failed. Check the output above for errors.
)

pause
