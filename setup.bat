@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

REM スクリプトのディレクトリに移動
cd /d "%~dp0"

echo ================================================
echo  男性ボイスチェンジャー セットアップ (Windows)
echo ================================================
echo.
echo 現在のフォルダ: %CD%
echo.

REM requirements.txtの確認
if not exist "requirements.txt" (
    echo [エラー] requirements.txtが見つかりません。
    echo 正しいフォルダでsetup.batを実行してください。
    echo.
    echo 現在のフォルダ: %CD%
    echo.
    pause
    exit /b 1
)

echo ================================================
echo  ステップ 1/5: Pythonの確認
echo ================================================
echo.

python --version >nul 2>&1
if !ERRORLEVEL! neq 0 (
    echo Pythonが見つかりません。
    echo.

    REM wingetが利用可能か確認
    winget --version >nul 2>&1
    if !ERRORLEVEL! neq 0 (
        echo ================================================
        echo  Pythonを手動でインストールしてください
        echo ================================================
        echo.
        echo 1. https://www.python.org/downloads/ を開く
        echo 2. 「Download Python 3.xx」をクリック
        echo 3. インストール時に「Add Python to PATH」に必ずチェック！
        echo.
        pause
        exit /b 1
    )

    echo wingetでPythonをインストール中...
    echo （数分かかる場合があります）
    echo.
    winget install Python.Python.3.11 --accept-source-agreements --accept-package-agreements

    echo.
    echo ================================================
    echo  Pythonをインストールしました！
    echo ================================================
    echo.
    echo 重要: PATHを反映するため、以下の手順を実行してください：
    echo.
    echo   1. 何かキーを押してこのウィンドウを閉じる
    echo   2. setup.bat をもう一度ダブルクリック
    echo.
    echo ================================================
    pause
    exit /b 0
)

echo [OK] Pythonが見つかりました
python --version

echo.
echo ================================================
echo  ステップ 2/5: ffmpegの確認
echo ================================================
echo.

ffmpeg -version >nul 2>&1
if !ERRORLEVEL! neq 0 (
    echo ffmpegが見つかりません。

    winget --version >nul 2>&1
    if !ERRORLEVEL! neq 0 (
        echo [警告] wingetが見つかりません。ffmpegを手動でインストールしてください。
        echo https://ffmpeg.org/download.html
        echo.
    ) else (
        echo wingetでffmpegをインストール中...
        winget install Gyan.FFmpeg --accept-source-agreements --accept-package-agreements

        if !ERRORLEVEL! equ 0 (
            echo.
            echo ================================================
            echo  ffmpegをインストールしました！
            echo ================================================
            echo.
            echo 重要: PATHを反映するため、以下の手順を実行してください：
            echo.
            echo   1. 何かキーを押してこのウィンドウを閉じる
            echo   2. setup.bat をもう一度ダブルクリック
            echo.
            echo ================================================
            pause
            exit /b 0
        ) else (
            echo [警告] ffmpegのインストールに失敗しました。
            echo 手動でインストールしてください: https://ffmpeg.org/download.html
            echo.
        )
    )
) else (
    echo [OK] ffmpegが見つかりました
)

echo.
echo ================================================
echo  ステップ 3/5: Node.jsの確認
echo ================================================
echo.

set "NODE_INSTALLED=0"
node --version >nul 2>&1
if !ERRORLEVEL! neq 0 (
    echo Node.jsが見つかりません。

    winget --version >nul 2>&1
    if !ERRORLEVEL! neq 0 (
        echo [警告] wingetが見つかりません。Node.jsを手動でインストールしてください。
        echo https://nodejs.org/
        echo.
    ) else (
        echo wingetでNode.jsをインストール中...
        winget install OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements

        if !ERRORLEVEL! equ 0 (
            echo.
            echo ================================================
            echo  Node.jsをインストールしました！
            echo ================================================
            echo.
            echo 重要: PATHを反映するため、以下の手順を実行してください：
            echo.
            echo   1. 何かキーを押してこのウィンドウを閉じる
            echo   2. setup.bat をもう一度ダブルクリック
            echo.
            echo ================================================
            pause
            exit /b 0
        ) else (
            echo [警告] Node.jsのインストールに失敗しました。
            echo 手動でインストールしてください: https://nodejs.org/
            echo.
        )
    )
) else (
    echo [OK] Node.jsが見つかりました
    node --version
    set "NODE_INSTALLED=1"
)

echo.
echo ================================================
echo  ステップ 4/5: Pythonパッケージのインストール
echo ================================================
echo.

echo pipをアップグレード中...
python -m pip install --upgrade pip >nul 2>&1

echo 依存パッケージをインストール中...
echo （初回は10-20分かかる場合があります。お待ちください...）
echo.

pip install -r requirements.txt
if !ERRORLEVEL! neq 0 (
    echo.
    echo [エラー] パッケージのインストールに失敗しました。
    echo.
    echo 考えられる原因:
    echo   - インターネット接続を確認してください
    echo   - ウイルス対策ソフトが干渉している可能性があります
    echo   - 管理者権限で実行してみてください
    echo.
    pause
    exit /b 1
)

echo.
echo [OK] Pythonパッケージのインストール完了

echo.
echo ================================================
echo  ステップ 5/5: フロントエンドのビルド
echo ================================================
echo.

REM Node.jsを再確認（インストール直後の場合もあるため）
node --version >nul 2>&1
if !ERRORLEVEL! neq 0 (
    echo [スキップ] Node.jsがないためフロントエンドビルドをスキップ
    echo.
    echo [!] start.bat実行時に自動でビルドされます
    goto :setup_done
)

if not exist "frontend\package.json" (
    echo [警告] frontend/package.jsonが見つかりません
    goto :setup_done
)

echo フロントエンドをビルド中...
pushd frontend

echo npm install を実行中...
call npm install
if !ERRORLEVEL! neq 0 (
    echo [警告] npm installに失敗しました
    popd
    goto :setup_done
)

echo npm run build を実行中...
call npm run build
if !ERRORLEVEL! neq 0 (
    echo [警告] ビルドに失敗しました
    popd
    goto :setup_done
)

popd

if exist "static\index.html" (
    echo [OK] フロントエンドのビルド完了
) else (
    echo [警告] ビルドは完了しましたが、static/index.htmlが見つかりません
)

:setup_done

echo.
echo ================================================
echo.
echo   セットアップが完了しました！
echo.
echo ================================================
echo.
echo 次のステップ:
echo   start.bat をダブルクリックしてアプリを起動
echo.
echo アプリのURL: http://localhost:5003
echo.
echo ================================================
echo.
pause
