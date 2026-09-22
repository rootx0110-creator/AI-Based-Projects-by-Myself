# build_exe.ps1
# One-command PyInstaller build for MSF Lab Module Studio.
#   powershell -ExecutionPolicy Bypass -File build_exe.ps1
# Output: dist\MSF-Lab-Module-Studio.exe  (single-file, windowed GUI)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $root

Write-Host "[1/4] Verifying python + pyinstaller..."
python --version
python -m pip install --upgrade pyinstaller

Write-Host "[2/4] Cleaning old build artifacts..."
if (Test-Path ".\build") { Remove-Item -Recurse -Force ".\build" }
if (Test-Path ".\dist")  { Remove-Item -Recurse -Force ".\dist" }

Write-Host "[3/4] Freezing application -> onefile windowed exe..."
python -m PyInstaller `
  --onefile `
  --windowed `
  --name "MSF-Lab-Module-Studio" `
  --clean `
  --noconfirm `
  app.py

Write-Host "[4/4] Done."
$exe = Join-Path $root "dist\MSF-Lab-Module-Studio.exe"
if (Test-Path $exe) {
    $size = [math]::Round((Get-Item $exe).Length / 1MB, 1)
    Write-Host ("Built OK: {0}  ({1} MB)" -f $exe, $size)
} else {
    Write-Error "Build produced no exe."
    exit 1
}