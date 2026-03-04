@echo off
echo ========================================
echo   Cookie Robot - Auto Installer
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo Install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH"
    pause
    exit /b 1
)

echo [OK] Python found
echo.

REM Create virtual environment
echo [1/4] Creating virtual environment...
if not exist "venv" (
    python -m venv venv
)
call venv\Scripts\activate.bat

echo [2/4] Installing dependencies...
pip install --quiet PyQt5 playwright requests schedule pyinstaller

echo [3/4] Installing Chromium browser...
playwright install chromium

echo.
echo ========================================
echo   Installation complete!
echo ========================================
echo.
echo To run the app: python main.py
echo To build .exe: run build.bat
echo.
echo Run the app now? (Y/N)
set /p choice="> "
if /i "%choice%"=="Y" (
    python main.py
)

pause
