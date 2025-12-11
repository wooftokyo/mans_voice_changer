#!/usr/bin/env python3
"""
男性の声だけピッチを下げる動画処理アプリ - Web GUI版（編集機能付き）
"""

import os
import sys
import threading
import uuid
import traceback
import json
from pathlib import Path
from datetime import datetime

from flask import Flask, render_template_string, request, jsonify, send_file, send_from_directory
from werkzeug.utils import secure_filename

from voice_changer import process_video, analyze_pitch_distribution, pitch_shift_region

app = Flask(__name__)

# アップロード設定
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv', 'webm', 'm4v', 'flv', 'wmv'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# アップロードサイズ無制限

# 処理状態を保持
processing_status = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <title>男性ボイスチェンジャー v3</title>
    <script src="https://unpkg.com/wavesurfer.js@7"></script>
    <script src="https://unpkg.com/wavesurfer.js@7/dist/plugins/regions.min.js"></script>
    <script src="https://unpkg.com/wavesurfer.js@7/dist/plugins/timeline.min.js"></script>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 30px;
            max-width: 1200px;
            margin: 0 auto;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }
        h1 {
            text-align: center;
            color: #1a1a2e;
            margin-bottom: 10px;
            font-size: 1.8em;
        }
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 20px;
            font-size: 0.95em;
        }
        .tabs {
            display: flex;
            border-bottom: 2px solid #e0e0e0;
            margin-bottom: 20px;
        }
        .tab {
            padding: 12px 24px;
            cursor: pointer;
            border: none;
            background: none;
            font-size: 1em;
            color: #666;
            border-bottom: 3px solid transparent;
            margin-bottom: -2px;
            transition: all 0.3s;
        }
        .tab:hover {
            color: #4a90d9;
        }
        .tab.active {
            color: #4a90d9;
            border-bottom-color: #4a90d9;
            font-weight: bold;
        }
        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }
        .upload-area {
            border: 3px dashed #4a90d9;
            border-radius: 15px;
            padding: 40px 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-bottom: 20px;
            background: #f8faff;
        }
        .upload-area:hover {
            border-color: #357abd;
            background: #eef5ff;
        }
        .upload-area.dragover {
            border-color: #28a745;
            background: #e8f5e9;
        }
        .upload-area.has-file {
            border-color: #28a745;
            background: #e8f5e9;
        }
        .upload-icon {
            font-size: 48px;
            margin-bottom: 15px;
        }
        .upload-text {
            color: #666;
            font-size: 1em;
            margin-bottom: 10px;
        }
        .upload-hint {
            color: #999;
            font-size: 0.85em;
        }
        .file-info {
            background: #f0f7ff;
            border: 1px solid #d0e3ff;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 20px;
            display: none;
        }
        .file-info.show {
            display: block;
        }
        .file-name {
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
        }
        .file-size {
            color: #666;
            font-size: 0.9em;
        }
        .settings {
            margin-bottom: 20px;
        }
        .setting-group {
            margin-bottom: 15px;
        }
        .setting-label {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            color: #333;
            font-weight: 500;
        }
        .setting-value {
            color: #4a90d9;
            font-weight: bold;
        }
        input[type="range"] {
            width: 100%;
            height: 8px;
            border-radius: 4px;
            background: #e0e0e0;
            outline: none;
            -webkit-appearance: none;
        }
        input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 22px;
            height: 22px;
            border-radius: 50%;
            background: #4a90d9;
            cursor: pointer;
            box-shadow: 0 2px 6px rgba(74, 144, 217, 0.4);
        }
        .btn {
            padding: 12px 24px;
            font-size: 1em;
            font-weight: bold;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-right: 10px;
            margin-bottom: 10px;
        }
        .btn-full {
            width: 100%;
            margin-right: 0;
        }
        .btn-primary {
            background: linear-gradient(135deg, #4a90d9 0%, #357abd 100%);
            color: white;
        }
        .btn-primary:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(74, 144, 217, 0.4);
        }
        .btn-primary:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .btn-success {
            background: linear-gradient(135deg, #28a745 0%, #218838 100%);
            color: white;
        }
        .btn-danger {
            background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
            color: white;
        }
        .btn-secondary {
            background: #6c757d;
            color: white;
        }
        /* 話者カード */
        .speaker-card {
            border: 2px solid #e0e0e0;
            border-radius: 12px;
            padding: 15px;
            width: 200px;
            background: #fafafa;
            transition: all 0.3s;
            cursor: pointer;
        }
        .speaker-card:hover {
            border-color: #4a90d9;
            background: #f0f7ff;
        }
        .speaker-card.selected {
            border-color: #28a745;
            background: #e8f5e9;
        }
        .speaker-card .speaker-title {
            font-weight: bold;
            font-size: 1.1em;
            margin-bottom: 8px;
        }
        .speaker-card .speaker-pitch {
            color: #666;
            font-size: 0.9em;
            margin-bottom: 10px;
        }
        .speaker-card audio {
            width: 100%;
        }
        .speaker-card .select-label {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-top: 10px;
            font-size: 0.9em;
        }
        .speaker-card .select-label input[type="checkbox"] {
            width: 18px;
            height: 18px;
        }
        .progress-container {
            margin-top: 20px;
            display: none;
        }
        .progress-bar {
            height: 10px;
            background: #e0e0e0;
            border-radius: 5px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #4a90d9, #357abd);
            width: 0%;
            transition: width 0.3s ease;
        }
        .status-text {
            text-align: center;
            margin-top: 10px;
            color: #666;
            font-size: 0.9em;
        }
        .error {
            background: #fee;
            color: #c00;
            padding: 15px;
            border-radius: 10px;
            margin-top: 20px;
            white-space: pre-wrap;
            font-family: monospace;
            font-size: 0.85em;
            max-height: 150px;
            overflow-y: auto;
        }
        .success {
            background: #efe;
            color: #080;
            padding: 15px;
            border-radius: 10px;
            margin-top: 20px;
            text-align: center;
        }
        .log-container {
            margin-top: 20px;
            display: none;
        }
        .log-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .log-header h3 {
            color: #333;
            font-size: 1em;
        }
        .log-toggle {
            background: none;
            border: 1px solid #ddd;
            padding: 5px 10px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 0.85em;
        }
        .log-box {
            background: #1a1a2e;
            color: #0f0;
            padding: 15px;
            border-radius: 10px;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 0.75em;
            height: 150px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-break: break-all;
        }
        .log-box .log-error { color: #f66; }
        .log-box .log-warn { color: #ff0; }
        .log-box .log-info { color: #6cf; }
        .log-box .log-time { color: #888; }
        input[type="file"] { display: none; }
        .upload-progress {
            margin-top: 15px;
            display: none;
        }
        .upload-progress.show { display: block; }

        /* Editor styles */
        .editor-container {
            display: none;
            margin-top: 20px;
        }
        .editor-container.show {
            display: block;
        }
        .video-preview {
            width: 100%;
            max-height: 300px;
            background: #000;
            border-radius: 10px;
            margin-bottom: 15px;
        }
        .waveform-container {
            background: #1a1a2e;
            border-radius: 10px;
            padding: 10px;
            margin-bottom: 15px;
        }
        #waveform {
            width: 100%;
            height: 128px;
        }
        .editor-controls {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 15px;
            align-items: center;
        }
        .time-display {
            background: #f0f0f0;
            padding: 8px 15px;
            border-radius: 8px;
            font-family: monospace;
            font-size: 0.9em;
        }
        .regions-list {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
            max-height: 200px;
            overflow-y: auto;
        }
        .regions-list h4 {
            margin-bottom: 10px;
            color: #333;
        }
        .region-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 12px;
            background: white;
            border-radius: 8px;
            margin-bottom: 8px;
            border-left: 4px solid #4a90d9;
        }
        .region-info {
            font-size: 0.9em;
        }
        .region-time {
            color: #666;
            font-family: monospace;
        }
        .region-actions {
            display: flex;
            gap: 5px;
        }
        .region-btn {
            padding: 4px 8px;
            font-size: 0.8em;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        .region-btn-play {
            background: #4a90d9;
            color: white;
        }
        .region-btn-delete {
            background: #dc3545;
            color: white;
        }
        .help-text {
            background: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 15px;
            font-size: 0.9em;
            color: #856404;
        }
        .analysis-result {
            display: none;
            background: #e8f4fd;
            border: 1px solid #b8daff;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
        }
        .analysis-result.show {
            display: block;
        }
        .analysis-result h4 {
            margin: 0 0 10px 0;
            color: #004085;
        }
        .analysis-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 10px;
            margin-bottom: 15px;
        }
        .stat-box {
            background: white;
            padding: 10px;
            border-radius: 8px;
            text-align: center;
        }
        .stat-label {
            font-size: 0.8em;
            color: #666;
        }
        .stat-value {
            font-size: 1.2em;
            font-weight: bold;
            color: #333;
        }
        .stat-value.male { color: #2196F3; }
        .stat-value.female { color: #E91E63; }
        .stat-desc {
            font-size: 0.7em;
            color: #999;
            margin-top: 2px;
        }
        .suggested-threshold {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            border-radius: 8px;
            padding: 12px;
            text-align: center;
        }
        .suggested-threshold strong {
            color: #155724;
            font-size: 1.1em;
        }
        .apply-suggestion {
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <h1 style="margin: 0;">男性ボイスチェンジャー</h1>
            <div style="display: flex; gap: 10px;">
                <a href="/editor" style="padding: 8px 16px; background: #6c757d; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; text-decoration: none;">波形エディタ</a>
                <button id="clearProgressBtn" style="padding: 8px 16px; background: #dc3545; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold;">進捗クリア</button>
            </div>
        </div>
        <p class="subtitle">男性の声だけピッチを下げます。自動処理後に手動で編集も可能。</p>

        <!-- 作成したプロジェクト -->
        <div id="projectHistory" style="margin-bottom: 20px; display: none;">
            <h3 style="margin: 0 0 10px 0; font-size: 1.1em; color: #333;">📂 作成したプロジェクト</h3>
            <div id="projectList" style="display: flex; flex-wrap: wrap; gap: 10px; max-height: 200px; overflow-y: auto; padding: 10px; background: #f8f9fa; border-radius: 8px;"></div>
        </div>

        <div class="main-content">
            <div class="upload-area" id="uploadArea">
                <div class="upload-icon">📁</div>
                <div class="upload-text">ここをクリックまたはファイルをドロップ</div>
                <div class="upload-hint">対応形式: MP4, MOV, AVI, MKV, WebM</div>
            </div>
            <input type="file" id="fileInput" accept=".mp4,.mov,.avi,.mkv,.webm,.m4v,.flv,.wmv">

            <div class="file-info" id="fileInfo">
                <div class="file-name" id="fileName"></div>
                <div class="file-size" id="fileSize"></div>
            </div>

            <div class="upload-progress" id="uploadProgress">
                <div class="progress-bar">
                    <div class="progress-fill" id="uploadProgressFill"></div>
                </div>
                <div class="status-text" id="uploadStatusText">アップロード中...</div>
            </div>

            <div class="settings">
                <div class="setting-group">
                    <div class="setting-label">
                        <span>処理モード</span>
                    </div>
                    <div style="display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 10px;">
                        <label class="mode-option" id="modeSimpleLabel" style="display: flex; align-items: center; cursor: pointer; padding: 10px 15px; border-radius: 8px; background: #f8f9fa; border: 2px solid #ddd; flex: 1; min-width: 200px;">
                            <input type="radio" name="mode" id="modeSimple" value="simple" style="margin-right: 8px;">
                            <span><strong>簡易版（高速）</strong><br><small style="color: #666;">精度: 約70-80%</small></span>
                        </label>
                        <label class="mode-option selected" id="modeTimbreLabel" style="display: flex; align-items: center; cursor: pointer; padding: 10px 15px; border-radius: 8px; background: #e8f4fd; border: 2px solid #4a90d9; flex: 1; min-width: 200px;">
                            <input type="radio" name="mode" id="modeTimbre" value="timbre" checked style="margin-right: 8px;">
                            <span><strong>AI声質判定（推奨）</strong><br><small style="color: #666;">精度: 約95-98%</small></span>
                        </label>
                    </div>
                    <div id="modeDescription" style="background: #f8f9fa; border-radius: 8px; padding: 12px; margin-top: 10px; font-size: 0.85em; color: #555;">
                        <div id="modeDescSimple" style="display: none;">
                            <strong>簡易版の仕組み:</strong><br>
                            音声を短い区間（0.5秒など）に分割し、各区間の<strong>ピッチ（声の高さ/Hz）</strong>を測定。<br>
                            閾値（例: 165Hz）より低ければ男性、高ければ女性と判定。<br><br>
                            <span style="color: #28a745;">✓ 長所:</span> 処理が非常に高速（数秒〜数十秒）<br>
                            <span style="color: #dc3545;">✗ 短所:</span> 高い声の男性や低い声の女性を誤判定しやすい
                        </div>
                        <div id="modeDescTimbre">
                            <strong>AI声質判定の仕組み:</strong><br>
                            <strong>inaSpeechSegmenter</strong>（フランス国立視聴覚研究所開発のCNN）で声質から性別を判定。<br>
                            声の高さだけでなく、声道の形状・声の響き・話し方のパターンなどを総合的に分析。<br><br>
                            <strong>さらに精度向上のため:</strong><br>
                            1. <strong>後処理:</strong> 短い孤立判定（0.3秒未満）を周囲に統合してノイズ除去<br>
                            2. <strong>ダブルチェック:</strong> CNNが「男性」と判定した区間を音響特徴（スペクトル重心・ピッチ）で再確認<br><br>
                            <span style="color: #28a745;">✓ 長所:</span> 高い声の男性も正しく判定、女性の誤判定が少ない<br>
                            <span style="color: #dc3545;">✗ 短所:</span> 初回起動時にAIモデル読込で時間がかかる（2回目以降は高速）
                        </div>
                    </div>
                </div>
                <div class="setting-group">
                    <div class="setting-label">
                        <span>ピッチシフト（半音）</span>
                        <span class="setting-value" id="pitchValue">-3.0</span>
                    </div>
                    <input type="range" id="pitchSlider" min="-12" max="0" step="0.5" value="-3">
                    <div style="display: flex; justify-content: space-between; font-size: 0.8em; color: #888; margin-top: 5px;">
                        <span>-12 (とても低く)</span>
                        <span>0 (変更なし)</span>
                    </div>
                </div>
                <div class="setting-group" id="segmentGroup" style="display: none;">
                    <div class="setting-label">
                        <span>セグメント長（秒）<small style="color: #888;">（簡易版のみ）</small></span>
                        <span class="setting-value" id="segmentValue">0.5</span>
                    </div>
                    <input type="range" id="segmentSlider" min="0.2" max="2.0" step="0.1" value="0.5">
                    <div style="display: flex; justify-content: space-between; font-size: 0.8em; color: #888; margin-top: 5px;">
                        <span>0.2 (細かく)</span>
                        <span>2.0 (粗く)</span>
                    </div>
                </div>
                <div class="setting-group" id="adaptiveGroup" style="display: none;">
                    <div class="setting-label">
                        <span>動的閾値調整（秒）<small style="color: #888;">（簡易版のみ）</small></span>
                        <span class="setting-value" id="adaptiveValue">300</span>
                    </div>
                    <input type="range" id="adaptiveSlider" min="0" max="600" step="60" value="300">
                    <div style="display: flex; justify-content: space-between; font-size: 0.8em; color: #888; margin-top: 5px;">
                        <span>0 (固定)</span>
                        <span>5分ごと</span>
                        <span>10分ごと</span>
                    </div>
                    <div style="font-size: 0.75em; color: #666; margin-top: 5px;">
                        ※区間ごとにピッチ分布を解析して閾値を自動調整
                    </div>
                </div>
                <div class="setting-group" id="thresholdGroup" style="display: none;">
                    <div class="setting-label">
                        <span>男性判定閾値（Hz）<small style="color: #888;">（簡易版のみ）</small></span>
                        <span class="setting-value" id="thresholdValue">165</span>
                    </div>
                    <input type="range" id="thresholdSlider" min="120" max="200" step="5" value="165">
                    <div style="display: flex; justify-content: space-between; font-size: 0.8em; color: #888; margin-top: 5px;">
                        <span>120 (厳しく)</span>
                        <span>200 (緩く)</span>
                    </div>
                </div>
            </div>

            <div id="simpleAnalyzeArea" style="display: none; margin-bottom: 10px;">
                <button class="btn btn-secondary" id="analyzeBtn" disabled style="width: 100%;">音声を解析して閾値を推定</button>
                <div id="analysisResult" class="analysis-result"></div>
            </div>
            <button class="btn btn-primary btn-full" id="processBtn" disabled>処理開始</button>

            <div class="progress-container" id="progressContainer">
                <div class="progress-bar">
                    <div class="progress-fill" id="progressFill"></div>
                </div>
                <div class="status-text" id="statusText">処理中...</div>
            </div>

            <div class="log-container" id="logContainer">
                <div class="log-header">
                    <h3>処理ログ</h3>
                    <button class="log-toggle" id="logToggle">非表示</button>
                </div>
                <div class="log-box" id="logBox"></div>
            </div>

            <div id="resultArea"></div>

            <!-- 手動編集セクション -->
            <div id="editorSection" style="display: none; margin-top: 20px; padding-top: 20px; border-top: 2px solid #e0e0e0;">
                <h3 style="margin-bottom: 10px; color: #333;">手動編集</h3>
                <p style="color: #666; margin-bottom: 15px; font-size: 0.9em;">
                    AIが間違えた部分を波形上でドラッグ選択し、ピッチを再適用できます。ズームスライダーで波形を拡大できます。
                </p>

                <!-- 動画プレビュー -->
                <video id="editorVideo" controls style="width: 100%; border-radius: 8px; background: #000;"></video>

                <!-- タイムライン表示エリア -->
                <div id="timeline" style="margin-top: 15px;"></div>

                <!-- 波形表示エリア -->
                <div id="waveform" style="background: #1a1a2e; border-radius: 8px; padding: 10px; overflow-x: auto;"></div>

                <!-- ズームコントロール -->
                <div style="margin-top: 15px; display: flex; gap: 15px; align-items: center; background: #f8f9fa; padding: 10px; border-radius: 8px;">
                    <label for="zoomSlider" style="font-size: 0.9em; font-weight: bold;">ズーム:</label>
                    <input type="range" id="zoomSlider" min="10" max="1000" value="10" style="flex: 1;">
                    <span id="zoomValue" style="font-size: 0.85em; color: #666; min-width: 50px;">10x</span>
                </div>

                <!-- 選択区間リスト -->
                <div id="regionsListContainer" style="margin-top: 15px; display: none;">
                    <h4 style="margin-bottom: 10px; color: #333;">選択区間</h4>
                    <div id="regionsList" style="max-height: 150px; overflow-y: auto;"></div>
                </div>

                <!-- 編集コントロール -->
                <div style="margin-top: 15px; display: flex; flex-wrap: wrap; gap: 15px; align-items: flex-end;">
                    <div style="flex: 1; min-width: 200px;">
                        <div class="setting-label">
                            <span>ピッチシフト（半音）</span>
                            <span class="setting-value" id="editorPitchValue">-3.0</span>
                        </div>
                        <input type="range" id="editorPitchSlider" min="-12" max="12" step="0.5" value="-3">
                    </div>
                    <button id="applyManualBtn" class="btn btn-primary" disabled>選択区間にピッチ適用</button>
                    <button id="clearRegionsBtn" class="btn btn-secondary">区間クリア</button>
                </div>

                <!-- 手動編集結果 -->
                <div id="manualResultArea" style="margin-top: 15px;"></div>
            </div>
        </div>
    </div>

    <script>
        // ==================== メイン処理 ====================
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const fileInfo = document.getElementById('fileInfo');
        const fileName = document.getElementById('fileName');
        const fileSize = document.getElementById('fileSize');
        const processBtn = document.getElementById('processBtn');
        const pitchSlider = document.getElementById('pitchSlider');
        const pitchValue = document.getElementById('pitchValue');
        const progressContainer = document.getElementById('progressContainer');
        const progressFill = document.getElementById('progressFill');
        const statusText = document.getElementById('statusText');
        const resultArea = document.getElementById('resultArea');
        const logContainer = document.getElementById('logContainer');
        const logBox = document.getElementById('logBox');
        const logToggle = document.getElementById('logToggle');
        const uploadProgress = document.getElementById('uploadProgress');
        const uploadProgressFill = document.getElementById('uploadProgressFill');
        const uploadStatusText = document.getElementById('uploadStatusText');
        const projectHistory = document.getElementById('projectHistory');
        const projectList = document.getElementById('projectList');

        let selectedFile = null;
        let logVisible = true;

        // ==================== プロジェクト履歴 ====================
        function getProjects() {
            try {
                return JSON.parse(localStorage.getItem('voiceChangerProjects') || '[]');
            } catch { return []; }
        }

        function saveProject(taskId, filename, timestamp) {
            const projects = getProjects();
            // 重複チェック
            if (projects.find(p => p.taskId === taskId)) return;
            projects.unshift({ taskId, filename, timestamp, date: new Date().toLocaleString('ja-JP') });
            // 最大20件保持
            if (projects.length > 20) projects.pop();
            localStorage.setItem('voiceChangerProjects', JSON.stringify(projects));
            renderProjects();
        }

        function removeProject(taskId) {
            const projects = getProjects().filter(p => p.taskId !== taskId);
            localStorage.setItem('voiceChangerProjects', JSON.stringify(projects));
            renderProjects();
        }

        function renderProjects() {
            const projects = getProjects();
            if (projects.length === 0) {
                projectHistory.style.display = 'none';
                return;
            }
            projectHistory.style.display = 'block';
            projectList.innerHTML = projects.map(p => `
                <div style="background: white; border: 1px solid #ddd; border-radius: 8px; padding: 10px; min-width: 200px; flex: 1; max-width: 300px;">
                    <div style="font-weight: bold; font-size: 0.9em; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${p.filename}">${p.filename}</div>
                    <div style="font-size: 0.8em; color: #666; margin: 4px 0;">${p.date}</div>
                    <div style="display: flex; gap: 5px; margin-top: 8px;">
                        <a href="/editor?task_id=${p.taskId}" style="flex: 1; padding: 4px 8px; background: #4a90d9; color: white; border-radius: 4px; text-decoration: none; text-align: center; font-size: 0.85em;">編集</a>
                        <a href="/download/${p.taskId}?format=video" style="flex: 1; padding: 4px 8px; background: #28a745; color: white; border-radius: 4px; text-decoration: none; text-align: center; font-size: 0.85em;">DL</a>
                        <button onclick="removeProject('${p.taskId}')" style="padding: 4px 8px; background: #dc3545; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.85em;">×</button>
                    </div>
                </div>
            `).join('');
        }

        // ページ読み込み時にプロジェクト履歴を表示
        renderProjects();

        function formatFileSize(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        function formatTime(seconds) {
            const mins = Math.floor(seconds / 60);
            const secs = (seconds % 60).toFixed(2);
            return `${mins.toString().padStart(2, '0')}:${secs.padStart(5, '0')}`;
        }

        uploadArea.addEventListener('click', () => fileInput.click());
        uploadArea.addEventListener('dragover', (e) => { e.preventDefault(); uploadArea.classList.add('dragover'); });
        uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('dragover'));
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) handleFile(e.dataTransfer.files[0]);
        });
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) handleFile(e.target.files[0]);
        });

        const analyzeBtn = document.getElementById('analyzeBtn');
        const analysisResult = document.getElementById('analysisResult');

        function handleFile(file) {
            const ext = file.name.split('.').pop().toLowerCase();
            const allowedExts = ['mp4', 'mov', 'avi', 'mkv', 'webm', 'm4v', 'flv', 'wmv'];
            if (!allowedExts.includes(ext)) {
                alert('対応していないファイル形式です');
                return;
            }
            selectedFile = file;
            fileName.textContent = file.name;
            fileSize.textContent = formatFileSize(file.size);
            fileInfo.classList.add('show');
            uploadArea.classList.add('has-file');
            processBtn.disabled = false;
            analyzeBtn.disabled = false;
            analysisResult.classList.remove('show');
        }

        analyzeBtn.addEventListener('click', async () => {
            if (!selectedFile) return;

            analyzeBtn.disabled = true;
            analyzeBtn.textContent = '解析中...';
            analysisResult.classList.remove('show');
            logContainer.style.display = 'block';
            logBox.innerHTML = '';

            addLog('ファイルをアップロード中...');

            const formData = new FormData();
            formData.append('file', selectedFile);

            try {
                const response = await fetch('/analyze', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (data.error) {
                    addLog('解析エラー: ' + data.error, 'error');
                    analyzeBtn.disabled = false;
                    analyzeBtn.textContent = '音声を解析して閾値を推定';
                    return;
                }

                addLog('アップロード完了、解析開始...');

                // ポーリングで解析状況を監視
                await pollAnalyzeStatus(data.task_id);

            } catch (error) {
                addLog('解析エラー: ' + error.message, 'error');
                analyzeBtn.disabled = false;
                analyzeBtn.textContent = '音声を解析して閾値を推定';
            }
        });

        async function pollAnalyzeStatus(taskId) {
            const poll = async () => {
                const response = await fetch(`/status/${taskId}`);
                const data = await response.json();

                // ログを更新
                if (data.logs) {
                    const currentCount = logBox.querySelectorAll('span.log-info, span.log-error, span.log-warn').length;
                    for (let i = currentCount; i < data.logs.length; i++) {
                        addLog(data.logs[i].message, data.logs[i].type || 'info');
                    }
                }

                if (data.status === 'analyzing') {
                    setTimeout(poll, 500);
                } else if (data.status === 'complete' && data.result) {
                    // 解析結果を表示
                    const result = data.result;
                    const stats = result.stats;
                    const maleCount = result.male_pitches.length;
                    const femaleCount = result.female_pitches.length;
                    const totalCount = maleCount + femaleCount;

                    analysisResult.innerHTML = `
                        <h4>音声解析結果</h4>
                        <div class="analysis-stats">
                            <div class="stat-box">
                                <div class="stat-label">検出セグメント数</div>
                                <div class="stat-value">${totalCount}</div>
                                <div class="stat-desc">0.3秒ごとの音声区間</div>
                            </div>
                            <div class="stat-box">
                                <div class="stat-label">男性の声と推定</div>
                                <div class="stat-value male">${maleCount}</div>
                                <div class="stat-desc">ピッチダウン対象</div>
                            </div>
                            <div class="stat-box">
                                <div class="stat-label">女性の声と推定</div>
                                <div class="stat-value female">${femaleCount}</div>
                                <div class="stat-desc">そのまま維持</div>
                            </div>
                            <div class="stat-box">
                                <div class="stat-label">最低ピッチ</div>
                                <div class="stat-value">${stats ? stats.min.toFixed(0) : '-'}Hz</div>
                            </div>
                            <div class="stat-box">
                                <div class="stat-label">最高ピッチ</div>
                                <div class="stat-value">${stats ? stats.max.toFixed(0) : '-'}Hz</div>
                            </div>
                            <div class="stat-box">
                                <div class="stat-label">中央値</div>
                                <div class="stat-value">${stats ? stats.median.toFixed(0) : '-'}Hz</div>
                            </div>
                        </div>
                        <div class="suggested-threshold">
                            <strong>推奨閾値: ${result.suggested_threshold}Hz</strong>
                            <div class="apply-suggestion">
                                <button class="btn btn-success" onclick="applySuggestedThreshold(${result.suggested_threshold})">
                                    この閾値を適用
                                </button>
                            </div>
                        </div>
                        ${result.suggested_segment ? `
                        <div class="suggested-threshold" style="margin-top: 10px;" id="suggestedSegmentArea">
                            <strong>推奨セグメント長: ${result.suggested_segment}秒</strong>
                            <small style="color: #666;">（発話パターンから算出）</small>
                            <div class="apply-suggestion">
                                <button class="btn btn-success" onclick="applySuggestedSegment(${result.suggested_segment})">
                                    このセグメント長を適用
                                </button>
                            </div>
                        </div>
                        ` : ''}
                    `;
                    analysisResult.classList.add('show');
                    // 簡易版モードでない場合はセグメント推奨を非表示
                    const segArea = document.getElementById('suggestedSegmentArea');
                    if (segArea && !document.getElementById('modeSimple').checked) {
                        segArea.style.display = 'none';
                    }
                    analyzeBtn.disabled = false;
                    analyzeBtn.textContent = '音声を解析して閾値を推定';
                } else if (data.status === 'error') {
                    addLog('エラー: ' + data.message, 'error');
                    analyzeBtn.disabled = false;
                    analyzeBtn.textContent = '音声を解析して閾値を推定';
                }
            };
            await poll();
        }

        window.applySuggestedThreshold = (value) => {
            thresholdSlider.value = value;
            thresholdValue.textContent = value;
        };

        window.applySuggestedSegment = (value) => {
            segmentSlider.value = value;
            segmentValue.textContent = value;
            // 簡易版モードに切り替え
            document.getElementById('modeSimple').checked = true;
            updateModeVisibility();
        };

        logToggle.addEventListener('click', () => {
            logVisible = !logVisible;
            logBox.style.display = logVisible ? 'block' : 'none';
            logToggle.textContent = logVisible ? '非表示' : '表示';
        });

        function addLog(message, type = 'info') {
            const time = new Date().toLocaleTimeString('ja-JP');
            const typeClass = type === 'error' ? 'log-error' : type === 'warn' ? 'log-warn' : 'log-info';
            logBox.innerHTML += `<span class="log-time">[${time}]</span> <span class="${typeClass}">${escapeHtml(message)}</span>\\n`;
            logBox.scrollTop = logBox.scrollHeight;
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // 次の動画を処理するために進捗をクリア（ログは保持）
        window.resetForNextVideo = function() {
            // ファイル選択をリセット
            selectedFile = null;
            fileInput.value = '';
            fileInfo.classList.remove('show');
            uploadArea.classList.remove('has-file');

            // 進捗をリセット
            progressContainer.style.display = 'none';
            progressFill.style.width = '0%';
            statusText.textContent = '';

            // 結果エリアをクリア
            resultArea.innerHTML = '';

            // 手動編集セクションを非表示
            editorSection.style.display = 'none';

            // ボタン状態をリセット
            processBtn.disabled = true;
            analyzeBtn.disabled = true;

            // 解析結果をクリア
            analysisResult.classList.remove('show');

            // ログに区切りを追加
            addLog('--- 次の動画を処理 ---', 'info');

            // ページ上部にスクロール
            window.scrollTo({ top: 0, behavior: 'smooth' });
        };

        // 進捗クリアボタンのイベント
        document.getElementById('clearProgressBtn').addEventListener('click', function() {
            window.resetForNextVideo();
        });

        const segmentSlider = document.getElementById('segmentSlider');
        const segmentValue = document.getElementById('segmentValue');
        const thresholdSlider = document.getElementById('thresholdSlider');
        const thresholdValue = document.getElementById('thresholdValue');
        const adaptiveSlider = document.getElementById('adaptiveSlider');
        const adaptiveValue = document.getElementById('adaptiveValue');

        pitchSlider.addEventListener('input', () => pitchValue.textContent = pitchSlider.value);
        segmentSlider.addEventListener('input', () => segmentValue.textContent = segmentSlider.value);
        thresholdSlider.addEventListener('input', () => thresholdValue.textContent = thresholdSlider.value);
        adaptiveSlider.addEventListener('input', () => {
            const val = parseInt(adaptiveSlider.value);
            adaptiveValue.textContent = val === 0 ? '固定' : val;
        });

        // モード切り替え時に設定の表示/非表示を切り替え
        const segmentGroup = document.getElementById('segmentGroup');
        const adaptiveGroup = document.getElementById('adaptiveGroup');
        const thresholdGroup = document.getElementById('thresholdGroup');
        const simpleAnalyzeArea = document.getElementById('simpleAnalyzeArea');
        const modeSimple = document.getElementById('modeSimple');
        const modeTimbre = document.getElementById('modeTimbre');
        const modeLabels = {
            simple: document.getElementById('modeSimpleLabel'),
            timbre: document.getElementById('modeTimbreLabel')
        };

        function updateModeVisibility() {
            const selectedMode = document.querySelector('input[name="mode"]:checked').value;
            // 簡易版のみHz設定を表示
            const showHzSettings = (selectedMode === 'simple');

            segmentGroup.style.display = showHzSettings ? 'block' : 'none';
            adaptiveGroup.style.display = showHzSettings ? 'block' : 'none';
            thresholdGroup.style.display = showHzSettings ? 'block' : 'none';
            simpleAnalyzeArea.style.display = showHzSettings ? 'block' : 'none';

            // モード説明の切り替え
            document.getElementById('modeDescSimple').style.display = (selectedMode === 'simple') ? 'block' : 'none';
            document.getElementById('modeDescTimbre').style.display = (selectedMode === 'timbre') ? 'block' : 'none';

            // モード選択のスタイル更新
            Object.keys(modeLabels).forEach(mode => {
                const label = modeLabels[mode];
                if (label) {
                    if (mode === selectedMode) {
                        label.style.background = '#e8f4fd';
                        label.style.borderColor = '#4a90d9';
                    } else {
                        label.style.background = '#f8f9fa';
                        label.style.borderColor = '#ddd';
                    }
                }
            });
        }
        modeSimple.addEventListener('change', updateModeVisibility);
        modeTimbre.addEventListener('change', updateModeVisibility);

        processBtn.addEventListener('click', async () => {
            if (!selectedFile) return;
            processBtn.disabled = true;
            uploadProgress.classList.add('show');
            logContainer.style.display = 'block';
            logBox.innerHTML = '';
            resultArea.innerHTML = '';

            addLog('ファイルをアップロード中...');

            const formData = new FormData();
            formData.append('file', selectedFile);
            formData.append('pitch', pitchSlider.value);
            formData.append('segment', segmentSlider.value);
            formData.append('threshold', thresholdSlider.value);
            formData.append('adaptive_window', adaptiveSlider.value);
            formData.append('mode', document.querySelector('input[name="mode"]:checked').value);

            const xhr = new XMLHttpRequest();
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const percent = (e.loaded / e.total) * 100;
                    uploadProgressFill.style.width = percent + '%';
                    uploadStatusText.textContent = `アップロード中... ${Math.round(percent)}%`;
                }
            });

            xhr.addEventListener('load', async () => {
                uploadProgress.classList.remove('show');
                if (xhr.status === 200) {
                    const data = JSON.parse(xhr.responseText);
                    if (data.error) {
                        addLog(`エラー: ${data.error}`, 'error');
                        resultArea.innerHTML = `<div class="error">${escapeHtml(data.error)}</div>`;
                        processBtn.disabled = false;
                        return;
                    }
                    addLog('アップロード完了');
                    progressContainer.style.display = 'block';
                    await pollStatus(data.task_id);
                } else {
                    addLog('アップロードエラー', 'error');
                    processBtn.disabled = false;
                }
            });

            xhr.open('POST', '/upload');
            xhr.send(formData);
        });

        async function pollStatus(taskId) {
            const poll = async () => {
                const response = await fetch(`/status/${taskId}`);
                const data = await response.json();

                if (data.logs) {
                    const currentCount = logBox.querySelectorAll('span.log-info, span.log-error, span.log-warn').length;
                    for (let i = currentCount; i < data.logs.length; i++) {
                        addLog(data.logs[i].message, data.logs[i].type || 'info');
                    }
                }
                if (data.progress) progressFill.style.width = `${data.progress}%`;
                if (data.step) statusText.textContent = data.step;

                if (data.status === 'processing') {
                    setTimeout(poll, 500);
                } else if (data.status === 'complete') {
                    progressFill.style.width = '100%';
                    statusText.textContent = '完了!';
                    addLog('処理が完了しました!');
                    currentTaskId = taskId;
                    // プロジェクト履歴に保存
                    saveProject(taskId, selectedFile ? selectedFile.name : 'unknown', Date.now());
                    resultArea.innerHTML = `
                        <div class="success" style="margin-bottom: 15px;">処理が完了しました!</div>
                        <div style="display: flex; gap: 10px; margin-bottom: 10px;">
                            <a href="/download/${taskId}?format=video" class="btn btn-primary" download style="flex: 1; text-align: center; text-decoration: none;">動画 (MP4)</a>
                            <a href="/download/${taskId}?format=audio" class="btn btn-success" download style="flex: 1; text-align: center; text-decoration: none;">音声 (WAV)</a>
                            <a href="/editor?task_id=${taskId}" class="btn btn-secondary" style="flex: 1; text-align: center; text-decoration: none; background: #6c757d;">波形エディタ</a>
                        </div>
                    `;
                    processBtn.disabled = false;
                } else if (data.status === 'error') {
                    addLog(`エラー: ${data.message}`, 'error');
                    resultArea.innerHTML = `<div class="error">${escapeHtml(data.message)}</div>`;
                    progressContainer.style.display = 'none';
                    processBtn.disabled = false;
                }
            };
            await poll();
        }

        // ==================== 手動編集機能 ====================
        let wavesurfer = null;
        let wsRegions = null;
        let currentTaskId = null;

        const editorSection = document.getElementById('editorSection');
        const editorVideo = document.getElementById('editorVideo');
        const editorPitchSlider = document.getElementById('editorPitchSlider');
        const editorPitchValue = document.getElementById('editorPitchValue');
        const applyManualBtn = document.getElementById('applyManualBtn');
        const clearRegionsBtn = document.getElementById('clearRegionsBtn');
        const regionsList = document.getElementById('regionsList');
        const regionsListContainer = document.getElementById('regionsListContainer');
        const manualResultArea = document.getElementById('manualResultArea');

        editorPitchSlider.addEventListener('input', () => {
            editorPitchValue.textContent = editorPitchSlider.value;
        });

        // グローバルに公開
        window.openManualEditor = function(taskId) {
            currentTaskId = taskId;
            editorSection.style.display = 'block';
            editorSection.scrollIntoView({ behavior: 'smooth' });

            // 動画を設定
            const videoUrl = `/download/${taskId}?format=video`;
            editorVideo.src = videoUrl;

            // 既存のWaveSurferを破棄
            if (wavesurfer) {
                wavesurfer.destroy();
                wavesurfer = null;
            }

            // タイムラインコンテナをクリア
            document.getElementById('timeline').innerHTML = '';

            // WaveSurferを本格的に初期化
            wavesurfer = WaveSurfer.create({
                container: '#waveform',
                waveColor: '#4a90d9',
                progressColor: '#357abd',
                cursorColor: '#c82333',
                cursorWidth: 2,
                media: editorVideo,
                height: 150,
                barWidth: 3,
                barGap: 1,
                barRadius: 3,
                normalize: true,
                plugins: [
                    WaveSurfer.Timeline.create({
                        container: '#timeline',
                        primaryLabelInterval: 5,
                        secondaryLabelInterval: 1,
                        style: {
                            fontSize: '11px',
                            color: '#666'
                        }
                    })
                ]
            });

            // Regionsプラグインを有効化
            wsRegions = wavesurfer.registerPlugin(WaveSurfer.Regions.create());

            // ドラッグで区間選択を有効化
            wsRegions.enableDragSelection({
                color: 'rgba(255, 100, 100, 0.3)',
            });

            // ズーム機能
            const zoomSlider = document.getElementById('zoomSlider');
            const zoomValue = document.getElementById('zoomValue');

            zoomSlider.addEventListener('input', () => {
                const minPxPerSec = Number(zoomSlider.value);
                wavesurfer.zoom(minPxPerSec);
                zoomValue.textContent = minPxPerSec + 'x';
            });

            // 動画の準備ができたらズームの初期値を設定
            wavesurfer.on('ready', () => {
                const containerWidth = document.getElementById('waveform').clientWidth;
                const duration = wavesurfer.getDuration();
                const minZoom = Math.max(10, Math.ceil(containerWidth / duration));
                zoomSlider.min = minZoom;
                zoomSlider.value = minZoom;
                zoomValue.textContent = minZoom + 'x';
            });

            // 区間が作成されたとき
            wsRegions.on('region-created', (region) => {
                updateRegionsList();
                applyManualBtn.disabled = false;
            });

            // 区間が更新されたとき
            wsRegions.on('region-updated', () => {
                updateRegionsList();
            });

            // 区間がクリックされたとき（再生）
            wsRegions.on('region-clicked', (region, e) => {
                e.stopPropagation();
                region.play();
            });

            // 区間リストを更新
            function updateRegionsList() {
                const regions = wsRegions.getRegions();
                if (regions.length === 0) {
                    regionsListContainer.style.display = 'none';
                    applyManualBtn.disabled = true;
                    return;
                }

                regionsListContainer.style.display = 'block';
                regionsList.innerHTML = regions.map((r, i) => `
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: #f8f9fa; border-radius: 8px; margin-bottom: 8px; border-left: 4px solid #dc3545;">
                        <span style="font-family: monospace;">区間${i + 1}: ${formatTime(r.start)} - ${formatTime(r.end)}</span>
                        <div style="display: flex; gap: 5px;">
                            <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 0.8em;" onclick="playRegion('${r.id}')">再生</button>
                            <button class="btn btn-danger" style="padding: 4px 8px; font-size: 0.8em;" onclick="removeRegion('${r.id}')">削除</button>
                        </div>
                    </div>
                `).join('');
            }

            // 区間クリア
            clearRegionsBtn.addEventListener('click', () => {
                wsRegions.clearRegions();
                updateRegionsList();
            });

            addLog('手動編集モード: 波形上をドラッグして区間を選択してください');
        }

        // 区間を再生
        window.playRegion = function(regionId) {
            const regions = wsRegions.getRegions();
            const region = regions.find(r => r.id === regionId);
            if (region) region.play();
        };

        // 区間を削除
        window.removeRegion = function(regionId) {
            const regions = wsRegions.getRegions();
            const region = regions.find(r => r.id === regionId);
            if (region) {
                region.remove();
                // リストを更新
                setTimeout(() => {
                    const remainingRegions = wsRegions.getRegions();
                    if (remainingRegions.length === 0) {
                        regionsListContainer.style.display = 'none';
                        applyManualBtn.disabled = true;
                    } else {
                        regionsList.innerHTML = remainingRegions.map((r, i) => `
                            <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: #f8f9fa; border-radius: 8px; margin-bottom: 8px; border-left: 4px solid #dc3545;">
                                <span style="font-family: monospace;">区間${i + 1}: ${formatTime(r.start)} - ${formatTime(r.end)}</span>
                                <div style="display: flex; gap: 5px;">
                                    <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 0.8em;" onclick="playRegion('${r.id}')">再生</button>
                                    <button class="btn btn-danger" style="padding: 4px 8px; font-size: 0.8em;" onclick="removeRegion('${r.id}')">削除</button>
                                </div>
                            </div>
                        `).join('');
                    }
                }, 100);
            }
        };

        // 手動編集を適用
        applyManualBtn.addEventListener('click', async () => {
            const regions = wsRegions.getRegions();
            if (regions.length === 0) {
                alert('区間を選択してください');
                return;
            }

            const regionsData = regions.map(r => ({ start: r.start, end: r.end }));
            const pitch = parseFloat(editorPitchSlider.value);

            applyManualBtn.disabled = true;
            applyManualBtn.textContent = '処理中...';
            manualResultArea.innerHTML = '<div style="color: #666;">処理中...</div>';

            try {
                const response = await fetch('/apply_manual_pitch', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        task_id: currentTaskId,
                        regions: regionsData,
                        pitch: pitch
                    })
                });

                const result = await response.json();

                if (result.error) {
                    manualResultArea.innerHTML = `<div class="error">${escapeHtml(result.error)}</div>`;
                    applyManualBtn.disabled = false;
                    applyManualBtn.textContent = '選択区間にピッチ適用';
                    return;
                }

                // 処理完了を待つ
                await pollManualStatus(result.task_id);

            } catch (error) {
                manualResultArea.innerHTML = `<div class="error">エラー: ${error.message}</div>`;
                applyManualBtn.disabled = false;
                applyManualBtn.textContent = '選択区間にピッチ適用';
            }
        });

        async function pollManualStatus(taskId) {
            const poll = async () => {
                const response = await fetch(`/status/${taskId}`);
                const data = await response.json();

                if (data.status === 'processing') {
                    setTimeout(poll, 500);
                } else if (data.status === 'complete') {
                    manualResultArea.innerHTML = `
                        <div class="success" style="margin-bottom: 10px;">手動編集が完了しました!</div>
                        <div style="display: flex; gap: 10px;">
                            <a href="/download/${taskId}?format=video" class="btn btn-primary" download style="flex: 1; text-align: center; text-decoration: none;">編集後動画 (MP4)</a>
                            <a href="/download/${taskId}?format=audio" class="btn btn-success" download style="flex: 1; text-align: center; text-decoration: none;">編集後音声 (WAV)</a>
                        </div>
                    `;
                    applyManualBtn.disabled = false;
                    applyManualBtn.textContent = '選択区間にピッチ適用';

                    // 新しい動画で波形を更新
                    editorVideo.src = `/download/${taskId}?format=video`;
                    currentTaskId = taskId;
                    wsRegions.clearRegions();
                    regionsListContainer.style.display = 'none';
                } else if (data.status === 'error') {
                    manualResultArea.innerHTML = `<div class="error">${escapeHtml(data.message || 'エラーが発生しました')}</div>`;
                    applyManualBtn.disabled = false;
                    applyManualBtn.textContent = '選択区間にピッチ適用';
                }
            };
            await poll();
        }

        // ページ読み込み時にセッションから前回のタスクを復元
        window.addEventListener('DOMContentLoaded', async () => {
            const lastTaskId = sessionStorage.getItem('lastTaskId');
            if (lastTaskId) {
                try {
                    const response = await fetch(`/status/${lastTaskId}`);
                    const data = await response.json();
                    if (data.status === 'complete') {
                        currentTaskId = lastTaskId;
                        addLog('前回の処理結果を復元しました');
                        resultArea.innerHTML = `
                            <div class="success" style="margin-bottom: 15px;">前回の処理結果</div>
                            <div style="display: flex; gap: 10px; margin-bottom: 10px;">
                                <a href="/download/${lastTaskId}?format=video" class="btn btn-primary" download style="flex: 1; text-align: center; text-decoration: none;">動画 (MP4)</a>
                                <a href="/download/${lastTaskId}?format=audio" class="btn btn-success" download style="flex: 1; text-align: center; text-decoration: none;">音声 (WAV)</a>
                                <a href="/editor?task_id=${lastTaskId}" class="btn btn-secondary" style="flex: 1; text-align: center; text-decoration: none; background: #6c757d;">波形エディタ</a>
                            </div>
                        `;
                    }
                } catch (e) {
                    // タスクが見つからない場合は無視
                }
            }
        });
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/upload', methods=['POST'])
def upload():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'ファイルがありません'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'ファイルが選択されていません'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': '対応していないファイル形式です'}), 400

        pitch = float(request.form.get('pitch', -3.0))
        segment = float(request.form.get('segment', 0.5))
        threshold = float(request.form.get('threshold', 165))
        adaptive_window = float(request.form.get('adaptive_window', 300))
        mode = request.form.get('mode', 'hybrid')  # hybrid, simple, clearvoice
        task_id = str(uuid.uuid4())

        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{task_id[:8]}{ext}"
        input_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(input_path)

        output_filename = f"{name}_{task_id[:8]}_processed.mp4"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)

        processing_status[task_id] = {
            'status': 'processing',
            'input': input_path,
            'output': output_path,
            'original_filename': filename,
            'progress': 10,
            'step': '処理を開始中...',
            'logs': [{'message': 'ファイルを受信しました', 'type': 'info'}]
        }

        thread = threading.Thread(target=process_task, args=(task_id, input_path, output_path, pitch, segment, threshold, mode, adaptive_window))
        thread.daemon = True
        thread.start()

        return jsonify({'task_id': task_id})

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"[UPLOAD ERROR] {error_details}")
        return jsonify({'error': str(e), 'details': error_details}), 500


@app.route('/analyze', methods=['POST'])
def analyze():
    """音声を解析してピッチ分布と推奨閾値を返す（非同期）"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'ファイルがありません'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'ファイルが選択されていません'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': '対応していないファイル形式です'}), 400

        # 一時ファイルに保存
        task_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{task_id[:8]}{ext}"
        input_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(input_path)

        processing_status[task_id] = {
            'status': 'analyzing',
            'input': input_path,
            'progress': 0,
            'step': '解析を開始中...',
            'logs': [{'message': 'ファイルを受信しました', 'type': 'info'}]
        }

        # バックグラウンドで解析実行
        thread = threading.Thread(target=analyze_task, args=(task_id, input_path))
        thread.daemon = True
        thread.start()

        return jsonify({'task_id': task_id})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


def analyze_task(task_id, input_path):
    """バックグラウンドで解析を実行"""
    try:
        def progress_callback(message):
            add_log(task_id, message)

        result = analyze_pitch_distribution(input_path, progress_callback=progress_callback)

        # 結果を保存
        processing_status[task_id]['status'] = 'complete'
        processing_status[task_id]['result'] = result
        add_log(task_id, '解析が完了しました!')

    except Exception as e:
        error_msg = str(e)
        tb = traceback.format_exc()
        add_log(task_id, f'エラー発生: {error_msg}', 'error')
        processing_status[task_id]['status'] = 'error'
        processing_status[task_id]['message'] = error_msg
        processing_status[task_id]['traceback'] = tb

    finally:
        # 一時ファイルを削除
        try:
            os.remove(input_path)
        except:
            pass


@app.route('/upload_for_editor', methods=['POST'])
def upload_for_editor():
    """エディタ用にファイルをアップロード（処理はしない）"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'ファイルがありません'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'ファイルが選択されていません'}), 400

        task_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{task_id[:8]}{ext}"
        input_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(input_path)

        processing_status[task_id] = {
            'status': 'ready',
            'input': input_path,
            'output': input_path,
            'original_filename': filename,
        }

        return jsonify({'task_id': task_id})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/apply_pitch', methods=['POST'])
def apply_pitch():
    """選択した区間にピッチシフトを適用"""
    try:
        data = request.get_json()
        source_task_id = data.get('task_id')
        regions = data.get('regions', [])
        pitch = float(data.get('pitch', -3.0))

        if not source_task_id or source_task_id not in processing_status:
            return jsonify({'error': 'タスクが見つかりません'}), 400

        if not regions:
            return jsonify({'error': '区間が選択されていません'}), 400

        source_task = processing_status[source_task_id]
        input_path = source_task.get('output') or source_task.get('input')

        task_id = str(uuid.uuid4())
        name = Path(input_path).stem
        output_filename = f"{name}_edited_{task_id[:8]}.mp4"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)

        processing_status[task_id] = {
            'status': 'processing',
            'input': input_path,
            'output': output_path,
            'progress': 10,
            'step': '区間ピッチ変換中...',
            'logs': [{'message': f'{len(regions)}区間をピッチ変換します', 'type': 'info'}]
        }

        thread = threading.Thread(
            target=process_regions_task,
            args=(task_id, input_path, output_path, regions, pitch)
        )
        thread.daemon = True
        thread.start()

        return jsonify({'task_id': task_id})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


def add_log(task_id, message, log_type='info'):
    if task_id in processing_status:
        processing_status[task_id]['logs'].append({
            'message': message,
            'type': log_type,
            'time': datetime.now().isoformat()
        })
        print(f"[{log_type.upper()}] {message}")


def update_progress(task_id, progress, step):
    if task_id in processing_status:
        processing_status[task_id]['progress'] = progress
        processing_status[task_id]['step'] = step


def process_task(task_id, input_path, output_path, pitch, segment=0.5, threshold=165, mode='hybrid', adaptive_window=300.0):
    try:
        mode_names = {
            'simple': '簡易版（Hz判定のみ）',
            'timbre': 'AI声質判定（CNN学習モデル）',
            'hybrid': 'ハイブリッド（話者分離＋詳細分析）'
        }
        mode_name = mode_names.get(mode, mode)
        add_log(task_id, f'処理モード: {mode_name}')
        add_log(task_id, f'ピッチシフト: {pitch}半音')
        if mode == 'simple':
            add_log(task_id, f'男性判定閾値: {threshold}Hz')
            add_log(task_id, f'セグメント長: {segment}秒')
            adaptive_str = '固定' if adaptive_window == 0 else f'{adaptive_window}秒ごと'
            add_log(task_id, f'動的閾値調整: {adaptive_str}')
        elif mode == 'hybrid':
            add_log(task_id, f'男性判定閾値: {threshold}Hz')
        update_progress(task_id, 20, '音声を抽出中...')

        def progress_callback(step, message):
            progress_map = {
                'extract': (25, '音声を抽出中...'),
                'separate': (40, '話者分離AI実行中...'),
                'analyze': (55, '音声を解析中...'),
                'pitch': (70, 'ピッチ変換中...'),
                'merge': (85, '音声を合成中...'),
                'combine': (95, '動画を出力中...'),
            }
            if step in progress_map:
                prog, status = progress_map[step]
                update_progress(task_id, prog, status)
            add_log(task_id, message)

        # 音声ファイル保存パスを生成
        audio_output_path = output_path.replace('.mp4', '.wav')

        process_video(input_path, output_path, pitch, segment, threshold, mode, adaptive_window,
                      progress_callback=progress_callback, save_audio_path=audio_output_path)

        update_progress(task_id, 100, '完了!')
        add_log(task_id, '処理が完了しました!')
        processing_status[task_id]['status'] = 'complete'
        processing_status[task_id]['processed_audio'] = audio_output_path

        try:
            os.remove(input_path)
        except:
            pass

    except Exception as e:
        error_msg = str(e)
        tb = traceback.format_exc()
        add_log(task_id, f'エラー発生: {error_msg}', 'error')
        processing_status[task_id]['status'] = 'error'
        processing_status[task_id]['message'] = error_msg
        processing_status[task_id]['traceback'] = tb


def process_regions_task(task_id, input_path, output_path, regions, pitch):
    """選択区間のみピッチ変換"""
    try:
        add_log(task_id, f'{len(regions)}区間をピッチ {pitch}半音で変換')
        update_progress(task_id, 30, '音声を処理中...')

        pitch_shift_region(input_path, output_path, regions, pitch)

        update_progress(task_id, 100, '完了!')
        add_log(task_id, '処理が完了しました!')
        processing_status[task_id]['status'] = 'complete'

    except Exception as e:
        error_msg = str(e)
        tb = traceback.format_exc()
        add_log(task_id, f'エラー発生: {error_msg}', 'error')
        processing_status[task_id]['status'] = 'error'
        processing_status[task_id]['message'] = error_msg
        processing_status[task_id]['traceback'] = tb


@app.route('/status/<task_id>')
def status(task_id):
    if task_id not in processing_status:
        return jsonify({'error': 'タスクが見つかりません'}), 404
    return jsonify(processing_status[task_id])


@app.route('/apply_manual_pitch', methods=['POST'])
def apply_manual_pitch():
    """手動編集: 選択区間にピッチシフトを適用"""
    try:
        data = request.get_json()
        source_task_id = data.get('task_id')
        regions = data.get('regions', [])
        pitch = float(data.get('pitch', -3.0))

        if not source_task_id or source_task_id not in processing_status:
            return jsonify({'error': '元のタスクが見つかりません'}), 400

        if not regions:
            return jsonify({'error': '区間が選択されていません'}), 400

        source_task = processing_status[source_task_id]
        input_path = source_task.get('output')

        if not input_path or not os.path.exists(input_path):
            return jsonify({'error': '入力ファイルが見つかりません'}), 400

        # 新しいタスクIDを生成
        new_task_id = str(uuid.uuid4())
        original_name = source_task.get('original_filename', 'output.mp4')
        name, _ = os.path.splitext(original_name)
        output_filename = f"{name}_manual_{new_task_id[:8]}.mp4"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        audio_output_path = output_path.replace('.mp4', '.wav')

        processing_status[new_task_id] = {
            'status': 'processing',
            'input': input_path,
            'output': output_path,
            'processed_audio': audio_output_path,
            'original_filename': original_name,
            'progress': 10,
            'step': '手動編集を処理中...',
            'logs': [{'message': f'{len(regions)}区間をピッチ変換します', 'type': 'info'}]
        }

        # バックグラウンドで処理
        thread = threading.Thread(
            target=process_manual_regions_task,
            args=(new_task_id, input_path, output_path, audio_output_path, regions, pitch)
        )
        thread.daemon = True
        thread.start()

        return jsonify({'task_id': new_task_id})

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"[MANUAL PITCH ERROR] {error_details}")
        return jsonify({'error': str(e)}), 500


def process_manual_regions_task(task_id, input_path, output_path, audio_output_path, regions, pitch):
    """手動選択区間のピッチ変換"""
    try:
        # 各regionにpitchが含まれているかログ出力
        print(f"[DEBUG] regions received: {regions}")
        for i, r in enumerate(regions):
            region_pitch = r.get('pitch', pitch)
            print(f"[DEBUG] region {i}: start={r.get('start')}, end={r.get('end')}, pitch={region_pitch}")
            add_log(task_id, f"区間{i+1}: {r.get('start'):.2f}s - {r.get('end'):.2f}s, {region_pitch}半音")

        add_log(task_id, f'{len(regions)}区間を処理中...')
        update_progress(task_id, 30, '音声を処理中...')

        # pitch_shift_regionを呼び出し（音声も保存）
        pitch_shift_region(input_path, output_path, regions, pitch, save_audio_path=audio_output_path)

        update_progress(task_id, 100, '完了!')
        add_log(task_id, '手動編集が完了しました!')
        processing_status[task_id]['status'] = 'complete'

    except Exception as e:
        error_msg = str(e)
        tb = traceback.format_exc()
        add_log(task_id, f'エラー発生: {error_msg}', 'error')
        processing_status[task_id]['status'] = 'error'
        processing_status[task_id]['message'] = error_msg
        processing_status[task_id]['traceback'] = tb


@app.route('/download/<task_id>')
def download(task_id):
    if task_id not in processing_status:
        return jsonify({'error': 'タスクが見つかりません'}), 404

    task = processing_status[task_id]
    output_path = task.get('output')
    audio_path = task.get('processed_audio')

    if not output_path or not os.path.exists(output_path):
        return jsonify({'error': 'ファイルが見つかりません'}), 404

    original_name = task.get('original_filename', 'output.mp4')
    name, _ = os.path.splitext(original_name)

    # フォーマット指定（video または audio）
    format_type = request.args.get('format', 'video')

    if format_type == 'audio':
        # WAVファイルをダウンロード
        if audio_path and os.path.exists(audio_path):
            download_name = f"{name}_processed.wav"
            return send_file(audio_path, as_attachment=True, download_name=download_name)
        else:
            return jsonify({'error': '音声ファイルが見つかりません'}), 404
    else:
        # 動画ファイルをダウンロード
        download_name = f"{name}_processed.mp4"
        return send_file(output_path, as_attachment=True, download_name=download_name)


# ==================== 話者分離API ====================

@app.route('/separate_speakers', methods=['POST'])
def separate_speakers():
    """話者分離を実行する"""
    if 'file' not in request.files:
        return jsonify({'error': 'ファイルがありません'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'ファイルが選択されていません'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': '対応していないファイル形式です'}), 400

    # タスクID生成
    task_id = str(uuid.uuid4())

    # ファイル保存
    filename = secure_filename(file.filename)
    name, ext = os.path.splitext(filename)
    saved_filename = f"{name}_{task_id[:8]}{ext}"
    input_path = os.path.join(UPLOAD_FOLDER, saved_filename)
    file.save(input_path)

    # 話者ファイル用ディレクトリ
    speaker_dir = os.path.join(OUTPUT_FOLDER, f"speakers_{task_id[:8]}")
    os.makedirs(speaker_dir, exist_ok=True)

    # ステータス初期化
    processing_status[task_id] = {
        'status': 'separating',
        'progress': 0,
        'step': '話者分離を開始中...',
        'logs': [],
        'input': input_path,
        'speaker_dir': speaker_dir,
        'original_filename': filename
    }

    def add_log(task_id, message):
        processing_status[task_id]['logs'].append(message)

    def separate_task(task_id, input_path, speaker_dir):
        try:
            def progress_callback(step, message):
                add_log(task_id, message)
                processing_status[task_id]['step'] = message

            result = separate_speakers_to_files(
                input_path,
                speaker_dir,
                progress_callback
            )

            processing_status[task_id]['status'] = 'separated'
            processing_status[task_id]['speakers'] = result['speakers']
            processing_status[task_id]['step'] = '話者分離完了'

        except Exception as e:
            processing_status[task_id]['status'] = 'error'
            processing_status[task_id]['error'] = str(e)
            processing_status[task_id]['traceback'] = traceback.format_exc()

    # バックグラウンド実行
    thread = threading.Thread(
        target=separate_task,
        args=(task_id, input_path, speaker_dir),
        daemon=True
    )
    thread.start()

    return jsonify({'task_id': task_id})


@app.route('/speaker_audio/<task_id>/<int:speaker_id>')
def speaker_audio(task_id, speaker_id):
    """分離された話者の音声ファイルを返す"""
    if task_id not in processing_status:
        return jsonify({'error': 'タスクが見つかりません'}), 404

    task = processing_status[task_id]
    speaker_dir = task.get('speaker_dir')

    if not speaker_dir:
        return jsonify({'error': '話者ディレクトリが見つかりません'}), 404

    speaker_file = os.path.join(speaker_dir, f"speaker_{speaker_id}.wav")
    if not os.path.exists(speaker_file):
        return jsonify({'error': '話者ファイルが見つかりません'}), 404

    return send_file(speaker_file, mimetype='audio/wav')


@app.route('/process_selected_speakers', methods=['POST'])
def process_selected_speakers_api():
    """選択された話者をピッチダウンして動画を出力する"""
    data = request.get_json()
    task_id = data.get('task_id')
    male_speaker_ids = data.get('male_speaker_ids', [])
    pitch = float(data.get('pitch', -3.0))

    if not task_id or task_id not in processing_status:
        return jsonify({'error': 'タスクが見つかりません'}), 400

    task = processing_status[task_id]
    input_path = task.get('input')
    speaker_dir = task.get('speaker_dir')
    original_filename = task.get('original_filename', 'output.mp4')

    if not input_path or not speaker_dir:
        return jsonify({'error': '入力ファイルが見つかりません'}), 400

    # 出力パス
    name, _ = os.path.splitext(original_filename)
    output_filename = f"{name}_{task_id[:8]}_processed.mp4"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)

    processing_status[task_id]['status'] = 'processing'
    processing_status[task_id]['output'] = output_path
    processing_status[task_id]['step'] = '処理を開始中...'

    def add_log(task_id, message):
        processing_status[task_id]['logs'].append(message)

    def process_task(task_id, input_path, output_path, speaker_dir, male_speaker_ids, pitch):
        try:
            def progress_callback(step, message):
                add_log(task_id, message)
                processing_status[task_id]['step'] = message

            process_with_selected_speakers(
                input_path,
                output_path,
                speaker_dir,
                male_speaker_ids,
                pitch,
                progress_callback
            )

            processing_status[task_id]['status'] = 'complete'
            processing_status[task_id]['step'] = '処理完了'

        except Exception as e:
            processing_status[task_id]['status'] = 'error'
            processing_status[task_id]['error'] = str(e)
            processing_status[task_id]['traceback'] = traceback.format_exc()

    # バックグラウンド実行
    thread = threading.Thread(
        target=process_task,
        args=(task_id, input_path, output_path, speaker_dir, male_speaker_ids, pitch),
        daemon=True
    )
    thread.start()

    return jsonify({'status': 'processing'})


EDITOR_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <title>波形エディタ - 男性ボイスチェンジャー</title>
    <script src="https://unpkg.com/wavesurfer.js@7"></script>
    <script src="https://unpkg.com/wavesurfer.js@7/dist/plugins/regions.min.js"></script>
    <script src="https://unpkg.com/wavesurfer.js@7/dist/plugins/timeline.min.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #fff;
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        /* ヘッダー */
        .editor-header {
            background: #16213e;
            padding: 10px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #333;
        }
        .editor-header h1 {
            font-size: 1.2em;
            color: #4a90d9;
        }
        .header-actions {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
            font-size: 0.9em;
            transition: all 0.2s;
        }
        .btn-primary { background: #4a90d9; color: white; }
        .btn-primary:hover { background: #357abd; }
        .btn-success { background: #28a745; color: white; }
        .btn-success:hover { background: #218838; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-danger:hover { background: #c82333; }
        .btn-secondary { background: #6c757d; color: white; }
        .btn-secondary:hover { background: #5a6268; }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }

        /* メインエリア */
        .editor-main {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        /* 上部エリア（動画＋区間リスト） */
        .top-area {
            display: flex;
            height: 280px;
            border-bottom: 1px solid #333;
        }
        /* 動画プレビュー */
        .video-container {
            background: #000;
            display: flex;
            justify-content: center;
            align-items: center;
            flex: 1;
            min-width: 0;
        }
        .video-container video {
            max-height: 100%;
            max-width: 100%;
        }
        /* 区間リスト（右側） */
        .regions-sidebar {
            width: 300px;
            background: #1a1a2e;
            border-left: 1px solid #333;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        .regions-sidebar h4 {
            padding: 12px 15px;
            margin: 0;
            font-size: 0.9em;
            color: #aaa;
            background: #252540;
            border-bottom: 1px solid #333;
        }
        .regions-list {
            flex: 1;
            overflow-y: auto;
            padding: 10px;
        }
        .region-item {
            display: flex;
            flex-direction: column;
            padding: 8px 10px;
            background: #252540;
            border-radius: 6px;
            margin-bottom: 8px;
            border-left: 3px solid #dc3545;
        }
        .region-item.pitch-up { border-left-color: #28a745; }
        .region-info {
            font-family: monospace;
            font-size: 0.8em;
            margin-bottom: 5px;
        }
        .region-pitch {
            font-size: 0.75em;
            margin-bottom: 5px;
        }
        .region-actions {
            display: flex;
            gap: 5px;
        }
        .region-actions button {
            flex: 1;
            padding: 4px 8px;
            font-size: 0.7em;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        .regions-empty {
            color: #666;
            text-align: center;
            padding: 20px;
            font-size: 0.85em;
        }

        /* ツールバー */
        .toolbar {
            background: #252540;
            padding: 10px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #333;
        }
        .tool-group {
            display: flex;
            gap: 5px;
            align-items: center;
        }
        .tool-btn {
            width: 40px;
            height: 40px;
            border: 2px solid #444;
            border-radius: 8px;
            background: #1a1a2e;
            color: #fff;
            cursor: pointer;
            font-size: 1.2em;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
        }
        .tool-btn:hover { border-color: #4a90d9; background: #252540; }
        .tool-btn.active { border-color: #4a90d9; background: #4a90d9; }
        .tool-btn svg { width: 20px; height: 20px; }
        .tool-separator {
            width: 1px;
            height: 30px;
            background: #444;
            margin: 0 10px;
        }
        .zoom-control {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .zoom-control label { font-size: 0.85em; color: #aaa; }
        .zoom-control input[type="range"] {
            width: 150px;
            accent-color: #4a90d9;
        }
        .zoom-value {
            font-size: 0.85em;
            color: #4a90d9;
            min-width: 50px;
        }
        .time-display {
            font-family: monospace;
            font-size: 1em;
            color: #4a90d9;
            background: #1a1a2e;
            padding: 8px 15px;
            border-radius: 6px;
            border: 1px solid #333;
        }

        /* 波形エリア */
        .waveform-area {
            flex: 1;
            background: #0d0d1a;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }
        #timeline {
            background: #1a1a2e;
            padding: 5px 0;
        }
        #waveform {
            flex: 1;
            overflow-x: scroll;
            overflow-y: hidden;
        }

        /* 下部パネル */
        .bottom-panel {
            background: #16213e;
            padding: 15px 20px;
            border-top: 1px solid #333;
        }
        .panel-row {
            display: flex;
            gap: 20px;
            align-items: center;
            flex-wrap: wrap;
        }
        .panel-group {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .panel-group label {
            font-size: 0.9em;
            color: #aaa;
        }
        .panel-group select, .panel-group input[type="number"] {
            padding: 8px 12px;
            border: 1px solid #444;
            border-radius: 6px;
            background: #1a1a2e;
            color: #fff;
            font-size: 0.9em;
        }
        .pitch-value {
            font-weight: bold;
            color: #4a90d9;
            min-width: 60px;
            text-align: center;
        }

        /* キーボードヘルプ */
        .keyboard-help {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: rgba(0,0,0,0.8);
            padding: 15px;
            border-radius: 10px;
            font-size: 0.8em;
            color: #aaa;
            display: none;
        }
        .keyboard-help.show { display: block; }
        .keyboard-help kbd {
            background: #333;
            padding: 2px 6px;
            border-radius: 3px;
            color: #fff;
        }

        /* ステータスバー */
        .status-bar {
            background: #0d0d1a;
            padding: 5px 20px;
            font-size: 0.8em;
            color: #666;
            border-top: 1px solid #333;
            display: flex;
            justify-content: space-between;
        }
    </style>
</head>
<body>
    <!-- ヘッダー -->
    <div class="editor-header">
        <h1>波形エディタ</h1>
        <div class="header-actions">
            <button id="backBtn" class="btn btn-secondary">メインに戻る</button>
            <button id="downloadBtn" class="btn btn-primary">ダウンロード</button>
        </div>
    </div>

    <!-- アップロードエリア（タスクIDがない時に表示） -->
    <div id="uploadSection" class="editor-main" style="display: none;">
        <div style="flex: 1; display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 40px;">
            <!-- プロジェクト履歴 -->
            <div id="editorProjectHistory" style="width: 100%; max-width: 800px; margin-bottom: 30px; display: none;">
                <h3 style="margin: 0 0 15px 0; color: #ddd; font-size: 1.1em;">📂 作成したプロジェクト</h3>
                <div id="editorProjectList" style="display: flex; flex-wrap: wrap; gap: 10px; max-height: 250px; overflow-y: auto; padding: 15px; background: #1a1a2e; border-radius: 8px; border: 1px solid #333;"></div>
            </div>

            <div id="editorUploadArea" style="width: 100%; max-width: 600px; border: 3px dashed #4a90d9; border-radius: 16px; padding: 60px 40px; text-align: center; cursor: pointer; transition: all 0.3s; background: #1a1a2e;">
                <div style="font-size: 4em; margin-bottom: 20px;">📁</div>
                <div style="font-size: 1.3em; margin-bottom: 10px;">動画ファイルをドロップまたはクリック</div>
                <div style="color: #888; font-size: 0.9em;">対応形式: MP4, MOV, AVI, MKV, WebM</div>
            </div>
            <input type="file" id="editorFileInput" accept=".mp4,.mov,.avi,.mkv,.webm,.m4v,.flv,.wmv" style="display: none;">
            <div id="editorUploadProgress" style="display: none; width: 100%; max-width: 600px; margin-top: 20px;">
                <div style="background: #333; border-radius: 10px; height: 10px; overflow: hidden;">
                    <div id="editorProgressFill" style="background: #4a90d9; height: 100%; width: 0%; transition: width 0.3s;"></div>
                </div>
                <div id="editorUploadStatus" style="text-align: center; margin-top: 10px; color: #aaa;">アップロード中...</div>
            </div>
        </div>
    </div>

    <!-- メインエリア（タスクIDがある時に表示） -->
    <div id="editorSection" class="editor-main" style="display: none;">
        <!-- 上部エリア（動画＋区間リスト） -->
        <div class="top-area">
            <!-- 動画プレビュー -->
            <div class="video-container">
                <video id="video" controls></video>
            </div>
            <!-- 区間リスト（右側） -->
            <div class="regions-sidebar">
                <h4>区間リスト (<span id="regionCount">0</span>)</h4>
                <div class="regions-list" id="regionsList">
                    <div class="regions-empty">波形をドラッグして区間を選択<br>→「リストに追加」で確定</div>
                </div>
            </div>
        </div>

        <!-- ツールバー -->
        <div class="toolbar">
            <div class="tool-group">
                <!-- 再生コントロール -->
                <button id="playBtn" class="tool-btn" title="再生/一時停止 (Space)">
                    <svg id="playIcon" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
                    <svg id="pauseIcon" viewBox="0 0 24 24" fill="currentColor" style="display:none;"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
                </button>
                <button id="stopBtn" class="tool-btn" title="停止">
                    <svg viewBox="0 0 24 24" fill="currentColor"><path d="M6 6h12v12H6z"/></svg>
                </button>
            </div>

            <div class="time-display">
                <span id="currentTime">00:00.00</span> / <span id="totalTime">00:00.00</span>
            </div>

            <div class="zoom-control">
                <label>ズーム:</label>
                <input type="range" id="zoomSlider" min="10" max="500" value="50">
                <span id="zoomValue" class="zoom-value">50x</span>
                <span style="color: #666; font-size: 0.75em; margin-left: 10px;">↑↓:ズーム ←→:移動</span>
            </div>
        </div>

        <!-- 波形エリア -->
        <div class="waveform-area">
            <div id="timeline"></div>
            <div id="waveform"></div>
        </div>

        <!-- 下部パネル -->
        <div class="bottom-panel">
            <div class="panel-row">
                <div class="panel-group">
                    <label>ピッチ操作:</label>
                    <select id="pitchMode">
                        <option value="down">下げる（男性化）</option>
                        <option value="up">上げる（元に戻す）</option>
                    </select>
                </div>
                <div class="panel-group">
                    <label>シフト量:</label>
                    <input type="range" id="pitchSlider" min="-12" max="12" step="0.5" value="-3" style="width: 150px;">
                    <span id="pitchValue" class="pitch-value">-3.0</span>
                </div>
                <div class="panel-group">
                    <button id="addToListBtn" class="btn btn-primary" disabled>リストに追加</button>
                    <button id="processAllBtn" class="btn btn-success" disabled style="font-size: 1.1em; padding: 10px 20px;">🔊 まとめて処理</button>
                    <button id="clearRegionsBtn" class="btn btn-danger">全クリア</button>
                </div>
            </div>
        </div>

        <!-- ステータスバー -->
        <div class="status-bar">
            <span id="statusText">準備完了</span>
            <span>Space: 再生/停止 | Delete: 区間削除 | スクロール↑↓: ズーム | Shift+スクロール: 移動</span>
        </div>
    </div><!-- /editorSection -->

    <!-- キーボードヘルプ -->
    <div class="keyboard-help" id="keyboardHelp">
        <div><kbd>Space</kbd> 再生/一時停止</div>
        <div><kbd>Delete</kbd> 最後の区間を削除</div>
        <div><kbd>↑↓</kbd> ズームイン/アウト</div>
        <div><kbd>←→</kbd> 波形を移動</div>
        <div><kbd>?</kbd> このヘルプを表示</div>
    </div>

    <script>
        let taskId = new URLSearchParams(window.location.search).get('task_id');

        // セクション
        const uploadSection = document.getElementById('uploadSection');
        const editorSection = document.getElementById('editorSection');

        // 要素取得
        const video = document.getElementById('video');
        const playBtn = document.getElementById('playBtn');
        const playIcon = document.getElementById('playIcon');
        const pauseIcon = document.getElementById('pauseIcon');
        const stopBtn = document.getElementById('stopBtn');
        const zoomSlider = document.getElementById('zoomSlider');
        const zoomValue = document.getElementById('zoomValue');
        const pitchSlider = document.getElementById('pitchSlider');
        const pitchValue = document.getElementById('pitchValue');
        const pitchMode = document.getElementById('pitchMode');
        const currentTimeEl = document.getElementById('currentTime');
        const totalTimeEl = document.getElementById('totalTime');
        const downloadBtn = document.getElementById('downloadBtn');
        const addToListBtn = document.getElementById('addToListBtn');
        const processAllBtn = document.getElementById('processAllBtn');
        const clearRegionsBtn = document.getElementById('clearRegionsBtn');
        const regionsList = document.getElementById('regionsList');
        const regionCount = document.getElementById('regionCount');
        const statusText = document.getElementById('statusText');
        const keyboardHelp = document.getElementById('keyboardHelp');
        const waveformEl = document.getElementById('waveform');

        let wavesurfer = null;
        let wsRegions = null;
        let currentSelection = null; // 現在選択中の区間（未確定）
        let regionsData = []; // 確定済み区間リスト {id, start, end, pitch}
        let currentFilename = null; // 現在のファイル名

        // ==================== プロジェクト履歴 ====================
        const editorProjectHistory = document.getElementById('editorProjectHistory');
        const editorProjectList = document.getElementById('editorProjectList');

        function getProjects() {
            try {
                return JSON.parse(localStorage.getItem('voiceChangerProjects') || '[]');
            } catch { return []; }
        }

        function saveProject(projTaskId, filename) {
            const projects = getProjects();
            // 重複チェック（同じタスクIDなら更新）
            const existing = projects.findIndex(p => p.taskId === projTaskId);
            if (existing >= 0) {
                projects[existing].date = new Date().toLocaleString('ja-JP');
                projects[existing].filename = filename || projects[existing].filename;
            } else {
                projects.unshift({ taskId: projTaskId, filename: filename || 'unknown', date: new Date().toLocaleString('ja-JP') });
            }
            if (projects.length > 20) projects.pop();
            localStorage.setItem('voiceChangerProjects', JSON.stringify(projects));
            renderEditorProjects();
        }

        function removeProjectFromEditor(projTaskId) {
            const projects = getProjects().filter(p => p.taskId !== projTaskId);
            localStorage.setItem('voiceChangerProjects', JSON.stringify(projects));
            renderEditorProjects();
        }

        function renderEditorProjects() {
            const projects = getProjects();
            if (projects.length === 0) {
                editorProjectHistory.style.display = 'none';
                return;
            }
            editorProjectHistory.style.display = 'block';
            editorProjectList.innerHTML = projects.map(p => `
                <div style="background: #252540; border: 1px solid #444; border-radius: 8px; padding: 12px; min-width: 180px; flex: 1; max-width: 250px;">
                    <div style="font-weight: bold; font-size: 0.9em; color: #ddd; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${p.filename}">${p.filename}</div>
                    <div style="font-size: 0.8em; color: #888; margin: 4px 0;">${p.date}</div>
                    <div style="display: flex; gap: 5px; margin-top: 8px;">
                        <a href="/editor?task_id=${p.taskId}" style="flex: 1; padding: 4px 8px; background: #4a90d9; color: white; border-radius: 4px; text-decoration: none; text-align: center; font-size: 0.85em;">開く</a>
                        <a href="/download/${p.taskId}?format=video" style="flex: 1; padding: 4px 8px; background: #28a745; color: white; border-radius: 4px; text-decoration: none; text-align: center; font-size: 0.85em;">DL</a>
                        <button onclick="removeProjectFromEditor('${p.taskId}')" style="padding: 4px 8px; background: #dc3545; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.85em;">×</button>
                    </div>
                </div>
            `).join('');
        }

        // ==================== アップロード機能 ====================
        const editorUploadArea = document.getElementById('editorUploadArea');
        const editorFileInput = document.getElementById('editorFileInput');
        const editorUploadProgress = document.getElementById('editorUploadProgress');
        const editorProgressFill = document.getElementById('editorProgressFill');
        const editorUploadStatus = document.getElementById('editorUploadStatus');

        editorUploadArea.addEventListener('click', () => editorFileInput.click());
        editorUploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            editorUploadArea.style.borderColor = '#28a745';
            editorUploadArea.style.background = '#252540';
        });
        editorUploadArea.addEventListener('dragleave', () => {
            editorUploadArea.style.borderColor = '#4a90d9';
            editorUploadArea.style.background = '#1a1a2e';
        });
        editorUploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            editorUploadArea.style.borderColor = '#4a90d9';
            editorUploadArea.style.background = '#1a1a2e';
            if (e.dataTransfer.files.length > 0) {
                handleEditorUpload(e.dataTransfer.files[0]);
            }
        });
        editorFileInput.addEventListener('change', () => {
            if (editorFileInput.files.length > 0) {
                handleEditorUpload(editorFileInput.files[0]);
            }
        });

        function handleEditorUpload(file) {
            editorUploadProgress.style.display = 'block';
            editorProgressFill.style.width = '0%';
            editorUploadStatus.textContent = 'アップロード中...';

            const formData = new FormData();
            formData.append('file', file);
            formData.append('skip_processing', 'true'); // 処理をスキップ

            const xhr = new XMLHttpRequest();
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const percent = (e.loaded / e.total) * 100;
                    editorProgressFill.style.width = percent + '%';
                }
            });

            xhr.addEventListener('load', () => {
                if (xhr.status === 200) {
                    const data = JSON.parse(xhr.responseText);
                    editorUploadStatus.textContent = '完了！';
                    // タスクIDを設定してエディタを表示
                    taskId = data.task_id;
                    currentFilename = file.name;
                    sessionStorage.setItem('lastTaskId', taskId);
                    window.history.replaceState({}, '', `/editor?task_id=${taskId}`);
                    // プロジェクトを保存
                    saveProject(taskId, file.name);
                    showEditor();
                } else {
                    editorUploadStatus.textContent = 'エラーが発生しました';
                }
            });

            xhr.open('POST', '/upload_for_editor');
            xhr.send(formData);
        }

        // ==================== 表示切替 ====================
        function showUpload() {
            uploadSection.style.display = 'flex';
            editorSection.style.display = 'none';
            downloadBtn.style.display = 'none';
            // プロジェクト履歴を表示
            renderEditorProjects();
        }

        function showEditor() {
            uploadSection.style.display = 'none';
            editorSection.style.display = 'flex';
            downloadBtn.style.display = 'inline-block';

            // 動画ソース設定
            video.src = `/download/${taskId}?format=video`;
            video.addEventListener('loadedmetadata', () => {
                initWaveSurfer();
            }, { once: true });
        }

        // 初期表示
        if (taskId) {
            showEditor();
        } else {
            showUpload();
        }

        // 時間フォーマット
        function formatTime(seconds) {
            const mins = Math.floor(seconds / 60);
            const secs = (seconds % 60).toFixed(2);
            return `${mins.toString().padStart(2, '0')}:${secs.padStart(5, '0')}`;
        }

        // WaveSurfer初期化
        function initWaveSurfer() {
            document.getElementById('timeline').innerHTML = '';

            wavesurfer = WaveSurfer.create({
                container: '#waveform',
                waveColor: '#4a90d9',
                progressColor: '#357abd',
                cursorColor: '#ff6b6b',
                cursorWidth: 2,
                media: video,
                height: 200,
                barWidth: 2,
                barGap: 1,
                barRadius: 2,
                normalize: true,
                scrollParent: true,
                minPxPerSec: 50,
                plugins: [
                    WaveSurfer.Timeline.create({
                        container: '#timeline',
                        primaryLabelInterval: 5,
                        secondaryLabelInterval: 1,
                        style: { fontSize: '11px', color: '#888' }
                    })
                ]
            });

            wsRegions = wavesurfer.registerPlugin(WaveSurfer.Regions.create());

            // ドラッグで区間選択を有効化
            wsRegions.enableDragSelection({
                color: 'rgba(255, 100, 100, 0.3)'
            });

            // 区間イベント
            wsRegions.on('region-created', (region) => {
                // 既に確定済みの区間ならスキップ
                if (regionsData.find(r => r.id === region.id)) return;

                // 前の未確定選択を削除（確定済みでないもののみ）
                if (currentSelection && currentSelection.id !== region.id) {
                    const isConfirmed = regionsData.find(r => r.id === currentSelection.id);
                    if (!isConfirmed) {
                        try {
                            const oldRegion = wsRegions.getRegions().find(r => r.id === currentSelection.id);
                            if (oldRegion) oldRegion.remove();
                        } catch(e) {}
                    }
                }

                // 新しい選択を保持（未確定）
                currentSelection = {
                    id: region.id,
                    start: region.start,
                    end: region.end,
                    region: region
                };
                region.setOptions({ color: 'rgba(255, 200, 100, 0.4)' }); // 未確定は黄色
                addToListBtn.disabled = false;
                statusText.textContent = `区間選択: ${formatTime(region.start)} - ${formatTime(region.end)} → 「リストに追加」で確定`;
            });

            wsRegions.on('region-updated', (region) => {
                // 確定済み区間の更新
                const confirmed = regionsData.find(r => r.id === region.id);
                if (confirmed) {
                    confirmed.start = region.start;
                    confirmed.end = region.end;
                    updateRegionsList();
                }
                // 未確定の選択区間の更新
                if (currentSelection && currentSelection.id === region.id) {
                    currentSelection.start = region.start;
                    currentSelection.end = region.end;
                    statusText.textContent = `区間選択: ${formatTime(region.start)} - ${formatTime(region.end)} → 「リストに追加」で確定`;
                }
            });

            wsRegions.on('region-clicked', (region, e) => {
                e.stopPropagation();
                region.play();
            });

            // 準備完了
            wavesurfer.on('ready', () => {
                totalTimeEl.textContent = formatTime(wavesurfer.getDuration());
                statusText.textContent = '準備完了 - 波形をドラッグして区間を選択';
            });

            // 時間更新
            wavesurfer.on('timeupdate', (time) => {
                currentTimeEl.textContent = formatTime(time);
            });

            // 再生状態
            wavesurfer.on('play', () => {
                playIcon.style.display = 'none';
                pauseIcon.style.display = 'block';
            });
            wavesurfer.on('pause', () => {
                playIcon.style.display = 'block';
                pauseIcon.style.display = 'none';
            });
        }

        // マウスホイール/タッチパッドで操作
        // Mac タッチパッド: 上下スワイプ=ズーム、左右スワイプ=スクロール
        // Windows マウス: 上下ホイール=ズーム、Shift+ホイール=スクロール
        waveformEl.addEventListener('wheel', (e) => {
            e.preventDefault();

            // WaveSurferの内部スクロールコンテナを取得
            const scrollContainer = waveformEl.querySelector('div[style*="overflow"]') || waveformEl.firstChild;

            // 横スクロール量を計算
            let scrollX = 0;

            // Shift+ホイール: 横スクロール (Windows向け)
            if (e.shiftKey) {
                scrollX = e.deltaY;
            }
            // 左右スクロール（Macタッチパッド横スワイプ）
            else if (Math.abs(e.deltaX) > Math.abs(e.deltaY) * 0.5) {
                scrollX = e.deltaX;
            }

            if (scrollX !== 0) {
                // WaveSurferの現在時間を調整してスクロール
                const duration = wavesurfer.getDuration();
                const currentTime = wavesurfer.getCurrentTime();
                const pixelsPerSecond = wavesurfer.options.minPxPerSec || 100;
                const timeShift = scrollX / pixelsPerSecond;
                const newTime = Math.max(0, Math.min(duration, currentTime + timeShift));
                wavesurfer.setTime(newTime);
                return;
            }

            // 上下スクロール（ズーム）
            const delta = e.deltaY > 0 ? -30 : 30;
            let newZoom = parseInt(zoomSlider.value) + delta;
            newZoom = Math.max(parseInt(zoomSlider.min), Math.min(parseInt(zoomSlider.max), newZoom));
            zoomSlider.value = newZoom;
            wavesurfer.zoom(newZoom);
            zoomValue.textContent = newZoom + 'x';
        }, { passive: false });

        // イベントリスナー
        playBtn.addEventListener('click', () => wavesurfer.playPause());
        stopBtn.addEventListener('click', () => { wavesurfer.stop(); });

        zoomSlider.addEventListener('input', () => {
            const zoom = parseInt(zoomSlider.value);
            wavesurfer.zoom(zoom);
            zoomValue.textContent = zoom + 'x';
        });

        pitchSlider.addEventListener('input', () => {
            pitchValue.textContent = pitchSlider.value;
        });

        pitchMode.addEventListener('change', () => {
            if (pitchMode.value === 'up') {
                pitchSlider.value = 3;
            } else {
                pitchSlider.value = -3;
            }
            pitchValue.textContent = pitchSlider.value;
            // 区間選択の色を更新
            wsRegions.enableDragSelection({
                color: pitchMode.value === 'up' ? 'rgba(40, 167, 69, 0.3)' : 'rgba(255, 100, 100, 0.3)'
            });
        });

        // 区間リスト更新
        function updateRegionsList() {
            regionCount.textContent = regionsData.length;
            if (regionsData.length === 0) {
                regionsList.innerHTML = '<div class="regions-empty">波形をドラッグして区間を選択<br>→「リストに追加」で確定</div>';
                processAllBtn.disabled = true;
                return;
            }
            processAllBtn.disabled = false;
            regionsList.innerHTML = regionsData.map((r, i) => `
                <div class="region-item ${r.pitch > 0 ? 'pitch-up' : ''}" style="padding: 8px; margin: 4px 0; background: #2a2a40; border-radius: 4px; border-left: 3px solid ${r.pitch > 0 ? '#28a745' : '#dc3545'};">
                    <div style="font-size: 0.9em;">区間${i + 1}: ${formatTime(r.start)} - ${formatTime(r.end)}</div>
                    <div style="font-size: 0.85em; color: ${r.pitch > 0 ? '#28a745' : '#dc3545'};">${r.pitch > 0 ? '+' : ''}${r.pitch}半音</div>
                    <div style="margin-top: 4px;">
                        <button onclick="playRegion('${r.id}')" style="padding: 2px 8px; background: #4a90d9; color: white; border: none; border-radius: 3px; cursor: pointer; font-size: 0.8em;">再生</button>
                        <button onclick="removeRegion('${r.id}')" style="padding: 2px 8px; background: #dc3545; color: white; border: none; border-radius: 3px; cursor: pointer; font-size: 0.8em;">削除</button>
                    </div>
                </div>
            `).join('');
        }

        // 区間再生
        window.playRegion = function(regionId) {
            const regions = wsRegions.getRegions();
            const region = regions.find(r => r.id === regionId);
            if (region) region.play();
        };

        // 区間削除
        window.removeRegion = function(regionId) {
            const regions = wsRegions.getRegions();
            const region = regions.find(r => r.id === regionId);
            if (region) region.remove();
            regionsData = regionsData.filter(r => r.id !== regionId);
            updateRegionsList();
        };

        // リストに追加
        addToListBtn.addEventListener('click', () => {
            if (!currentSelection) {
                statusText.textContent = '区間を選択してください';
                return;
            }

            const pitch = pitchMode.value === 'up'
                ? Math.abs(parseFloat(pitchSlider.value))
                : -Math.abs(parseFloat(pitchSlider.value));

            // 確定済みリストに追加
            regionsData.push({
                id: currentSelection.id,
                start: currentSelection.start,
                end: currentSelection.end,
                pitch: pitch
            });

            // 色を確定色に変更
            const color = pitch > 0 ? 'rgba(40, 167, 69, 0.4)' : 'rgba(220, 53, 69, 0.4)';
            currentSelection.region.setOptions({ color: color });

            // 選択をクリア
            currentSelection = null;
            addToListBtn.disabled = true;

            updateRegionsList();
            statusText.textContent = `区間を追加しました（${pitch > 0 ? '+' : ''}${pitch}半音） - 続けて選択するか「まとめて処理」`;
        });

        // まとめて処理
        processAllBtn.addEventListener('click', async () => {
            if (regionsData.length === 0) {
                statusText.textContent = 'リストに区間を追加してください';
                return;
            }

            processAllBtn.disabled = true;
            processAllBtn.textContent = '処理中...';
            statusText.textContent = '処理中...';

            try {
                const response = await fetch('/apply_manual_pitch', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        task_id: taskId,
                        regions: regionsData.map(r => ({
                            start: r.start,
                            end: r.end,
                            pitch: r.pitch
                        }))
                    })
                });

                const result = await response.json();
                if (result.error) {
                    alert('エラー: ' + result.error);
                    processAllBtn.disabled = false;
                    processAllBtn.textContent = '🔊 まとめて処理';
                    return;
                }

                await pollStatus(result.task_id);

            } catch (error) {
                alert('エラー: ' + error.message);
                processAllBtn.disabled = false;
                processAllBtn.textContent = '🔊 まとめて処理';
            }
        });

        clearRegionsBtn.addEventListener('click', () => {
            wsRegions.clearRegions();
            currentSelection = null;
            regionsData = [];
            addToListBtn.disabled = true;
            updateRegionsList();
            statusText.textContent = '全てクリアしました';
        });

        async function pollStatus(newTaskId) {
            const poll = async () => {
                const response = await fetch(`/status/${newTaskId}`);
                const data = await response.json();

                if (data.status === 'processing') {
                    statusText.textContent = data.step || '処理中...';
                    setTimeout(poll, 500);
                } else if (data.status === 'complete') {
                    // 新しいタスクIDでプロジェクトを保存
                    saveProject(newTaskId, currentFilename);
                    window.location.href = `/editor?task_id=${newTaskId}`;
                } else if (data.status === 'error') {
                    alert('エラー: ' + (data.message || '処理に失敗しました'));
                    processAllBtn.disabled = false;
                    processAllBtn.textContent = '🔊 まとめて処理';
                }
            };
            await poll();
        }

        downloadBtn.addEventListener('click', () => {
            window.open(`/download/${taskId}?format=video`, '_blank');
        });

        // 戻るボタン - 最新タスクIDを保存してメインに戻る
        const backBtn = document.getElementById('backBtn');
        backBtn.addEventListener('click', () => {
            sessionStorage.setItem('lastTaskId', taskId);
            window.location.href = '/';
        });

        // タスクIDをセッションに保存
        sessionStorage.setItem('lastTaskId', taskId);

        // キーボードショートカット
        document.addEventListener('keydown', (e) => {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;

            switch (e.code) {
                case 'Space':
                    e.preventDefault();
                    wavesurfer.playPause();
                    break;
                case 'Delete':
                case 'Backspace':
                    e.preventDefault();
                    // 選択中の区間を削除
                    if (currentSelection) {
                        try {
                            currentSelection.region.remove();
                        } catch(e) {}
                        currentSelection = null;
                        addToListBtn.disabled = true;
                        statusText.textContent = '選択を削除しました';
                    }
                    break;
                case 'Slash':
                    if (e.shiftKey) {
                        keyboardHelp.classList.toggle('show');
                    }
                    break;
            }
        });
    </script>
</body>
</html>
'''


@app.route('/editor')
def editor():
    """波形エディタページ"""
    return render_template_string(EDITOR_TEMPLATE)


if __name__ == '__main__':
    print("\\n" + "="*50)
    print("男性ボイスチェンジャー Web GUI")
    print("="*50)
    print("\\nブラウザで以下のURLを開いてください:")
    print("  http://localhost:5003")
    print(f"\\nアップロードフォルダ: {UPLOAD_FOLDER}")
    print(f"出力フォルダ: {OUTPUT_FOLDER}")
    print("\\n終了するには Ctrl+C を押してください")
    print("="*50 + "\\n")
    app.run(host='0.0.0.0', port=5003, debug=False)
