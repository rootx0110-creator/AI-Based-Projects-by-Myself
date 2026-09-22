# build_exe.ps1
# Build a standalone Windows EXE with PyInstaller (Flask app + embedded UI).
# Usage:  powershell -ExecutionPolicy Bypass -File build_exe.ps1
# Output: dist\XSS-Payload-Tester.exe

$ErrorActionPreference = "Stop"

Write-Host "== XSS Payload Tester - EXE build =="

python -m pip show pyinstaller 2>$null | Out-Null
if (-not $?) {
    Write-Host "Installing pyinstaller..."
    python -m pip install pyinstaller
}

python -m pip show flask requests 2>$null | Out-Null
if (-not $?) {
    Write-Host "Installing flask + requests..."
    python -m pip install flask requests
}

$here = $PSScriptRoot
$name = "XSS-Payload-Tester"
$icon = ""
if (Test-Path (Join-Path $here "assets\app.ico")) {
    $icon = "--icon=$(Join-Path $here 'assets\app.ico')"
}

python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --name $name `
    $icon `
    --add-data "$here\templates;templates" `
    --add-data "$here\static;static" `
    --hidden-import requests `
    --hidden-import flask `
    --exclude-module tkinter `
    "$here\app.py"

Write-Host ""
Write-Host "Built: $(Join-Path $here "dist\$name.exe")"
Write-Host "Run it and open http://127.0.0.1:5173 in a browser."