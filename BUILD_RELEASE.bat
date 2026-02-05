@echo off
REM Quick Build Script for Hallmark Record v1.0.3

echo ========================================
echo Hallmark Record - Quick Build
echo ========================================
echo.

REM Check if PyInstaller is installed
python -c "import PyInstaller" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo PyInstaller not found! Installing...
    pip install pyinstaller
)

echo Step 1/3: Building Recorder executable...
echo.
python -m PyInstaller recorder.spec --clean

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to build Recorder
    pause
    exit /b 1
)

echo.
echo Step 2/3: Building Editor executable...
echo.
python -m PyInstaller editor.spec --clean

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to build Editor
    pause
    exit /b 1
)

echo.
echo Step 3/3: Creating installer package...
echo.

REM Check if Inno Setup is installed
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
    
    if %ERRORLEVEL% EQU 0 (
        echo.
        echo ========================================
        echo SUCCESS!
        echo ========================================
        echo.
        echo Installer created in: installer_output\
        echo.
        echo Files created:
        dir /B installer_output\*.exe 2>nul
        echo.
    ) else (
        echo ERROR: Inno Setup compilation failed
        pause
        exit /b 1
    )
) else (
    echo.
    echo WARNING: Inno Setup not found
    echo.
    echo Executables were built successfully, but installer was not created.
    echo.
    echo To create the installer:
    echo 1. Install Inno Setup 6 from https://jrsoftware.org/isinfo.php
    echo 2. Run: "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
    echo.
)

echo.
echo Build complete!
echo.
pause
