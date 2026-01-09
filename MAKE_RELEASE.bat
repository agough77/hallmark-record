@echo off
REM =============================================================================
REM Hallmark Record - Quick Release Script
REM Creates a release package and prepares it for GitHub
REM =============================================================================

echo ========================================
echo   Hallmark Record - Quick Release
echo ========================================
echo.

REM Get version from user
set /p VERSION="Enter version number (e.g., 1.0.2): "
if "%VERSION%"=="" (
    echo ERROR: Version number required
    pause
    exit /b 1
)

echo.
echo Creating release v%VERSION%...
echo.

REM Step 1: Copy updated executables to package
echo [1/4] Copying updated executables...
robocopy "dist\Hallmark Recorder" "HallmarkRecord_Complete\Recorder" /E /IS /IT /NFL /NDL /NJH /NJS
robocopy "dist\Hallmark Editor" "HallmarkRecord_Complete\Editor" /E /IS /IT /NFL /NDL /NJH /NJS
echo Done!
echo.

REM Step 2: Create ZIP package
echo [2/4] Creating release package...
if exist "HallmarkRecord_v%VERSION%_Complete.zip" del "HallmarkRecord_v%VERSION%_Complete.zip"
powershell -Command "Compress-Archive -Path 'HallmarkRecord_Complete\*' -DestinationPath 'HallmarkRecord_v%VERSION%_Complete.zip' -Force"
if errorlevel 1 (
    echo ERROR: Failed to create ZIP package
    pause
    exit /b 1
)
echo Done! Created: HallmarkRecord_v%VERSION%_Complete.zip
echo.

REM Step 3: Show file size
echo [3/4] Package information:
for %%A in ("HallmarkRecord_v%VERSION%_Complete.zip") do echo   Size: %%~zA bytes
echo.

REM Step 4: Instructions
echo [4/4] Next steps:
echo.
echo 1. Update version.json with:
echo    - version: "%VERSION%"
echo    - release_date: %DATE%
echo.
echo 2. Commit and push to Git:
echo    git add .
echo    git commit -m "Release v%VERSION%"
echo    git push origin main
echo.
echo 3. Create GitHub Release:
echo    - Go to: https://github.com/agough77/hallmark-record/releases
echo    - Click "Draft a new release"
echo    - Tag: v%VERSION%
echo    - Upload: HallmarkRecord_v%VERSION%_Complete.zip
echo    - Publish release
echo.
echo 4. Update version.json download URL with GitHub release URL
echo.
echo ========================================
echo   Release package ready!
echo ========================================
echo.

REM Open folder
explorer /select,"HallmarkRecord_v%VERSION%_Complete.zip"

pause
