# 男性ボイスチェンジャー

動画内の男性の声をAIで検出し、ピッチを下げて変換するツールです。

## 機能

### 自動処理
- **AI声質判定（推奨）**: CNN（inaSpeechSegmenter）による高精度な性別判定（精度95-98%）
- **簡易ピッチ検出**: 軽量・高速処理（精度70-80%）
- **ダブルチェック**: 追加検証による精度向上

### 波形エディタ（手動編集）
- **WaveSurfer.js**: プロ仕様の波形表示
- **タイムライン**: 時間軸でのナビゲーション
- **ズーム**: 細かい区間の精密編集
- **複数区間選択**: まとめて処理可能
- **ピッチ上げ/下げ**: 区間ごとに異なる設定
- **スクロール操作**:
  - Mac: 上下スワイプ = ズーム、左右スワイプ = スクロール
  - Windows: スクロールホイール = ズーム、Shift+スクロール = スクロール

### プロジェクト管理
- **履歴**: 処理したプロジェクトを自動保存（最大20件）
- **復元**: 過去の処理状態に戻る
- **ダウンロード**: MP4（動画）とWAV（音声）を別々にダウンロード

## 必要環境

- Python 3.10以上
- Node.js 18以上（フロントエンド開発用）
- ffmpeg

## クイックスタート

### 本番モード

```bash
# Python依存パッケージをインストール
pip install -r requirements.txt

# フロントエンドをビルド（初回または変更後）
cd frontend && npm install && npm run build && cd ..

# サーバーを起動
python voice_changer_web.py

# http://localhost:5003 を開く
```

### 開発モード

```bash
# ターミナル1: Flask APIを起動
python voice_changer_web.py

# ターミナル2: Vite開発サーバーを起動
cd frontend && npm run dev

# http://localhost:5173 を開く（ホットリロード対応）
```

### Windows（バッチファイル）

1. `setup.bat` - 初回セットアップ（5-10分）
2. `start.bat` - サーバーを起動
3. ブラウザが自動で http://localhost:5003 を開きます

### Mac / Linux

```bash
# 依存パッケージをインストール
brew install python3 ffmpeg

# Pythonパッケージをインストール
pip3 install -r requirements.txt

# フロントエンドをビルド
cd frontend && npm install && npm run build && cd ..

# サーバーを起動
python3 voice_changer_web.py
```

## アーキテクチャ

```
mans_voice_changer/
├── frontend/           # React SPA (Vite + shadcn/ui)
│   ├── src/
│   │   ├── features/   # 機能モジュール
│   │   ├── components/ # UIコンポーネント
│   │   └── lib/        # ユーティリティ & APIクライアント
│   └── package.json
├── static/             # ビルド済みフロントエンド（自動生成）
├── voice_changer_web.py # Flask APIサーバー
├── voice_changer.py    # 音声処理ロジック
└── requirements.txt
```

## APIエンドポイント

| エンドポイント | メソッド | 説明 |
|---------------|---------|------|
| `/upload` | POST | 動画をアップロードして処理 |
| `/upload_for_editor` | POST | 手動編集用にアップロード |
| `/status/<task_id>` | GET | 処理状況を取得 |
| `/apply_manual_pitch` | POST | 選択区間にピッチを適用 |
| `/download/<task_id>` | GET | 処理済みファイルをダウンロード |
| `/audio/<task_id>` | GET | 波形表示用の音声を取得 |

## 処理モード

### AI声質判定（推奨）
- inaSpeechSegmenter（CNN）による話者の性別判定
- 男性/女性の声を自動識別
- ダブルチェックオプションで精度向上
- 処理時間: 動画の長さの1-2倍

### 簡易モード
- セグメント単位のピッチ検出
- 閾値以下のピッチを男性の声と判定
- 処理時間: 動画の長さの0.5-1倍

## 設定

| 設定 | 説明 | デフォルト |
|-----|------|-----------|
| ピッチシフト | 半音単位（-12〜+12） | -3 |
| セグメント長 | 検出単位（簡易モード） | 0.5秒 |
| 男性判定閾値 | この周波数以下を男性と判定 | 165Hz |

## キーボードショートカット（波形エディタ）

| キー | 機能 |
|-----|------|
| Space | 再生/停止 |
| ← | 5秒戻る |
| → | 5秒進む |
| M | モード切り替え（選択/移動） |
| Delete/Backspace | 選択した区間を削除 |

## トラブルシューティング

### 「Pythonが見つかりません」
- Pythonをインストールし、PATHに追加してください
- Windows: インストール時に「Add Python to PATH」にチェック

### 「ffmpegが見つかりません」
- Windows: `winget install ffmpeg`
- Mac: `brew install ffmpeg`

### 処理に時間がかかる
- AI検出は時間がかかります（5分の動画で5-10分）
- 処理中のCPU使用率が高いのは正常です

### ポートが使用中
- 別のアプリがポート5003を使用しています
- voice_changer_web.pyでポート番号を変更してください

## コマンドライン

```bash
# 基本的な使い方
python voice_changer.py input.mp4

# 出力先を指定
python voice_changer.py input.mp4 -o output.mp4

# ピッチシフトを変更（デフォルト: -3半音）
python voice_changer.py input.mp4 -p -5
```

## ライセンス

MIT License
