#!/bin/bash
echo "================================================"
echo " 男性ボイスチェンジャー 起動中..."
echo "================================================"
echo

# Pythonの確認
if ! command -v python3 &> /dev/null; then
    echo "[エラー] Python3が見つかりません。"
    echo "先に ./setup.sh を実行してください。"
    exit 1
fi

echo "ブラウザで http://localhost:5003 を開いてください"
echo "（自動で開かない場合は手動で開いてください）"
echo
echo "終了するには Ctrl+C を押してください"
echo "================================================"
echo

# 2秒後にブラウザを開く（バックグラウンド）
(sleep 2 && open http://localhost:5003 2>/dev/null || xdg-open http://localhost:5003 2>/dev/null) &

# サーバー起動
python3 voice_changer_web.py
