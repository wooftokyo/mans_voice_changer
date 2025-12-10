# mans_voice_changer

男性の声だけピッチを下げる動画処理アプリです。女性の声はオリジナルのまま保持されます。

## 必要条件

- Python 3.8以上
- FFmpeg（システムにインストールされている必要があります）

## インストール

```bash
pip install -r requirements.txt
```

FFmpegのインストール:
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
# https://ffmpeg.org/download.html からダウンロード
```

## 使い方

### GUI版（おすすめ）

```bash
python voice_changer_gui.py
```

ウィンドウが開くので、動画ファイルを選択して「処理開始」ボタンを押してください。

### コマンドライン版

基本的な使い方:
```bash
python voice_changer.py 入力動画.mp4
```

出力ファイル名を指定:
```bash
python voice_changer.py 入力動画.mp4 -o 出力動画.mp4
```

ピッチシフト量を変更（デフォルト: -3半音）:
```bash
python voice_changer.py 入力動画.mp4 -p -5
```

## オプション

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `-o, --output` | 出力ファイルのパス | `入力ファイル名_processed.拡張子` |
| `-p, --pitch` | ピッチシフト量（半音単位） | `-3.0` |
| `-s, --segment` | 解析セグメント長（秒） | `0.5` |

## 仕組み

1. 動画から音声を抽出
2. 音声を短いセグメントに分割
3. 各セグメントの基本周波数（ピッチ）を解析
4. ピッチが160Hz以下の場合は男性の声と判定してピッチを下げる
5. ピッチが160Hz以上の場合は女性の声としてオリジナルを維持
6. 処理した音声を元の動画と結合して出力