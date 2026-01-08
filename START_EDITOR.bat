@echo off
echo ========================================
echo   Hallmark Record - Video Editor
echo ========================================
echo.
echo Starting video editor server...
echo.

cd /d "%~dp0"

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://python.org
    pause
    exit /b 1
)

REM Check if Flask is installed
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo Installing Flask...
    pip install Flask
    if errorlevel 1 (
        echo ERROR: Failed to install Flask
        pause
        exit /b 1
    )
)

echo.
echo Editor will be available at: http://localhost:5000
echo Press Ctrl+C to stop the server
echo.

REM Run the editor
cd editor
python video_editor.py

if errorlevel 1 (
    echo.
    echo ERROR: Editor server exited with an error
    pause
)
