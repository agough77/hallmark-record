@echo off
echo ========================================
echo   Hallmark Record - Installation
echo ========================================
echo.
echo This will install all required dependencies
echo.

cd /d "%~dp0"

REM Check if Python is installed
python --version
if errorlevel 1 (
    echo.
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://python.org
    pause
    exit /b 1
)

echo.
echo Installing Python packages...
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ERROR: Installation failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Installation Complete!
echo ========================================
echo.
echo You can now run:
echo   - START_RECORDER.bat  : Main recording application
echo   - START_EDITOR.bat    : Video editor (web-based)
echo.
echo Note: FFmpeg is included in the hallmark-scribble folder
echo.
pause
