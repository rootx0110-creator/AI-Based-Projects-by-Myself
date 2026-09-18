$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot\..
$root = (Get-Location).Path

Write-Host "==> Installing/checking build deps"
python -m pip install --quiet pyinstaller customtkinter psutil

Write-Host "==> Cleaning previous build"
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue build
Remove-Item -Force -ErrorAction SilentlyContinue dist\HIDS_Agent.exe
Remove-Item -Force -ErrorAction SilentlyContinue HIDS_Agent.spec

Write-Host "==> Running PyInstaller (onefile, windowed)"
python -m PyInstaller `
    --noconfirm `
    --onefile `
    --windowed `
    --name HIDS_Agent `
    --icon "$root\assets\icon.ico" `
    --add-data "$root\assets\icon.png;assets" `
    --exclude-module pytest `
    --exclude-module pandas `
    --exclude-module numpy `
    "$root\main.py"

Write-Host "==> Build complete"
Get-Item -LiteralPath "$root\dist\HIDS_Agent.exe" | Select-Object Name, Length, LastWriteTime