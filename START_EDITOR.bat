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
echo Editor will be available at: http://localhost:5500
echo Press Ctrl+C to stop the server
echo.

REM Run the editor
start "" cmd /c "cd editor && python video_editor.py"

REM Wait for server to start and open browser
timeout /t 3 /nobreak >nul
start http://localhost:5500

echo.
echo Editor is starting...
echo If the browser doesn't open automatically, navigate to http://localhost:5500
pause

if errorlevel 1 (
    echo.
    echo ERROR: Editor server exited with an error
    pause
)
