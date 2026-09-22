# Builds RulePackStudio.exe (single-file GUI) via PyInstaller.
# Usage: powershell -ExecutionPolicy Bypass -File build_exe.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host "== RulePackStudio EXE build ==" -ForegroundColor Cyan

# --- 0. dependencies -------------------------------------------------------
pip install -r requirements.txt

# --- 0b. options -----------------------------------------------------------
$name       = "RulePackStudio"
$entry      = "app/main.py"
$workpath   = "build/_pyi"
$distpath   = "dist"

if (Test-Path $workpath) { Remove-Item -Recurse -Force $workpath }
if (Test-Path $distpath) { Remove-Item -Recurse -Force $distpath }

# --- 1. pyinstaller ---------------------------------------------------------
$args = @(
  "--noconfirm",
  "--name",      $name,
  "--onefile",
  "--windowed",
  "--clean",
  "--workpath",  $workpath,
  "--distpath",  $distpath,
  "--collect-data", "customtkinter"
)

Write-Host "Running PyInstaller..." -ForegroundColor Cyan
python -m PyInstaller @args $entry
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

$exe = Join-Path $distpath "$name.exe"
if (-not (Test-Path $exe)) { throw "Build output missing: $exe" }

Write-Host ""
Write-Host "Build complete: $exe" -ForegroundColor Green
Write-Host "Test run: $exe --cli" -ForegroundColor Yellow