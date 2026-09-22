# build_exe.ps1
# ---------------------------------------------------------------------------
# Builds a standalone Windows EXE for the PolicyForge web application.
#
#   .\build_exe.ps1            -> builds dist\PolicyForge.exe
#   .\build_exe.ps1 -Clean     -> removes previous build/dist first
# ---------------------------------------------------------------------------
param([switch]$Clean)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

Write-Host "== PolicyForge EXE builder ==" -ForegroundColor Cyan

# 1. Locate python
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { Write-Error "python not found on PATH. Install Python 3.10+ and retry." }
Write-Host "Using: $($py.Source)"

# 2. Ensure tooling
python -m pip install --quiet --disable-pip-version-check pywebview pyinstaller
if ($LASTEXITCODE -ne 0) { Write-Error "pip install failed." }

# 3. Clean previous artifacts (optional)
if ($Clean) {
    Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
}

# 4. Verify the core asset exists
if (-not (Test-Path "index.html")) { Write-Error "index.html not found in $here" }

# 5. Freeze
Write-Host "Running PyInstaller (one-file build)..." -ForegroundColor Cyan
python -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name PolicyForge `
    --add-data "index.html;." `
    run_app.py
if ($LASTEXITCODE -ne 0) { Write-Error "PyInstaller failed." }

# 6. Report
$exe = Join-Path $here "dist\PolicyForge.exe"
if (Test-Path $exe) {
    $size = [math]::Round((Get-Item $exe).Length / 1MB, 1)
    Write-Host ""
    Write-Host "SUCCESS: $exe ($size MB)" -ForegroundColor Green
    Write-Host "Copy the single .exe anywhere and run it - no install needed."
} else {
    Write-Error "Build completed but $exe was not produced."
}