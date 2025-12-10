#!/usr/bin/env python3
"""
男性の声だけピッチを下げる動画処理アプリ
ClearVoice-Studioを使用した話者分離 + ピッチシフト
"""

import argparse
import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import librosa
import soundfile as sf

# ClearVoice のグローバルインスタンス（遅延ロード）
_clearvoice_separator = None


def get_clearvoice_separator():
    """ClearVoice話者分離モデルを取得（初回のみロード）"""
    global _clearvoice_separator
    if _clearvoice_separator is None:
        from clearvoice import ClearVoice
        print("ClearVoice話者分離モデルを初期化中...")
        _clearvoice_separator = ClearVoice(
            task='speech_separation',
            model_names=['MossFormer2_SS_16K']
        )
        print("ClearVoice初期化完了")
    return _clearvoice_separator


def separate_speakers_clearvoice(audio_path: str, output_dir: str, progress_callback=None) -> list:
    """
    ClearVoice-Studioを使用して話者を分離する

    Returns:
        分離された音声ファイルのパスのリスト
    """
    def log(message):
        print(message)
        if progress_callback:
            progress_callback('separate', message)

    log("ClearVoice話者分離を開始...")

    # 16kHzにリサンプリング（ClearVoiceの要求）
    log("音声を16kHzにリサンプリング中...")
    y, sr = librosa.load(audio_path, sr=16000, mono=True)

    # 一時ファイルに保存
    temp_input = os.path.join(output_dir, "temp_16k.wav")
    sf.write(temp_input, y, 16000)

    # ClearVoiceで分離（online_write=Trueでファイルに直接書き出し）
    log("話者分離AIを実行中（初回はモデルダウンロードに時間がかかります）...")
    separator = get_clearvoice_separator()

    # 分離実行（ファイルに直接出力）
    # ClearVoiceは output_path/<model_name>/ にファイルを出力する
    separator(input_path=temp_input, online_write=True, output_path=output_dir)

    # 出力されたファイルを探す
    separated_files = []
    import glob
    # ClearVoiceは <output_dir>/MossFormer2_SS_16K/<input_filename>_s1.wav, _s2.wav 形式で出力
    # 例: temp_16k.wav -> temp_16k_s1.wav, temp_16k_s2.wav
    patterns = [
        os.path.join(output_dir, "MossFormer2_SS_16K", "*_s*.wav"),
        os.path.join(output_dir, "MossFormer2_SS_16K", "*.wav"),
        os.path.join(output_dir, "**", "*_s*.wav"),
        os.path.join(output_dir, "**", "*.wav"),
    ]
    log(f"出力ディレクトリ内容: {os.listdir(output_dir)}")
    for pattern in patterns:
        found = glob.glob(pattern, recursive=True)
        for f in found:
            # temp_inputそのものは除外、但し_s1/_s2が付いた分離ファイルは含める
            if f != temp_input and f not in separated_files and "_s" in os.path.basename(f):
                separated_files.append(f)
                log(f"分離ファイル検出: {f}")

    if not separated_files:
        log("警告: 分離ファイルが見つかりませんでした")
    else:
        log(f"分離完了: {len(separated_files)}トラック")

    # 一時ファイル削除
    try:
        os.remove(temp_input)
    except:
        pass

    log(f"分離完了: {len(separated_files)}トラック")
    return separated_files


def process_with_clearvoice(
    audio_path: str,
    output_path: str,
    pitch_shift_semitones: float = -3.0,
    male_threshold: float = 165,
    progress_callback=None
) -> None:
    """
    ClearVoice話者分離を使用して男性の声のみピッチを下げる
    """
    def log(step, message):
        print(message)
        if progress_callback:
            progress_callback(step, message)

    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. ClearVoiceで話者分離
        log('separate', "ステップ1: ClearVoice話者分離...")
        separated_files = separate_speakers_clearvoice(
            audio_path, tmpdir,
            lambda step, msg: log('separate', msg)
        )

        if not separated_files:
            log('error', "話者分離に失敗しました")
            return

        # 2. 元の音声を読み込み（44100Hzのまま）
        log('analyze', "ステップ2: 元音声を読み込み中...")
        y_original, sr_original = librosa.load(audio_path, sr=44100, mono=False)
        if y_original.ndim == 1:
            y_original = np.stack([y_original, y_original])

        # 3. 各話者のピッチを分析
        log('analyze', "ステップ3: 各話者のピッチを分析中...")
        speaker_pitches = []

        for i, speaker_file in enumerate(separated_files):
            # 分離された音声を読み込み
            y_speaker, sr_speaker = librosa.load(speaker_file, sr=16000, mono=True)

            # ピッチを推定（長い音声用の関数を使用）
            pitch = estimate_pitch_for_speaker(y_speaker, sr_speaker)
            is_male = is_male_voice(pitch, male_threshold)

            speaker_pitches.append({
                'file': speaker_file,
                'pitch': pitch,
                'is_male': is_male
            })

            gender = "男性" if is_male else "女性"
            log('analyze', f"  話者{i+1}: {pitch:.1f}Hz → {gender}")

        # 4. 男性話者の音声をピッチシフト
        log('pitch', "ステップ4: 男性話者の音声をピッチシフト...")

        # 分離された各話者の音声を44100Hzで再読み込み・処理
        processed_speakers = []

        for i, sp_info in enumerate(speaker_pitches):
            # 16kHz音声を44100Hzにリサンプリング
            y_sp_16k, _ = librosa.load(sp_info['file'], sr=16000, mono=True)
            y_sp = librosa.resample(y_sp_16k, orig_sr=16000, target_sr=44100)

            if sp_info['is_male']:
                log('pitch', f"  話者{i+1}（男性）をピッチシフト中...")
                y_sp = pitch_shift_audio(y_sp, 44100, pitch_shift_semitones)
            else:
                log('pitch', f"  話者{i+1}（女性）はそのまま")

            processed_speakers.append(y_sp)

        # 5. 処理済み音声を合成
        log('merge', "ステップ5: 音声を合成中...")

        # 長さを揃える
        max_len = max(len(sp) for sp in processed_speakers)
        target_len = y_original.shape[1]

        # 合成
        y_mixed = np.zeros(target_len)
        for sp in processed_speakers:
            # 長さを揃える
            if len(sp) < target_len:
                sp = np.pad(sp, (0, target_len - len(sp)))
            elif len(sp) > target_len:
                sp = sp[:target_len]
            y_mixed += sp

        # 正規化
        if len(processed_speakers) > 1:
            y_mixed = y_mixed / len(processed_speakers)

        # クリッピング防止
        max_val = np.max(np.abs(y_mixed))
        if max_val > 1.0:
            y_mixed = y_mixed / max_val * 0.95

        # ステレオに変換
        y_stereo = np.stack([y_mixed, y_mixed])

        # 6. 保存
        sf.write(output_path, y_stereo.T, 44100)
        log('merge', f"処理済み音声を保存: {output_path}")


def extract_audio(video_path: str, audio_path: str) -> None:
    """動画から音声を抽出する"""
    ffmpeg_paths = [
        'ffmpeg',
        '/opt/homebrew/bin/ffmpeg',
        '/usr/local/bin/ffmpeg',
        '/usr/bin/ffmpeg'
    ]
    ffmpeg_cmd = 'ffmpeg'
    for path in ffmpeg_paths:
        if os.path.exists(path):
            ffmpeg_cmd = path
            break

    cmd = [
        ffmpeg_cmd, '-y', '-i', video_path,
        '-vn', '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '2',
        audio_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def merge_audio_video(video_path: str, audio_path: str, output_path: str) -> None:
    """処理した音声と元の動画を結合する"""
    ffmpeg_paths = [
        'ffmpeg',
        '/opt/homebrew/bin/ffmpeg',
        '/usr/local/bin/ffmpeg',
        '/usr/bin/ffmpeg'
    ]
    ffmpeg_cmd = 'ffmpeg'
    for path in ffmpeg_paths:
        if os.path.exists(path):
            ffmpeg_cmd = path
            break

    cmd = [
        ffmpeg_cmd, '-y', '-i', video_path, '-i', audio_path,
        '-c:v', 'copy', '-map', '0:v:0', '-map', '1:a:0',
        '-shortest', output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def estimate_pitch_for_segment(y: np.ndarray, sr: int) -> float:
    """セグメントの平均ピッチを推定する"""
    if len(y) < sr * 0.05:  # 50ms未満は無視
        return 0

    try:
        f0, voiced_flag, voiced_probs = librosa.pyin(
            y,
            fmin=50,
            fmax=400,
            sr=sr,
            frame_length=1024,  # より細かく
            hop_length=256
        )
        valid_f0 = f0[~np.isnan(f0)]
        if len(valid_f0) > 0:
            return np.median(valid_f0)
    except:
        pass

    return 0


def estimate_pitch_for_speaker(y: np.ndarray, sr: int, num_samples: int = 20) -> float:
    """
    話者の音声全体からピッチを推定する（長い音声ファイル用）
    有声部分を検出し、複数箇所からサンプリングして中央値を取る
    """
    if len(y) < sr * 0.5:  # 0.5秒未満は通常の関数を使用
        return estimate_pitch_for_segment(y, sr)

    # RMS（音量）で有声部分を検出
    frame_length = 2048
    hop_length = 512
    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]

    # 音量の閾値（全体のRMS平均の20%以上を有声とみなす）
    rms_threshold = np.mean(rms) * 0.2
    voiced_frames = np.where(rms > rms_threshold)[0]

    if len(voiced_frames) < 10:
        return 0

    # 有声フレームからランダムにサンプリング
    sample_indices = np.linspace(0, len(voiced_frames) - 1, min(num_samples, len(voiced_frames)), dtype=int)
    sample_frames = voiced_frames[sample_indices]

    pitches = []
    segment_duration = int(sr * 0.5)  # 0.5秒のセグメント

    for frame_idx in sample_frames:
        # フレームインデックスをサンプルインデックスに変換
        start_sample = frame_idx * hop_length
        end_sample = min(start_sample + segment_duration, len(y))

        if end_sample - start_sample < sr * 0.1:  # 0.1秒未満はスキップ
            continue

        segment = y[start_sample:end_sample]
        pitch = estimate_pitch_for_segment(segment, sr)

        if pitch > 0:
            pitches.append(pitch)

    if len(pitches) > 0:
        return np.median(pitches)

    return 0


def is_male_voice(pitch: float, threshold: float = 165) -> bool:
    """ピッチから男性の声かどうかを判定する"""
    return 0 < pitch < threshold


def pitch_shift_audio(y: np.ndarray, sr: int, semitones: float) -> np.ndarray:
    """音声のピッチをシフトする"""
    return librosa.effects.pitch_shift(y, sr=sr, n_steps=semitones)


def process_simple(
    audio_path: str,
    output_path: str,
    pitch_shift_semitones: float = -3.0,
    segment_duration: float = 0.5,
    male_threshold: float = 165,
    progress_callback=None
) -> None:
    """
    簡易版：ピッチ検出ベースで男性の声のみピッチを下げる
    Demucsを使わないので高速
    """
    def log(step, message):
        print(message)
        if progress_callback:
            progress_callback(step, message)

    # 音声を読み込み
    log('analyze', "音声ファイルを読み込み中...")
    y, sr = librosa.load(audio_path, sr=44100, mono=False)

    # モノラルの場合はステレオに変換
    if y.ndim == 1:
        y = np.stack([y, y])

    y_mono = librosa.to_mono(y)

    # セグメントごとに処理
    segment_samples = int(segment_duration * sr)
    num_segments = len(y_mono) // segment_samples + 1

    log('pitch', f"セグメント数: {num_segments} (各{segment_duration}秒)")
    log('pitch', f"男性判定閾値: {male_threshold}Hz")

    y_processed = y.copy()

    male_segments = 0
    female_segments = 0
    silent_segments = 0

    for i in range(num_segments):
        start = i * segment_samples
        end = min((i + 1) * segment_samples, len(y_mono))

        if start >= len(y_mono):
            break

        segment_mono = y_mono[start:end]

        # 無音チェック（閾値を下げる）
        if np.max(np.abs(segment_mono)) < 0.005:
            silent_segments += 1
            continue

        # ピッチを推定
        pitch = estimate_pitch_for_segment(segment_mono, sr)

        if pitch == 0:
            continue

        # 男性の声かどうか判定
        if is_male_voice(pitch, male_threshold):
            male_segments += 1

            # 男性の声：ピッチを下げる
            for ch in range(y.shape[0]):
                segment = y[ch, start:end]
                processed = pitch_shift_audio(segment, sr, pitch_shift_semitones)

                # 長さを調整
                target_len = end - start
                if len(processed) > target_len:
                    processed = processed[:target_len]
                elif len(processed) < target_len:
                    processed = np.pad(processed, (0, target_len - len(processed)))

                # クロスフェード（短め）
                fade_len = min(int(0.01 * sr), len(processed) // 4)
                if fade_len > 0:
                    if start > 0:
                        fade_in = np.linspace(0, 1, fade_len)
                        processed[:fade_len] = processed[:fade_len] * fade_in + y[ch, start:start+fade_len] * (1 - fade_in)
                    if end < y.shape[1]:
                        fade_out = np.linspace(1, 0, fade_len)
                        processed[-fade_len:] = processed[-fade_len:] * fade_out + y[ch, end-fade_len:end] * (1 - fade_out)

                y_processed[ch, start:end] = processed
        else:
            female_segments += 1

        # 進捗表示（10セグメントごと）
        if i > 0 and i % 10 == 0:
            progress = int((i / num_segments) * 100)
            log('pitch', f"  進捗: {progress}% ({i}/{num_segments})")

    log('pitch', f"結果: 男性={male_segments}, 女性={female_segments}, 無音={silent_segments}")

    # クリッピング防止
    max_val = np.max(np.abs(y_processed))
    if max_val > 1.0:
        y_processed = y_processed / max_val * 0.95

    # 保存
    sf.write(output_path, y_processed.T, sr)
    log('merge', f"処理済み音声を保存")


def process_video(
    input_video: str,
    output_video: str,
    pitch_shift_semitones: float = -3.0,
    segment_duration: float = 0.5,
    male_threshold: float = 165,
    use_clearvoice: bool = True,
    progress_callback=None
) -> None:
    """
    動画を処理して男性の声のみピッチを下げる

    use_clearvoice: TrueならClearVoice話者分離を使用（高精度）、Falseなら簡易版
    segment_duration: 簡易版のセグメント長（秒）
    male_threshold: 男性判定のピッチ閾値（Hz）
    """
    def log(step, message):
        print(message)
        if progress_callback:
            progress_callback(step, message)

    mode = "ClearVoice話者分離" if use_clearvoice else "簡易版"
    log('extract', f"入力動画: {input_video}")
    log('extract', f"出力動画: {output_video}")
    log('extract', f"処理モード: {mode}")
    log('extract', f"ピッチシフト: {pitch_shift_semitones} semitones")
    log('extract', f"男性判定閾値: {male_threshold}Hz")

    with tempfile.TemporaryDirectory() as tmpdir:
        extracted_audio = os.path.join(tmpdir, "extracted.wav")
        processed_audio = os.path.join(tmpdir, "processed.wav")

        # 1. 動画から音声を抽出
        log('extract', "1. 音声を抽出中...")
        extract_audio(input_video, extracted_audio)
        log('extract', "音声抽出完了")

        # 2. 音声処理
        if use_clearvoice:
            # ClearVoice話者分離モード
            log('separate', "2. ClearVoice話者分離で処理中...")
            process_with_clearvoice(
                extracted_audio,
                processed_audio,
                pitch_shift_semitones,
                male_threshold,
                progress_callback
            )
        else:
            # 簡易版モード
            log('analyze', "2. 簡易版で処理中...")
            process_simple(
                extracted_audio,
                processed_audio,
                pitch_shift_semitones,
                segment_duration,
                male_threshold,
                progress_callback
            )

        # 3. 処理した音声と元の動画を結合
        log('combine', "3. 動画と音声を結合中...")
        merge_audio_video(input_video, processed_audio, output_video)

    log('combine', f"完了！出力ファイル: {output_video}")


def extract_audio_only(video_path: str, output_path: str) -> None:
    """動画から音声のみを抽出してWAVで保存"""
    extract_audio(video_path, output_path)


def analyze_pitch_distribution(video_path: str, segment_duration: float = 0.3, progress_callback=None) -> dict:
    """
    動画の音声を分析してピッチ分布を取得する

    Returns:
        {
            'pitches': [float, ...],  # 検出されたピッチのリスト
            'male_pitches': [float, ...],  # 男性と思われるピッチ
            'female_pitches': [float, ...],  # 女性と思われるピッチ
            'suggested_threshold': float,  # 推奨閾値
            'stats': {
                'min': float, 'max': float, 'mean': float, 'median': float
            }
        }
    """
    import tempfile

    def log(message):
        print(message)
        if progress_callback:
            progress_callback(message)

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = os.path.join(tmpdir, "audio.wav")

        log("音声を抽出中...")
        extract_audio(video_path, audio_path)

        log("音声ファイルを読み込み中...")
        y, sr = librosa.load(audio_path, sr=44100, mono=True)

        # セグメントごとにピッチを検出
        segment_samples = int(segment_duration * sr)
        num_segments = len(y) // segment_samples + 1

        log(f"セグメント数: {num_segments} (各{segment_duration}秒)")

        pitches = []

        for i in range(num_segments):
            start = i * segment_samples
            end = min((i + 1) * segment_samples, len(y))

            if start >= len(y):
                break

            segment = y[start:end]

            # 無音チェック
            if np.max(np.abs(segment)) < 0.005:
                continue

            # ピッチを推定
            pitch = estimate_pitch_for_segment(segment, sr)

            if pitch > 0:
                pitches.append(pitch)

            # 進捗表示（20セグメントごと）
            if i > 0 and i % 20 == 0:
                progress = int((i / num_segments) * 100)
                log(f"ピッチ解析中... {progress}% ({i}/{num_segments})")

        if not pitches:
            return {
                'pitches': [],
                'male_pitches': [],
                'female_pitches': [],
                'suggested_threshold': 165,
                'stats': None
            }

        pitches_array = np.array(pitches)

        # 統計を計算
        stats = {
            'min': float(np.min(pitches_array)),
            'max': float(np.max(pitches_array)),
            'mean': float(np.mean(pitches_array)),
            'median': float(np.median(pitches_array))
        }

        # ピッチ分布から閾値を推定
        # 男性: 85-180Hz, 女性: 165-255Hz の一般的な範囲
        # 二峰性があれば谷を閾値に

        # ヒストグラムで分布を分析
        hist, bin_edges = np.histogram(pitches_array, bins=30, range=(50, 350))
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

        # 谷を探す（二峰性の場合）
        suggested_threshold = 165  # デフォルト

        if len(hist) > 5:
            # スムージング
            from scipy.ndimage import uniform_filter1d
            smoothed = uniform_filter1d(hist.astype(float), size=3)

            # 100-200Hzの範囲で谷を探す
            for j in range(len(bin_centers)):
                if 120 < bin_centers[j] < 200:
                    # 谷の検出（前後より小さい）
                    if j > 0 and j < len(smoothed) - 1:
                        if smoothed[j] < smoothed[j-1] and smoothed[j] < smoothed[j+1]:
                            if smoothed[j] < np.mean(smoothed) * 0.7:
                                suggested_threshold = bin_centers[j]
                                break

        # 男性/女性に分類
        male_pitches = [p for p in pitches if p < suggested_threshold]
        female_pitches = [p for p in pitches if p >= suggested_threshold]

        log(f"解析完了: {len(pitches)}セグメント検出")
        log(f"男性推定: {len(male_pitches)}, 女性推定: {len(female_pitches)}")
        log(f"推奨閾値: {round(suggested_threshold)}Hz")

        return {
            'pitches': pitches,
            'male_pitches': male_pitches,
            'female_pitches': female_pitches,
            'suggested_threshold': round(suggested_threshold),
            'stats': stats,
            'histogram': {
                'counts': hist.tolist(),
                'bins': bin_centers.tolist()
            }
        }


def pitch_shift_region(
    input_video: str,
    output_video: str,
    regions: list,
    pitch_shift_semitones: float = -3.0
) -> None:
    """
    動画の指定区間のみピッチシフトする

    regions: [{'start': float, 'end': float}, ...]  秒単位
    """
    print(f"入力動画: {input_video}")
    print(f"出力動画: {output_video}")
    print(f"区間数: {len(regions)}")
    print(f"ピッチシフト: {pitch_shift_semitones} semitones")

    with tempfile.TemporaryDirectory() as tmpdir:
        extracted_audio = os.path.join(tmpdir, "extracted.wav")
        processed_audio = os.path.join(tmpdir, "processed.wav")

        # 1. 動画から音声を抽出
        print("1. 音声を抽出中...")
        extract_audio(input_video, extracted_audio)

        # 2. 音声を読み込み
        print("2. 音声を処理中...")
        y, sr = librosa.load(extracted_audio, sr=44100, mono=False)

        # モノラルの場合はステレオに変換
        if y.ndim == 1:
            y = np.stack([y, y])

        # 3. 各区間をピッチシフト
        for i, region in enumerate(regions):
            start_sec = region['start']
            end_sec = region['end']
            start_sample = int(start_sec * sr)
            end_sample = int(end_sec * sr)

            # 範囲チェック
            if start_sample >= y.shape[1]:
                continue
            end_sample = min(end_sample, y.shape[1])

            print(f"  区間 {i+1}: {start_sec:.2f}s - {end_sec:.2f}s をピッチシフト")

            # 各チャンネルをピッチシフト
            for ch in range(y.shape[0]):
                segment = y[ch, start_sample:end_sample]
                shifted = pitch_shift_audio(segment, sr, pitch_shift_semitones)

                # 長さを調整
                target_len = end_sample - start_sample
                if len(shifted) > target_len:
                    shifted = shifted[:target_len]
                elif len(shifted) < target_len:
                    shifted = np.pad(shifted, (0, target_len - len(shifted)))

                # クロスフェード
                fade_len = min(int(0.01 * sr), len(shifted) // 4)
                if fade_len > 0:
                    if start_sample > 0:
                        fade_in = np.linspace(0, 1, fade_len)
                        shifted[:fade_len] = shifted[:fade_len] * fade_in + y[ch, start_sample:start_sample+fade_len] * (1 - fade_in)
                    if end_sample < y.shape[1]:
                        fade_out = np.linspace(1, 0, fade_len)
                        shifted[-fade_len:] = shifted[-fade_len:] * fade_out + y[ch, end_sample-fade_len:end_sample] * (1 - fade_out)

                y[ch, start_sample:end_sample] = shifted

        # 4. クリッピング防止
        max_val = np.max(np.abs(y))
        if max_val > 1.0:
            y = y / max_val * 0.95

        # 5. 保存
        sf.write(processed_audio, y.T, sr)
        print(f"  処理済み音声: {processed_audio}")

        # 6. 動画と音声を結合
        print("3. 動画と音声を結合中...")
        merge_audio_video(input_video, processed_audio, output_video)

    print(f"完了！出力ファイル: {output_video}")


def main():
    parser = argparse.ArgumentParser(
        description='男性の声だけピッチを下げる動画処理アプリ'
    )
    parser.add_argument(
        'input',
        help='入力動画ファイルのパス'
    )
    parser.add_argument(
        '-o', '--output',
        help='出力動画ファイルのパス（デフォルト: input_processed.mp4）'
    )
    parser.add_argument(
        '-p', '--pitch',
        type=float,
        default=-3.0,
        help='ピッチシフト量（半音単位、デフォルト: -3.0）'
    )
    parser.add_argument(
        '-s', '--segment',
        type=float,
        default=0.5,
        help='セグメント長（秒、デフォルト: 0.5）'
    )
    parser.add_argument(
        '-t', '--threshold',
        type=float,
        default=165,
        help='男性判定のピッチ閾値（Hz、デフォルト: 165）'
    )

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"エラー: 入力ファイルが見つかりません: {args.input}")
        return 1

    if args.output:
        output_path = args.output
    else:
        input_path = Path(args.input)
        output_path = str(input_path.parent / f"{input_path.stem}_processed{input_path.suffix}")

    process_video(args.input, output_path, args.pitch, args.segment, args.threshold)

    return 0


if __name__ == '__main__':
    exit(main())
