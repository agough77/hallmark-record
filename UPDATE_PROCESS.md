# Hallmark Record - Update & Release Process

## Overview
This guide explains how to push updates to Hallmark Record from Git.

## Current Setup
- **Git Repository**: `https://github.com/agough77/hallmark-record.git`
- **Update Method**: Git pull + rebuild (for development)
- **Release Method**: GitHub Releases (for end users)

---

## For Developers: Updating from Git

### Quick Update (Development Environment)
1. Run `update.bat` from the project root:
   ```batch
   update.bat
   ```

This will:
- Fetch latest changes from Git
- Pull updates from main branch
- Update Python dependencies
- You're ready to test!

### After Pulling Updates
If code changes affect the recorder or editor modules, rebuild:
```batch
python -m PyInstaller recorder.spec --noconfirm
python -m PyInstaller editor.spec --noconfirm
```

---

## For Releases: Publishing Updates to End Users

### Step 1: Update Version Number

Edit `version.json`:
```json
{
  "version": "1.0.2",
  "release_date": "2026-01-09",
  "download_url": "https://github.com/agough77/hallmark-record/releases/download/v1.0.2/HallmarkRecord_v1.0.2_Complete.zip",
  "changelog": [
    "Description of changes",
    "Bug fixes",
    "New features"
  ],
  "minimum_version": "1.0.0",
  "critical_update": false
}
```

### Step 2: Build the Complete Package

```batch
# Clean previous builds
rmdir /s /q dist
rmdir /s /q build

# Build both executables
python -m PyInstaller recorder.spec --clean --noconfirm
python -m PyInstaller editor.spec --clean --noconfirm

# Optional: Build installer (requires Inno Setup)
build_installer.bat
```

### Step 3: Create Release Package

Create a ZIP file named `HallmarkRecord_v1.0.2_Complete.zip` containing:
```
HallmarkRecord_Complete/
├── Recorder/
│   ├── Hallmark Recorder.exe
│   └── _internal/
├── Editor/
│   ├── Hallmark Editor.exe
│   └── _internal/
├── Start Recorder.bat
├── Start Editor.bat
├── Setup.bat
├── Uninstall.bat
├── README.txt
└── LICENSE.txt
```

You can use the existing folder:
```batch
cd "c:\Users\AGough\Hallmark University\IT Services - Documents\Scripts + Tools\Hallmark Record"
powershell Compress-Archive -Path "HallmarkRecord_Complete\*" -DestinationPath "HallmarkRecord_v1.0.2_Complete.zip" -Force
```

### Step 4: Commit and Push to Git

```batch
git add .
git commit -m "Release v1.0.2 - Fixed device detection"
git push origin main
```

### Step 5: Create GitHub Release

1. Go to https://github.com/agough77/hallmark-record/releases
2. Click "Draft a new release"
3. Fill in:
   - **Tag**: `v1.0.2`
   - **Title**: `Hallmark Record v1.0.2`
   - **Description**: Copy from changelog in version.json
4. Upload `HallmarkRecord_v1.0.2_Complete.zip`
5. Click "Publish release"

### Step 6: Update version.json with Download URL

After publishing the release, the download URL will be:
```
https://github.com/agough77/hallmark-record/releases/download/v1.0.2/HallmarkRecord_v1.0.2_Complete.zip
```

Update `version.json` with this URL, then commit:
```batch
git add version.json
git commit -m "Update download URL for v1.0.2"
git push origin main
```

---

## Automated Update Checker (Future Enhancement)

Currently, users need to manually download from GitHub. Here's how to add automatic updates:

### Option 1: Add Update Checker to Main Application

Add a menu item "Check for Updates" that:
1. Fetches `version.json` from GitHub
2. Compares with current version
3. Shows dialog if update available
4. Opens browser to release page

### Option 2: Use update.bat for Quick Updates

Users can run `update.bat` if they have:
- Git installed
- Python installed
- Cloned the repository

This is best for tech-savvy users or developers.

---

## Testing Updates

### Before Releasing:
1. Test on clean Windows machine
2. Install old version
3. Run update process
4. Verify all features work

### Checklist:
- [ ] Version number updated in version.json
- [ ] Changelog is accurate and descriptive
- [ ] All executables rebuilt and tested
- [ ] ZIP package created with correct structure
- [ ] Git changes committed and pushed
- [ ] GitHub release created
- [ ] Download URL verified
- [ ] Installation tested on clean machine

---

## Quick Reference Commands

**Pull latest from Git:**
```batch
update.bat
```

**Rebuild after code changes:**
```batch
python -m PyInstaller recorder.spec --noconfirm
python -m PyInstaller editor.spec --noconfirm
```

**Create release package:**
```batch
powershell Compress-Archive -Path "HallmarkRecord_Complete\*" -DestinationPath "HallmarkRecord_v1.0.2_Complete.zip" -Force
```

**Push to Git:**
```batch
git add .
git commit -m "Release v1.0.2"
git push origin main
```

---

## Troubleshooting

**Git pull conflicts:**
```batch
git stash
git pull origin main
git stash pop
```

**Clean build issues:**
- Close all terminals/applications
- Delete `build/` and `dist/` folders manually
- Restart VS Code
- Try build again

**PyInstaller errors:**
- Check Python version: `python --version`
- Update PyInstaller: `pip install --upgrade pyinstaller`
- Check requirements: `pip install -r requirements.txt`

---

## Current Version: 1.0.2

### Changes in this version:
- Fixed device detection in bundled executables
- Improved FFmpeg path resolution for PyInstaller
- Better logging and error handling

**Released**: January 9, 2026
