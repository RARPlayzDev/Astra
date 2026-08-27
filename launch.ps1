param(
    [switch]$NoBrowser,
    [int]$Port = 8000,
    [switch]$Rebuild
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$Dist = Join-Path $Root "frontend\dist\index.html"

function Write-Banner {
    $c = @"
"@
    Clear-Host
    Write-Host ""
    Write-Host "   ____  _         _ ____  ___  ____  _____ _    " -ForegroundColor DarkCyan
    Write-Host "  / ___|| | ___ __| / ___|/ _ \/ ___||  ___| |   " -ForegroundColor Cyan
    Write-Host "  \___ \| |/ / '_ \ \___ \ (_) \___ \| |_  | |   " -ForegroundColor Cyan
    Write-Host "   ___) |   <| | | |___) \__, |___) |  _|_| |___ " -ForegroundColor Cyan
    Write-Host "  |____/|_|\_\_| |_|____/  /_/____/|_|(_)_|_____/" -ForegroundColor DarkCyan
    Write-Host ""
    Write-Host "   ASTRA - ADAPTIVE SPECTRUM THREAT RECOGNITION & ANALYSIS" -ForegroundColor Gray
    Write-Host "   Electronic Support scan scheduler - SIH 2026 prototype" -ForegroundColor DarkGray
    Write-Host ""
}

function Step {
    param([string]$Name, [scriptblock]$Action)
    Write-Host ("  [ .. ] {0}" -f $Name) -NoNewline -ForegroundColor Yellow
    try {
        & $Action | Out-Null
        Write-Host ("`r  [ OK ] {0}" -f $Name) -ForegroundColor Green
        return $true
    } catch {
        Write-Host ("`r  [FAIL] {0}" -f $Name) -ForegroundColor Red
        Write-Host ("         {0}" -f $_.Exception.Message) -ForegroundColor DarkRed
        return $false
    }
}

function Test-Cmd { param([string]$Name) [bool](Get-Command $Name -ErrorAction SilentlyContinue) }

function Build-Frontend {
    Push-Location (Join-Path $Root "frontend")
    if (-not (Test-Path "node_modules")) {
        Write-Host "  [ .. ] installing frontend dependencies" -NoNewline -ForegroundColor Yellow
        npm install --no-audit --no-fund 2>&1 | Out-Null
        Write-Host "`r  [ OK ] installing frontend dependencies" -ForegroundColor Green
    }
    Write-Host "  [ .. ] building React bundle" -NoNewline -ForegroundColor Yellow
    npm run build 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "npm run build failed" }
    Write-Host "`r  [ OK ] building React bundle" -ForegroundColor Green
    Pop-Location
}

function Wait-Healthy {
    param([int]$Seconds = 40)
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/api/live/status" -UseBasicParsing -TimeoutSec 2
            if ($r.StatusCode -eq 200) { return $true }
        } catch { Start-Sleep -Milliseconds 400 }
    }
    return $false
}

Write-Banner

$py = Test-Cmd "python"
if (-not (Step "checking toolchain (python $(if($py){(python --version 2>&1).ToString()}))" { if (-not $py) { throw "python not on PATH" } })) {
    Read-Host "  python is required. Press Enter to exit"; exit 1
}

$already = $false
try {
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop
    if ($conn) { $already = $true }
} catch {}

if ($already) {
    Write-Host "  [INFO] a service is already listening on port $Port" -ForegroundColor Yellow
    Write-Host "  [INFO] reusing it - opening the dashboard" -ForegroundColor Yellow
    if (-not $NoBrowser) { Start-Process "http://localhost:$Port" }
    Write-Host ""
    Read-Host "  Press Enter to exit"
    exit 0
}

$needsBuild = $Rebuild -or -not (Test-Path $Dist)
if ($needsBuild) {
    if (-not (Test-Cmd "npm")) {
        Write-Host "  [FAIL] npm not found and no prebuilt frontend exists" -ForegroundColor Red
        Read-Host "  Install Node.js 18+, then rerun. Press Enter to exit"; exit 1
    }
    if (-not (Step "building frontend (first run takes ~30s)" { Build-Frontend })) {
        Read-Host "  Press Enter to exit"; exit 1
    }
} else {
    Step "frontend bundle found" {}
}

$resultsJson = Join-Path $Root "results\suite_results.json"
if (Test-Path $resultsJson) {
    Step "benchmark results present" {}
} else {
    Write-Host "  [WARN] results/suite_results.json missing - Benchmarks page will be empty." -ForegroundColor DarkYellow
    Write-Host "         Generate with:  python -m ewsmart.experiments --suite full" -ForegroundColor DarkYellow
}

Write-Host ""
Write-Host "  +- LAUNCH -------------------------------------------------+" -ForegroundColor DarkCyan
Write-Host "  |  URL      http://localhost:$Port                        |" -ForegroundColor White
Write-Host "  |  API docs http://localhost:$Port/docs                  |" -ForegroundColor Gray
Write-Host "  |  stop     close this window or press Ctrl+C             |" -ForegroundColor Gray
Write-Host "  +-----------------------------------------------------------+" -ForegroundColor DarkCyan
Write-Host ""

$openJob = $null
if (-not $NoBrowser) {
    $openJob = Start-Job -ArgumentList $Port -ScriptBlock {
        param($p)
        $deadline = (Get-Date).AddSeconds(45)
        while ((Get-Date) -lt $deadline) {
            try {
                $r = Invoke-WebRequest -Uri "http://127.0.0.1:$p/api/live/status" -UseBasicParsing -TimeoutSec 2
                if ($r.StatusCode -eq 200) { Start-Process "http://localhost:$p"; break }
            } catch { Start-Sleep -Milliseconds 400 }
        }
    }
}

try {
    python -X utf8 -m uvicorn server.api:app --host 127.0.0.1 --port $Port
} finally {
    if ($openJob) { Remove-Job $openJob -Force -ErrorAction SilentlyContinue }
    Write-Host ""
    Write-Host "  [STOP] command centre shut down." -ForegroundColor DarkCyan
}

