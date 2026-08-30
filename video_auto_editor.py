"""Simple Python video batch editor using FFmpeg.

Features:
- Detects video files in an input folder.
- Optionally trims each clip to a fixed duration.
- Concatenates clips in filename order.
- Writes the final MP4 to the output folder.

Requires FFmpeg/ffprobe to be installed and available on PATH.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}


def require_binary(name: str) -> None:
    if shutil.which(name) is None:
        raise SystemExit(f"未找到 {name}。请安装 FFmpeg，并确保 {name} 在 PATH 中。")


def duration_seconds(path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "json", str(path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(json.loads(result.stdout)["format"]["duration"])


def render_clip(src: Path, dst: Path, max_seconds: float | None) -> None:
    cmd = ["ffmpeg", "-y", "-i", str(src)]
    if max_seconds is not None:
        cmd += ["-t", str(max_seconds)]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "192k", str(dst)]
    subprocess.run(cmd, check=True)


def concat_clips(clips: list[Path], output: Path) -> None:
    concat_file = output.parent / "concat_list.txt"
    concat_file.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in clips), encoding="utf-8")
    try:
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
            "-c", "copy", str(output)
        ]
        subprocess.run(cmd, check=True)
    finally:
        concat_file.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="批量合并并可选裁剪视频")
    parser.add_argument("--input", default="input", help="输入视频文件夹")
    parser.add_argument("--output", default="output/final.mp4", help="输出 MP4 文件")
    parser.add_argument("--max-seconds", type=float, default=None, help="每个视频最多保留多少秒")
    args = parser.parse_args()

    require_binary("ffmpeg")
    require_binary("ffprobe")

    input_dir = Path(args.input)
    output = Path(args.output)
    input_dir.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)

    sources = sorted(p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS)
    if not sources:
        raise SystemExit(f"{input_dir} 中没有找到视频文件。")

    work_dir = output.parent / ".work"
    work_dir.mkdir(parents=True, exist_ok=True)
    clips: list[Path] = []

    try:
        for index, src in enumerate(sources, start=1):
            dst = work_dir / f"clip_{index:04d}.mp4"
            print(f"处理: {src.name} ({duration_seconds(src):.1f}s)")
            render_clip(src, dst, args.max_seconds)
            clips.append(dst)

        concat_clips(clips, output)
        print(f"完成: {output.resolve()}")
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
