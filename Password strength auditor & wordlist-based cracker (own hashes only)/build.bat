# VaultGuard build script
python tools/make_icon.py
if %errorlevel% neq 0 exit /b %errorlevel%
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name VaultGuard ^
  --icon app.ico ^
  --collect-all customtkinter ^
  --collect-all darkdetect ^
  --version-file version_info.txt ^
  main.py
echo.
echo Build finished. EXE located in the "dist" folder.
pause