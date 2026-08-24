; LabToolbox Inno Setup 安装向导
; 用法: iscc installer.iss (GitHub Actions 中调用)
#ifndef MyAppVersion
  #define MyAppVersion "0.1.1"
#endif
#define MyAppName "LabToolbox"
#define MyAppExeName "LabToolbox.exe"
#define MyAppPublisher "DrFermion"

[Setup]
AppId={{8E3F1C2A-5B4D-4E6F-9A7B-2C3D4E5F6A7B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\LabToolbox
DefaultGroupName=LabToolbox
DisableProgramGroupPage=yes
OutputDir=installer
OutputBaseFilename=LabToolbox-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoVersion=0.1.0
VersionInfoProductName=LabToolbox

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\LabToolbox\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
