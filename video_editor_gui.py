"""Windows GUI for the Python video auto editor."""
from __future__ import annotations

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
        self.title("AI 视频自动剪辑器")
        self.geometry("700x520")
        self.minsize(620, 460)
        self.files: list[str] = []
        self._build_ui()

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=24)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="AI 视频自动剪辑器", font=("Segoe UI", 20, "bold")).pack(anchor="w")
        ttk.Label(outer, text="Python + FFmpeg · 横屏 / 竖屏一键输出", font=("Segoe UI", 10)).pack(anchor="w", pady=(4, 20))
        actions = ttk.Frame(outer); actions.pack(fill="x")
        ttk.Button(actions, text="添加视频", command=self.add_files).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="选择文件夹", command=self.add_folder).pack(side="left")
        ttk.Button(actions, text="清空", command=self.clear_files).pack(side="right")
        self.listbox = tk.Listbox(outer, height=10); self.listbox.pack(fill="both", expand=True, pady=14)
        settings = ttk.LabelFrame(outer, text="输出设置", padding=12); settings.pack(fill="x")
        ttk.Label(settings, text="输出比例：").grid(row=0, column=0, sticky="w")
        self.mode = tk.StringVar(value=list(SIZES)[0])
        ttk.Combobox(settings, textvariable=self.mode, values=list(SIZES), state="readonly", width=32).grid(row=0, column=1, sticky="w", padx=8)
        ttk.Label(settings, text="每段最长（秒）：").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.max_seconds = tk.StringVar(value="")
        ttk.Entry(settings, textvariable=self.max_seconds, width=12).grid(row=1, column=1, sticky="w", padx=8, pady=(10, 0))
        self.progress = ttk.Progressbar(outer, mode="indeterminate"); self.progress.pack(fill="x", pady=(18, 8))
        self.status = tk.StringVar(value="等待添加视频"); ttk.Label(outer, textvariable=self.status).pack(anchor="w")
        ttk.Button(outer, text="▶ 开始自动剪辑", command=self.start).pack(fill="x", pady=(16, 0), ipady=6)

    def add_files(self) -> None:
        paths = filedialog.askopenfilenames(title="选择视频", filetypes=[("视频", "*.mp4 *.mov *.mkv *.avi *.webm *.m4v")])
        for path in paths:
            if path not in self.files:
                self.files.append(path); self.listbox.insert("end", path)
        self._refresh_status()

    def add_folder(self) -> None:
        folder = filedialog.askdirectory(title="选择视频文件夹")
        if not folder: return
        for path in sorted(Path(folder).iterdir()):
            if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS and str(path) not in self.files:
                self.files.append(str(path)); self.listbox.insert("end", str(path))
        self._refresh_status()

    def clear_files(self) -> None:
        self.files.clear(); self.listbox.delete(0, "end"); self._refresh_status()

    def _refresh_status(self) -> None:
        self.status.set(f"已添加 {len(self.files)} 个视频" if self.files else "等待添加视频")

    def start(self) -> None:
        if not self.files:
            messagebox.showwarning("提示", "请先添加视频或选择视频文件夹。"); return
        try:
            max_seconds = float(self.max_seconds.get()) if self.max_seconds.get().strip() else None
            if max_seconds is not None and max_seconds <= 0: raise ValueError
        except ValueError:
            messagebox.showerror("输入错误", "每段最长时间必须是正数。"); return
        output_dir = filedialog.askdirectory(title="选择输出文件夹")
        if not output_dir: return
        mode = SIZES[self.mode.get()]
        self.progress.start(12); self.status.set("正在剪辑，请稍候……")
        threading.Thread(target=self._run, args=(mode, max_seconds, Path(output_dir)), daemon=True).start()

    def _run(self, mode: str, max_seconds: float | None, output_dir: Path) -> None:
        try:
            output = output_dir / f"final_{mode}.mp4"
            video_auto_editor.run_editor([Path(p) for p in self.files], output, mode, max_seconds)
            self.after(0, lambda: self._done(output))
        except Exception as exc:
            self.after(0, lambda: self._error(str(exc)))

    def _done(self, output: Path) -> None:
        self.progress.stop(); self.status.set(f"完成：{output.name}")
        messagebox.showinfo("完成", f"视频已导出：\n{output}")

    def _error(self, text: str) -> None:
        self.progress.stop(); self.status.set("剪辑失败")
        messagebox.showerror("剪辑失败", text[-3000:])


if __name__ == "__main__":
    VideoEditorApp().mainloop()
