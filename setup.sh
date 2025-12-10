#!/bin/bash
echo "================================================"
echo " 男性ボイスチェンジャー セットアップ (Mac/Linux)"
echo "================================================"
echo

# OSの判定
if [[ "$OSTYPE" == "darwin"* ]]; then
    IS_MAC=true
else
    IS_MAC=false
fi

# Homebrewの確認（Macのみ）
if $IS_MAC; then
    echo "[1/4] Homebrewを確認中..."
    if ! command -v brew &> /dev/null; then
        echo "Homebrewが見つかりません。インストールを試みます..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

        # パスを通す
        if [[ -f /opt/homebrew/bin/brew ]]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        fi
    fi
    echo "Homebrewを確認しました"
fi

# Pythonの確認
echo
echo "[2/4] Pythonを確認中..."
if ! command -v python3 &> /dev/null; then
    echo "Python3が見つかりません。インストールを試みます..."

    if $IS_MAC; then
        brew install python3
    else
        echo "Linuxの場合は以下を実行してください:"
        echo "  sudo apt install python3 python3-pip"
        exit 1
    fi

    if [ $? -ne 0 ]; then
        echo "[エラー] Pythonのインストールに失敗しました。"
        exit 1
    fi
fi
echo "Pythonを確認しました:"
python3 --version

# ffmpegの確認
echo
echo "[3/4] ffmpegを確認中..."
if ! command -v ffmpeg &> /dev/null; then
    echo "ffmpegが見つかりません。インストールを試みます..."

    if $IS_MAC; then
        brew install ffmpeg
    else
        echo "Linuxの場合は以下を実行してください:"
        echo "  sudo apt install ffmpeg"
        exit 1
    fi

    if [ $? -ne 0 ]; then
        echo "[警告] ffmpegのインストールに失敗しました。"
        echo "手動でインストールしてください。"
    fi
else
    echo "ffmpegを確認しました"
fi

# 依存パッケージのインストール
echo
echo "[4/4] 依存パッケージをインストール中..."
echo "（初回は5-10分かかることがあります）"
echo

pip3 install --upgrade pip
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo
    echo "[エラー] パッケージのインストールに失敗しました。"
    exit 1
fi

echo
echo "================================================"
echo " セットアップ完了！"
echo " ./start.sh を実行してアプリを起動してください"
echo "================================================"
