@echo off
chcp 65001 >nul
echo ================================================
echo  男性ボイスチェンジャー セットアップ (Windows)
echo ================================================
echo.

REM Pythonの確認
echo [1/4] Pythonを確認中...
python --version >nul 2>&1
if errorlevel 1 (
    echo Pythonが見つかりません。インストールを試みます...
    echo.

    REM wingetが使えるか確認
    winget --version >nul 2>&1
    if errorlevel 1 (
        echo [エラー] wingetが見つかりません。
        echo 手動でPythonをインストールしてください:
        echo https://www.python.org/downloads/
        echo.
        echo インストール時に「Add Python to PATH」にチェックを入れてください！
        pause
        exit /b 1
    )

    echo wingetでPythonをインストール中...
    winget install Python.Python.3.11 --accept-source-agreements --accept-package-agreements

    if errorlevel 1 (
        echo [エラー] Pythonのインストールに失敗しました。
        echo 手動でインストールしてください: https://www.python.org/downloads/
        pause
        exit /b 1
    )

    echo.
    echo Pythonをインストールしました。
    echo ================================================
    echo 重要: 一度このウィンドウを閉じて、
    echo 新しいコマンドプロンプトでsetup.batを再実行してください。
    echo ================================================
    pause
    exit /b 0
)
echo Pythonを確認しました:
python --version

REM ffmpegの確認
echo.
echo [2/4] ffmpegを確認中...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo ffmpegが見つかりません。インストールを試みます...
    echo.

    winget --version >nul 2>&1
    if errorlevel 1 (
        echo [警告] wingetが見つかりません。
        echo 手動でffmpegをインストールしてください:
        echo https://ffmpeg.org/download.html
        echo.
    ) else (
        echo wingetでffmpegをインストール中...
        winget install Gyan.FFmpeg --accept-source-agreements --accept-package-agreements

        if errorlevel 1 (
            echo [警告] ffmpegのインストールに失敗しました。
            echo 手動でインストールしてください: https://ffmpeg.org/download.html
        ) else (
            echo ffmpegをインストールしました。
            echo ================================================
            echo 重要: 一度このウィンドウを閉じて、
            echo 新しいコマンドプロンプトでsetup.batを再実行してください。
            echo ================================================
            pause
            exit /b 0
        )
    )
) else (
    echo ffmpegを確認しました
)

REM pipのアップグレード
echo.
echo [3/4] pipをアップグレード中...
python -m pip install --upgrade pip

REM 依存パッケージのインストール
echo.
echo [4/4] 依存パッケージをインストール中...
echo （初回は5-10分かかることがあります）
echo.

pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [エラー] パッケージのインストールに失敗しました。
    pause
    exit /b 1
)

echo.
echo ================================================
echo  セットアップ完了！
echo  start.bat をダブルクリックしてアプリを起動してください
echo ================================================
pause
