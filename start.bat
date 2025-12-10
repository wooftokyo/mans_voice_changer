@echo off
chcp 65001 >nul
echo ================================================
echo  男性ボイスチェンジャー 起動中...
echo ================================================
echo.

REM Pythonの確認
python --version >nul 2>&1
if errorlevel 1 (
    echo [エラー] Pythonが見つかりません。
    echo 先に setup.bat を実行してください。
    pause
    exit /b 1
)

echo ブラウザで http://localhost:5003 を開いてください
echo （自動で開かない場合は手動で開いてください）
echo.
echo 終了するには Ctrl+C を押すか、このウィンドウを閉じてください
echo ================================================
echo.

REM 2秒後にブラウザを開く
start /b cmd /c "timeout /t 2 >nul && start http://localhost:5003"

REM サーバー起動
python voice_changer_web.py

pause
