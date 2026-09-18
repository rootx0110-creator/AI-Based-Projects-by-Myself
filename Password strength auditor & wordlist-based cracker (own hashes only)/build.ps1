# VaultGuard — one-file Windows executable build (PowerShell)
param()

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host "==> Generating app icon" -ForegroundColor Cyan
python tools/make_icon.py

Write-Host "==> Building EXE with PyInstaller" -ForegroundColor Cyan
python -m PyInstaller --noconfirm --clean --onefile --windowed `
  --name VaultGuard `
  --icon app.ico `
  --collect-all customtkinter `
  --collect-all darkdetect `
  --version-file version_info.txt `
  main.py

Write-Host ""
Write-Host "Build finished. EXE located at: dist\VaultGuard.exe" -ForegroundColor Green