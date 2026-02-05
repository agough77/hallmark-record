@echo off
REM Generate Unattended Configuration Template for Hallmark Record

echo ========================================
echo Hallmark Record - Unattended Installer
echo ========================================
echo.
echo This will create a configuration template that you can
echo customize for automated deployment across your organization.
echo.

python unattended_installer.py --create-config

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo SUCCESS!
    echo ========================================
    echo.
    echo Next steps:
    echo 1. Edit unattended_config.json with your settings
    echo 2. Deploy using: Setup.exe /VERYSILENT /CONFIG=unattended_config.json
    echo.
    echo For more options, see DEPLOYMENT_GUIDE.md
    echo.
) else (
    echo.
    echo ERROR: Failed to create configuration template
    echo Make sure Python is installed and in your PATH
    echo.
)

pause
