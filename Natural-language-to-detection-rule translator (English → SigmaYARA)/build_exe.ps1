# =============================================================================
#  NL2Rule Translator — package as a standalone Windows EXE
#
#  Usage:
#     .\build_exe.ps1
#
#  Produces: dist\NL2Rule-Translator.exe
#  That EXE boots its own embedded Flask server on 127.0.0.1:5001 and opens
#  the default browser automatically. Fully self-contained.
# =============================================================================
$ErrorActionPreference = "Stop"

Write-Host "== NL2Rule Translator EXE builder ==" -ForegroundColor Cyan

# 1. dependencies
python -m pip install --quiet flask pyinstaller
if (-not $?) { throw "Failed to install dependencies" }

# 2. clean previous build
$dist = Join-Path $PSScriptRoot "dist"
$build = Join-Path $PSScriptRoot "build"
if (Test-Path $dist) { Remove-Item $dist -Recurse -Force }
if (Test-Path $build) { Remove-Item $build -Recurse -Force }

# 3. bundle everything the app needs (engine, templates, static, examples)
python -m PyInstaller `
  --onefile `
  --name "NL2Rule-Translator" `
  --console `
  --add-data (Join-Path $PSScriptRoot "templates;templates") `
  --add-data (Join-Path $PSScriptRoot "static;static") `
  --exclude-module "tkinter" `
  --exclude-module "unittest" `
  --distpath $dist `
  --workpath $build `
  (Join-Path $PSScriptRoot "exe_entry.py")

if (-not $?) { throw "PyInstaller failed" }

Write-Host ""
Write-Host "Done -> $dist\NL2Rule-Translator.exe" -ForegroundColor Green
Write-Host "Run it; the translator opens in your browser."