@echo off
chcp 65001 >nul
echo ================================================
echo  Male Voice Changer Setup (Windows)
echo ================================================
echo.
echo Features:
echo   - AI voice detection (95-98%% accuracy)
echo   - Waveform editor for manual editing
echo   - Project history
echo.

REM Check Python
echo [1/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found. Attempting to install...
    echo.

    REM Check if winget is available
    winget --version >nul 2>&1
    if errorlevel 1 (
        echo [Error] winget not found.
        echo Please install Python manually:
        echo https://www.python.org/downloads/
        echo.
        echo Make sure to check "Add Python to PATH" during installation!
        pause
        exit /b 1
    )

    echo Installing Python via winget...
    winget install Python.Python.3.11 --accept-source-agreements --accept-package-agreements

    if errorlevel 1 (
        echo [Error] Failed to install Python.
        echo Please install manually: https://www.python.org/downloads/
        pause
        exit /b 1
    )

    echo.
    echo Python installed.
    echo ================================================
    echo Important: Close this window and re-run setup.bat
    echo in a new command prompt.
    echo ================================================
    pause
    exit /b 0
)
echo Python found:
python --version

REM Check ffmpeg
echo.
echo [2/5] Checking ffmpeg...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo ffmpeg not found. Attempting to install...
    echo.

    winget --version >nul 2>&1
    if errorlevel 1 (
        echo [Warning] winget not found.
        echo Please install ffmpeg manually:
        echo https://ffmpeg.org/download.html
        echo.
    ) else (
        echo Installing ffmpeg via winget...
        winget install Gyan.FFmpeg --accept-source-agreements --accept-package-agreements

        if errorlevel 1 (
            echo [Warning] Failed to install ffmpeg.
            echo Please install manually: https://ffmpeg.org/download.html
        ) else (
            echo ffmpeg installed.
            echo ================================================
            echo Important: Close this window and re-run setup.bat
            echo in a new command prompt.
            echo ================================================
            pause
            exit /b 0
        )
    )
) else (
    echo ffmpeg found
)

REM Check Node.js
echo.
echo [3/5] Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo Node.js not found. Attempting to install...
    echo.

    winget --version >nul 2>&1
    if errorlevel 1 (
        echo [Warning] winget not found.
        echo Please install Node.js manually:
        echo https://nodejs.org/
        echo.
    ) else (
        echo Installing Node.js via winget...
        winget install OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements

        if errorlevel 1 (
            echo [Warning] Failed to install Node.js.
            echo Please install manually: https://nodejs.org/
        ) else (
            echo Node.js installed.
            echo ================================================
            echo Important: Close this window and re-run setup.bat
            echo in a new command prompt.
            echo ================================================
            pause
            exit /b 0
        )
    )
) else (
    echo Node.js found:
    node --version
)

REM Upgrade pip
echo.
echo [4/5] Upgrading pip...
python -m pip install --upgrade pip

REM Install Python dependencies
echo.
echo [5/5] Installing dependencies...
echo (This may take 5-10 minutes on first run)
echo.

pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [Error] Failed to install packages.
    pause
    exit /b 1
)

REM Build frontend if Node.js is available
node --version >nul 2>&1
if not errorlevel 1 (
    echo.
    echo Building frontend...
    cd frontend
    call npm install
    call npm run build
    cd ..
)

echo.
echo ================================================
echo  Setup Complete!
echo ================================================
echo.
echo Run start.bat to launch the application
echo.
echo URL: http://localhost:5003
echo.
pause
