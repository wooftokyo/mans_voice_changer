#!/usr/bin/env python3
"""
男性の声だけピッチを下げる動画処理アプリ - Web GUI版
"""

import os
import threading
import uuid
from pathlib import Path

from flask import Flask, render_template_string, request, jsonify, send_file

from voice_changer import process_video

app = Flask(__name__)

# 処理状態を保持
processing_status = {}
OUTPUT_FOLDER = "/workspaces/mans_voice_changer/output"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>男性ボイスチェンジャー</title>
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
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 40px;
            max-width: 650px;
            width: 100%;
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
            margin-bottom: 30px;
            font-size: 0.95em;
        }
        .info-box {
            background: #f0f7ff;
            border: 1px solid #d0e3ff;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 20px;
            font-size: 0.9em;
            color: #444;
        }
        .info-box strong {
            color: #357abd;
        }
        .input-group {
            margin-bottom: 20px;
        }
        .input-group label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 500;
        }
        .input-group input[type="text"] {
            width: 100%;
            padding: 12px 15px;
            font-size: 1em;
            border: 2px solid #ddd;
            border-radius: 10px;
            transition: border-color 0.3s;
        }
        .input-group input[type="text"]:focus {
            outline: none;
            border-color: #4a90d9;
        }
        .input-group .hint {
            font-size: 0.85em;
            color: #888;
            margin-top: 5px;
        }
        .settings {
            margin-bottom: 25px;
        }
        .setting-group {
            margin-bottom: 20px;
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
            width: 100%;
            padding: 16px;
            font-size: 1.1em;
            font-weight: bold;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s ease;
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
            display: block;
            text-align: center;
            text-decoration: none;
            background: linear-gradient(135deg, #28a745 0%, #218838 100%);
            color: white;
            margin-top: 15px;
        }
        .progress-container {
            margin-top: 25px;
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
            animation: pulse 1.5s ease-in-out infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        .status-text {
            text-align: center;
            margin-top: 15px;
            color: #666;
            font-size: 0.95em;
        }
        .error {
            background: #fee;
            color: #c00;
            padding: 15px;
            border-radius: 10px;
            margin-top: 20px;
            text-align: center;
        }
        .success {
            background: #efe;
            color: #080;
            padding: 15px;
            border-radius: 10px;
            margin-top: 20px;
            text-align: center;
        }
        .output-path {
            background: #f5f5f5;
            padding: 10px 15px;
            border-radius: 8px;
            font-family: monospace;
            font-size: 0.9em;
            word-break: break-all;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>男性ボイスチェンジャー</h1>
        <p class="subtitle">男性の声だけピッチを下げます。女性の声はオリジナルのまま。</p>

        <div class="info-box">
            <strong>使い方:</strong> 動画ファイルをCodespacesのエクスプローラーにドラッグ＆ドロップしてアップロードし、そのファイルパスを下に入力してください。
        </div>

        <div class="input-group">
            <label for="inputPath">動画ファイルのパス</label>
            <input type="text" id="inputPath" placeholder="/workspaces/mans_voice_changer/video.mp4">
            <div class="hint">例: /workspaces/mans_voice_changer/my_video.mp4</div>
        </div>

        <div class="settings">
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
        </div>

        <button class="btn btn-primary" id="processBtn">処理開始</button>

        <div class="progress-container" id="progressContainer">
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill"></div>
            </div>
            <div class="status-text" id="statusText">処理中...</div>
        </div>

        <div id="resultArea"></div>
    </div>

    <script>
        const inputPath = document.getElementById('inputPath');
        const processBtn = document.getElementById('processBtn');
        const pitchSlider = document.getElementById('pitchSlider');
        const pitchValue = document.getElementById('pitchValue');
        const progressContainer = document.getElementById('progressContainer');
        const progressFill = document.getElementById('progressFill');
        const statusText = document.getElementById('statusText');
        const resultArea = document.getElementById('resultArea');

        // スライダー
        pitchSlider.addEventListener('input', () => {
            pitchValue.textContent = pitchSlider.value;
        });

        // 処理開始
        processBtn.addEventListener('click', async () => {
            const path = inputPath.value.trim();
            if (!path) {
                alert('動画ファイルのパスを入力してください');
                return;
            }

            processBtn.disabled = true;
            progressContainer.style.display = 'block';
            resultArea.innerHTML = '';

            try {
                statusText.textContent = '処理を開始中...';
                progressFill.style.width = '10%';

                const response = await fetch('/process', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        input_path: path,
                        pitch: parseFloat(pitchSlider.value)
                    })
                });

                const data = await response.json();

                if (data.error) {
                    throw new Error(data.error);
                }

                // 処理状態をポーリング
                statusText.textContent = '音声を解析中...';
                progressFill.style.width = '30%';

                await pollStatus(data.task_id, data.output_path);

            } catch (error) {
                resultArea.innerHTML = `<div class="error">エラー: ${error.message}</div>`;
                progressContainer.style.display = 'none';
                processBtn.disabled = false;
            }
        });

        async function pollStatus(taskId, outputPath) {
            const poll = async () => {
                const response = await fetch(`/status/${taskId}`);
                const data = await response.json();

                if (data.status === 'processing') {
                    progressFill.style.width = '50%';
                    statusText.textContent = '男性の声を検出してピッチ変換中...';
                    setTimeout(poll, 1000);
                } else if (data.status === 'complete') {
                    progressFill.style.width = '100%';
                    statusText.textContent = '完了!';
                    resultArea.innerHTML = `
                        <div class="success">処理が完了しました!</div>
                        <div class="output-path"><strong>出力ファイル:</strong><br>${outputPath}</div>
                        <a href="/download/${taskId}" class="btn btn-success" download>ダウンロード</a>
                    `;
                    processBtn.disabled = false;
                } else if (data.status === 'error') {
                    throw new Error(data.message || '処理中にエラーが発生しました');
                }
            };

            await poll();
        }
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/process', methods=['POST'])
def process():
    try:
        data = request.get_json()
        input_path = data.get('input_path', '').strip()
        pitch = float(data.get('pitch', -3.0))

        if not input_path:
            return jsonify({'error': 'ファイルパスを入力してください'}), 400

        if not os.path.exists(input_path):
            return jsonify({'error': f'ファイルが見つかりません: {input_path}'}), 400

        # タスクIDを生成
        task_id = str(uuid.uuid4())

        # 出力パス
        input_name = Path(input_path).stem
        output_path = os.path.join(OUTPUT_FOLDER, f'{input_name}_processed.mp4')

        # 処理状態を初期化
        processing_status[task_id] = {
            'status': 'processing',
            'input': input_path,
            'output': output_path
        }

        # バックグラウンドで処理
        thread = threading.Thread(
            target=process_task,
            args=(task_id, input_path, output_path, pitch)
        )
        thread.daemon = True
        thread.start()

        return jsonify({'task_id': task_id, 'output_path': output_path})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


def process_task(task_id, input_path, output_path, pitch):
    try:
        process_video(input_path, output_path, pitch)
        processing_status[task_id]['status'] = 'complete'
    except Exception as e:
        processing_status[task_id]['status'] = 'error'
        processing_status[task_id]['message'] = str(e)


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
    if task['status'] != 'complete':
        return jsonify({'error': '処理が完了していません'}), 400

    return send_file(
        task['output'],
        as_attachment=True,
        download_name=Path(task['output']).name
    )


if __name__ == '__main__':
    print("\n" + "="*50)
    print("男性ボイスチェンジャー Web GUI")
    print("="*50)
    print("\nブラウザで以下のURLを開いてください:")
    print("  http://localhost:5000")
    print(f"\n出力フォルダ: {OUTPUT_FOLDER}")
    print("\n終了するには Ctrl+C を押してください")
    print("="*50 + "\n")
    app.run(host='0.0.0.0', port=5000, debug=False)
