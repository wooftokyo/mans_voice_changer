@echo off
chcp 65001 >nul
echo ================================================
echo  Male Voice Changer - Starting...
echo ================================================
echo.

REM Change to script directory
cd /d "%~dp0"

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [Error] Python not found.
    echo Please run setup.bat first.
    echo.
    echo Press any key to close...
    pause >nul
    exit /b 1
)

echo Python found:
python --version
echo.

REM Check for main file
if not exist "voice_changer_web.py" (
    echo [Error] voice_changer_web.py not found.
    echo Make sure this file is in the same folder.
    echo.
    echo Press any key to close...
    pause >nul
    exit /b 1
)

REM Check for static files
if not exist "static\index.html" (
    echo [Warning] Frontend not built.
    echo Building frontend...
    cd frontend
    call npm install
    call npm run build
    cd ..
)

echo ================================================
echo  URL: http://localhost:5003
echo ================================================
echo.
echo Opening browser...
echo.
echo ================================================
echo  Server running... Do not close this window.
echo  Press Ctrl+C or close window to stop.
echo ================================================
echo.

REM Open browser after 2 seconds
start /b cmd /c "timeout /t 2 >nul && start http://localhost:5003"

REM Start server
python voice_changer_web.py

REM Server stopped
echo.
echo ================================================
echo  Server stopped
echo ================================================
echo.
echo Press any key to close...
pause >nul
