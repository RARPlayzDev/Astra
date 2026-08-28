# trust_and_sign.ps1 — Run in PowerShell as Administrator
# Trusts the self-signed certificate and signs ASTRA.exe

$ErrorActionPreference = "Stop"
$thumbprint = "ACB348F4CD70DE41F1E548127C6049E00D14BB42"
$pfxPath = "D:\Kaarthi\Dev Space\SIH2026\p1\tools\TeamMCS-signing.pfx"
$pfxPassword = "7702361622"
$exePath = "D:\Kaarthi\Dev Space\SIH2026\p1\dist\ASTRA\ASTRA.exe"

# 1. Find the certificate
$cert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert | Where-Object { $_.Thumbprint -eq $thumbprint }
if (-not $cert) { Write-Host "ERROR: Certificate not found"; exit 1 }
Write-Host "[1/4] Certificate found: $($cert.Subject)"

# 2. Add to Trusted Root Certification Authorities
$rootStore = New-Object System.Security.Cryptography.X509Certificates.X509Store("Root", "CurrentUser")
$rootStore.Open("ReadWrite")
$rootStore.Add($cert)
$rootStore.Close()
Write-Host "[2/4] Added to Trusted Root store"

# 3. Add to Trusted Publishers
$pubStore = New-Object System.Security.Cryptography.X509Certificates.X509Store("TrustedPublisher", "CurrentUser")
$pubStore.Open("ReadWrite")
$pubStore.Add($cert)
$pubStore.Close()
Write-Host "[3/4] Added to Trusted Publishers store"

# 4. Sign the EXE
$sig = Set-AuthenticodeSignature -FilePath $exePath -Certificate $cert -TimestampServer "http://timestamp.digicert.com" -HashAlgorithm SHA256
Write-Host "[4/4] Sign status: $($sig.Status)"
Write-Host "       Message: $($sig.StatusMessage)"

if ($sig.Status -eq "Valid") {
    Write-Host ""
    Write-Host "SUCCESS! ASTRA.exe is signed and trusted."
} else {
    Write-Host ""
    Write-Host "WARNING: Signing completed but status is not Valid. Check above."
}
