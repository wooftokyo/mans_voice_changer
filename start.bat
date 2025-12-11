@echo off
chcp 65001 >nul
echo ================================================
echo  男性ボイスチェンジャー 起動中...
echo ================================================
echo.

REM スクリプトのディレクトリに移動
cd /d "%~dp0"

REM Pythonの確認
python --version >nul 2>&1
if errorlevel 1 (
    echo [エラー] Pythonが見つかりません。
    echo 先に setup.bat を実行してください。
    echo.
    echo 何かキーを押すと閉じます...
    pause >nul
    exit /b 1
)

echo Pythonを確認しました:
python --version
echo.

REM 必要なファイルの確認
if not exist "voice_changer_web.py" (
    echo [エラー] voice_changer_web.py が見つかりません。
    echo このファイルと同じフォルダにあるか確認してください。
    echo.
    echo 何かキーを押すと閉じます...
    pause >nul
    exit /b 1
)

if not exist "requirements.txt" (
    echo [警告] requirements.txt が見つかりません。
    echo setup.bat を先に実行してください。
)

echo ================================================
echo  アクセスURL:
echo    メインページ:   http://localhost:5003
echo    波形エディタ:   http://localhost:5003/editor
echo ================================================
echo.
echo ブラウザで http://localhost:5003 を開きます
echo.
echo ================================================
echo  サーバー起動中... このウィンドウは閉じないでください
echo  終了するには Ctrl+C を押すか、ウィンドウを閉じてください
echo ================================================
echo.

REM 2秒後にブラウザを開く
start /b cmd /c "timeout /t 2 >nul && start http://localhost:5003"

REM サーバー起動（エラーが出ても表示する）
python voice_changer_web.py

REM サーバーが終了した場合
echo.
echo ================================================
echo  サーバーが停止しました
echo ================================================
echo.
echo 何かキーを押すと閉じます...
pause >nul
