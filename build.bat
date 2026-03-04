@echo off
echo ========================================
echo   Cookie Robot - Build EXE
echo ========================================
echo.

REM Activate virtual environment
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo [!] Virtual environment not found
    echo     Run install.bat first
    pause
    exit /b 1
)

echo Building application...
echo This may take 1-3 minutes...
echo.

pyinstaller build.spec

echo.
if exist "dist\CookieRobot.exe" (
    echo ========================================
    echo   Build successful!
    echo ========================================
    echo.
    echo Ready file: dist\CookieRobot.exe
    echo.
    echo Open dist folder? (Y/N)
    set /p choice="> "
    if /i "%choice%"=="Y" (
        explorer dist
    )
) else (
    echo [ERROR] Build failed
    echo Check errors above
)

pause
