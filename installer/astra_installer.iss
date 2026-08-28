; ASTRA installer - Inno Setup 6
; Build order:
;   1) powershell -File tools\build_exe.ps1        -> dist\ASTRA\
;   2) & "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" installer\astra_installer.iss
; Output: installer\ASTRA-Setup-2.0.0.exe

#define MyAppName "ASTRA"
#define MyAppLong "Adaptive Spectrum Threat Recognition & Analysis"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "ASTRA Project Team"
#define MyAppURL "https://astra-ew.vercel.app"
#define MyAppExeName "ASTRA.exe"

[Setup]
AppId={{8F3D2A61-94C7-4E05-B8A1-3C5F7D9E21B4}
AppName={#MyAppName} - {#MyAppLong}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
SetupIconFile=..\assets\astra.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=.
OutputBaseFilename=ASTRA-Setup-{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequiredOverridesAllowed=dialog commandline
ChangesEnvironment=no

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; \
    GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\ASTRA\*"; DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{#MyAppName} User Guide"; Filename: "{app}\docs\ASTRA_Software_Documentation.md"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; \
    Flags: nowait postinstall skipifsilent unchecked
