@echo off

echo ================================================
echo  Male Voice Changer - Setup
echo ================================================
echo.

cd /d "%~dp0"
echo Folder: %CD%
echo.

if not exist "requirements.txt" goto :no_requirements

echo ================================================
echo  1. Checking Python
echo ================================================
echo.

python --version >nul 2>&1
if %ERRORLEVEL% neq 0 goto :install_python
echo [OK] Python:
python --version
echo.
goto :check_ffmpeg

:no_requirements
echo [ERROR] requirements.txt not found.
echo Please extract ZIP first.
echo.
pause
exit /b 1

:install_python
echo Python not found.
echo.
winget --version >nul 2>&1
if %ERRORLEVEL% neq 0 goto :manual_python
echo Installing Python via winget...
winget install Python.Python.3.11 --accept-source-agreements --accept-package-agreements
echo.
echo ================================================
echo  Python installed!
echo  Close this window and run setup.bat again
echo ================================================
echo.
pause
exit /b 0

:manual_python
echo Please install Python manually:
echo https://www.python.org/downloads/
echo.
echo IMPORTANT: Check "Add Python to PATH"
echo.
pause
exit /b 1

:check_ffmpeg
echo ================================================
echo  2. Checking ffmpeg
echo ================================================
echo.

ffmpeg -version >nul 2>&1
if %ERRORLEVEL% neq 0 goto :install_ffmpeg
echo [OK] ffmpeg found
echo.
goto :install_packages

:install_ffmpeg
echo ffmpeg not found.
winget --version >nul 2>&1
if %ERRORLEVEL% neq 0 goto :manual_ffmpeg
echo Installing ffmpeg via winget...
winget install Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
echo.
echo ================================================
echo  ffmpeg installed!
echo  Close this window and run setup.bat again
echo ================================================
echo.
pause
exit /b 0

:manual_ffmpeg
echo Please install ffmpeg manually:
echo https://ffmpeg.org/download.html
echo.
goto :install_packages

:install_packages
echo ================================================
echo  3. Installing Python packages
echo ================================================
echo.
echo This may take 10-20 minutes. Please wait...
echo.

python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 goto :pip_failed

echo.
echo [OK] Packages installed
echo.
goto :check_frontend

:pip_failed
echo.
echo [ERROR] Package installation failed.
echo.
pause
exit /b 1

:check_frontend
echo ================================================
echo  4. Checking frontend
echo ================================================
echo.

if exist "static\index.html" goto :frontend_ok
echo [WARNING] static/index.html not found
echo Will try to build when running start.bat
goto :done

:frontend_ok
echo [OK] Frontend found

:done
echo.
echo ================================================
echo.
echo   Setup complete!
echo.
echo   Next: Double-click start.bat
echo.
echo ================================================
echo.
pause
