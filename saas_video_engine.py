"""Low-cost automatic short-video renderer for the SaaS MVP.

The first production slice deliberately avoids expensive generative video. It turns one
uploaded source into N distinct short clips, using evenly distributed windows and a
portrait/landscape crop. FFmpeg does the heavy lifting locally.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from app_config import MAX_UPLOAD_SECONDS, validate_duration

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}


def _binary(name: str) -> str:
    names = [name + ".exe", name]
    roots = []
    if getattr(sys, "frozen", False):
        roots.append(Path(sys.executable).resolve().parent / "ffmpeg")
    roots.append(Path(__file__).resolve().parent / "ffmpeg")
    for root in roots:
        for candidate in names:
            path = root / candidate
            if path.exists():
                return str(path)
    found = shutil.which(name)
    if found:
        return found
    raise FileNotFoundError("未找到 FFmpeg/FFprobe，请安装 FFmpeg 或放入 ffmpeg 文件夹。")


def probe_duration(source: Path) -> float:
    result = subprocess.run(
        [_binary("ffprobe"), "-v", "error", "-show_entries", "format=duration", "-of", "json", str(source)],
        capture_output=True,
        text=True,
        check=True,
    )
    duration = float(json.loads(result.stdout)["format"]["duration"])
    validate_duration(duration)
    return duration


def _clip_window(duration: float, index: int, total: int) -> tuple[float, float]:
    """Return a distinct start and length for a generated clip."""
    target = min(30.0, max(5.0, duration / 3.0))
    length = min(target, duration)
    if total == 1 or duration <= length:
        return 0.0, length
    max_start = duration - length
    start = max_start * index / (total - 1)
    return start, length


def render_variants(source: Path, output_dir: Path, count: int, mode: str = "portrait") -> list[Path]:
    if count < 1 or count > 20:
        raise ValueError("单次生成数量必须在 1 到 20 之间。")
    duration = probe_duration(source)
    output_dir.mkdir(parents=True, exist_ok=True)
    if mode == "portrait":
        vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    elif mode == "landscape":
        vf = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080"
    else:
        raise ValueError("mode 只能是 portrait 或 landscape。")

    outputs: list[Path] = []
    ffmpeg = _binary("ffmpeg")
    for index in range(count):
        start, length = _clip_window(duration, index, count)
        output = output_dir / f"video_{index + 1:02d}.mp4"
        cmd = [
            ffmpeg, "-y", "-ss", f"{start:.3f}", "-i", str(source), "-t", f"{length:.3f}",
            "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
            "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(output),
        ]
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        outputs.append(output)
    return outputs
