# 男性ボイスチェンジャー

動画内の男性の声だけをピッチダウンするツールです。
会話動画で男性の声を低くしたい場合に使用します。

## 機能

- **ClearVoice AI話者分離**: AIが話者を自動分離し、男性のみピッチシフト
- **簡易ピッチ検出モード**: 軽量な処理で高速に変換
- **手動編集**: 波形を見ながら任意の区間をピッチシフト
- **音声解析**: ピッチ分布を分析して最適な閾値を推定

## 必要環境

- Python 3.10以上
- ffmpeg

## セットアップ

### Windows

1. [Python](https://www.python.org/downloads/) をインストール
   - インストール時に **「Add Python to PATH」にチェック**を入れる
2. [ffmpeg](https://ffmpeg.org/download.html) をインストール
   - または PowerShell で `winget install ffmpeg`
3. `setup.bat` をダブルクリック
4. `start.bat` をダブルクリックで起動

### Mac / Linux

```bash
# Macの場合、Homebrewで依存関係をインストール
brew install python3 ffmpeg

# セットアップ
./setup.sh

# 起動
./start.sh
```

## 使い方

1. `start.bat` (Windows) または `./start.sh` (Mac/Linux) で起動
2. ブラウザで http://localhost:5003 が自動で開く
3. 動画ファイルをドラッグ＆ドロップまたはクリックで選択
4. 処理モードを選択:
   - **ClearVoice AI**: 高精度だが処理時間が長い（動画の2-3倍の時間）
   - **簡易版**: 高速だが精度は低め
5. 「自動処理開始」をクリック
6. 完了したらダウンロード

## 処理モード

### ClearVoice AI（推奨）
- MossFormer2モデルによる話者分離
- 男性/女性を自動判別してピッチシフト
- 処理時間: 動画の2-3倍程度（CPU）

### 簡易版
- セグメントごとのピッチ検出
- 閾値より低いピッチを男性と判定
- 処理時間: 動画の0.5-1倍程度

## 設定項目

| 設定 | 説明 | デフォルト |
|------|------|-----------|
| ピッチシフト | 半音単位（-12〜0） | -3 |
| セグメント長 | 検出単位（簡易版のみ） | 0.5秒 |
| 男性判定閾値 | この周波数未満を男性と判定 | 165Hz |

## トラブルシューティング

### 「Python が見つかりません」
- Pythonをインストールし、PATHに追加してください
- Windows: インストーラーで「Add Python to PATH」にチェック

### 「ffmpeg が見つかりません」
- ffmpegをインストールしてください
- Windows: `winget install ffmpeg`
- Mac: `brew install ffmpeg`

### 処理が終わらない
- ClearVoice AIは処理に時間がかかります
- 5分の動画で10-15分程度かかることがあります
- CPU使用率が高い状態が続いていれば正常です

### ポートが使用中
- 他のアプリが5003ポートを使っている場合があります
- voice_changer_web.py の最後の行でポート番号を変更できます

## コマンドライン版

Web UIを使わずにコマンドラインでも実行できます：

```bash
# 基本的な使い方
python voice_changer.py 入力動画.mp4

# 出力ファイル名を指定
python voice_changer.py 入力動画.mp4 -o 出力動画.mp4

# ピッチシフト量を変更（デフォルト: -3半音）
python voice_changer.py 入力動画.mp4 -p -5
```

## ライセンス

MIT License
