#!/usr/bin/env python3
"""
男性の声だけピッチを下げる動画処理アプリ - GUI版
"""

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

from voice_changer import process_video


class VoiceChangerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("男性ボイスチェンジャー")
        self.root.geometry("600x400")
        self.root.resizable(True, True)

        # 変数
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.pitch_shift = tk.DoubleVar(value=-3.0)
        self.segment_duration = tk.DoubleVar(value=0.5)
        self.processing = False

        self.create_widgets()

    def create_widgets(self):
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # タイトル
        title_label = ttk.Label(
            main_frame,
            text="男性の声だけピッチを下げる",
            font=("", 16, "bold")
        )
        title_label.pack(pady=(0, 20))

        # 入力ファイル選択
        input_frame = ttk.LabelFrame(main_frame, text="入力動画", padding="10")
        input_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Entry(input_frame, textvariable=self.input_path, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(input_frame, text="参照...", command=self.browse_input).pack(side=tk.RIGHT, padx=(10, 0))

        # 出力ファイル選択
        output_frame = ttk.LabelFrame(main_frame, text="出力動画", padding="10")
        output_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Entry(output_frame, textvariable=self.output_path, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(output_frame, text="参照...", command=self.browse_output).pack(side=tk.RIGHT, padx=(10, 0))

        # 設定フレーム
        settings_frame = ttk.LabelFrame(main_frame, text="設定", padding="10")
        settings_frame.pack(fill=tk.X, pady=(0, 10))

        # ピッチシフト設定
        pitch_frame = ttk.Frame(settings_frame)
        pitch_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(pitch_frame, text="ピッチシフト (半音):").pack(side=tk.LEFT)
        self.pitch_label = ttk.Label(pitch_frame, text="-3.0")
        self.pitch_label.pack(side=tk.RIGHT)

        pitch_scale = ttk.Scale(
            settings_frame,
            from_=-12,
            to=0,
            variable=self.pitch_shift,
            orient=tk.HORIZONTAL,
            command=self.update_pitch_label
        )
        pitch_scale.pack(fill=tk.X, pady=(0, 10))

        # セグメント長設定
        segment_frame = ttk.Frame(settings_frame)
        segment_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(segment_frame, text="解析セグメント長 (秒):").pack(side=tk.LEFT)
        self.segment_label = ttk.Label(segment_frame, text="0.5")
        self.segment_label.pack(side=tk.RIGHT)

        segment_scale = ttk.Scale(
            settings_frame,
            from_=0.1,
            to=2.0,
            variable=self.segment_duration,
            orient=tk.HORIZONTAL,
            command=self.update_segment_label
        )
        segment_scale.pack(fill=tk.X)

        # プログレスバー
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=(10, 10))

        # ステータスラベル
        self.status_label = ttk.Label(main_frame, text="動画ファイルを選択してください")
        self.status_label.pack(pady=(0, 10))

        # 処理ボタン
        self.process_button = ttk.Button(
            main_frame,
            text="処理開始",
            command=self.start_processing,
            style="Accent.TButton"
        )
        self.process_button.pack(pady=(10, 0))

    def update_pitch_label(self, value):
        self.pitch_label.config(text=f"{float(value):.1f}")

    def update_segment_label(self, value):
        self.segment_label.config(text=f"{float(value):.1f}")

    def browse_input(self):
        filetypes = [
            ("動画ファイル", "*.mp4 *.avi *.mov *.mkv *.webm"),
            ("すべてのファイル", "*.*")
        ]
        path = filedialog.askopenfilename(filetypes=filetypes)
        if path:
            self.input_path.set(path)
            # 自動的に出力パスを設定
            input_file = Path(path)
            output_file = input_file.parent / f"{input_file.stem}_processed{input_file.suffix}"
            self.output_path.set(str(output_file))
            self.status_label.config(text="準備完了 - 処理開始ボタンを押してください")

    def browse_output(self):
        filetypes = [
            ("MP4ファイル", "*.mp4"),
            ("AVIファイル", "*.avi"),
            ("すべてのファイル", "*.*")
        ]
        path = filedialog.asksaveasfilename(
            filetypes=filetypes,
            defaultextension=".mp4"
        )
        if path:
            self.output_path.set(path)

    def start_processing(self):
        if self.processing:
            return

        input_path = self.input_path.get()
        output_path = self.output_path.get()

        if not input_path:
            messagebox.showerror("エラー", "入力動画を選択してください")
            return

        if not os.path.exists(input_path):
            messagebox.showerror("エラー", "入力ファイルが見つかりません")
            return

        if not output_path:
            messagebox.showerror("エラー", "出力先を指定してください")
            return

        self.processing = True
        self.process_button.config(state=tk.DISABLED)
        self.progress.start()
        self.status_label.config(text="処理中... しばらくお待ちください")

        # バックグラウンドで処理
        thread = threading.Thread(target=self.process_video_thread)
        thread.daemon = True
        thread.start()

    def process_video_thread(self):
        try:
            process_video(
                self.input_path.get(),
                self.output_path.get(),
                self.pitch_shift.get(),
                self.segment_duration.get()
            )
            self.root.after(0, self.processing_complete)
        except Exception as e:
            self.root.after(0, lambda: self.processing_error(str(e)))

    def processing_complete(self):
        self.processing = False
        self.progress.stop()
        self.process_button.config(state=tk.NORMAL)
        self.status_label.config(text="処理完了!")
        messagebox.showinfo("完了", f"処理が完了しました\n\n出力ファイル:\n{self.output_path.get()}")

    def processing_error(self, error_message):
        self.processing = False
        self.progress.stop()
        self.process_button.config(state=tk.NORMAL)
        self.status_label.config(text="エラーが発生しました")
        messagebox.showerror("エラー", f"処理中にエラーが発生しました:\n\n{error_message}")


def main():
    root = tk.Tk()
    app = VoiceChangerGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
