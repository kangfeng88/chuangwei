"""Windows GUI for the Python video auto editor.

Provides one-click landscape (1920x1080) or portrait (1080x1920) output.
"""
from __future__ import annotations

import subprocess
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

SIZES = {
    "横屏 1920×1080 (16:9)": "landscape",
    "竖屏 1080×1920 (9:16)": "portrait",
}


class VideoEditorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("AI 视频自动剪辑器")
        self.geometry("700x520")
        self.minsize(620, 460)
        self.files: list[str] = []
        self.input_dir: Path | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=24)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="AI 视频自动剪辑器", font=("Segoe UI", 20, "bold")).pack(anchor="w")
        ttk.Label(outer, text="Python + FFmpeg · 横屏 / 竖屏一键输出", font=("Segoe UI", 10)).pack(anchor="w", pady=(4, 20))

        actions = ttk.Frame(outer)
        actions.pack(fill="x")
        ttk.Button(actions, text="添加视频", command=self.add_files).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="选择文件夹", command=self.add_folder).pack(side="left")
        ttk.Button(actions, text="清空", command=self.clear_files).pack(side="right")

        self.listbox = tk.Listbox(outer, height=10)
        self.listbox.pack(fill="both", expand=True, pady=14)

        settings = ttk.LabelFrame(outer, text="输出设置", padding=12)
        settings.pack(fill="x")
        ttk.Label(settings, text="输出比例：").grid(row=0, column=0, sticky="w")
        self.mode = tk.StringVar(value=list(SIZES)[0])
        ttk.Combobox(settings, textvariable=self.mode, values=list(SIZES), state="readonly", width=32).grid(row=0, column=1, sticky="w", padx=8)
        ttk.Label(settings, text="每段最长（秒）：").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.max_seconds = tk.StringVar(value="")
        ttk.Entry(settings, textvariable=self.max_seconds, width=12).grid(row=1, column=1, sticky="w", padx=8, pady=(10, 0))

        self.progress = ttk.Progressbar(outer, mode="indeterminate")
        self.progress.pack(fill="x", pady=(18, 8))
        self.status = tk.StringVar(value="等待添加视频")
        ttk.Label(outer, textvariable=self.status).pack(anchor="w")
        ttk.Button(outer, text="▶ 开始自动剪辑", command=self.start).pack(fill="x", pady=(16, 0), ipady=6)

    def add_files(self) -> None:
        paths = filedialog.askopenfilenames(title="选择视频", filetypes=[("视频", "*.mp4 *.mov *.mkv *.avi *.webm *.m4v")])
        for path in paths:
            if path not in self.files:
                self.files.append(path)
                self.listbox.insert("end", path)
        self._refresh_status()

    def add_folder(self) -> None:
        folder = filedialog.askdirectory(title="选择视频文件夹")
        if not folder:
            return
        self.input_dir = Path(folder)
        for path in sorted(self.input_dir.iterdir()):
            if path.is_file() and path.suffix.lower() in {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"} and str(path) not in self.files:
                self.files.append(str(path))
                self.listbox.insert("end", str(path))
        self._refresh_status()

    def clear_files(self) -> None:
        self.files.clear()
        self.input_dir = None
        self.listbox.delete(0, "end")
        self._refresh_status()

    def _refresh_status(self) -> None:
        self.status.set(f"已添加 {len(self.files)} 个视频" if self.files else "等待添加视频")

    def start(self) -> None:
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

        output_dir = Path(filedialog.askdirectory(title="选择输出文件夹"))
        if not output_dir:
            return
        mode = SIZES[self.mode.get()]
        script = Path(__file__).with_name("video_auto_editor.py")
        self.progress.start(12)
        self.status.set("正在剪辑，请稍候……")
        threading.Thread(target=self._run, args=(script, mode, max_seconds, output_dir), daemon=True).start()

    def _run(self, script: Path, mode: str, max_seconds: float | None, output_dir: Path) -> None:
        # Use a temporary input directory containing links/copies so the core CLI remains reusable.
        temp_dir = output_dir / ".editor_input"
        temp_dir.mkdir(exist_ok=True)
        try:
            for i, src in enumerate(self.files, 1):
                link = temp_dir / f"{i:04d}_{Path(src).name}"
                if not link.exists():
                    try:
                        link.symlink_to(Path(src).resolve())
                    except OSError:
                        import shutil
                        shutil.copy2(src, link)
            output = output_dir / f"final_{mode}.mp4"
            cmd = [sys.executable, str(script), "--input", str(temp_dir), "--output", str(output), "--mode", mode]
            if max_seconds is not None:
                cmd += ["--max-seconds", str(max_seconds)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                self.after(0, lambda: self._done(output))
            else:
                self.after(0, lambda: self._error(result.stderr or result.stdout or "未知错误"))
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _done(self, output: Path) -> None:
        self.progress.stop()
        self.status.set(f"完成：{output.name}")
        messagebox.showinfo("完成", f"视频已导出：\n{output}")

    def _error(self, text: str) -> None:
        self.progress.stop()
        self.status.set("剪辑失败")
        messagebox.showerror("剪辑失败", text[-3000:])


if __name__ == "__main__":
    VideoEditorApp().mainloop()
