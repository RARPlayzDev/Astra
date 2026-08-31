# Sign the installer with Team MCS certificate
$cert = Get-ChildItem Cert:\CurrentUser\My\ACB348F4CD70DE41F1E548127C6049E00D14BB42
$password = ConvertTo-SecureString "7702361622" -Force -AsPlainText

# Sign installer
$exePath = "D:\Kaarthi\Dev Space\SIH2026\p1\installer\ASTRA-Setup-2.0.0.exe"
Set-AuthenticodeSignature -FilePath $exePath -Certificate $cert -TimestampServer "http://timestamp.digicert.com" -HashAlgorithm SHA256
Write-Host "Signed installer: $exePath"

# Verify
Get-AuthenticodeSignature $exePath | Format-List Status, SignerCertificate, TimeStamperCertificate
