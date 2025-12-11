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

# ffmpegへのPATHを確保（inaSpeechSegmenter等が必要とする）
ffmpeg_paths = ['/opt/homebrew/bin', '/usr/local/bin', '/usr/bin']
for p in ffmpeg_paths:
    if p not in os.environ.get('PATH', ''):
        os.environ['PATH'] = p + ':' + os.environ.get('PATH', '')

import numpy as np
import librosa
import soundfile as sf

# グローバルインスタンス（遅延ロード）
_clearvoice_separator = None
_gender_segmenter = None
_ina_segmenter = None

# inaSpeechSegmenterを使うために環境変数を設定
os.environ['TF_USE_LEGACY_KERAS'] = '1'


def _patch_torch_numpy_compat():
    """
    torch/numpy互換性問題を修正するパッチ
    'expected np.ndarray (got numpy.ndarray)' エラー対策
    このアプリ内でのみ有効
    """
    try:
        import torch
        # torchの内部でnumpy配列チェックを緩和
        original_from_numpy = torch.from_numpy
        def patched_from_numpy(arr):
            if hasattr(arr, '__array__'):
                arr = np.asarray(arr)
            return original_from_numpy(arr)
        torch.from_numpy = patched_from_numpy
    except ImportError:
        pass

# アプリ起動時にパッチを適用
_patch_torch_numpy_compat()


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


def get_ina_segmenter():
    """inaSpeechSegmenter（CNN性別判定）を取得（初回のみロード）"""
    global _ina_segmenter
    if _ina_segmenter is None:
        from inaSpeechSegmenter import Segmenter
        print("inaSpeechSegmenter（CNN性別判定）を初期化中...")
        _ina_segmenter = Segmenter()
        print("inaSpeechSegmenter初期化完了")
    return _ina_segmenter


def detect_gender_ina(audio_path: str, progress_callback=None) -> list:
    """
    inaSpeechSegmenterを使用してCNNベースの性別判定を行う

    Returns:
        list of tuples: [(label, start, end), ...]
        labelは 'male', 'female', 'noEnergy', 'music' など
    """
    log = progress_callback or print
    log("inaSpeechSegmenter（CNN）で性別を判定中...")

    seg = get_ina_segmenter()
    result = seg(audio_path)

    # 統計を計算
    male_time = 0
    female_time = 0
    for label, start, end in result:
        duration = end - start
        if label == 'male':
            male_time += duration
        elif label == 'female':
            female_time += duration

    log(f"CNN判定結果: 男性={male_time:.1f}秒, 女性={female_time:.1f}秒")

    return result


def postprocess_gender_segments(segments: list, min_duration: float = 0.3) -> list:
    """
    性別判定結果の後処理: 短い孤立判定を周囲に統合

    例: [女性, 女性, 男性(0.2秒), 女性, 女性] → [女性, 女性, 女性, 女性, 女性]

    Args:
        segments: [(label, start, end), ...] のリスト
        min_duration: この秒数未満の孤立セグメントを統合対象とする

    Returns:
        修正されたセグメントリスト
    """
    if len(segments) <= 2:
        return segments

    result = list(segments)

    # 複数回パスして孤立セグメントを除去
    for _ in range(2):
        i = 1
        while i < len(result) - 1:
            label, start, end = result[i]
            duration = end - start

            # 音声セグメント（male/female）のみ対象
            if label not in ('male', 'female'):
                i += 1
                continue

            # 短いセグメントかどうか
            if duration >= min_duration:
                i += 1
                continue

            # 前後のセグメントを取得
            prev_label, _, _ = result[i - 1]
            next_label, _, _ = result[i + 1]

            # 前後が同じラベルで、現在と異なる場合は統合
            if prev_label == next_label and prev_label != label and prev_label in ('male', 'female'):
                # 現在のセグメントを前後と同じラベルに変更
                result[i] = (prev_label, start, end)

            i += 1

    return result


def detect_gender_for_segment(y: np.ndarray, sr: int) -> dict:
    """
    短いセグメント用の軽量な性別判定（ダブルチェック用）

    フォルマント比率とスペクトル特徴で簡易判定

    Returns:
        {'is_male': bool, 'confidence': float}
    """
    if len(y) < sr * 0.1:  # 0.1秒未満は判定不可
        return {'is_male': True, 'confidence': 0.0}

    male_score = 0.0
    total_weight = 0.0

    # 1. スペクトル重心（声の明るさ）
    try:
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        mean_centroid = np.mean(centroid[centroid > 0]) if np.any(centroid > 0) else 0

        if mean_centroid > 0:
            # 男性: 1000-2000Hz, 女性: 2000-3500Hz
            if mean_centroid < 1800:
                male_score += 1.0
            elif mean_centroid < 2500:
                male_score += 0.5
            else:
                male_score += 0.0
            total_weight += 1.0
    except:
        pass

    # 2. スペクトルロールオフ
    try:
        rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, roll_percent=0.85)[0]
        mean_rolloff = np.mean(rolloff[rolloff > 0]) if np.any(rolloff > 0) else 0

        if mean_rolloff > 0:
            if mean_rolloff < 3500:
                male_score += 1.0
            elif mean_rolloff < 5000:
                male_score += 0.5
            else:
                male_score += 0.0
            total_weight += 1.0
    except:
        pass

    # 3. ピッチ（F0）
    try:
        f0, _, _ = librosa.pyin(y, fmin=50, fmax=400, sr=sr)
        valid_f0 = f0[~np.isnan(f0)]
        if len(valid_f0) > 0:
            mean_f0 = np.median(valid_f0)
            if mean_f0 < 165:
                male_score += 1.0
            elif mean_f0 < 200:
                male_score += 0.5
            else:
                male_score += 0.0
            total_weight += 1.5  # ピッチは重要なので重み大きめ
    except:
        pass

    # 最終スコア
    if total_weight > 0:
        final_score = male_score / total_weight
    else:
        final_score = 0.5

    return {
        'is_male': final_score >= 0.5,
        'confidence': abs(final_score - 0.5) * 2
    }


def detect_gender_by_timbre(audio_path: str, progress_callback=None) -> dict:
    """
    声質（timbre）から性別を判定する

    以下の特徴量を使用：
    1. フォルマント周波数（F1, F2, F3） - 声道の長さを反映、男性は約10-20%低い
    2. MFCC（メル周波数ケプストラム係数） - 声道の形状
    3. スペクトル重心 - 声の「明るさ」
    4. スペクトルロールオフ - 高周波成分の分布

    Returns:
        dict: {'gender': 'male'/'female', 'confidence': float, 'features': dict}
    """
    log = progress_callback or print

    log("声質（timbre）から性別を判定中...")

    try:
        import parselmouth
        from parselmouth import praat
        has_parselmouth = True
    except ImportError:
        has_parselmouth = False
        log("警告: parselmouthがインストールされていません。フォルマント分析をスキップします")

    # 音声読み込み
    sr = 16000  # 16kHzで統一
    y, _ = librosa.load(audio_path, sr=sr, mono=True)

    # 無音チェック
    if np.max(np.abs(y)) < 0.01:
        return {'gender': 'unknown', 'confidence': 0.0, 'features': {}}

    features = {}
    male_score = 0
    total_weight = 0

    # === 1. フォルマント分析（parselmouth使用） ===
    if has_parselmouth:
        try:
            log("  フォルマント周波数を分析中...")
            sound = parselmouth.Sound(y, sampling_frequency=sr)

            # フォルマント抽出（男性向け設定: max_formant=5000）
            # 女性は5500Hz、男性は5000Hzが推奨
            formant = sound.to_formant_burg(
                time_step=0.01,
                max_number_of_formants=4,
                maximum_formant=5250,  # 男女中間値
                window_length=0.025,
                pre_emphasis_from=50.0
            )

            # 各時点でフォルマントを取得
            f1_values = []
            f2_values = []
            f3_values = []

            for t in formant.ts():
                f1 = formant.get_value_at_time(1, t)
                f2 = formant.get_value_at_time(2, t)
                f3 = formant.get_value_at_time(3, t)
                if not np.isnan(f1) and f1 > 0:
                    f1_values.append(f1)
                if not np.isnan(f2) and f2 > 0:
                    f2_values.append(f2)
                if not np.isnan(f3) and f3 > 0:
                    f3_values.append(f3)

            if f1_values and f2_values and f3_values:
                mean_f1 = np.median(f1_values)
                mean_f2 = np.median(f2_values)
                mean_f3 = np.median(f3_values)

                features['F1'] = mean_f1
                features['F2'] = mean_f2
                features['F3'] = mean_f3

                # フォルマント判定
                # 研究データ: 男性F1は女性より約20%低い、F2は約15%低い
                # 典型的な男性: F1≈500Hz, F2≈1500Hz, F3≈2500Hz
                # 典型的な女性: F1≈600Hz, F2≈1750Hz, F3≈2800Hz

                f1_male_score = 1.0 if mean_f1 < 550 else (0.5 if mean_f1 < 650 else 0.0)
                f2_male_score = 1.0 if mean_f2 < 1600 else (0.5 if mean_f2 < 1800 else 0.0)
                f3_male_score = 1.0 if mean_f3 < 2650 else (0.5 if mean_f3 < 2900 else 0.0)

                formant_score = (f1_male_score * 0.4 + f2_male_score * 0.35 + f3_male_score * 0.25)
                male_score += formant_score * 3.0  # 重み3
                total_weight += 3.0

                log(f"    F1={mean_f1:.0f}Hz, F2={mean_f2:.0f}Hz, F3={mean_f3:.0f}Hz → スコア={formant_score:.2f}")
        except Exception as e:
            log(f"    フォルマント分析エラー: {e}")

    # === 2. MFCC分析 ===
    try:
        log("  MFCC（声道特徴）を分析中...")
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)

        # MFCC係数の統計
        mfcc_means = np.mean(mfccs, axis=1)

        features['mfcc_mean'] = mfcc_means.tolist()

        # MFCC2は声のスペクトル傾斜を反映（男性は低い傾向）
        # MFCC3以降は声道の形状
        mfcc2 = mfcc_means[1]
        mfcc3 = mfcc_means[2]

        # 男性はMFCC2が低い傾向（スペクトル傾斜が緩い）
        mfcc2_male_score = 1.0 if mfcc2 < -5 else (0.5 if mfcc2 < 5 else 0.0)

        male_score += mfcc2_male_score * 1.5  # 重み1.5
        total_weight += 1.5

        log(f"    MFCC2={mfcc2:.1f} → スコア={mfcc2_male_score:.2f}")
    except Exception as e:
        log(f"    MFCC分析エラー: {e}")

    # === 3. スペクトル重心 ===
    try:
        log("  スペクトル重心を分析中...")
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        mean_centroid = np.median(spectral_centroid)

        features['spectral_centroid'] = mean_centroid

        # 男性は声が「暗い」（スペクトル重心が低い）
        # 典型的な男性: 1500-2500Hz、女性: 2000-3500Hz
        centroid_male_score = 1.0 if mean_centroid < 2000 else (0.5 if mean_centroid < 2800 else 0.0)

        male_score += centroid_male_score * 1.0  # 重み1
        total_weight += 1.0

        log(f"    スペクトル重心={mean_centroid:.0f}Hz → スコア={centroid_male_score:.2f}")
    except Exception as e:
        log(f"    スペクトル重心分析エラー: {e}")

    # === 4. スペクトルロールオフ ===
    try:
        log("  スペクトルロールオフを分析中...")
        spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, roll_percent=0.85)[0]
        mean_rolloff = np.median(spectral_rolloff)

        features['spectral_rolloff'] = mean_rolloff

        # 男性はロールオフが低い傾向
        rolloff_male_score = 1.0 if mean_rolloff < 3500 else (0.5 if mean_rolloff < 5000 else 0.0)

        male_score += rolloff_male_score * 0.5  # 重み0.5
        total_weight += 0.5

        log(f"    スペクトルロールオフ={mean_rolloff:.0f}Hz → スコア={rolloff_male_score:.2f}")
    except Exception as e:
        log(f"    スペクトルロールオフ分析エラー: {e}")

    # === 5. ピッチ（参考情報として追加、重みは低め） ===
    try:
        f0, voiced_flag, voiced_probs = librosa.pyin(y, fmin=50, fmax=400, sr=sr)
        valid_f0 = f0[~np.isnan(f0)]
        if len(valid_f0) > 0:
            median_pitch = np.median(valid_f0)
            features['pitch'] = median_pitch

            # ピッチは参考程度（高い声の男性もいるため重みを下げる）
            pitch_male_score = 1.0 if median_pitch < 150 else (0.5 if median_pitch < 180 else 0.0)
            male_score += pitch_male_score * 0.5  # 重み0.5（低め）
            total_weight += 0.5

            log(f"    ピッチ中央値={median_pitch:.0f}Hz → スコア={pitch_male_score:.2f}")
    except Exception as e:
        log(f"    ピッチ分析エラー: {e}")

    # === 最終判定 ===
    if total_weight > 0:
        final_score = male_score / total_weight
    else:
        final_score = 0.5

    # 0.5以上なら男性、未満なら女性
    is_male = final_score >= 0.5
    gender = 'male' if is_male else 'female'
    confidence = abs(final_score - 0.5) * 2  # 0-1のconfidence

    log(f"  総合スコア={final_score:.2f} → {gender}（確信度={confidence:.0%}）")

    return {
        'gender': gender,
        'confidence': confidence,
        'score': final_score,
        'features': features
    }


def detect_gender_by_voice(audio_path: str, progress_callback=None) -> str:
    """
    声質（timbre）から性別を判定する（簡易インターフェース）

    Returns:
        'male' or 'female'
    """
    result = detect_gender_by_timbre(audio_path, progress_callback)
    return result['gender']


def detect_gender_by_pitch_distribution(audio_path: str, progress_callback=None) -> str:
    """
    ピッチ分布から性別を判定（バックアップ用）
    """
    log = progress_callback or print
    log("ピッチ分布から性別を推定中...")

    y, sr = librosa.load(audio_path, sr=22050)

    # ピッチ推定
    pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
    pitch_values = []

    for t in range(pitches.shape[1]):
        idx = magnitudes[:, t].argmax()
        pitch = pitches[idx, t]
        if pitch > 50 and pitch < 400:
            pitch_values.append(pitch)

    if not pitch_values:
        return 'unknown'

    median_pitch = np.median(pitch_values)
    result = 'male' if median_pitch < 165 else 'female'
    log(f"ピッチ中央値={median_pitch:.1f}Hz → {result}")

    return result


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
    global _clearvoice_separator
    if _clearvoice_separator is None:
        log("話者分離AIを初期化中（初回のみ、少し時間がかかります）...")
    else:
        log("話者分離AIを実行中...")
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


def separate_speakers_to_files(
    input_video: str,
    output_dir: str,
    progress_callback=None
) -> dict:
    """
    動画から話者を分離して永続ファイルに保存する（プレビュー用）

    Returns:
        {
            'speakers': [
                {'id': 0, 'file': '/path/to/speaker_0.wav', 'pitch': 186.0},
                {'id': 1, 'file': '/path/to/speaker_1.wav', 'pitch': 181.0},
            ],
            'original_audio': '/path/to/original.wav'
        }
    """
    def log(message):
        print(message)
        if progress_callback:
            progress_callback('separate', message)

    os.makedirs(output_dir, exist_ok=True)

    # 1. 音声抽出
    log("動画から音声を抽出中...")
    original_audio = os.path.join(output_dir, "original.wav")
    extract_audio_only(input_video, original_audio)

    # 2. ClearVoice話者分離
    log("ClearVoice話者分離を実行中...")
    separated_files = separate_speakers_clearvoice(original_audio, output_dir, progress_callback)

    if not separated_files:
        log("話者分離に失敗しました")
        return {'speakers': [], 'original_audio': original_audio}

    # 3. 各話者のピッチを分析して返す
    speakers = []
    for i, speaker_file in enumerate(sorted(separated_files)):
        log(f"話者{i+1}のピッチを分析中...")
        y_speaker, sr_speaker = librosa.load(speaker_file, sr=16000, mono=True)
        pitch = estimate_pitch_for_speaker(y_speaker, sr_speaker)

        # 出力ファイル名を整理（speaker_0.wav, speaker_1.wav...）
        clean_file = os.path.join(output_dir, f"speaker_{i}.wav")
        if speaker_file != clean_file:
            import shutil
            shutil.copy(speaker_file, clean_file)

        speakers.append({
            'id': i,
            'file': clean_file,
            'pitch': float(pitch)
        })
        log(f"  話者{i+1}: {pitch:.1f}Hz")

    log(f"話者分離完了: {len(speakers)}人の話者を検出")
    return {
        'speakers': speakers,
        'original_audio': original_audio
    }


def process_with_selected_speakers(
    input_video: str,
    output_video: str,
    speaker_dir: str,
    male_speaker_ids: list,
    pitch_shift_semitones: float = -3.0,
    progress_callback=None
) -> None:
    """
    選択された話者のみピッチダウンして動画を出力する

    Args:
        input_video: 入力動画パス
        output_video: 出力動画パス
        speaker_dir: 分離された話者ファイルが保存されているディレクトリ
        male_speaker_ids: 男性としてピッチダウンする話者のIDリスト [0, 1, ...]
        pitch_shift_semitones: ピッチシフト量（半音単位）
    """
    def log(message):
        print(message)
        if progress_callback:
            progress_callback('process', message)

    log(f"選択された話者をピッチダウン: {male_speaker_ids}")

    # 1. 話者ファイルを読み込み
    speaker_files = sorted([
        f for f in os.listdir(speaker_dir)
        if f.startswith('speaker_') and f.endswith('.wav')
    ])

    if not speaker_files:
        raise ValueError("話者ファイルが見つかりません")

    # 2. 元の音声を読み込み（44100Hz）
    original_audio = os.path.join(speaker_dir, "original.wav")
    log("元音声を読み込み中...")
    y_original, sr_original = librosa.load(original_audio, sr=44100, mono=False)
    if y_original.ndim == 1:
        y_original = np.stack([y_original, y_original])
    target_len = y_original.shape[1]

    # 3. 各話者を処理
    processed_speakers = []
    for speaker_file in speaker_files:
        speaker_id = int(speaker_file.replace('speaker_', '').replace('.wav', ''))
        speaker_path = os.path.join(speaker_dir, speaker_file)

        # 16kHz -> 44.1kHzにリサンプリング
        y_sp_16k, _ = librosa.load(speaker_path, sr=16000, mono=True)
        y_sp = librosa.resample(y_sp_16k, orig_sr=16000, target_sr=44100)

        if speaker_id in male_speaker_ids:
            log(f"話者{speaker_id+1}（男性選択）をピッチダウン中...")
            y_sp = pitch_shift_audio(y_sp, 44100, pitch_shift_semitones)
        else:
            log(f"話者{speaker_id+1}はそのまま")

        processed_speakers.append(y_sp)

    # 4. 合成
    log("音声を合成中...")
    y_mixed = np.zeros(target_len)
    for sp in processed_speakers:
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

    # 5. 一時ファイルに保存
    temp_audio = os.path.join(speaker_dir, "processed_audio.wav")
    sf.write(temp_audio, y_stereo.T, 44100)

    # 6. 動画と合成
    log("動画と音声を合成中...")
    merge_audio_video(input_video, temp_audio, output_video)

    log("処理完了!")


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

            speaker_pitches.append({
                'file': speaker_file,
                'pitch': pitch,
                'is_male': False  # 後で相対比較で決定
            })

            log('analyze', f"  話者{i+1}: {pitch:.1f}Hz")

        # 相対比較で男性を判定（ピッチが最も低い話者以外を男性とする）
        # 注: ClearVoiceの分離結果では、低ピッチ=女性、高ピッチ=男性の傾向がある
        if len(speaker_pitches) >= 2:
            # 有効なピッチ（0より大きい）を持つ話者のみ比較
            valid_speakers = [sp for sp in speaker_pitches if sp['pitch'] > 0]
            if valid_speakers:
                # 最も低いピッチの話者を女性、それ以外を男性とする
                min_pitch_speaker = min(valid_speakers, key=lambda x: x['pitch'])
                for sp in valid_speakers:
                    if sp != min_pitch_speaker:
                        sp['is_male'] = True
                log('analyze', f"  → 相対比較: 最低ピッチ({min_pitch_speaker['pitch']:.1f}Hz)を女性、他を男性と判定")
        elif len(speaker_pitches) == 1:
            # 1人の場合は閾値で判定
            sp = speaker_pitches[0]
            sp['is_male'] = is_male_voice(sp['pitch'], male_threshold)
            gender = "男性" if sp['is_male'] else "女性"
            log('analyze', f"  → 単独話者: 閾値判定で{gender}")

        # 判定結果をログ出力
        for i, sp_info in enumerate(speaker_pitches):
            gender = "男性" if sp_info['is_male'] else "女性"
            log('analyze', f"  話者{i+1}: {sp_info['pitch']:.1f}Hz → {gender}")

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


def detect_gender_for_segment(segment_audio: np.ndarray, sr: int) -> dict:
    """
    セグメント用の声質判定（軽量版）

    複数の特徴を組み合わせて判定：
    1. ピッチ（F0）- 基本的な判定基準
    2. スペクトル重心 - 声の「明るさ」
    3. スペクトルロールオフ - 高周波成分
    4. MFCC - 声道特徴
    5. フォルマント比率 - 声道の長さの比較指標
    """
    try:
        import parselmouth
        has_parselmouth = True
    except ImportError:
        has_parselmouth = False

    male_score = 0
    total_weight = 0

    # === 1. ピッチ（F0）分析 - 重み0.5（参考程度） ===
    # 声質判定ではピッチは補助的。高い声の男性もいる
    try:
        f0, voiced_flag, voiced_probs = librosa.pyin(
            segment_audio, fmin=50, fmax=400, sr=sr
        )
        valid_f0 = f0[~np.isnan(f0)]
        if len(valid_f0) > 3:
            median_pitch = np.median(valid_f0)
            # 非常に低いピッチのみ男性判定に寄与
            if median_pitch < 120:
                pitch_male = 1.0
            elif median_pitch < 150:
                pitch_male = 0.6
            else:
                pitch_male = 0.3  # 高くても0.3（声質で判断するため）
            male_score += pitch_male * 0.5  # 重みを大幅に下げる
            total_weight += 0.5
    except:
        pass

    # === 2. スペクトル重心 - 重み2.5（最重要：声の明るさ） ===
    # 男性は声道が長いため、スペクトル重心が低い
    # これはピッチに関係なく一定
    try:
        centroid = librosa.feature.spectral_centroid(y=segment_audio, sr=sr)[0]
        mean_centroid = np.median(centroid)
        # 閾値を緩和して男性を検出しやすく
        if mean_centroid < 1800:
            centroid_male = 1.0
        elif mean_centroid < 2500:
            centroid_male = 0.7
        elif mean_centroid < 3200:
            centroid_male = 0.4
        else:
            centroid_male = 0.1
        male_score += centroid_male * 2.5
        total_weight += 2.5
    except:
        pass

    # === 3. スペクトルロールオフ - 重み1.5（声の倍音構造） ===
    # 男性は高周波成分が少ない
    try:
        rolloff = librosa.feature.spectral_rolloff(y=segment_audio, sr=sr, roll_percent=0.85)[0]
        mean_rolloff = np.median(rolloff)
        if mean_rolloff < 3500:
            rolloff_male = 1.0
        elif mean_rolloff < 5000:
            rolloff_male = 0.7
        elif mean_rolloff < 6500:
            rolloff_male = 0.4
        else:
            rolloff_male = 0.1
        male_score += rolloff_male * 1.5
        total_weight += 1.5
    except:
        pass

    # === 4. MFCC分析 - 重み1.5（声道の形状） ===
    # MFCCは声道の形状を表す - ピッチに依存しない
    try:
        mfccs = librosa.feature.mfcc(y=segment_audio, sr=sr, n_mfcc=13)
        mfcc_means = np.mean(mfccs, axis=1)
        # MFCC2: スペクトル傾斜（男性は緩やか=値が低い傾向）
        mfcc2 = mfcc_means[1]
        # 閾値を緩和
        if mfcc2 < -5:
            mfcc_male = 1.0
        elif mfcc2 < 5:
            mfcc_male = 0.7
        elif mfcc2 < 15:
            mfcc_male = 0.4
        else:
            mfcc_male = 0.1
        male_score += mfcc_male * 1.5
        total_weight += 1.5
    except:
        pass

    # === 5. フォルマント分析（補助的） - 重み1.0 ===
    if has_parselmouth and len(segment_audio) > sr * 0.2:
        try:
            sound = parselmouth.Sound(segment_audio, sampling_frequency=sr)
            formant = sound.to_formant_burg(
                time_step=0.01,
                max_number_of_formants=4,
                maximum_formant=5500,  # 広めに取る
                window_length=0.025,
                pre_emphasis_from=50.0
            )

            f1_values = []
            f2_values = []

            for t in formant.ts():
                f1 = formant.get_value_at_time(1, t)
                f2 = formant.get_value_at_time(2, t)
                if not np.isnan(f1) and 200 < f1 < 1200:
                    f1_values.append(f1)
                if not np.isnan(f2) and 500 < f2 < 3000:
                    f2_values.append(f2)

            if f1_values and f2_values:
                mean_f1 = np.median(f1_values)
                mean_f2 = np.median(f2_values)
                # F2/F1比率で判定（男性は比率が低い傾向）
                ratio = mean_f2 / mean_f1 if mean_f1 > 0 else 2.5
                if ratio < 2.2:
                    formant_male = 1.0
                elif ratio < 2.8:
                    formant_male = 0.6
                else:
                    formant_male = 0.2
                male_score += formant_male * 1.0
                total_weight += 1.0
        except:
            pass

    # === 最終判定 ===
    if total_weight > 0:
        final_score = male_score / total_weight
    else:
        final_score = 0.5

    # 閾値を0.45に下げて男性を検出しやすくする
    is_male = final_score >= 0.45
    return {
        'is_male': is_male,
        'score': final_score,
        'confidence': abs(final_score - 0.5) * 2
    }


def process_timbre(
    audio_path: str,
    output_path: str,
    pitch_shift_semitones: float = -3.0,
    segment_duration: float = 3.0,
    progress_callback=None
) -> None:
    """
    声質版: inaSpeechSegmenter（CNN）による性別判定 + 後処理 + ダブルチェック

    改善点:
    1. 後処理: 短い孤立判定を周囲に統合（ノイズ除去）
    2. ダブルチェック: CNNが「男性」と判定した区間を音響特徴で再確認
    """
    def log(step, message):
        print(message)
        if progress_callback:
            progress_callback(step, message)

    log('analyze', "声質版: CNN判定 + 後処理 + ダブルチェック...")

    # 1. 音声を読み込み
    log('pitch', "ステップ1: 音声を読み込み中...")
    y, sr = librosa.load(audio_path, sr=44100, mono=False)
    if y.ndim == 1:
        y = np.stack([y, y])

    # モノラル版も用意（ダブルチェック用）
    y_mono = y[0] if y.ndim > 1 else y

    total_duration = y.shape[1] / sr
    log('pitch', f"音声長: {total_duration:.1f}秒")

    # 2. inaSpeechSegmenterで性別判定
    log('analyze', "ステップ2: CNNで性別を判定中（初回は時間がかかります）...")
    segments_raw = detect_gender_ina(audio_path, lambda msg: log('analyze', msg))

    # 3. 後処理: 短い孤立判定を統合
    log('analyze', "ステップ3: 後処理（孤立判定の統合）...")
    segments = postprocess_gender_segments(segments_raw, min_duration=0.3)

    # 統計を再計算
    male_before = sum(e - s for l, s, e in segments_raw if l == 'male')
    male_after = sum(e - s for l, s, e in segments if l == 'male')
    if male_before != male_after:
        log('analyze', f"  後処理で調整: 男性 {male_before:.1f}秒 → {male_after:.1f}秒")

    # 4. 男性区間をダブルチェック + ピッチシフト
    log('pitch', "ステップ4: ダブルチェック + ピッチシフト中...")

    y_processed = y.copy()
    male_duration = 0
    female_duration = 0
    processed_count = 0
    double_check_rejected = 0

    for label, start_sec, end_sec in segments:
        if label == 'male':
            start_sample = int(start_sec * sr)
            end_sample = int(end_sec * sr)

            # 範囲チェック
            if start_sample >= y.shape[1]:
                continue
            end_sample = min(end_sample, y.shape[1])

            segment_mono = y_mono[start_sample:end_sample]

            # ダブルチェック: 音響特徴で再確認（1秒以上の区間のみ）
            duration = end_sec - start_sec
            should_process = True

            if duration >= 1.0:
                # 長い区間はダブルチェック
                double_check = detect_gender_for_segment(segment_mono, sr)
                if not double_check['is_male'] and double_check['confidence'] > 0.3:
                    # ダブルチェックで「女性」と高確信度で判定された場合はスキップ
                    should_process = False
                    double_check_rejected += 1
                    female_duration += duration

            if should_process:
                male_duration += duration

                # 各チャンネルをピッチシフト
                for ch in range(y.shape[0]):
                    segment = y[ch, start_sample:end_sample]
                    if len(segment) < sr * 0.1:  # 0.1秒未満はスキップ
                        continue

                    processed = pitch_shift_audio(segment, sr, pitch_shift_semitones)

                    # 長さを調整
                    target_len = end_sample - start_sample
                    if len(processed) > target_len:
                        processed = processed[:target_len]
                    elif len(processed) < target_len:
                        processed = np.pad(processed, (0, target_len - len(processed)))

                    # クロスフェード
                    fade_len = min(int(0.02 * sr), len(processed) // 4)
                    if fade_len > 0:
                        if start_sample > 0:
                            fade_in = np.linspace(0, 1, fade_len)
                            processed[:fade_len] = processed[:fade_len] * fade_in + y[ch, start_sample:start_sample+fade_len] * (1 - fade_in)
                        if end_sample < y.shape[1]:
                            fade_out = np.linspace(1, 0, fade_len)
                            processed[-fade_len:] = processed[-fade_len:] * fade_out + y[ch, end_sample-fade_len:end_sample] * (1 - fade_out)

                    y_processed[ch, start_sample:end_sample] = processed

                processed_count += 1

        elif label == 'female':
            female_duration += end_sec - start_sec

        # 進捗表示
        if processed_count > 0 and processed_count % 10 == 0:
            log('pitch', f"  処理中: {processed_count}区間完了")

    if double_check_rejected > 0:
        log('pitch', f"  ダブルチェックで{double_check_rejected}区間を女性に修正")

    log('pitch', f"結果: 男性={male_duration:.1f}秒, 女性={female_duration:.1f}秒")

    # 4. クリッピング防止
    max_val = np.max(np.abs(y_processed))
    if max_val > 1.0:
        y_processed = y_processed / max_val * 0.95

    # 5. 保存
    sf.write(output_path, y_processed.T, sr)

    log('merge', f"処理完了: 男性{male_duration:.1f}秒をピッチシフト、女性{female_duration:.1f}秒はそのまま")


def process_hybrid(
    audio_path: str,
    output_path: str,
    pitch_shift_semitones: float = -3.0,
    male_threshold: float = 165,
    progress_callback=None
) -> None:
    """
    ハイブリッド版: ClearVoice話者分離 + SpeechBrain声質判定 + Hz判定
    - 話者分離後、声質=男性 かつ Hz < 閾値 の話者のみピッチシフト
    - より確実な男性判定が可能
    """
    def log(step, message):
        print(message)
        if progress_callback:
            progress_callback(step, message)

    log('separate', "ハイブリッド版: ClearVoice + SpeechBrain + Hz判定...")
    log('analyze', f"  Hz閾値: {male_threshold}Hz")

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

        # 3. 各話者を声質+Hzで判定
        log('analyze', "ステップ3: 各話者の性別を声質+Hzで判定中...")
        speaker_info = []

        for i, speaker_file in enumerate(separated_files):
            log('analyze', f"  話者{i+1}を分析中...")

            # 声質で性別判定
            gender = detect_gender_by_voice(speaker_file, lambda msg: log('analyze', f"    {msg}"))

            # ピッチ分布も確認
            pitch_gender = detect_gender_by_pitch_distribution(speaker_file, lambda msg: log('analyze', f"    {msg}"))

            # ハイブリッド判定：両方で男性の場合のみ男性と判定
            is_male = (gender == 'male' and pitch_gender == 'male')

            speaker_info.append({
                'file': speaker_file,
                'gender': gender,
                'pitch_gender': pitch_gender,
                'is_male': is_male
            })

            gender_jp = "男性" if is_male else "女性"
            log('analyze', f"  話者{i+1}: 声質={gender}, Hz={pitch_gender} → {gender_jp}")

        # 4. 男性話者の音声をピッチシフト
        log('pitch', "ステップ4: 男性話者の音声をピッチシフト...")

        processed_speakers = []
        target_len = y_original.shape[1]

        for i, sp_info in enumerate(speaker_info):
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

        y_mixed = np.zeros(target_len)
        for sp in processed_speakers:
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

        male_count = sum(1 for sp in speaker_info if sp['is_male'])
        log('merge', f"処理完了: {male_count}人の男性話者をピッチシフト")


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
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        error_msg = result.stderr or result.stdout or "ffmpeg error"
        raise RuntimeError(f"音声抽出失敗: {error_msg}")


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
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        error_msg = result.stderr or result.stdout or "ffmpeg error"
        raise RuntimeError(f"ffmpeg失敗: {error_msg}")


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


def calculate_local_threshold(pitches: list, base_threshold: float = 165) -> float:
    """
    区間内のピッチ分布から最適な閾値を計算する

    Args:
        pitches: 区間内で検出されたピッチのリスト
        base_threshold: ベース閾値（分布が不十分な場合に使用）

    Returns:
        計算された閾値
    """
    if len(pitches) < 10:
        return base_threshold

    pitches_array = np.array(pitches)

    # ヒストグラムで分布を分析
    hist, bin_edges = np.histogram(pitches_array, bins=20, range=(50, 350))
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    # スムージング
    from scipy.ndimage import uniform_filter1d
    smoothed = uniform_filter1d(hist.astype(float), size=3)

    # 100-200Hzの範囲で谷を探す（二峰性の場合）
    for j in range(len(bin_centers)):
        if 120 < bin_centers[j] < 200:
            if j > 0 and j < len(smoothed) - 1:
                if smoothed[j] < smoothed[j-1] and smoothed[j] < smoothed[j+1]:
                    if smoothed[j] < np.mean(smoothed) * 0.7:
                        return bin_centers[j]

    # 谷が見つからない場合は中央値ベースで判定
    median = np.median(pitches_array)
    if median < 140:
        # 低い声が多い → 男性が主体、閾値を少し上げる
        return min(base_threshold + 10, 190)
    elif median > 200:
        # 高い声が多い → 女性が主体、閾値を少し下げる
        return max(base_threshold - 10, 140)

    return base_threshold


def pitch_shift_audio(y: np.ndarray, sr: int, semitones: float) -> np.ndarray:
    """音声のピッチをシフトする"""
    return librosa.effects.pitch_shift(y, sr=sr, n_steps=semitones)


def process_simple(
    audio_path: str,
    output_path: str,
    pitch_shift_semitones: float = -3.0,
    segment_duration: float = 0.5,
    male_threshold: float = 165,
    adaptive_window: float = 300.0,
    progress_callback=None
) -> None:
    """
    簡易版：ピッチ検出ベースで男性の声のみピッチを下げる
    動的閾値調整: adaptive_window秒ごとに閾値を再計算

    Args:
        adaptive_window: 閾値再計算の区間（秒）。0で固定閾値モード
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
    total_duration = len(y_mono) / sr

    # セグメントごとに処理
    segment_samples = int(segment_duration * sr)
    num_segments = len(y_mono) // segment_samples + 1

    log('pitch', f"セグメント数: {num_segments} (各{segment_duration}秒)")
    log('pitch', f"ベース閾値: {male_threshold}Hz")

    # 動的閾値調整の設定
    if adaptive_window > 0 and total_duration > adaptive_window:
        adaptive_samples = int(adaptive_window * sr)
        num_windows = int(np.ceil(len(y_mono) / adaptive_samples))
        log('pitch', f"動的閾値調整: {adaptive_window}秒ごと ({num_windows}区間)")
    else:
        adaptive_samples = len(y_mono)
        num_windows = 1
        log('pitch', f"固定閾値モード")

    y_processed = y.copy()

    male_segments = 0
    female_segments = 0
    silent_segments = 0
    threshold_history = []

    # 第1パス: 各区間のピッチを収集
    log('pitch', "第1パス: ピッチ分布を解析中...")
    window_pitches = [[] for _ in range(num_windows)]

    for i in range(num_segments):
        start = i * segment_samples
        end = min((i + 1) * segment_samples, len(y_mono))

        if start >= len(y_mono):
            break

        segment_mono = y_mono[start:end]

        # 無音チェック
        if np.max(np.abs(segment_mono)) < 0.005:
            continue

        # ピッチを推定
        pitch = estimate_pitch_for_segment(segment_mono, sr)

        if pitch > 0:
            # どの区間に属するか
            window_idx = min(start // adaptive_samples, num_windows - 1)
            window_pitches[window_idx].append(pitch)

        # 進捗表示（20セグメントごと）
        if i > 0 and i % 20 == 0:
            progress = int((i / num_segments) * 50)
            log('pitch', f"  ピッチ解析: {progress}%")

    # 各区間の閾値を計算
    window_thresholds = []
    for idx, pitches in enumerate(window_pitches):
        local_threshold = calculate_local_threshold(pitches, male_threshold)
        window_thresholds.append(local_threshold)
        start_time = idx * adaptive_window
        end_time = min((idx + 1) * adaptive_window, total_duration)
        log('pitch', f"  区間 {start_time:.0f}-{end_time:.0f}秒: 閾値={local_threshold:.0f}Hz (サンプル={len(pitches)})")

    # 第2パス: ピッチシフト処理
    log('pitch', "第2パス: ピッチシフト処理中...")
    for i in range(num_segments):
        start = i * segment_samples
        end = min((i + 1) * segment_samples, len(y_mono))

        if start >= len(y_mono):
            break

        segment_mono = y_mono[start:end]

        # 無音チェック
        if np.max(np.abs(segment_mono)) < 0.005:
            silent_segments += 1
            continue

        # ピッチを推定
        pitch = estimate_pitch_for_segment(segment_mono, sr)

        if pitch == 0:
            continue

        # この区間の閾値を取得
        window_idx = min(start // adaptive_samples, num_windows - 1)
        current_threshold = window_thresholds[window_idx]

        # 男性の声かどうか判定
        if is_male_voice(pitch, current_threshold):
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
            progress = 50 + int((i / num_segments) * 50)
            log('pitch', f"  処理: {progress}%")

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
    mode: str = 'hybrid',
    adaptive_window: float = 300.0,
    progress_callback=None
) -> None:
    """
    動画を処理して男性の声のみピッチを下げる

    mode:
      'simple' - 簡易版: Hz判定のみ（高速）
      'timbre' - 声質版: CNN声質判定のみ（inaSpeechSegmenter）
      'hybrid' - ハイブリッド: Hz + 声質（両方で男性判定された区間のみ変換）

    segment_duration: 簡易版のセグメント長（秒）
    male_threshold: 男性判定のピッチ閾値（Hz）- 簡易版とハイブリッドで使用
    adaptive_window: 動的閾値調整の区間（秒）。0で固定閾値モード - 簡易版で使用
    """
    def log(step, message):
        print(message)
        if progress_callback:
            progress_callback(step, message)

    mode_names = {
        'simple': '簡易版（Hz判定のみ）',
        'timbre': '声質版（CNN声質判定）',
        'hybrid': 'ハイブリッド（Hz＋声質）'
    }
    mode_name = mode_names.get(mode, mode)

    log('extract', f"入力動画: {input_video}")
    log('extract', f"出力動画: {output_video}")
    log('extract', f"処理モード: {mode_name}")
    log('extract', f"ピッチシフト: {pitch_shift_semitones} semitones")
    if mode in ['simple', 'hybrid']:
        log('extract', f"男性判定閾値: {male_threshold}Hz")

    with tempfile.TemporaryDirectory() as tmpdir:
        extracted_audio = os.path.join(tmpdir, "extracted.wav")
        processed_audio = os.path.join(tmpdir, "processed.wav")

        # 1. 動画から音声を抽出
        log('extract', "1. 音声を抽出中...")
        extract_audio(input_video, extracted_audio)
        log('extract', "音声抽出完了")

        # 2. 音声処理（モードに応じて分岐）
        if mode == 'timbre':
            # 声質版（セグメントごとのピッチ判定）
            log('analyze', "2. 声質版で処理中...")
            process_timbre(
                extracted_audio,
                processed_audio,
                pitch_shift_semitones,
                segment_duration=2.0,
                progress_callback=progress_callback
            )
        elif mode == 'hybrid':
            # ハイブリッド版（Hz + 声質の両方で判定）
            log('analyze', "2. ハイブリッド版で処理中...")
            process_hybrid(
                extracted_audio,
                processed_audio,
                pitch_shift_semitones,
                male_threshold,
                progress_callback
            )
        else:
            # 簡易版モード（Hzセグメント判定）
            log('analyze', "2. 簡易版で処理中...")
            process_simple(
                extracted_audio,
                processed_audio,
                pitch_shift_semitones,
                segment_duration,
                male_threshold,
                adaptive_window,
                progress_callback
            )

        # 3. 処理した音声と元の動画を結合
        log('combine', "3. 動画と音声を結合中...")
        merge_audio_video(input_video, processed_audio, output_video)

    log('combine', f"完了！出力ファイル: {output_video}")


def extract_audio_only(video_path: str, output_path: str) -> None:
    """動画から音声のみを抽出してWAVで保存"""
    extract_audio(video_path, output_path)


def analyze_speech_segments(y: np.ndarray, sr: int, silence_threshold: float = 0.01) -> list:
    """
    音声の発話区間を分析し、各発話の長さ（秒）のリストを返す

    Args:
        y: 音声データ
        sr: サンプルレート
        silence_threshold: 無音判定の閾値（RMS）

    Returns:
        発話区間の長さ（秒）のリスト
    """
    # RMSエネルギーを計算（フレーム単位）
    frame_length = int(0.025 * sr)  # 25ms
    hop_length = int(0.010 * sr)    # 10ms

    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]

    # 無音/有音を判定
    is_speech = rms > silence_threshold

    # 発話区間の長さを計算
    speech_durations = []
    in_speech = False
    speech_start = 0

    for i, speech in enumerate(is_speech):
        if speech and not in_speech:
            # 発話開始
            in_speech = True
            speech_start = i
        elif not speech and in_speech:
            # 発話終了
            in_speech = False
            duration = (i - speech_start) * hop_length / sr
            if duration > 0.1:  # 0.1秒以上の発話のみカウント
                speech_durations.append(duration)

    # 最後の発話区間
    if in_speech:
        duration = (len(is_speech) - speech_start) * hop_length / sr
        if duration > 0.1:
            speech_durations.append(duration)

    return speech_durations


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

        # 発話区間を分析して推奨セグメント長を算出
        log("発話パターンを分析中...")
        speech_durations = analyze_speech_segments(y, sr)
        if speech_durations:
            # 発話区間の中央値を基準に推奨セグメント長を決定
            median_duration = float(np.median(speech_durations))
            # 推奨値: 発話区間の中央値の50-70%程度（細かく捉える）
            suggested_segment = max(0.2, min(2.0, round(median_duration * 0.6, 1)))
            log(f"発話区間の中央値: {median_duration:.2f}秒 → 推奨セグメント長: {suggested_segment}秒")
        else:
            suggested_segment = 0.5  # デフォルト

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
        log(f"推奨セグメント長: {suggested_segment}秒")

        return {
            'pitches': pitches,
            'male_pitches': male_pitches,
            'female_pitches': female_pitches,
            'suggested_threshold': round(suggested_threshold),
            'suggested_segment': suggested_segment,
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
