@echo off
rem ============================================================
rem  NetPulse build script
rem  Creates a venv, installs deps, builds dist\NetPulse.exe
rem ============================================================
setlocal
cd /d "%~dp0"

echo [1/4] Creating virtual environment...
if not exist .venv (
    python -m venv .venv || goto :error
)

echo [2/4] Activating venv and installing requirements...
call .venv\Scripts\activate.bat || goto :error
python -m pip install --upgrade pip || goto :error
pip install -r requirements.txt || goto :error

echo [3/4] Generating assets (icon.ico, logo.png)...
python scripts\generate_assets.py || goto :error

echo [4/4] Running PyInstaller...
pyinstaller --clean --noconfirm build.spec || goto :error

echo.
echo Build OK: dist\NetPulse.exe
goto :eof

:error
echo.
echo BUILD FAILED (exit code %errorlevel%)
exit /b %errorlevel%
