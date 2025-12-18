@echo off
chcp 65001 >nul 2>&1

echo ================================================
echo  男性ボイスチェンジャー 起動
echo ================================================
echo.

REM スクリプトのディレクトリに移動
cd /d "%~dp0"

REM Pythonの確認
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 goto :no_python
echo [OK] Python確認済み
goto :check_main

:no_python
echo [エラー] Pythonが見つかりません。
echo setup.batを先に実行してください。
echo.
pause
exit /b 1

:check_main
REM メインファイルの確認
if not exist "voice_changer_web.py" goto :no_main
echo [OK] voice_changer_web.py確認済み
goto :check_flask

:no_main
echo [エラー] voice_changer_web.pyが見つかりません。
echo.
pause
exit /b 1

:check_flask
REM Flaskの確認
python -c "import flask" >nul 2>&1
if %ERRORLEVEL% neq 0 goto :no_flask
echo [OK] Python依存関係確認済み
goto :check_static

:no_flask
echo [エラー] Pythonパッケージがインストールされていません。
echo setup.batを先に実行してください。
echo.
pause
exit /b 1

:check_static
REM 静的ファイルの確認
if exist "static\index.html" goto :static_ok

echo.
echo [!] フロントエンドがありません。ビルドを試みます...
echo.

node --version >nul 2>&1
if %ERRORLEVEL% neq 0 goto :no_node

if not exist "frontend\package.json" goto :no_package

cd frontend
echo npm install 実行中...
call npm install
if %ERRORLEVEL% neq 0 goto :npm_install_failed

echo npm run build 実行中...
call npm run build
if %ERRORLEVEL% neq 0 goto :npm_build_failed
cd ..

if not exist "static\index.html" goto :build_no_output
echo [OK] フロントエンドビルド完了
goto :static_ok

:no_node
echo [エラー] Node.jsがありません。
echo.
echo 解決方法:
echo 1. GitHubから最新版をダウンロードしてください
echo 2. または Node.js をインストール: https://nodejs.org/
echo.
pause
exit /b 1

:no_package
echo [エラー] frontend/package.jsonがありません。
echo GitHubから最新版をダウンロードしてください。
echo.
pause
exit /b 1

:npm_install_failed
echo [エラー] npm installに失敗しました。
cd ..
pause
exit /b 1

:npm_build_failed
echo [エラー] ビルドに失敗しました。
cd ..
pause
exit /b 1

:build_no_output
echo [エラー] ビルド後もstatic/index.htmlがありません。
echo.
pause
exit /b 1

:static_ok
echo [OK] フロントエンド確認済み
echo.
echo ================================================
echo  URL: http://localhost:5003
echo ================================================
echo.
echo ブラウザを開いています...

REM 2秒後にブラウザを開く
start "" cmd /c "timeout /t 2 >nul && start http://localhost:5003"

echo.
echo ================================================
echo  サーバー実行中
echo  停止: Ctrl+C または このウィンドウを閉じる
echo ================================================
echo.

REM サーバーを起動
python voice_changer_web.py

echo.
echo サーバーが停止しました。
echo.
pause
