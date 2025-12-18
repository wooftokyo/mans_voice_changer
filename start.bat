@echo off

echo ================================================
echo  Male Voice Changer - Starting
echo ================================================
echo.

cd /d "%~dp0"

python --version >nul 2>&1
if %ERRORLEVEL% neq 0 goto :no_python
echo [OK] Python found
goto :check_main

:no_python
echo [ERROR] Python not found.
echo Run setup.bat first.
echo.
pause
exit /b 1

:check_main
if not exist "voice_changer_web.py" goto :no_main
echo [OK] voice_changer_web.py found
goto :check_flask

:no_main
echo [ERROR] voice_changer_web.py not found.
echo.
pause
exit /b 1

:check_flask
python -c "import flask" >nul 2>&1
if %ERRORLEVEL% neq 0 goto :no_flask
echo [OK] Python packages OK
goto :check_static

:no_flask
echo [ERROR] Python packages not installed.
echo Run setup.bat first.
echo.
pause
exit /b 1

:check_static
if exist "static\index.html" goto :static_ok

echo.
echo [!] Frontend not found. Trying to build...
echo.

node --version >nul 2>&1
if %ERRORLEVEL% neq 0 goto :no_node

if not exist "frontend\package.json" goto :no_package

cd frontend
echo Running npm install...
call npm install
if %ERRORLEVEL% neq 0 goto :npm_install_failed

echo Running npm run build...
call npm run build
if %ERRORLEVEL% neq 0 goto :npm_build_failed
cd ..

if not exist "static\index.html" goto :build_no_output
echo [OK] Frontend built
goto :static_ok

:no_node
echo [ERROR] Node.js not found.
echo.
echo Solutions:
echo 1. Download latest version from GitHub
echo 2. Or install Node.js: https://nodejs.org/
echo.
pause
exit /b 1

:no_package
echo [ERROR] frontend/package.json not found.
echo Download latest version from GitHub.
echo.
pause
exit /b 1

:npm_install_failed
echo [ERROR] npm install failed.
cd ..
pause
exit /b 1

:npm_build_failed
echo [ERROR] Build failed.
cd ..
pause
exit /b 1

:build_no_output
echo [ERROR] static/index.html still not found after build.
echo.
pause
exit /b 1

:static_ok
echo [OK] Frontend OK
echo.
echo ================================================
echo  URL: http://localhost:5003
echo ================================================
echo.
echo Opening browser...

start "" cmd /c "timeout /t 2 >nul && start http://localhost:5003"

echo.
echo ================================================
echo  Server running
echo  Stop: Ctrl+C or close this window
echo ================================================
echo.

python voice_changer_web.py

echo.
echo Server stopped.
echo.
pause
