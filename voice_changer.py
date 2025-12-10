#!/usr/bin/env python3
"""
男性の声だけピッチを下げる動画処理アプリ
音声分離AIを使用して高精度に処理します
"""

import argparse
import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import librosa
import soundfile as sf
import torch


def extract_audio(video_path: str, audio_path: str) -> None:
    """動画から音声を抽出する"""
    cmd = [
        'ffmpeg', '-y', '-i', video_path,
        '-vn', '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '2',
        audio_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def merge_audio_video(video_path: str, audio_path: str, output_path: str) -> None:
    """処理した音声と元の動画を結合する"""
    cmd = [
        'ffmpeg', '-y', '-i', video_path, '-i', audio_path,
        '-c:v', 'copy', '-map', '0:v:0', '-map', '1:a:0',
        '-shortest', output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def separate_voices(audio_path: str, output_dir: str) -> dict:
    """
    Demucsを使用して音声を分離する
    Returns: {'vocals': path, 'other': path} または話者分離結果
    """
    from demucs.pretrained import get_model
    from demucs.apply import apply_model

    print("  音声分離モデルを読み込み中...")

    # htdemucs モデルを使用（ボーカル分離に優れている）
    model = get_model('htdemucs')
    model.eval()

    if torch.cuda.is_available():
        model.cuda()
        device = 'cuda'
    else:
        device = 'cpu'

    print(f"  デバイス: {device}")

    # 音声を読み込み
    print("  音声ファイルを読み込み中...")
    wav, sr = librosa.load(audio_path, sr=model.samplerate, mono=False)

    # モノラルの場合はステレオに変換
    if wav.ndim == 1:
        wav = np.stack([wav, wav])

    # PyTorchテンソルに変換
    wav_tensor = torch.from_numpy(wav).float().unsqueeze(0)

    if device == 'cuda':
        wav_tensor = wav_tensor.cuda()

    # 音声分離を実行
    print("  音声を分離中（時間がかかります）...")
    with torch.no_grad():
        sources = apply_model(model, wav_tensor, device=device, progress=True)

    # 結果を取得 (sources: [batch, sources, channels, samples])
    # htdemucs の出力: drums, bass, other, vocals
    sources = sources.squeeze(0).cpu().numpy()

    source_names = ['drums', 'bass', 'other', 'vocals']
    result = {}

    for i, name in enumerate(source_names):
        output_path = os.path.join(output_dir, f'{name}.wav')
        sf.write(output_path, sources[i].T, model.samplerate)
        result[name] = output_path
        print(f"  {name}: {output_path}")

    return result


def estimate_pitch_for_audio(y: np.ndarray, sr: int) -> float:
    """音声全体の平均ピッチを推定する"""
    if len(y) < sr * 0.1:
        return 0

    try:
        f0, voiced_flag, voiced_probs = librosa.pyin(
            y,
            fmin=50,
            fmax=400,
            sr=sr,
            frame_length=2048
        )
        valid_f0 = f0[~np.isnan(f0)]
        if len(valid_f0) > 0:
            return np.median(valid_f0)
    except:
        pass

    return 0


def is_male_voice(pitch: float) -> bool:
    """ピッチから男性の声かどうかを判定する"""
    return 0 < pitch < 165


def pitch_shift_audio(y: np.ndarray, sr: int, semitones: float) -> np.ndarray:
    """音声のピッチをシフトする"""
    return librosa.effects.pitch_shift(y, sr=sr, n_steps=semitones)


def process_with_separation(
    audio_path: str,
    output_path: str,
    pitch_shift_semitones: float = -3.0
) -> None:
    """
    音声分離を使用して男性の声のみピッチを下げる
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. 音声を分離
        print("  ステップ1: 音声分離...")
        separated = separate_voices(audio_path, tmpdir)

        # 2. ボーカルトラックを読み込み
        print("  ステップ2: ボーカル解析...")
        vocals, sr = librosa.load(separated['vocals'], sr=44100, mono=False)
        if vocals.ndim == 1:
            vocals = np.stack([vocals, vocals])

        vocals_mono = librosa.to_mono(vocals)

        # 3. ボーカルのピッチを分析して話者を特定
        # セグメントごとに分析
        segment_duration = 2.0  # 2秒ごと
        segment_samples = int(segment_duration * sr)
        num_segments = len(vocals_mono) // segment_samples + 1

        vocals_processed = vocals.copy()

        print(f"  ステップ3: 話者判定とピッチ変換 ({num_segments}セグメント)...")

        male_segments = 0
        female_segments = 0

        for i in range(num_segments):
            start = i * segment_samples
            end = min((i + 1) * segment_samples, len(vocals_mono))

            if start >= len(vocals_mono):
                break

            segment_mono = vocals_mono[start:end]

            # 無音チェック
            if np.max(np.abs(segment_mono)) < 0.01:
                continue

            # ピッチを推定
            pitch = estimate_pitch_for_audio(segment_mono, sr)

            if pitch == 0:
                continue

            # 男性の声かどうか判定
            if is_male_voice(pitch):
                male_segments += 1

                # 男性の声：ピッチを下げる
                for ch in range(vocals.shape[0]):
                    segment = vocals[ch, start:end]
                    processed = pitch_shift_audio(segment, sr, pitch_shift_semitones)

                    # 長さを調整
                    if len(processed) > end - start:
                        processed = processed[:end-start]
                    elif len(processed) < end - start:
                        processed = np.pad(processed, (0, end - start - len(processed)))

                    # クロスフェード
                    fade_len = min(int(0.02 * sr), len(processed) // 4)
                    if fade_len > 0 and start > 0:
                        fade_in = np.linspace(0, 1, fade_len)
                        processed[:fade_len] = processed[:fade_len] * fade_in + vocals[ch, start:start+fade_len] * (1 - fade_in)
                    if fade_len > 0 and end < vocals.shape[1]:
                        fade_out = np.linspace(1, 0, fade_len)
                        processed[-fade_len:] = processed[-fade_len:] * fade_out + vocals[ch, end-fade_len:end] * (1 - fade_out)

                    vocals_processed[ch, start:end] = processed
            else:
                female_segments += 1

        print(f"  結果: 男性={male_segments}セグメント, 女性={female_segments}セグメント")

        # 4. 他のトラック（drums, bass, other）を読み込み
        print("  ステップ4: トラックを合成...")

        # 各トラックを読み込んで合成
        drums, _ = librosa.load(separated['drums'], sr=sr, mono=False)
        bass, _ = librosa.load(separated['bass'], sr=sr, mono=False)
        other, _ = librosa.load(separated['other'], sr=sr, mono=False)

        # モノラルの場合はステレオに変換
        for track_name, track in [('drums', drums), ('bass', bass), ('other', other)]:
            if track.ndim == 1:
                if track_name == 'drums':
                    drums = np.stack([track, track])
                elif track_name == 'bass':
                    bass = np.stack([track, track])
                else:
                    other = np.stack([track, track])

        # 長さを揃える
        min_len = min(vocals_processed.shape[1], drums.shape[1], bass.shape[1], other.shape[1])
        vocals_processed = vocals_processed[:, :min_len]
        drums = drums[:, :min_len]
        bass = bass[:, :min_len]
        other = other[:, :min_len]

        # 合成
        final_audio = vocals_processed + drums + bass + other

        # クリッピング防止
        max_val = np.max(np.abs(final_audio))
        if max_val > 1.0:
            final_audio = final_audio / max_val * 0.95

        # 5. 保存
        sf.write(output_path, final_audio.T, sr)
        print(f"  出力: {output_path}")


def process_video(
    input_video: str,
    output_video: str,
    pitch_shift_semitones: float = -3.0
) -> None:
    """
    動画を処理して男性の声のみピッチを下げる（音声分離版）
    """
    print(f"入力動画: {input_video}")
    print(f"出力動画: {output_video}")
    print(f"ピッチシフト: {pitch_shift_semitones} semitones")
    print("\n※ 音声分離AIを使用（高精度モード）")

    with tempfile.TemporaryDirectory() as tmpdir:
        extracted_audio = os.path.join(tmpdir, "extracted.wav")
        processed_audio = os.path.join(tmpdir, "processed.wav")

        # 1. 動画から音声を抽出
        print("\n1. 音声を抽出中...")
        extract_audio(input_video, extracted_audio)

        # 2. 音声分離を使用して処理
        print("\n2. 音声分離と処理中...")
        process_with_separation(
            extracted_audio,
            processed_audio,
            pitch_shift_semitones
        )

        # 3. 処理した音声と元の動画を結合
        print("\n3. 動画と音声を結合中...")
        merge_audio_video(input_video, processed_audio, output_video)

    print(f"\n完了！出力ファイル: {output_video}")


def main():
    parser = argparse.ArgumentParser(
        description='男性の声だけピッチを下げる動画処理アプリ（高精度版）'
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

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"エラー: 入力ファイルが見つかりません: {args.input}")
        return 1

    if args.output:
        output_path = args.output
    else:
        input_path = Path(args.input)
        output_path = str(input_path.parent / f"{input_path.stem}_processed{input_path.suffix}")

    process_video(args.input, output_path, args.pitch)

    return 0


if __name__ == '__main__':
    exit(main())
