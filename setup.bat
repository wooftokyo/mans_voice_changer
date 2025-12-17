@echo off
chcp 65001 >nul

REM スクリプトのディレクトリに移動
cd /d "%~dp0"

echo ================================================
echo  男性ボイスチェンジャー セットアップ (Windows)
echo ================================================
echo.
echo 現在のフォルダ: %CD%
echo.
echo 機能:
echo   - AI声質判定（精度95-98%%）
echo   - 波形エディタで手動編集
echo   - プロジェクト履歴
echo.

REM Pythonの確認
echo [1/5] Pythonを確認中...
python --version >nul 2>&1
if errorlevel 1 (
    echo Pythonが見つかりません。インストールを試みます...
    echo.

    REM wingetが利用可能か確認
    winget --version >nul 2>&1
    if errorlevel 1 (
        echo [エラー] wingetが見つかりません。
        echo Pythonを手動でインストールしてください:
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
    echo ================================================
    echo  Pythonをインストールしました！
    echo ================================================
    echo.
    echo 次のステップ:
    echo   1. このウィンドウが閉じます
    echo   2. setup.bat をもう一度ダブルクリックしてください
    echo.
    echo ================================================
    pause
    exit /b 0
)
echo Pythonが見つかりました:
python --version

REM ffmpegの確認
echo.
echo [2/5] ffmpegを確認中...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo ffmpegが見つかりません。インストールを試みます...
    echo.

    winget --version >nul 2>&1
    if errorlevel 1 (
        echo [警告] wingetが見つかりません。
        echo ffmpegを手動でインストールしてください:
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
            echo.
            echo ================================================
            echo  ffmpegをインストールしました！
            echo ================================================
            echo.
            echo 次のステップ:
            echo   1. このウィンドウが閉じます
            echo   2. setup.bat をもう一度ダブルクリックしてください
            echo.
            echo ================================================
            pause
            exit /b 0
        )
    )
) else (
    echo ffmpegが見つかりました
)

REM Node.jsの確認
echo.
echo [3/5] Node.jsを確認中...
node --version >nul 2>&1
if errorlevel 1 (
    echo Node.jsが見つかりません。インストールを試みます...
    echo.

    winget --version >nul 2>&1
    if errorlevel 1 (
        echo [警告] wingetが見つかりません。
        echo Node.jsを手動でインストールしてください:
        echo https://nodejs.org/
        echo.
    ) else (
        echo wingetでNode.jsをインストール中...
        winget install OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements

        if errorlevel 1 (
            echo [警告] Node.jsのインストールに失敗しました。
            echo 手動でインストールしてください: https://nodejs.org/
        ) else (
            echo Node.jsをインストールしました。
            echo.
            echo ================================================
            echo  Node.jsをインストールしました！
            echo ================================================
            echo.
            echo 次のステップ:
            echo   1. このウィンドウが閉じます
            echo   2. setup.bat をもう一度ダブルクリックしてください
            echo.
            echo ================================================
            pause
            exit /b 0
        )
    )
) else (
    echo Node.jsが見つかりました:
    node --version
)

REM pipをアップグレード
echo.
echo [4/5] pipをアップグレード中...
python -m pip install --upgrade pip

REM Python依存パッケージをインストール
echo.
echo [5/5] 依存パッケージをインストール中...
echo （初回は5-10分かかる場合があります）
echo.

pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [エラー] パッケージのインストールに失敗しました。
    pause
    exit /b 1
)

REM Node.jsがあればフロントエンドをビルド
node --version >nul 2>&1
if not errorlevel 1 (
    echo.
    echo フロントエンドをビルド中...
    cd frontend
    call npm install
    call npm run build
    cd ..
)

echo.
echo ================================================
echo  セットアップ完了！
echo ================================================
echo.
echo start.batを実行してアプリケーションを起動してください
echo.
echo URL: http://localhost:5003
echo.
pause
