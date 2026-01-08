@echo off
echo ========================================
echo   Hallmark Record Updater
echo ========================================
echo.

REM Check if git is available
git --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Git is not installed or not in PATH
    echo Please install Git from git-scm.com
    pause
    exit /b 1
)

echo [1/3] Fetching latest updates from Git...
git fetch origin
if errorlevel 1 (
    echo ERROR: Failed to fetch updates
    echo Make sure you have an active internet connection
    pause
    exit /b 1
)

echo.
echo [2/3] Pulling latest changes...
git pull origin main
if errorlevel 1 (
    echo ERROR: Failed to pull updates
    echo You may have local changes that conflict
    pause
    exit /b 1
)

echo.
echo [3/3] Updating Python dependencies...
python -m pip install --upgrade -r requirements.txt
if errorlevel 1 (
    echo WARNING: Some dependencies failed to update
    echo The application may still work
)

echo.
echo ========================================
echo   Update Complete!
echo ========================================
echo.
echo Hallmark Record has been updated to the latest version.
echo.
pause
