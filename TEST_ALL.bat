@echo off
echo ================================================
echo   Hallmark Record - Quick Test
echo ================================================
echo.
echo This will test all components:
echo   1. Device Detection
echo   2. GUI Application
echo   3. Web Editor
echo.
pause

echo.
echo === Step 1: Testing Device Detection ===
python test_devices.py
echo.
pause

echo.
echo === Step 2: Testing GUI Application ===
echo The GUI will open in a new window.
echo Close it when you're done testing.
echo.
pause
start python main.py

echo.
echo === Step 3: Testing Web Editor ===
echo The editor will open in your browser.
echo Press Ctrl+C to stop the server when done.
echo.
pause
cd editor
python video_editor.py

echo.
echo ================================================
echo   Testing Complete!
echo ================================================
pause
