# Build NEON//GRID CTF as a single Windows EXE.
# Usage:  powershell -ExecutionPolicy Bypass -File build_exe.ps1

$ErrorActionPreference = "Stop"

Write-Host "==> Ensuring dependencies..."
pip install -r requirements.txt pyinstaller | Out-Null

Write-Host "==> Cleaning previous build..."
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist")  { Remove-Item -Recurse -Force "dist" }

Write-Host "==> Running PyInstaller..."
python -m PyInstaller --noconfirm --onefile --name NeonGridCTF `
  --add-data "app/templates;app/templates" `
  --add-data "app/static;app/static" `
  --hidden-import simple_websocket `
  --hidden-import waitress `
  run.py

Write-Host ""
Write-Host "==> Done: dist\NeonGridCTF.exe"
Write-Host "    Double-click it; it serves http://127.0.0.1:5000 (data\ folder created next to the EXE)."
Write-Host "    Admin login: admin / admin123"
