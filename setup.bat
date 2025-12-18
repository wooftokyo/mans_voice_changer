@echo off
chcp 65001 >nul 2>&1

echo ================================================
echo  男性ボイスチェンジャー セットアップ
echo ================================================
echo.

REM スクリプトのディレクトリに移動
cd /d "%~dp0"
echo フォルダ: %CD%
echo.

REM requirements.txtの確認
if not exist "requirements.txt" goto :no_requirements

echo ================================================
echo  1. Pythonの確認
echo ================================================
echo.

python --version >nul 2>&1
if %ERRORLEVEL% neq 0 goto :install_python
echo [OK] Python:
python --version
echo.
goto :check_ffmpeg

:no_requirements
echo [エラー] requirements.txtが見つかりません。
echo ZIPを解凍してからsetup.batを実行してください。
echo.
pause
exit /b 1

:install_python
echo Pythonが見つかりません。
echo.
winget --version >nul 2>&1
if %ERRORLEVEL% neq 0 goto :manual_python
echo wingetでPythonをインストール中...
winget install Python.Python.3.11 --accept-source-agreements --accept-package-agreements
echo.
echo ================================================
echo  Pythonをインストールしました
echo  このウィンドウを閉じて、setup.batをもう一度実行
echo ================================================
echo.
pause
exit /b 0

:manual_python
echo Pythonを手動でインストールしてください:
echo https://www.python.org/downloads/
echo.
echo ※「Add Python to PATH」に必ずチェック！
echo.
pause
exit /b 1

:check_ffmpeg
echo ================================================
echo  2. ffmpegの確認
echo ================================================
echo.

ffmpeg -version >nul 2>&1
if %ERRORLEVEL% neq 0 goto :install_ffmpeg
echo [OK] ffmpeg確認済み
echo.
goto :install_packages

:install_ffmpeg
echo ffmpegが見つかりません。
winget --version >nul 2>&1
if %ERRORLEVEL% neq 0 goto :manual_ffmpeg
echo wingetでffmpegをインストール中...
winget install Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
echo.
echo ================================================
echo  ffmpegをインストールしました
echo  このウィンドウを閉じて、setup.batをもう一度実行
echo ================================================
echo.
pause
exit /b 0

:manual_ffmpeg
echo ffmpegを手動でインストールしてください:
echo https://ffmpeg.org/download.html
echo.
goto :install_packages

:install_packages
echo ================================================
echo  3. Pythonパッケージのインストール
echo ================================================
echo.
echo ※初回は10-20分かかります。お待ちください...
echo.

python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 goto :pip_failed

echo.
echo [OK] パッケージインストール完了
echo.
goto :check_frontend

:pip_failed
echo.
echo [エラー] パッケージのインストールに失敗しました。
echo.
pause
exit /b 1

:check_frontend
echo ================================================
echo  4. フロントエンドの確認
echo ================================================
echo.

if exist "static\index.html" goto :frontend_ok
echo [警告] static/index.htmlがありません
echo start.bat実行時にビルドを試みます
goto :done

:frontend_ok
echo [OK] フロントエンド確認済み

:done
echo.
echo ================================================
echo.
echo   セットアップ完了！
echo.
echo   次: start.bat をダブルクリック
echo.
echo ================================================
echo.
pause
