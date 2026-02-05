# Hallmark Record - Deployment Guide

## Overview

This guide explains how to deploy Hallmark Record across your organization using unattended installation with pre-configured settings.

## Quick Start

### 1. Create Configuration Template

Run the batch file to generate a configuration template:

```batch
CREATE_UNATTENDED_CONFIG.bat
```

This creates `unattended_config.json` with default values.

### 2. Customize Configuration

Edit `unattended_config.json` with your organization's settings:

```json
{
  "installation": {
    "silent": true,
    "install_path": "C:\\Program Files\\Hallmark Record",
    "output_folder": "D:\\HallmarkRecordings",
    "create_desktop_shortcut": true,
    "create_start_menu_shortcut": true
  },
  "watermark": {
    "enabled": true,
    "image_path": "\\\\fileserver\\logos\\company_logo.png",
    "position": "top_right",
    "opacity": 0.7
  },
  "upload": {
    "enabled": true,
    "auto_upload_after_export": true,
    "destinations": [
      {
        "name": "Company SharePoint",
        "type": "sharepoint",
        "url": "https://yourcompany.sharepoint.com/sites/videos",
        "enabled": true
      }
    ]
  }
}
```

### 3. Deploy

Deploy using one of these methods:

#### Silent Install
```batch
Setup.exe /SILENT /CONFIG=unattended_config.json
```
- Shows progress bar
- User can cancel
- Good for attended deployment

#### Very Silent Install
```batch
Setup.exe /VERYSILENT /CONFIG=unattended_config.json
```
- No UI at all
- Cannot be cancelled
- Perfect for SCCM, GPO, or remote deployment

## Configuration Options

### Installation Settings

| Setting | Type | Description | Default |
|---------|------|-------------|---------|
| `install_path` | String | Installation directory | `C:\Program Files\Hallmark Record` |
| `output_folder` | String | Where recordings are saved | `C:\HallmarkRecordings` |
| `create_desktop_shortcut` | Boolean | Create desktop shortcut | `true` |
| `create_start_menu_shortcut` | Boolean | Create start menu shortcut | `true` |
| `auto_start` | Boolean | Start with Windows | `false` |

### Recording Settings

| Setting | Type | Description | Default |
|---------|------|-------------|---------|
| `default_quality` | String | Recording quality (high/medium/low) | `high` |
| `auto_name_sessions` | Boolean | Auto-generate session names | `true` |
| `session_name_format` | String | Datetime format for sessions | `session_%Y%m%d_%H%M%S` |

### Export Settings

| Setting | Type | Description | Default |
|---------|------|-------------|---------|
| `default_quality` | String | Export quality (high/medium/low) | `medium` |
| `auto_export_after_recording` | Boolean | Auto-export when recording stops | `false` |
| `export_format` | String | Video format (mp4/avi/mov) | `mp4` |

### Watermark Settings

| Setting | Type | Description | Default |
|---------|------|-------------|---------|
| `enabled` | Boolean | Enable watermark | `false` |
| `image_path` | String | Path to watermark image | `""` |
| `position` | String | Position (top_left/top_right/bottom_left/bottom_right/center) | `top_right` |
| `opacity` | Number | Opacity (0.0-1.0) | `0.7` |

### Upload Settings

| Setting | Type | Description | Default |
|---------|------|-------------|---------|
| `enabled` | Boolean | Enable upload features | `false` |
| `auto_upload_after_export` | Boolean | Auto-upload after export | `false` |
| `destinations` | Array | Upload destinations (see below) | `[]` |

### Upload Destinations

#### SharePoint
```json
{
  "name": "Company SharePoint",
  "type": "sharepoint",
  "url": "https://company.sharepoint.com/sites/videos",
  "username": "user@company.com",
  "password_encrypted": "",
  "enabled": true
}
```

#### OneDrive
```json
{
  "name": "OneDrive",
  "type": "onedrive",
  "path": "Videos/Recordings",
  "enabled": true
}
```

#### Network Share
```json
{
  "name": "File Server",
  "type": "network_share",
  "unc_path": "\\\\fileserver\\videos",
  "username": "domain\\user",
  "password_encrypted": "",
  "enabled": true
}
```

#### FTP
```json
{
  "name": "FTP Server",
  "type": "ftp",
  "host": "ftp.company.com",
  "port": 21,
  "username": "ftpuser",
  "password_encrypted": "",
  "remote_path": "/videos",
  "enabled": true
}
```

## Deployment Methods

### 1. Group Policy (GPO)

1. Share your installer and config:
   ```
   \\domain\software\HallmarkRecord\Setup.exe
   \\domain\software\HallmarkRecord\unattended_config.json
   ```

2. Create GPO:
   - Computer Configuration → Policies → Software Settings → Software Installation
   - Add new package → Point to Setup.exe
   - Properties → Modifications → Add unattended_config.json

### 2. Microsoft SCCM/Intune

Create package with install command:
```batch
Setup.exe /VERYSILENT /NORESTART /CONFIG=unattended_config.json
```

Detection method: Check for file
```
C:\Program Files\Hallmark Record\Recorder\Hallmark Recorder.exe
```

### 3. PowerShell Remote Deployment

```powershell
$computers = Get-Content "computers.txt"
$installer = "\\fileserver\software\HallmarkRecord\Setup.exe"
$config = "\\fileserver\software\HallmarkRecord\unattended_config.json"

foreach ($computer in $computers) {
    Write-Host "Installing on $computer..."
    
    Invoke-Command -ComputerName $computer -ScriptBlock {
        param($installer, $config)
        
        # Copy files locally
        Copy-Item $installer "C:\Temp\Setup.exe"
        Copy-Item $config "C:\Temp\unattended_config.json"
        
        # Install
        Start-Process "C:\Temp\Setup.exe" -ArgumentList "/VERYSILENT", "/CONFIG=C:\Temp\unattended_config.json" -Wait
        
        # Cleanup
        Remove-Item "C:\Temp\Setup.exe"
        Remove-Item "C:\Temp\unattended_config.json"
        
    } -ArgumentList $installer, $config
    
    Write-Host "✓ Installed on $computer"
}
```

### 4. Network Share Installation

Place on network share:
```
\\fileserver\software\HallmarkRecord\
  ├── Setup.exe
  ├── unattended_config.json
  └── INSTALL.bat
```

Create `INSTALL.bat`:
```batch
@echo off
\\fileserver\software\HallmarkRecord\Setup.exe /VERYSILENT /CONFIG=\\fileserver\software\HallmarkRecord\unattended_config.json
```

Users can run `INSTALL.bat` or you can push via login script.

## Post-Installation

### Verify Installation

Check that these files exist:
```
C:\Program Files\Hallmark Record\Recorder\Hallmark Recorder.exe
C:\Program Files\Hallmark Record\Editor\Hallmark Editor.exe
%APPDATA%\Hallmark Record\config.json
```

### User Configuration Location

Configuration is saved per-user:
```
%APPDATA%\Hallmark Record\config.json
```

Users can modify their settings through the application UI or by editing this file directly.

### Centralized Watermark

Place company logo on network share:
```
\\fileserver\logos\company_logo.png
```

Set in config:
```json
{
  "watermark": {
    "enabled": true,
    "image_path": "\\\\fileserver\\logos\\company_logo.png"
  }
}
```

## Troubleshooting

### Installation Logs

Check Inno Setup logs:
```
%TEMP%\Setup Log YYYY-MM-DD #001.txt
```

### Application Logs

Check application logs:
```
%APPDATA%\Hallmark Record\logs\
```

### Common Issues

**Issue**: "Configuration file not found"
- Ensure config file path is absolute
- Check network path is accessible
- Verify JSON syntax is valid

**Issue**: "Cannot create output folder"
- Ensure user has write permissions
- Check disk space
- Verify path is valid

**Issue**: "FFmpeg not found"
- Reinstall application
- Check antivirus isn't blocking FFmpeg
- Verify installation directory

## Security Considerations

### Password Encryption

Passwords in config should be encrypted. Use this Python script:

```python
from config_manager import ConfigManager
import base64

config = ConfigManager()

# Encrypt password (basic base64 - use better encryption in production)
password = "YourPassword123"
encrypted = base64.b64encode(password.encode()).decode()

config.set('upload.destinations.0.password_encrypted', encrypted)
```

**NOTE**: For production, use Windows DPAPI or Azure Key Vault for secure credential storage.

### Network Path Access

If using network paths (UNC), ensure:
- Service account has access
- Paths are accessible from all target machines
- Consider using DFS for reliability

## Support

For issues or questions:
- Email: [email protected]
- GitHub: https://github.com/agough77/hallmark-record
- Documentation: See README.md

## Version History

**v1.0.3** (2026-02-05)
- Added wizard-style desktop editor
- Unattended installation support
- Configuration management
- Upload destinations

**v1.0.0** (2026-01-08)
- Initial release
