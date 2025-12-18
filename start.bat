@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

REM スクリプトのディレクトリに移動
cd /d "%~dp0"

echo ================================================
echo  男性ボイスチェンジャー - 起動中...
echo ================================================
echo.

REM Pythonの確認
python --version >nul 2>&1
if !ERRORLEVEL! neq 0 (
    echo [エラー] Pythonが見つかりません。
    echo 先にsetup.batを実行してください。
    pause
    exit /b 1
)
echo [OK] Python確認済み

REM メインファイルの確認
if not exist "voice_changer_web.py" (
    echo [エラー] voice_changer_web.pyが見つかりません。
    pause
    exit /b 1
)
echo [OK] voice_changer_web.py確認済み

REM 依存パッケージの確認
python -c "import flask" >nul 2>&1
if !ERRORLEVEL! neq 0 (
    echo [エラー] Flaskがインストールされていません。
    echo setup.batを実行してください。
    pause
    exit /b 1
)
echo [OK] Python依存関係確認済み

REM 静的ファイルの確認とビルド
if not exist "static\index.html" (
    echo.
    echo [!] フロントエンドがビルドされていません。ビルド中...
    echo.

    REM Node.jsの確認
    node --version >nul 2>&1
    if !ERRORLEVEL! neq 0 (
        echo [エラー] Node.jsが見つかりません。
        echo setup.batを実行してNode.jsをインストールしてください。
        pause
        exit /b 1
    )

    if not exist "frontend\package.json" (
        echo [エラー] frontend/package.jsonが見つかりません。
        pause
        exit /b 1
    )

    pushd frontend

    echo npm install 実行中...
    call npm install
    if !ERRORLEVEL! neq 0 (
        echo [エラー] npm installに失敗しました。
        popd
        pause
        exit /b 1
    )

    echo npm run build 実行中...
    call npm run build
    if !ERRORLEVEL! neq 0 (
        echo [エラー] ビルドに失敗しました。
        popd
        pause
        exit /b 1
    )

    popd

    if not exist "static\index.html" (
        echo [エラー] ビルド後もstatic/index.htmlが見つかりません。
        pause
        exit /b 1
    )

    echo [OK] フロントエンドビルド完了
)

echo [OK] static/index.html確認済み
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
echo  サーバー実行中 - このウィンドウを閉じないで！
echo  停止: Ctrl+C またはウィンドウを閉じる
echo ================================================
echo.

REM サーバーを起動
python voice_changer_web.py

echo.
echo サーバーが停止しました。
pause
