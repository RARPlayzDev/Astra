# Self-Signing a PyInstaller EXE for Windows (Free, No Certificate Purchase)

> Honest summary: A self-signed certificate **will** eliminate SmartScreen on
> machines where you install the certificate as a trusted root CA (your team's
> laptops). It **will not** eliminate SmartScreen on stranger machines — only a
> publicly trusted certificate (DigiCert, Sectigo, etc.) does that. This guide
> covers everything you can do for free.

---

## Table of Contents

1. [Why SmartScreen Blocks Your EXE](#1-why-smartscreen-blocks-your-exe)
2. [Create a Self-Signed Code-Signing Certificate](#2-create-a-self-signed-code-signing-certificate)
3. [Sign Your EXE and Installer](#3-sign-your-exe-and-installer)
4. [Verify the Signature](#4-verify-the-signature)
5. [Trust the Certificate on Team Computers](#5-trust-the-certificate-on-team-computers)
6. [Honest Answer: Will SmartScreen Disappear on Other PCs?](#6-honest-answer-will-smartscreen-disappear-on-other-pcs)
7. [Package into a Professional Installer](#7-package-into-a-professional-installer)
8. [Reduce False Malware Warnings from PyInstaller](#8-reduce-false-malware-warnings-from-pyinstaller)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Why SmartScreen Blocks Your EXE

Microsoft Defender SmartScreen maintains a **reputation database**. An executable
is flagged when:

| Factor | Your EXE |
|--------|----------|
| **Publisher signature** | Unsigned → unknown publisher |
| **Download source** | Website/email → "untrusted origin" |
| **Usage history** | New file → zero reputation data |
| **Code characteristics** | PyInstaller stubs resemble some malware packers |

SmartScreen does **not** analyse your code. It checks: (a) is there a valid
signature from a known publisher? (b) has this file been seen before and rated
safe? Your EXE fails both checks.

A self-signed certificate answers (a) with "yes, signed — by an entity we can
verify locally." It does **not** answer (b) for machines that don't know your
certificate.

---

## 2. Create a Self-Signed Code-Signing Certificate

### Prerequisites
- Windows 10 or 11
- PowerShell (run as **Administrator**)
- Your PyInstaller `.exe` already built

### Step 2.1 — Open PowerShell as Administrator

Right-click the Start button → **Windows Terminal (Admin)** or **PowerShell (Admin)**.

### Step 2.2 — Create the Certificate

```powershell
# Creates a self-signed code-signing certificate valid for 5 years.
# Saved to your Personal certificate store AND exported as a .pfx file.

$cert = New-SelfSignedCertificate `
    -Type CodeSigningCert `
    -Subject "CN=ASTRA Project Team, O=ASTRA, C=IN" `
    -KeyAlgorithm RSA `
    -KeyLength 2048 `
    -KeyUsage DigitalSignature `
    -CertStoreLocation Cert:\CurrentUser\My `
    -NotAfter (Get-Date).AddYears(5) `
    -FriendlyName "ASTRA Code Signing"
```

**What this creates:**
- A certificate stored in your Windows certificate store (`Cert:\CurrentUser\My`)
- The certificate has a thumbprint — note it from the output (e.g. `A1B2C3...`)

**Save the thumbprint** — you'll need it in Step 2.3.

### Step 2.3 — Export to a `.pfx` File (for backup and sharing)

Replace `<THUMBPRINT>` with the actual thumbprint from Step 2.2:

```powershell
# Set a password for the .pfx file — remember it!
$pfxPassword = ConvertTo-SecureString -String "YourSecurePassword123!" -Force -AsPlainText

Export-PfxCertificate `
    -Cert "Cert:\CurrentUser\My\<THUMBPRINT>" `
    -FilePath "D:\Kaarthi\Dev Space\SIH2026\p1\tools\ASTRA-signing.pfx" `
    -Password $pfxPassword
```

**What this creates:**
- `tools\ASTRA-signing.pfx` — your signing certificate file (keep this secure!)

> **Security note:** The `.pfx` file is your signing identity. Do NOT commit it
> to git. Add `*.pfx` to your `.gitignore` immediately.

### Step 2.4 — Export the Public Certificate (for team trust distribution)

```powershell
Export-Certificate `
    -Cert "Cert:\CurrentUser\My\<THUMBPRINT>" `
    -FilePath "D:\Kaarthi\Dev Space\SIH2026\p1\tools\ASTRA-signing.cer"
```

**What this creates:**
- `tools\ASTRA-signing.cer` — the public certificate (safe to share / commit)

### Step 2.5 — Verify the Certificate Exists

```powershell
Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert | 
    Where-Object { $_.FriendlyName -eq "ASTRA Code Signing" } |
    Format-List Subject, Thumbprint, NotAfter, HasPrivateKey
```

Expected output:
```
Subject      : CN=ASTRA Project Team, O=ASTRA, C=IN
Thumbprint   : A1B2C3D4E5F6...
NotAfter     : 8/29/2031 12:00:00 AM
HasPrivateKey: True
```

---

## 3. Sign Your EXE and Installer

### Prerequisites
- `signtool.exe` — ships with the **Windows SDK**. If not found, install the
  Windows SDK from: https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/
  
  Or, if you installed Visual Studio or Windows Terminal build tools, it's
  already at a path like:
  ```
  C:\Program Files (x86)\Windows Kits\10\bin\<version>\x64\signtool.exe
  ```

**Finding signtool:**
```powershell
# Search for it:
Get-ChildItem "C:\Program Files*" -Recurse -Filter "signtool.exe" -ErrorAction SilentlyContinue |
    Select-Object -First 3 FullName
```

### Step 3.1 — Sign the PyInstaller EXE

```powershell
# Navigate to where signtool is (adjust path to match your installation)
$signtool = "C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe"

# Your .pfx password
$pfxPassword = "YourSecurePassword123!"

# Sign the EXE
& $signtool sign `
    /f "D:\Kaarthi\Dev Space\SIH2026\p1\tools\ASTRA-signing.pfx" `
    /p $pfxPassword `
    /tr http://timestamp.digicert.com `
    /td sha256 `
    /fd sha256 `
    /d "ASTRA - Adaptive Spectrum Threat Recognition & Analysis" `
    "D:\Kaarthi\Dev Space\SIH2026\p1\dist\ASTRA\ASTRA.exe"
```

**What each flag means:**
| Flag | Purpose |
|------|---------|
| `/f` | Path to the `.pfx` certificate file |
| `/p` | Password for the `.pfx` |
| `/tr` | Timestamp server (proves *when* you signed it) |
| `/td` | Timestamp digest algorithm (SHA-256) |
| `/fd` | File digest algorithm (SHA-256) |
| `/d` | Description embedded in the signature |

> If `timestamp.digicert.com` fails, try `http://timestamp.sectigo.com` or
> `http://timestamp.comodoca.com`.

### Step 3.2 — Sign the Inno Setup Installer (if applicable)

```powershell
# Sign the installer AFTER it's built
& $signtool sign `
    /f "D:\Kaarthi\Dev Space\SIH2026\p1\tools\ASTRA-signing.pfx" `
    /p $pfxPassword `
    /tr http://timestamp.digicert.com `
    /td sha256 `
    /fd sha256 `
    /d "ASTRA Installer v2.0.0" `
    "D:\Kaarthi\Dev Space\SIH2026\p1\installer\ASTRA-Setup-2.0.0.exe"
```

### Step 3.3 — Sign the QT Desktop EXE (if you use desktop_qt.py)

```powershell
& $signtool sign `
    /f "D:\Kaarthi\Dev Space\SIH2026\p1\tools\ASTRA-signing.pfx" `
    /p $pfxPassword `
    /tr http://timestamp.digicert.com `
    /td sha256 `
    /fd sha256 `
    /d "ASTRA Desktop (Qt)" `
    "D:\Kaarthi\Dev Space\SIH2026\p1\dist\ASTRA-Qt\ASTRA.exe"
```

### Step 3.4 — Automate Signing in Your Build Script

Add signing to `tools/build_exe.ps1`:

```powershell
# ... existing build code ...

# After successful build, sign the EXE
$signTool = Get-ChildItem "C:\Program Files*" -Recurse -Filter "signtool.exe" -ErrorAction SilentlyContinue |
    Select-Object -First 1 -ExpandProperty FullName

if ($signTool) {
    $pfxPath = Join-Path $PSScriptRoot "ASTRA-signing.pfx"
    if (Test-Path $pfxPath) {
        Write-Host "[ .. ] signing executable"
        $env:AstraPfxPassword = Read-Host "Enter signing password" -AsSecureString
        # For automation, store password in environment variable instead
        & $signTool sign /f $pfxPath /p $env:ASTRA_SIGN_PASSWORD `
            /tr http://timestamp.digicert.com /td sha256 /fd sha256 `
            /d "ASTRA" (Resolve-Path 'dist\ASTRA\ASTRA.exe')
        Write-Host "[ OK ] signed"
    } else {
        Write-Host "[SKIP] no signing certificate found at $pfxPath"
    }
}
```

For CI/automation, set `ASTRA_SIGN_PASSWORD` as an environment variable (never
commit passwords to source control).

---

## 4. Verify the Signature

### Step 4.1 — Verify with signtool

```powershell
& $signtool verify /pa /v "D:\Kaarthi\Dev Space\SIH2026\p1\dist\ASTRA\ASTRA.exe"
```

Expected output (success):
```
Successfully verified: dist\ASTRA\ASTRA.exe
```

### Step 4.2 — Verify with PowerShell

```powershell
Get-AuthenticodeSignature "D:\Kaarthi\Dev Space\SIH2026\p1\dist\ASTRA\ASTRA.exe" |
    Format-List *
```

Expected output:
```
SignerCertificate : [Subject]
                       CN=ASTRA Project Team, O=ASTRA, C=IN

                   [Issuer]
                       CN=ASTRA Project Team, O=ASTRA, C=IN

                   [Serial Number]
                       ...

                   [Not Before]
                       8/29/2026 12:00:00 AM

                   [Not After]
                       8/29/2031 12:00:00 AM

                   [Thumbprint]
                       A1B2C3D4E5F6...

Status            : Valid
StatusMessage     : Signature verified.
Path              : D:\Kaarthi\Dev Space\SIH2026\p1\dist\ASTRA\ASTRA.exe
SignatureType      : Authenticode
IsSigned          : True
IsSignatureValid  : True
```

Key fields to check:
- **Status**: `Valid`
- **IsSigned**: `True`
- **IsSignatureValid**: `True`

### Step 4.3 — Quick Visual Check (File Properties)

1. Right-click `ASTRA.exe` → **Properties**
2. You should now see a **"Digital Signatures"** tab (it was absent before signing)
3. Click it → select the signature → **Details** → **"This digital signature is OK."**

---

## 5. Trust the Certificate on Team Computers

This is the critical step. A self-signed certificate is only trusted on machines
that have explicitly been told to trust it.

### Step 5.1 — Export the Public Certificate (you did this in Step 2.4)

Make sure `tools\ASTRA-signing.cer` exists.

### Step 5.2 — On Each Team Computer

**Option A: Double-click method (simplest)**

1. Copy `ASTRA-signing.cer` to the team computer
2. Double-click the `.cer` file
3. Click **"Install Certificate..."**
4. Select **"Local Machine"** (requires admin) → Next
5. Select **"Place all certificates in the following store"** → Browse
6. Select **"Trusted Root Certification Authorities"** → OK → Next → Finish
7. Click **Yes** on the security warning → **OK**

**Option B: PowerShell method (repeatable)**

Run as Administrator on each team computer:

```powershell
# Import the public certificate as a trusted root CA
Import-Certificate `
    -FilePath "D:\path\to\ASTRA-signing.cer" `
    -CertStoreLocation Cert:\LocalMachine\Root
```

**Option C: Group Policy (for multiple machines in a domain — overkill for SIH)**

```powershell
# Export to a .sst file for bulk import
certutil -generateSSTFromCAFile rootsst.sst ASTRA-signing.cer
# Then import on target machines
certutil -EnterpriseStore root rootsst.sst
```

### Step 5.3 — Verify It's Trusted

On the team computer:

```powershell
Get-ChildItem Cert:\LocalMachine\Root -CodeSigningCert |
    Where-Object { $_.Subject -like "*ASTRA*" } |
    Format-List Subject, Thumbprint, NotAfter
```

---

## 6. Honest Answer: Will SmartScreen Disappear on Other PCs?

**Short answer: No, not entirely.**

| Scenario | SmartScreen behavior |
|----------|---------------------|
| Your dev machine (cert trusted) | ✅ **No warning** — certificate is trusted |
| Team laptops (cert imported as trusted root) | ✅ **No warning** — same reason |
| A judge's laptop / stranger's PC | ❌ **Still shows SmartScreen** — they don't have your cert |
| A judge's laptop after clicking "Run anyway" once | ⚠️ **Future runs may be allowed** — SmartScreen builds per-user reputation |

**Why:** SmartScreen's reputation is per-user and per-certificate. Your
self-signed cert is unknown to Microsoft's global reputation database. Only
certificates from publicly trusted CAs (DigiCert, Sectigo, GlobalSign, etc.)
bypass SmartScreen universally.

### What You Can Do for Judges/Demo Machines

1. **Before the demo:** Ask the judge to right-click → Properties → Unblock the
   downloaded file, then click "More info" → "Run anyway" once. After the first
   run, SmartScreen typically stops warning for that specific file.

2. **Distribute via USB instead of download:** Files copied from USB drives
   receive slightly more trust from SmartScreen than files downloaded from the
   internet.

3. **Walkthrough at demo time:** Be ready to click "More info" → "Run anyway".
   Every team at SIH faces this — judges understand it's a prototype.

4. **Include a `README-INSTALL.txt`:** Add instructions like:
   ```
   If Windows SmartScreen appears:
   1. Click "More info"
   2. Click "Run anyway"
   This is normal for prototype software without a commercial certificate.
   ```

---

## 7. Package into a Professional Installer

You already have an Inno Setup installer at `installer/astra_installer.iss`.
Here's how to build and sign it:

### Step 7.1 — Build the Installer

```powershell
# First, build the PyInstaller EXE
powershell -File tools\build_exe.ps1

# Then, build the Inno Setup installer
& "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" installer\astra_installer.iss
```

Output: `installer\ASTRA-Setup-2.0.0.exe`

### Step 7.2 — Sign the Installer

```powershell
& $signtool sign `
    /f "tools\ASTRA-signing.pfx" `
    /p "YourSecurePassword123!" `
    /tr http://timestamp.digicert.com `
    /td sha256 `
    /fd sha256 `
    /d "ASTRA Setup v2.0.0" `
    "installer\ASTRA-Setup-2.0.0.exe"
```

### Step 7.3 — Verify

```powershell
Get-AuthenticodeSignature "installer\ASTRA-Setup-2.0.0.exe" | Format-List Status
# Should show: Status : Valid
```

### Why Inno Setup Is Better Than Raw PyInstaller for Distribution

| Aspect | Raw PyInstaller folder | Inno Setup installer |
|--------|----------------------|---------------------|
| User experience | Copy entire folder | Double-click → wizard → Start Menu shortcut |
| Uninstall | Manual folder delete | Proper Add/Remove Programs entry |
| Desktop icon | Manual | Optional during install |
| File association | Not possible | Possible |
| Size | Same | Same (compressed) |
| Signing | Sign EXE only | Sign the single installer EXE (one file to trust) |

---

## 8. Reduce False Malware Warnings from PyInstaller

PyInstaller executables are flagged more often than average because their
internal structure resembles certain malware packers. Here's how to minimize
false positives:

### 8.1 — Use Folder Mode, Not Onefile

Your `astra.spec` already uses `COLLECT` (folder mode) — **good**. Onefile mode
extracts to a temp directory at runtime, which is exactly what some malware
does. Folder mode is less suspicious.

```python
# astra.spec — already correct (folder mode)
coll = COLLECT(exe, a.binaries, a.datas, ...)
```

### 8.2 — Add a Version Resource

Create `tools\version_info.txt`:

```powershell
# UTF-8 encoded version resource file
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(2, 0, 0, 0),
    prodvers=(2, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          u'040904B0',
          [
            StringStruct(u'CompanyName', u'ASTRA Project Team'),
            StringStruct(u'FileDescription', u'ASTRA - Adaptive Spectrum Threat Recognition & Analysis'),
            StringStruct(u'FileVersion', u'2.0.0.0'),
            StringStruct(u'InternalName', u'ASTRA'),
            StringStruct(u'OriginalFilename', u'ASTRA.exe'),
            StringStruct(u'ProductName', u'ASTRA'),
            StringStruct(u'ProductVersion', u'2.0.0.0'),
            StringStruct(u'LegalCopyright', u'© 2026 ASTRA Project Team'),
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
```

Reference it in `astra.spec`:

```python
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ASTRA",
    icon="assets/astra.ico",
    version="tools/version_info.txt",   # ← ADD THIS LINE
    debug=False,
    ...
)
```

**Effect:** Right-clicking the EXE → Properties → Details now shows company
name, file version, description. This looks professional and helps reputation
engines.

### 8.3 — Use UPX Compression Carefully

UPX can cause false positives because malware also uses UPX. Your spec already
has `upx=False` — **keep it that way**.

### 8.4 — Avoid Bundling Unnecessary Dependencies

The spec already excludes heavy packages (torch, tensorflow, etc.) — good.
Smaller EXEs with fewer bundled DLLs produce fewer false positives.

### 8.5 — Submit to Microsoft for Analysis

If SmartScreen still flags your signed EXE, submit it for manual review:

1. Go to: https://www.microsoft.com/en-us/wdsi/filesubmission
2. Fill in the form:
   - **File type:** select the EXE
   - **Category:** False positive / Detection
   - **Your email:** your email
3. Upload the signed EXE
4. Microsoft typically reviews within 24-48 hours and whitelists the file

This is **free** and the most effective long-term fix for distribution.

### 8.6 — Use a Professional Installer

SmartScreen treats standalone EXEs more suspiciously than installers from known
tools like Inno Setup. The Inno Setup installer you already have is the right
approach — sign it as shown in Section 7.

---

## 9. Troubleshooting

### "signtool.exe is not recognized"

```powershell
# Find it:
Get-ChildItem "C:\Program Files*" -Recurse -Filter "signtool.exe" `
    -ErrorAction SilentlyContinue | Select FullName

# If not found, install Windows SDK:
winget install Microsoft.WindowsSDK.10.0.22621
```

### "The specified password is not correct"

- Make sure the password matches what you set in `Export-PfxCertificate`
- Try wrapping in quotes: `/p "password"`
- Verify the PFX has a private key:

```powershell
Get-PfxData -FilePath "tools\ASTRA-signing.pfx" -Password (ConvertTo-SecureString "pass" -AsPlainText -Force)
```

### "No certificates were found that can be used to sign this content"

- The PFX file may not contain the private key
- Re-export from the certificate store:

```powershell
$cert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert |
    Where-Object { $_.Subject -like "*ASTRA*" }
Export-PfxCertificate -Cert $cert -FilePath "tools\ASTRA-signing.pfx" -Password $pwd
```

### "A certificate chain could not be built to a trusted root authority"

This is **expected** for self-signed certificates on machines that haven't
imported the `.cer` file. Follow Section 5.

### SmartScreen still appears after signing

This is normal on machines that don't trust your certificate (see Section 6).
To resolve:
1. Import the `.cer` as trusted root (Section 5), OR
2. Click "More info" → "Run anyway", OR
3. Submit to Microsoft for analysis (Section 8.5)

### "Digital Signatures" tab is missing from EXE properties

The EXE was not signed correctly. Verify with:

```powershell
Get-AuthenticodeSignature "dist\ASTRA\ASTRA.exe" | Format-List Status
```

If `Status` is `NotSigned`, re-run the signing command from Section 3.

---

## Quick Reference — Complete Command Sequence

```powershell
# 1. Create certificate
$cert = New-SelfSignedCertificate -Type CodeSigningCert `
    -Subject "CN=ASTRA Project Team, O=ASTRA, C=IN" `
    -KeyAlgorithm RSA -KeyLength 2048 -KeyUsage DigitalSignature `
    -CertStoreLocation Cert:\CurrentUser\My `
    -NotAfter (Get-Date).AddYears(5) `
    -FriendlyName "ASTRA Code Signing"

# 2. Export PFX (set your password)
$pfxPwd = ConvertTo-SecureString "MyPassword123!" -Force -AsPlainText
Export-PfxCertificate -Cert "Cert:\CurrentUser\My\$($cert.Thumbprint)" `
    -FilePath "tools\ASTRA-signing.pfx" -Password $pfxPwd

# 3. Export public CER (for team trust)
Export-Certificate -Cert "Cert:\CurrentUser\My\$($cert.Thumbprint)" `
    -FilePath "tools\ASTRA-signing.cer"

# 4. Sign the EXE (adjust signtool path)
$signtool = (Get-ChildItem "C:\Program Files*" -Recurse -Filter "signtool.exe" |
    Select-Object -First 1).FullName
& $signtool sign /f "tools\ASTRA-signing.pfx" /p "MyPassword123!" `
    /tr http://timestamp.digicert.com /td sha256 /fd sha256 `
    /d "ASTRA" "dist\ASTRA\ASTRA.exe"

# 5. Verify
Get-AuthenticodeSignature "dist\ASTRA\ASTRA.exe" | Format-List Status

# 6. On team computers: import the .cer as Trusted Root CA
Import-Certificate -FilePath "tools\ASTRA-signing.cer" `
    -CertStoreLocation Cert:\LocalMachine\Root
```

---

*Guide written for ASTRA — SIH 2026. All tools used are free and ship with Windows.*
