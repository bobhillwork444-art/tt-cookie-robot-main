@echo off
REM TT Cookie Robot - Windows Build Script
REM Run this script in the project root directory

echo ========================================
echo TT Cookie Robot - Building for Windows
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found! Please install Python 3.11+
    pause
    exit /b 1
)

REM Install dependencies
echo [1/4] Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

REM Install Playwright browsers
echo [2/4] Installing Playwright browsers...
playwright install chromium
if errorlevel 1 (
    echo WARNING: Playwright browser installation may have issues
)

REM Build with PyInstaller
echo [3/4] Building executable...
pyinstaller build_windows.spec --clean --noconfirm
if errorlevel 1 (
    echo ERROR: PyInstaller build failed
    pause
    exit /b 1
)

REM Create ZIP
echo [4/4] Creating portable ZIP...
powershell -Command "Compress-Archive -Path 'dist\TTCookieRobot\*' -DestinationPath 'TTCookieRobot_Windows_Portable.zip' -Force"

echo.
echo ========================================
echo Build complete!
echo ========================================
echo.
echo Output:
echo   - Folder: dist\TTCookieRobot\
echo   - ZIP:    TTCookieRobot_Windows_Portable.zip
echo.
echo To run: dist\TTCookieRobot\TTCookieRobot.exe
echo.
pause
