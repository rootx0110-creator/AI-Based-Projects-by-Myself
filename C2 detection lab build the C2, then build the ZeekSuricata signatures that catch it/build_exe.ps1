# C2 Detection Lab - Windows executable build script
# Usage:  powershell -ExecutionPolicy Bypass -File build_exe.ps1

$ErrorActionPreference = "Stop"

Write-Host "== C2 Detection Lab build ==" -ForegroundColor Cyan

# 1. Regenerate docs/*.md from the single source of truth (c2lab/docs.py)
Write-Host "[1/4] Regenerating documentation..."; python -m c2lab.docs

# 2. Generate the icon asset
Write-Host "[2/4] Generating icon..."; python tools\make_icon.py

# 3. Clean previous build artifacts
Write-Host "[3/4] Cleaning previous build...";
if (Test-Path -LiteralPath "build") { Remove-Item -Recurse -Force -LiteralPath "build" }
if (Test-Path -LiteralPath "dist") { Remove-Item -Recurse -Force -LiteralPath "dist" }

# 4. PyInstaller one-file, windowed build
Write-Host "[4/4] Running PyInstaller..."
python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --onefile `
    --name "C2DetectionLab" `
    --icon "assets\c2lab.ico" `
    main.py

if ($?) {
    Write-Host "`nBuild complete." -ForegroundColor Green
    Write-Host "Executable: $PWD\dist\C2DetectionLab.exe" -ForegroundColor Yellow
} else {
    Write-Host "`nBuild FAILED - inspect the PyInstaller warnings above." -ForegroundColor Red
    exit 1
}