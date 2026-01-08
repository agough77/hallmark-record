@echo off
echo ========================================
echo   Hallmark Record Uninstaller
echo ========================================
echo.
echo This will remove:
echo   - Desktop shortcuts
echo   - Python dependencies
echo.
echo Output files in Downloads\Hallmark Record will NOT be deleted.
echo.
set /p CONFIRM="Continue with uninstall? (Y/N): "
if /i not "%CONFIRM%"=="Y" (
    echo Uninstall cancelled.
    pause
    exit /b 0
)

echo.
echo [1/2] Removing desktop shortcuts...
if exist "%USERPROFILE%\Desktop\Hallmark Record.lnk" (
    del "%USERPROFILE%\Desktop\Hallmark Record.lnk"
    echo   - Removed Hallmark Record shortcut
)

echo.
echo [2/2] Uninstalling Python dependencies...
python -m pip uninstall -y PyQt5 Flask pywin32

echo.
echo ========================================
echo   Uninstall Complete!
echo ========================================
echo.
echo Your recordings in Downloads\Hallmark Record are still safe.
echo You can manually delete them if needed.
echo.
pause
