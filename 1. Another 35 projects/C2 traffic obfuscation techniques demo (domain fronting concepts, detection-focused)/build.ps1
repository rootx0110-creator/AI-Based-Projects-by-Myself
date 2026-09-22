# Build the standalone Windows EXE with PyInstaller
# Output: dist\C2TrafficObfuscationLab.exe
# Uses the system Python if PyInstaller is available; otherwise creates a venv.

$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
Set-Location -LiteralPath $here

$py = "python"
& $py -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller missing - creating isolated venv..."
    python -m venv .venv
    $py = Join-Path $here ".venv\Scripts\python.exe"
    & $py -m pip install --upgrade pyinstaller cryptography
}

& $py -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name "C2TrafficObfuscationLab" `
    --specpath "build" `
    --distpath "dist" `
    --workpath "build\pycache" `
    launcher.py

Write-Host ""
Write-Host "Build complete:"
Write-Host "  $here\dist\C2TrafficObfuscationLab.exe"