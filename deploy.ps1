# ═══════════════════════════════════════════════════════════════════
#  ASTRA — republish the website to Vercel
#  Root vercel.json serves the pre-built website/dist, so: build, then deploy.
#  Usage:  powershell -ExecutionPolicy Bypass -File deploy.ps1
#  One-off first run:  npx vercel login   (then link the `astra-ew` project)
# ═══════════════════════════════════════════════════════════════════
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
  Write-Host '» building website' -ForegroundColor Cyan
  Push-Location website
  npm run build
  Pop-Location

  Write-Host '» deploying website/dist to Vercel production' -ForegroundColor Cyan
  npx --yes vercel deploy --prod --yes

  Write-Host '» smoke-checking the deployed host' -ForegroundColor Cyan
  foreach ($u in @('https://astra-ew.vercel.app/',
                   'https://astra-ew.vercel.app/results',
                   'https://astra-ew.vercel.app/console',
                   'https://astra-ew.vercel.app/documentation')) {
    $code = curl.exe -s -o NUL -w '%{http_code}' --max-time 25 $u
    Write-Host ("  {0} {1}" -f $code, $u)
  }
}
finally { Pop-Location }
