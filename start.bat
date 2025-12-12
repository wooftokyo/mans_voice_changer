@echo off
chcp 65001 >nul
echo ================================================
echo  男性ボイスチェンジャー - 起動中...
echo ================================================
echo.

REM スクリプトのディレクトリに移動
cd /d "%~dp0"

REM Pythonの確認
python --version >nul 2>&1
if errorlevel 1 (
    echo [エラー] Pythonが見つかりません。
    echo 先にsetup.batを実行してください。
    echo.
    echo 何かキーを押すと閉じます...
    pause >nul
    exit /b 1
)

echo Pythonが見つかりました:
python --version
echo.

REM メインファイルの確認
if not exist "voice_changer_web.py" (
    echo [エラー] voice_changer_web.pyが見つかりません。
    echo このファイルが同じフォルダにあることを確認してください。
    echo.
    echo 何かキーを押すと閉じます...
    pause >nul
    exit /b 1
)

REM 静的ファイルの確認
if not exist "static\index.html" (
    echo [警告] フロントエンドがビルドされていません。
    echo フロントエンドをビルド中...
    cd frontend
    call npm install
    call npm run build
    cd ..
)

echo ================================================
echo  URL: http://localhost:5003
echo ================================================
echo.
echo ブラウザを開いています...
echo.
echo ================================================
echo  サーバー実行中... このウィンドウを閉じないでください。
echo  停止するにはCtrl+Cを押すかウィンドウを閉じてください。
echo ================================================
echo.

REM 2秒後にブラウザを開く
start /b cmd /c "timeout /t 2 >nul && start http://localhost:5003"

REM サーバーを起動
python voice_changer_web.py

REM サーバー停止
echo.
echo ================================================
echo  サーバーが停止しました
echo ================================================
echo.
echo 何かキーを押すと閉じます...
pause >nul
