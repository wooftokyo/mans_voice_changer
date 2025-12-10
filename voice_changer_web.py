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

from voice_changer import process_video, pitch_shift_region, extract_audio_only, analyze_pitch_distribution

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
    <title>男性ボイスチェンジャー</title>
    <script src="https://unpkg.com/wavesurfer.js@7"></script>
    <script src="https://unpkg.com/wavesurfer.js@7/dist/plugins/regions.min.js"></script>
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
        <h1>男性ボイスチェンジャー</h1>
        <p class="subtitle">男性の声だけピッチを下げます。自動処理後に手動で編集も可能。</p>

        <div class="tabs">
            <button class="tab active" data-tab="auto">自動処理</button>
            <button class="tab" data-tab="editor">手動編集</button>
        </div>

        <!-- 自動処理タブ -->
        <div class="tab-content active" id="tab-auto">
            <div class="upload-area" id="uploadArea">
                <div class="upload-icon">📁</div>
                <div class="upload-text">ここをクリックまたはファイルをドロップ</div>
                <div class="upload-hint">対応形式: MP4, MOV, AVI, MKV, WebM (最大2GB)</div>
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
                    <div style="display: flex; gap: 10px; margin-bottom: 10px;">
                        <label style="display: flex; align-items: center; cursor: pointer; padding: 10px 15px; border-radius: 8px; background: #e8f4fd; border: 2px solid #4a90d9;">
                            <input type="radio" name="mode" id="modeClearvoice" value="clearvoice" checked style="margin-right: 8px;">
                            <span><strong>ClearVoice AI</strong><br><small style="color: #666;">話者分離（高精度・初回はモデルDL）</small></span>
                        </label>
                        <label style="display: flex; align-items: center; cursor: pointer; padding: 10px 15px; border-radius: 8px; background: #f8f9fa; border: 2px solid #ddd;">
                            <input type="radio" name="mode" id="modeSimple" value="simple" style="margin-right: 8px;">
                            <span><strong>簡易版</strong><br><small style="color: #666;">ピッチ検出（高速）</small></span>
                        </label>
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
                <div class="setting-group" id="segmentGroup">
                    <div class="setting-label">
                        <span>セグメント長（秒）</span>
                        <span class="setting-value" id="segmentValue">0.5</span>
                    </div>
                    <input type="range" id="segmentSlider" min="0.2" max="2.0" step="0.1" value="0.5">
                    <div style="display: flex; justify-content: space-between; font-size: 0.8em; color: #888; margin-top: 5px;">
                        <span>0.2 (細かく)</span>
                        <span>2.0 (粗く)</span>
                    </div>
                </div>
                <div class="setting-group">
                    <div class="setting-label">
                        <span>男性判定閾値（Hz）</span>
                        <span class="setting-value" id="thresholdValue">165</span>
                    </div>
                    <input type="range" id="thresholdSlider" min="120" max="200" step="5" value="165">
                    <div style="display: flex; justify-content: space-between; font-size: 0.8em; color: #888; margin-top: 5px;">
                        <span>120 (厳しく)</span>
                        <span>200 (緩く)</span>
                    </div>
                </div>
            </div>

            <div style="display: flex; gap: 10px; margin-bottom: 10px;">
                <button class="btn btn-secondary" id="analyzeBtn" disabled style="flex: 1;">音声を解析して閾値を推定</button>
            </div>
            <div id="analysisResult" class="analysis-result"></div>
            <button class="btn btn-primary btn-full" id="processBtn" disabled>自動処理開始</button>

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
        </div>

        <!-- 手動編集タブ -->
        <div class="tab-content" id="tab-editor">
            <div class="help-text">
                <strong>使い方:</strong>
                1. 処理済みの動画をアップロード →
                2. 波形上でドラッグして区間を選択 →
                3. 「選択区間をピッチ変換」をクリック
            </div>

            <div class="upload-area" id="editorUploadArea">
                <div class="upload-icon">🎬</div>
                <div class="upload-text">編集する動画をドロップまたはクリック</div>
                <div class="upload-hint">自動処理後の動画、または元の動画</div>
            </div>
            <input type="file" id="editorFileInput" accept=".mp4,.mov,.avi,.mkv,.webm,.m4v,.flv,.wmv">

            <div class="editor-container" id="editorContainer">
                <video id="videoPreview" class="video-preview" controls></video>

                <div class="waveform-container">
                    <div id="waveform"></div>
                </div>

                <div class="editor-controls">
                    <button class="btn btn-secondary" id="playPauseBtn">▶ 再生</button>
                    <span class="time-display" id="timeDisplay">00:00.00 / 00:00.00</span>
                    <div style="flex-grow: 1;"></div>
                    <div class="setting-group" style="width: 200px; margin: 0;">
                        <div class="setting-label">
                            <span>ピッチ</span>
                            <span class="setting-value" id="editorPitchValue">-3.0</span>
                        </div>
                        <input type="range" id="editorPitchSlider" min="-12" max="12" step="0.5" value="-3">
                    </div>
                </div>

                <div class="regions-list" id="regionsList">
                    <h4>選択した区間 (ドラッグで追加)</h4>
                    <div id="regionsContent">
                        <p style="color: #999; font-size: 0.9em;">波形上をドラッグして区間を選択してください</p>
                    </div>
                </div>

                <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                    <button class="btn btn-primary" id="applyPitchBtn" disabled>選択区間をピッチ変換</button>
                    <button class="btn btn-danger" id="clearRegionsBtn">区間をクリア</button>
                </div>

                <div class="progress-container" id="editorProgressContainer">
                    <div class="progress-bar">
                        <div class="progress-fill" id="editorProgressFill"></div>
                    </div>
                    <div class="status-text" id="editorStatusText">処理中...</div>
                </div>

                <div id="editorResultArea"></div>
            </div>
        </div>
    </div>

    <script>
        // タブ切り替え
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                tab.classList.add('active');
                document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
            });
        });

        // ==================== 自動処理タブ ====================
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

        let selectedFile = null;
        let logVisible = true;

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
                                <div class="stat-label">検出セグメント</div>
                                <div class="stat-value">${totalCount}</div>
                            </div>
                            <div class="stat-box">
                                <div class="stat-label">男性と推定</div>
                                <div class="stat-value male">${maleCount}</div>
                            </div>
                            <div class="stat-box">
                                <div class="stat-label">女性と推定</div>
                                <div class="stat-value female">${femaleCount}</div>
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
                    `;
                    analysisResult.classList.add('show');
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

        const segmentSlider = document.getElementById('segmentSlider');
        const segmentValue = document.getElementById('segmentValue');
        const thresholdSlider = document.getElementById('thresholdSlider');
        const thresholdValue = document.getElementById('thresholdValue');

        pitchSlider.addEventListener('input', () => pitchValue.textContent = pitchSlider.value);
        segmentSlider.addEventListener('input', () => segmentValue.textContent = segmentSlider.value);
        thresholdSlider.addEventListener('input', () => thresholdValue.textContent = thresholdSlider.value);

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
            formData.append('use_clearvoice', document.getElementById('modeClearvoice').checked ? 'true' : 'false');

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
                    resultArea.innerHTML = `
                        <div class="success">処理が完了しました!</div>
                        <a href="/download/${taskId}" class="btn btn-success" download>ダウンロード</a>
                        <button class="btn btn-primary" onclick="openInEditor('${taskId}')">エディタで編集</button>
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

        function openInEditor(taskId) {
            document.querySelector('[data-tab="editor"]').click();
            loadVideoInEditor(`/download/${taskId}`);
        }

        // ==================== 手動編集タブ ====================
        const editorUploadArea = document.getElementById('editorUploadArea');
        const editorFileInput = document.getElementById('editorFileInput');
        const editorContainer = document.getElementById('editorContainer');
        const videoPreview = document.getElementById('videoPreview');
        const playPauseBtn = document.getElementById('playPauseBtn');
        const timeDisplay = document.getElementById('timeDisplay');
        const editorPitchSlider = document.getElementById('editorPitchSlider');
        const editorPitchValue = document.getElementById('editorPitchValue');
        const regionsContent = document.getElementById('regionsContent');
        const applyPitchBtn = document.getElementById('applyPitchBtn');
        const clearRegionsBtn = document.getElementById('clearRegionsBtn');
        const editorProgressContainer = document.getElementById('editorProgressContainer');
        const editorProgressFill = document.getElementById('editorProgressFill');
        const editorStatusText = document.getElementById('editorStatusText');
        const editorResultArea = document.getElementById('editorResultArea');

        let wavesurfer = null;
        let wsRegions = null;
        let currentEditorFile = null;
        let editorTaskId = null;

        editorUploadArea.addEventListener('click', () => editorFileInput.click());
        editorUploadArea.addEventListener('dragover', (e) => { e.preventDefault(); editorUploadArea.classList.add('dragover'); });
        editorUploadArea.addEventListener('dragleave', () => editorUploadArea.classList.remove('dragover'));
        editorUploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            editorUploadArea.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) handleEditorFile(e.dataTransfer.files[0]);
        });
        editorFileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) handleEditorFile(e.target.files[0]);
        });

        editorPitchSlider.addEventListener('input', () => editorPitchValue.textContent = editorPitchSlider.value);

        function handleEditorFile(file) {
            currentEditorFile = file;
            const url = URL.createObjectURL(file);
            loadVideoInEditor(url, file);
        }

        function loadVideoInEditor(url, file = null) {
            editorContainer.classList.add('show');
            videoPreview.src = url;

            if (wavesurfer) wavesurfer.destroy();

            wavesurfer = WaveSurfer.create({
                container: '#waveform',
                waveColor: '#4a90d9',
                progressColor: '#357abd',
                cursorColor: '#fff',
                height: 128,
                normalize: true,
                backend: 'MediaElement',
                media: videoPreview
            });

            wsRegions = wavesurfer.registerPlugin(WaveSurfer.Regions.create());

            wsRegions.enableDragSelection({
                color: 'rgba(255, 100, 100, 0.3)',
            });

            wsRegions.on('region-created', updateRegionsList);
            wsRegions.on('region-updated', updateRegionsList);
            wsRegions.on('region-removed', updateRegionsList);

            wavesurfer.on('timeupdate', (time) => {
                timeDisplay.textContent = `${formatTime(time)} / ${formatTime(wavesurfer.getDuration() || 0)}`;
            });

            wavesurfer.on('ready', () => {
                timeDisplay.textContent = `00:00.00 / ${formatTime(wavesurfer.getDuration())}`;
            });

            // ファイルをアップロードしてtaskIdを取得
            if (file) {
                uploadForEditor(file);
            }
        }

        async function uploadForEditor(file) {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('editor_mode', 'true');

            const response = await fetch('/upload_for_editor', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            if (data.task_id) {
                editorTaskId = data.task_id;
            }
        }

        playPauseBtn.addEventListener('click', () => {
            if (wavesurfer) {
                wavesurfer.playPause();
                playPauseBtn.textContent = wavesurfer.isPlaying() ? '⏸ 一時停止' : '▶ 再生';
            }
        });

        function updateRegionsList() {
            const regions = wsRegions.getRegions();
            if (regions.length === 0) {
                regionsContent.innerHTML = '<p style="color: #999; font-size: 0.9em;">波形上をドラッグして区間を選択してください</p>';
                applyPitchBtn.disabled = true;
                return;
            }

            applyPitchBtn.disabled = false;
            regionsContent.innerHTML = regions.map((region, i) => `
                <div class="region-item">
                    <div class="region-info">
                        <strong>区間 ${i + 1}</strong>
                        <div class="region-time">${formatTime(region.start)} - ${formatTime(region.end)}</div>
                    </div>
                    <div class="region-actions">
                        <button class="region-btn region-btn-play" onclick="playRegion('${region.id}')">▶</button>
                        <button class="region-btn region-btn-delete" onclick="deleteRegion('${region.id}')">✕</button>
                    </div>
                </div>
            `).join('');
        }

        window.playRegion = (id) => {
            const region = wsRegions.getRegions().find(r => r.id === id);
            if (region) region.play();
        };

        window.deleteRegion = (id) => {
            const region = wsRegions.getRegions().find(r => r.id === id);
            if (region) region.remove();
        };

        clearRegionsBtn.addEventListener('click', () => {
            wsRegions.clearRegions();
            updateRegionsList();
        });

        applyPitchBtn.addEventListener('click', async () => {
            const regions = wsRegions.getRegions();
            if (regions.length === 0 || !editorTaskId) return;

            applyPitchBtn.disabled = true;
            editorProgressContainer.style.display = 'block';
            editorProgressFill.style.width = '0%';
            editorStatusText.textContent = '処理中...';
            editorResultArea.innerHTML = '';

            const regionsData = regions.map(r => ({
                start: r.start,
                end: r.end
            }));

            try {
                const response = await fetch('/apply_pitch', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        task_id: editorTaskId,
                        regions: regionsData,
                        pitch: parseFloat(editorPitchSlider.value)
                    })
                });

                const data = await response.json();

                if (data.error) {
                    throw new Error(data.error);
                }

                // ポーリング
                const pollEditor = async () => {
                    const res = await fetch(`/status/${data.task_id}`);
                    const status = await res.json();

                    if (status.progress) editorProgressFill.style.width = `${status.progress}%`;
                    if (status.step) editorStatusText.textContent = status.step;

                    if (status.status === 'processing') {
                        setTimeout(pollEditor, 500);
                    } else if (status.status === 'complete') {
                        editorProgressFill.style.width = '100%';
                        editorStatusText.textContent = '完了!';
                        editorResultArea.innerHTML = `
                            <div class="success">ピッチ変換が完了しました!</div>
                            <a href="/download/${data.task_id}" class="btn btn-success" download>ダウンロード</a>
                        `;
                        applyPitchBtn.disabled = false;

                        // 新しい動画を読み込み
                        editorTaskId = data.task_id;
                    } else if (status.status === 'error') {
                        throw new Error(status.message);
                    }
                };
                await pollEditor();

            } catch (error) {
                editorResultArea.innerHTML = `<div class="error">${escapeHtml(error.message)}</div>`;
                editorProgressContainer.style.display = 'none';
                applyPitchBtn.disabled = false;
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
        use_clearvoice = request.form.get('use_clearvoice', 'true').lower() == 'true'
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

        thread = threading.Thread(target=process_task, args=(task_id, input_path, output_path, pitch, segment, threshold, use_clearvoice))
        thread.daemon = True
        thread.start()

        return jsonify({'task_id': task_id})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


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


def process_task(task_id, input_path, output_path, pitch, segment=0.5, threshold=165, use_clearvoice=True):
    try:
        mode = "ClearVoice AI" if use_clearvoice else "簡易版"
        add_log(task_id, f'処理モード: {mode}')
        add_log(task_id, f'ピッチシフト: {pitch}半音')
        add_log(task_id, f'男性判定閾値: {threshold}Hz')
        if not use_clearvoice:
            add_log(task_id, f'セグメント長: {segment}秒')
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

        process_video(input_path, output_path, pitch, segment, threshold, use_clearvoice, progress_callback=progress_callback)

        update_progress(task_id, 100, '完了!')
        add_log(task_id, '処理が完了しました!')
        processing_status[task_id]['status'] = 'complete'

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


@app.route('/download/<task_id>')
def download(task_id):
    if task_id not in processing_status:
        return jsonify({'error': 'タスクが見つかりません'}), 404

    task = processing_status[task_id]
    output_path = task.get('output')

    if not output_path or not os.path.exists(output_path):
        return jsonify({'error': 'ファイルが見つかりません'}), 404

    original_name = task.get('original_filename', 'output.mp4')
    name, _ = os.path.splitext(original_name)
    download_name = f"{name}_processed.mp4"

    return send_file(output_path, as_attachment=True, download_name=download_name)


if __name__ == '__main__':
    print("\n" + "="*50)
    print("男性ボイスチェンジャー Web GUI")
    print("="*50)
    print("\nブラウザで以下のURLを開いてください:")
    print("  http://localhost:5003")
    print(f"\nアップロードフォルダ: {UPLOAD_FOLDER}")
    print(f"出力フォルダ: {OUTPUT_FOLDER}")
    print("\n終了するには Ctrl+C を押してください")
    print("="*50 + "\n")
    app.run(host='0.0.0.0', port=5003, debug=False)
