# Builds VPN Tunnel Builder.exe as a standalone Windows executable.
$ErrorActionPreference = "Stop"

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

Write-Host "== Building VPN Tunnel Builder (PyInstaller) =="

python -m PyInstaller `
    --noconfirm `
    --onefile `
    --windowed `
    --clean `
    --name "VPN Tunnel Builder" `
    main.py

if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }

$exe = Join-Path $here "dist\VPN Tunnel Builder.exe"
if (Test-Path $exe) {
    Write-Host ""
    Write-Host "SUCCESS: $exe"
    Write-Host ("SIZE   : {0:N0} KB" -f ((Get-Item $exe).Length / 1KB))
} else {
    throw "Build completed but the exe was not found."
}