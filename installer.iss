; Hallmark Record Installer Script for Inno Setup
; Requires Inno Setup 6.0 or later: https://jrsoftware.org/isinfo.php

#define MyAppName "Hallmark Record"
#define MyAppVersion "1.0.7"
#define MyAppPublisher "Hallmark University"
#define MyAppURL "https://github.com/agough77/hallmark-record"
#define MyAppExeName "Hallmark Recorder.exe"

[Setup]
AppId={{8F3B2C1D-9E4A-4B5C-8D7F-1A2B3C4D5E6F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=LICENSE
OutputDir=installer_output
OutputBaseFilename=HallmarkRecord_Setup_v{#MyAppVersion}
SetupIconFile=
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
Source: "dist\Hallmark Recorder\*"; DestDir: "{app}\Recorder"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme
Source: "config_template.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "unattended_installer.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "config_manager.py"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Hallmark Recorder"; Filename: "{app}\Recorder\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Hallmark Recorder"; Filename: "{app}\Recorder\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\Hallmark Recorder"; Filename: "{app}\Recorder\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\Recorder\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Registry]
; Register custom URL protocol for launching Recorder from browser
Root: HKCU; Subkey: "Software\Classes\hallmark-recorder"; ValueType: string; ValueName: ""; ValueData: "URL:Hallmark Recorder Protocol"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\hallmark-recorder"; ValueType: string; ValueName: "URL Protocol"; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\hallmark-recorder\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\Recorder\{#MyAppExeName},0"
Root: HKCU; Subkey: "Software\Classes\hallmark-recorder\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Recorder\{#MyAppExeName}"""

[Code]
var
  ConfigFilePage: TInputFileWizardPage;
  OutputFolderPage: TInputDirWizardPage;

procedure InitializeWizard;
begin
  // Page for optional unattended config file
  ConfigFilePage := CreateInputFilePage(wpSelectDir,
    'Unattended Configuration (Optional)', 
    'Do you have a pre-configured settings file?',
    'If your organization provided a configuration file, select it here. Otherwise, leave blank for default settings.');
  ConfigFilePage.Add('Configuration file (unattended_config.json):', 'JSON Files|*.json|All Files|*.*', '.json');
  ConfigFilePage.Values[0] := '';
  
  // Page for output folder selection
  OutputFolderPage := CreateInputDirPage(wpSelectDir,
    'Select Recording Output Folder',
    'Where should recordings be saved?',
    'Select the folder where your recordings will be saved by default. You can change this later in the application.',
    False, '');
  OutputFolderPage.Add('');
  OutputFolderPage.Values[0] := ExpandConstant('{userdesktop}\..\Downloads\Hallmark Record');
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  ConfigFile: String;
  OutputFolder: String;
  AppDataDir: String;
  UserConfigPath: String;
  ConfigContent: String;
begin
  Result := True;
  
  // When leaving the output folder page, save the configuration
  if CurPageID = OutputFolderPage.ID then
  begin
    OutputFolder := OutputFolderPage.Values[0];
    
    // Create output folder if it doesn't exist
    if not DirExists(OutputFolder) then
      CreateDir(OutputFolder);
    
    // Create AppData config directory
    AppDataDir := ExpandConstant('{userappdata}\Hallmark Record');
    if not DirExists(AppDataDir) then
      CreateDir(AppDataDir);
    
    UserConfigPath := AppDataDir + '\config.json';
    
    // Check if unattended config was provided
    ConfigFile := ConfigFilePage.Values[0];
    if (ConfigFile <> '') and FileExists(ConfigFile) then
    begin
      // Copy the provided config file
      FileCopy(ConfigFile, UserConfigPath, False);
      Log('Using provided configuration file: ' + ConfigFile);
    end
    else
    begin
      // Create default config with selected output folder
      ConfigContent := '{' + #13#10 +
        '  "version": "1.0",' + #13#10 +
        '  "installation": {' + #13#10 +
        '    "output_folder": "' + OutputFolder + '"' + #13#10 +
        '  },' + #13#10 +
        '  "recording": {' + #13#10 +
        '    "default_quality": "high",' + #13#10 +
        '    "auto_name_sessions": true' + #13#10 +
        '  },' + #13#10 +
        '  "export": {' + #13#10 +
        '    "default_quality": "medium",' + #13#10 +
        '    "auto_export_after_recording": false' + #13#10 +
        '  },' + #13#10 +
        '  "watermark": {' + #13#10 +
        '    "enabled": false,' + #13#10 +
        '    "image_path": "",' + #13#10 +
        '    "position": "top_right",' + #13#10 +
        '    "opacity": 0.7' + #13#10 +
        '  },' + #13#10 +
        '  "upload": {' + #13#10 +
        '    "enabled": false,' + #13#10 +
        '    "auto_upload_after_export": false,' + #13#10 +
        '    "destinations": []' + #13#10 +
        '  },' + #13#10 +
        '  "advanced": {' + #13#10 +
        '    "enable_logging": true,' + #13#10 +
        '    "check_for_updates": true' + #13#10 +
        '  }' + #13#10 +
        '}';
      
      SaveStringToFile(UserConfigPath, ConfigContent, False);
      Log('Created default configuration with output folder: ' + OutputFolder);
    end;
  end;
end;

function GetUninstallString(): String;
var
  sUnInstPath: String;
  sUnInstallString: String;
begin
  sUnInstPath := ExpandConstant('Software\Microsoft\Windows\CurrentVersion\Uninstall\{#emit SetupSetting("AppId")}_is1');
  sUnInstallString := '';
  if not RegQueryStringValue(HKLM, sUnInstPath, 'UninstallString', sUnInstallString) then
    RegQueryStringValue(HKCU, sUnInstPath, 'UninstallString', sUnInstallString);
  Result := sUnInstallString;
end;

function IsUpgrade(): Boolean;
begin
  Result := (GetUninstallString() <> '');
end;

function UnInstallOldVersion(): Integer;
var
  sUnInstallString: String;
  iResultCode: Integer;
begin
  Result := 0;
  sUnInstallString := GetUninstallString();
  if sUnInstallString <> '' then begin
    sUnInstallString := RemoveQuotes(sUnInstallString);
    if Exec(sUnInstallString, '/SILENT /NORESTART /SUPPRESSMSGBOXES','', SW_HIDE, ewWaitUntilTerminated, iResultCode) then
      Result := 3
    else
      Result := 2;
  end else
    Result := 1;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep=ssInstall) then
  begin
    if (IsUpgrade()) then
    begin
      UnInstallOldVersion();
    end;
  end;
end;
