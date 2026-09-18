@echo off
rem Build TimelineBuilder.exe (single file, no console)
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name TimelineBuilder --icon app.ico main.py
echo.
echo Build finished. Executable is in dist\TimelineBuilder.exe
pause