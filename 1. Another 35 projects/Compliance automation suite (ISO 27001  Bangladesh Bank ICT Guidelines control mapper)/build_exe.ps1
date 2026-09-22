# ============================================================================
#  Compliance Automation Suite - EXE build script (PyInstaller)
#  Usage:  powershell -ExecutionPolicy Bypass -File build_exe.ps1
#  Output: dist\ComplianceSuite.exe  (single file)
# ============================================================================

$ErrorActionPreference = "Stop"
Write-Host "=== Compliance Automation Suite :: EXE build ===" -ForegroundColor Cyan

# --- 1. locate python -------------------------------------------------------
$py = "python"
try { $null = & $py --version } catch {
    Write-Error "Python not found on PATH. Install Python 3.10+ first."
}

# --- 2. ensure pyinstaller --------------------------------------------------
Write-Host "[1/3] Ensuring PyInstaller..." -ForegroundColor Yellow
& $py -m pip show pyinstaller *> $null
if ($LASTEXITCODE -ne 0) {
    & $py -m pip install --user pyinstaller
    if ($LASTEXITCODE -ne 0) { Write-Error "Could not install PyInstaller." }
}

# --- 3. clean previous builds ----------------------------------------------
Write-Host "[2/3] Cleaning previous build..." -ForegroundColor Yellow
if (Test-Path "build")      { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist")       { Remove-Item -Recurse -Force "dist" }
if (Test-Path "ComplianceSuite.spec") { Remove-Item -Force "ComplianceSuite.spec" }

# --- 4. build ---------------------------------------------------------------
Write-Host "[3/3] Building single-file EXE..." -ForegroundColor Yellow
& $py -m PyInstaller `
    --noconfirm `
    --onefile `
    --name ComplianceSuite `
    --add-data "app/web;app/web" `
    --hidden-import app.server `
    --hidden-import app.services `
    --hidden-import app.report `
    --hidden-import app.store `
    --hidden-import app.data `
    --hidden-import app.config `
    exe_start.py

if ($LASTEXITCODE -ne 0) { Write-Error "PyInstaller build failed." }

Write-Host ""
Write-Host "=== SUCCESS ===" -ForegroundColor Green
Write-Host "Executable: $(Join-Path (Get-Location) 'dist\ComplianceSuite.exe')"
Write-Host "Run it and open http://127.0.0.1:9999 (browser opens automatically)."
Write-Host "Assessment data is stored in %APPDATA%\ComplianceSuite."
