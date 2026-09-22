# Build PhishGuard into a standalone Windows executable.
# Run from PowerShell:   .\build_exe.ps1
# Output: dist\PhishGuard.exe

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "[1/3] Verifying python and pyinstaller..." -ForegroundColor Cyan
python -c "import sys; assert sys.version_info >= (3,9)" 
python -m PyInstaller --version 2>$null | Out-Null
if (-not $?) {
    Write-Host "Installing pyinstaller..." -ForegroundColor Yellow
    python -m pip install pyinstaller
}

Write-Host "[2/3] Installing runtime deps..." -ForegroundColor Cyan
python -m pip install -r requirements.txt

Write-Host "[3/3] Building executable (this can take a minute)..." -ForegroundColor Cyan

python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name "PhishGuard" `
    --add-data "templates;templates" `
    --add-data "static;static" `
    --add-data "config.ini.example;." `
    app.py

if ($?) {
    $exe = Join-Path $PSScriptRoot "dist\PhishGuard.exe"
    if (Test-Path $exe) {
        Write-Host ""
        Write-Host "SUCCESS: $exe" -ForegroundColor Green
        Write-Host "Double-click PhishGuard.exe - it launches and opens your browser." -ForegroundColor Green
    }
}