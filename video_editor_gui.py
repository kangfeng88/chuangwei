"""Windows GUI for the Python video auto editor."""
from __future__ import annotations

import os
import subprocess
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import video_auto_editor

SIZES = {"横屏 1920×1080 (16:9)": "landscape", "竖屏 1080×1920 (9:16)": "portrait"}
VIDEO_EXTENSIONS = video_auto_editor.VIDEO_EXTENSIONS


class VideoEditorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("创维视频剪辑器")
        self.geometry("760x600")
        self.minsize(680, 520)
        self.files: list[str] = []
        self.output_dir: Path | None = None
        self._running = False
        self._build_ui()

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=24)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="创维视频剪辑器", font=("Segoe UI", 20, "bold")).pack(anchor="w")
        ttk.Label(
            outer,
            text="第一阶段：批量导入 · 自动缩放裁切 · 合并 · MP4 输出",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(4, 18))

        actions = ttk.Frame(outer)
        actions.pack(fill="x")
        self.add_button = ttk.Button(actions, text="添加视频", command=self.add_files)
        self.add_button.pack(side="left", padx=(0, 8))
        self.folder_button = ttk.Button(actions, text="选择视频文件夹", command=self.add_folder)
        self.folder_button.pack(side="left")
        self.clear_button = ttk.Button(actions, text="清空", command=self.clear_files)
        self.clear_button.pack(side="right")

        list_frame = ttk.Frame(outer)
        list_frame.pack(fill="both", expand=True, pady=12)
        self.listbox = tk.Listbox(list_frame, height=10, selectmode="extended")
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.configure(yscrollcommand=scrollbar.set)

        settings = ttk.LabelFrame(outer, text="输出设置", padding=12)
        settings.pack(fill="x")
        ttk.Label(settings, text="输出比例：").grid(row=0, column=0, sticky="w")
        self.mode = tk.StringVar(value=list(SIZES)[0])
        ttk.Combobox(
            settings,
            textvariable=self.mode,
            values=list(SIZES),
            state="readonly",
            width=32,
        ).grid(row=0, column=1, sticky="w", padx=8)
        ttk.Label(settings, text="每段最长（秒）：").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.max_seconds = tk.StringVar(value="")
        ttk.Entry(settings, textvariable=self.max_seconds, width=12).grid(
            row=1, column=1, sticky="w", padx=8, pady=(10, 0)
        )

        output_row = ttk.Frame(outer)
        output_row.pack(fill="x", pady=(12, 0))
        self.output_label = ttk.Label(output_row, text="输出文件夹：未选择")
        self.output_label.pack(side="left", fill="x", expand=True)
        self.output_button = ttk.Button(output_row, text="选择输出文件夹", command=self.choose_output)
        self.output_button.pack(side="right")

        self.progress = ttk.Progressbar(outer, mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=(16, 6))
        self.progress_label = ttk.Label(outer, text="0%")
        self.progress_label.pack(anchor="e")
        self.status = tk.StringVar(value="等待添加视频")
        ttk.Label(outer, textvariable=self.status).pack(anchor="w", pady=(2, 0))

        bottom = ttk.Frame(outer)
        bottom.pack(fill="x", pady=(14, 0))
        self.start_button = ttk.Button(bottom, text="▶ 开始剪辑", command=self.start)
        self.start_button.pack(side="left", fill="x", expand=True, ipady=6)
        self.open_button = ttk.Button(bottom, text="打开输出文件夹", command=self.open_output_folder, state="disabled")
        self.open_button.pack(side="left", padx=(10, 0), ipady=6)

    def add_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="选择视频",
            filetypes=[("视频文件", "*.mp4 *.mov *.mkv *.avi *.webm *.m4v")],
        )
        for path in paths:
            if path not in self.files:
                self.files.append(path)
                self.listbox.insert("end", path)
        self._refresh_status()

    def add_folder(self) -> None:
        folder = filedialog.askdirectory(title="选择视频文件夹")
        if not folder:
            return
        for path in sorted(Path(folder).iterdir()):
            if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS and str(path) not in self.files:
                self.files.append(str(path))
                self.listbox.insert("end", str(path))
        self._refresh_status()

    def clear_files(self) -> None:
        if self._running:
            return
        self.files.clear()
        self.listbox.delete(0, "end")
        self._refresh_status()

    def choose_output(self) -> None:
        folder = filedialog.askdirectory(title="选择输出文件夹")
        if folder:
            self.output_dir = Path(folder)
            self.output_label.configure(text=f"输出文件夹：{self.output_dir}")

    def open_output_folder(self) -> None:
        folder = self.output_dir
        if folder is None:
            return
        try:
            folder.mkdir(parents=True, exist_ok=True)
            os.startfile(str(folder))
        except AttributeError:
            subprocess.Popen(["explorer", str(folder)])
        except OSError as exc:
            messagebox.showerror("打开失败", f"无法打开输出文件夹：\n{exc}")

    def _refresh_status(self) -> None:
        self.status.set(f"已添加 {len(self.files)} 个视频" if self.files else "等待添加视频")

    def _set_running(self, running: bool) -> None:
        self._running = running
        state = "disabled" if running else "normal"
        for button in (self.add_button, self.folder_button, self.clear_button, self.output_button):
            button.configure(state=state)
        self.start_button.configure(state=state)

    def start(self) -> None:
        if self._running:
            return
        if not self.files:
            messagebox.showwarning("提示", "请先添加视频或选择视频文件夹。")
            return
        try:
            max_seconds = float(self.max_seconds.get()) if self.max_seconds.get().strip() else None
            if max_seconds is not None and max_seconds <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("输入错误", "每段最长时间必须是正数。")
            return

        if self.output_dir is None:
            self.choose_output()
            if self.output_dir is None:
                return

        mode = SIZES[self.mode.get()]
        output_dir = self.output_dir
        sources = [Path(path) for path in self.files]
        width, height = video_auto_editor.SIZES[mode]
        output = output_dir / f"final_{mode}_{width}x{height}.mp4"

        self.progress["value"] = 0
        self.progress_label.configure(text="0%")
        self.status.set("正在处理，请稍候……")
        self.open_button.configure(state="disabled")
        self._set_running(True)
        threading.Thread(
            target=self._run,
            args=(sources, mode, max_seconds, output),
            daemon=True,
        ).start()

    def _run(
        self,
        sources: list[Path],
        mode: str,
        max_seconds: float | None,
        output: Path,
    ) -> None:
        try:
            video_auto_editor.run_editor(
                sources,
                output,
                mode,
                max_seconds,
                progress_callback=lambda percent, index, name: self.after(
                    0, self._progress, percent, index, len(sources), name
                ),
            )
            self.after(0, lambda: self._done(output))
        except Exception as exc:
            self.after(0, lambda: self._error(str(exc)))

    def _progress(self, percent: int, index: int, total: int, name: str) -> None:
        self.progress["value"] = percent
        self.progress_label.configure(text=f"{percent}%")
        if name == "合并视频":
            self.status.set("正在合并视频……")
        else:
            self.status.set(f"正在处理第 {index}/{total} 个：{name}")

    def _done(self, output: Path) -> None:
        self._set_running(False)
        self.progress["value"] = 100
        self.progress_label.configure(text="100%")
        self.status.set(f"完成：{output.name}")
        self.open_button.configure(state="normal")
        messagebox.showinfo("完成", f"视频已导出：\n{output}")

    def _error(self, text: str) -> None:
        self._set_running(False)
        self.status.set("剪辑失败，请检查 FFmpeg 和输入视频")
        messagebox.showerror("剪辑失败", text[-4000:] or "发生未知错误。")


if __name__ == "__main__":
    VideoEditorApp().mainloop()
