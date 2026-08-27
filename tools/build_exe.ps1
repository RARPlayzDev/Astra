# Builds the ASTRA desktop executable.
# Usage:  powershell -File tools\build_exe.ps1
# Output: dist\ASTRA\ASTRA.exe  (folder distribution; ship the whole folder)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

python -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
  Write-Host "[.. ] installing PyInstaller"
  python -m pip install --quiet pyinstaller
}

Write-Host "[ .. ] verifying frontend bundle exists"
if (-not (Test-Path "frontend\dist\index.html")) {
  Write-Host "[FAIL] frontend not built. Run: cd frontend; npm install; npm run build"
  exit 1
}

Write-Host "[ .. ] running PyInstaller (2-5 minutes)"
python -m PyInstaller --noconfirm --clean astra.spec
if ($LASTEXITCODE -ne 0) { Write-Host "[FAIL] build error"; exit 1 }

Write-Host ""
Write-Host "[ OK ] built: $(Resolve-Path 'dist\ASTRA')\ASTRA.exe"
Write-Host "       ship the entire dist\ASTRA folder (contains the runtime)."
