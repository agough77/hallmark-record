@echo off
REM Build script for Hallmark Record installer package
REM This script creates standalone executables and an installer

echo ============================================
echo Hallmark Record - Build Installer Package
echo ============================================
echo.

REM Check if PyInstaller is installed
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [INFO] PyInstaller not found. Installing...
    pip install pyinstaller
    if errorlevel 1 (
        echo [ERROR] Failed to install PyInstaller
        pause
        exit /b 1
    )
)

echo [1/5] Cleaning previous builds...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist installer_output rmdir /s /q installer_output
echo.

echo [2/5] Building Hallmark Recorder executable...
python -m PyInstaller recorder.spec --clean --noconfirm
if errorlevel 1 (
    echo [ERROR] Failed to build Recorder executable
    pause
    exit /b 1
)
echo.

echo [3/5] Building Hallmark Editor executable...
python -m PyInstaller editor.spec --clean --noconfirm
if errorlevel 1 (
    echo [ERROR] Failed to build Editor executable
    pause
    exit /b 1
)
echo.

echo [4/5] Checking for Inno Setup...
if not exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    echo [WARNING] Inno Setup not found
    echo.
    echo Please install Inno Setup from: https://jrsoftware.org/isinfo.php
    echo After installing, run this script again to create the installer.
    echo.
    echo Standalone executables are ready in the 'dist' folder:
    echo - dist\Hallmark Recorder\Hallmark Recorder.exe
    echo - dist\Hallmark Editor\Hallmark Editor.exe
    echo.
    pause
    exit /b 0
)

echo [5/5] Creating installer with Inno Setup...
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
if errorlevel 1 (
    echo [ERROR] Failed to create installer
    pause
    exit /b 1
)
echo.

echo ============================================
echo Build Complete!
echo ============================================
echo.
echo Standalone executables:
echo - dist\Hallmark Recorder\Hallmark Recorder.exe
echo - dist\Hallmark Editor\Hallmark Editor.exe
echo.
if exist installer_output (
    echo Installer package:
    echo - installer_output\HallmarkRecord_Setup_v1.0.0.exe
    echo.
)
echo You can now distribute the installer to users.
echo.
pause
