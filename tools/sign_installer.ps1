# sign_installer.ps1 — Signs the ASTRA installer
$ErrorActionPreference = "Stop"
$thumbprint = "ACB348F4CD70DE41F1E548127C6049E00D14BB42"
$installerPath = "D:\Kaarthi\Dev Space\SIH2026\p1\installer\ASTRA-Setup-2.0.0.exe"

$cert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert | Where-Object { $_.Thumbprint -eq $thumbprint }
if (-not $cert) { Write-Host "ERROR: Certificate not found"; exit 1 }

Write-Host "Signing installer: $installerPath"
$sig = Set-AuthenticodeSignature -FilePath $installerPath -Certificate $cert -TimestampServer "http://timestamp.digicert.com" -HashAlgorithm SHA256
Write-Host "Status: $($sig.Status)"
Write-Host "Message: $($sig.StatusMessage)"
