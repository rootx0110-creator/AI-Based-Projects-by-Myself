@echo off
rem Build CustomProxyServer.exe with PyInstaller
python make_icon.py
pyinstaller CustomProxyServer.spec --clean --noconfirm
echo.
if exist dist\CustomProxyServer.exe (
    echo Build OK: dist\CustomProxyServer.exe
) else (
    echo Build FAILED - see warnings above.
)
