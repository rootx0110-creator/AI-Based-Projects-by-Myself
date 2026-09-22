# Build the Threat Actor TTP Profiler into a single-file Windows EXE.
# Run from the project root:  powershell -ExecutionPolicy Bypass -File build_exe.ps1

$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

$Staging = Join-Path $ProjectRoot "_staging"
$Exe = Join-Path $ProjectRoot "dist\ThreatActorTTPProfiler.exe"

if (Test-Path $Staging) { Remove-Item -Recurse -Force $Staging }
if (Test-Path $Exe) { Remove-Item -Force $Exe }

Write-Host "[1/4] Collecting assets into staging directory..." -ForegroundColor Cyan
New-Item -ItemType Directory -Path (Join-Path $Staging "app") | Out-Null
Copy-Item -Recurse -Force (Join-Path $ProjectRoot "app\data") (Join-Path $Staging "app\data")
if (-not (Test-Path (Join-Path $Staging "app\data\attack_techniques.json"))) {
    throw "Asset staging failed: attack_techniques.json not copied"
}

Write-Host "[2/4] Running PyInstaller..."  -ForegroundColor Cyan
python -m PyInstaller `
  --noconfirm --clean `
  --onefile --windowed `
  --name "ThreatActorTTPProfiler" `
  --add-data "$Staging\app\data;app\data" `
  --hidden-import "pefile" `
  --hidden-import "PIL._tkinter_finder" `
  --hidden-import "customtkinter" `
  --hidden-import "tkinter.filedialog" `
  --hidden-import "tkinter.messagebox" `
  "launcher.py"
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $Exe)) {
    Write-Host "[FAILED] PyInstaller exited with code $LASTEXITCODE" -ForegroundColor Red
    exit 1
}

Write-Host "[3/4] Cleaning up staging directory..." -ForegroundColor Cyan
if (Test-Path $Staging) { Remove-Item -Recurse -Force $Staging }

Write-Host "[4/4] Build complete: $Exe ($([math]::Round((Get-Item $Exe).Length / 1MB, 1)) MB)" -ForegroundColor Green