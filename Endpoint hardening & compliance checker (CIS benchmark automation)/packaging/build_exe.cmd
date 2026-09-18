@echo off
rem Build HardeningChecker.exe with PyInstaller (run from project root)
cd /d "%~dp0.."
pyinstaller --clean packaging\hardening-checker.spec
echo.
echo Output: dist\HardeningChecker.exe
