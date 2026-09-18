@echo off
rem ---------------------------------------------------------------
rem  build_exe.bat — build dist\PacketSniffer.exe with PyInstaller
rem  Run from an x64 Native Tools / regular cmd in the project root.
rem ---------------------------------------------------------------
setlocal
cd /d "%~dp0"

where pyinstaller >nul 2>nul
if errorlevel 1 (
    echo [build] Installing PyInstaller...
    python -m pip install pyinstaller
)

echo [build] Cleaning previous build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [build] Building PacketSniffer.exe ...
python -m PyInstaller ^
    --name PacketSniffer ^
    --onedir ^
    --windowed ^
    --clean ^
    --noconfirm ^
    main.py

if errorlevel 1 (
    echo [build] FAILED
    exit /b 1
)

echo.
echo [build] Done: dist\PacketSniffer.exe
echo [build] Right-click the exe and choose "Run as administrator".
endlocal
