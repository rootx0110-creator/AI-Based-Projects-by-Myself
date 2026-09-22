# =============================================================================
#  SOAR-Lite — package as a standalone Windows EXE
#
#  Usage:
#     .\build_exe.ps1
#
#  Produces: dist\SOAR-Lite.exe
#  That EXE boots its own embedded Flask server on 127.0.0.1:5000 and opens
#  the default browser automatically. Fully self-contained (data writes to
#  ./data next to the EXE).
# =============================================================================
$ErrorActionPreference = "Stop"

Write-Host "== SOAR-Lite EXE builder ==" -ForegroundColor Cyan

# 1. dependencies
python -m pip install --quiet flask pyinstaller
if (-not $?) { throw "Failed to install dependencies" }

# 2. clean previous build
$dist = Join-Path $PSScriptRoot "dist"
if (Test-Path $dist) { Remove-Item $dist -Recurse -Force }

# 3. bundle
python -m PyInstaller `
  --onefile `
  --name "SOAR-Lite" `
  --console `
  --add-data (Join-Path $PSScriptRoot "templates;templates") `
  --add-data (Join-Path $PSScriptRoot "static;static") `
  --add-data (Join-Path $PSScriptRoot "playbooks;playbooks") `
  --exclude-module "tkinter" `
  --exclude-module "unittest" `
  --distpath $dist `
  (Join-Path $PSScriptRoot "exe_entry.py")

if (-not $?) { throw "PyInstaller failed" }

Write-Host ""
Write-Host "Done -> $dist\SOAR-Lite.exe" -ForegroundColor Green
Write-Host "Run it; the SOC dashboard opens in your browser."