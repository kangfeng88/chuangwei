"""Simple Python video batch editor using FFmpeg.

Supports two output formats:
- landscape: 1920x1080 (16:9)
- portrait: 1080x1920 (9:16)

Requires FFmpeg/ffprobe on PATH.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
SIZES = {"landscape": (1920, 1080), "portrait": (1080, 1920)}


def require_binary(name: str) -> None:
    if shutil.which(name) is None:
        raise SystemExit(f"未找到 {name}。请安装 FFmpeg，并确保 {name} 在 PATH 中。")


def duration_seconds(path: Path) -> float:
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(json.loads(result.stdout)["format"]["duration"])


def render_clip(src: Path, dst: Path, max_seconds: float | None, size: tuple[int, int]) -> None:
    width, height = size
    # Scale to cover the target canvas, then center-crop. This avoids distortion.
    vf = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"
    cmd = ["ffmpeg", "-y", "-i", str(src)]
    if max_seconds is not None:
        cmd += ["-t", str(max_seconds)]
    cmd += [
        "-vf", vf,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(dst),
    ]
    subprocess.run(cmd, check=True)


def concat_clips(clips: list[Path], output: Path) -> None:
    concat_file = output.parent / "concat_list.txt"
    concat_file.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in clips), encoding="utf-8")
    try:
        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(output)]
        subprocess.run(cmd, check=True)
    finally:
        concat_file.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="批量合并并裁剪为横屏或竖屏视频")
    parser.add_argument("--input", default="input", help="输入视频文件夹")
    parser.add_argument("--output", default=None, help="输出 MP4 文件；默认按尺寸自动命名")
    parser.add_argument("--mode", choices=SIZES, default="landscape", help="landscape=1920x1080 横屏；portrait=1080x1920 竖屏")
    parser.add_argument("--max-seconds", type=float, default=None, help="每个视频最多保留多少秒")
    args = parser.parse_args()

    require_binary("ffmpeg")
    require_binary("ffprobe")
    input_dir = Path(args.input)
    width, height = SIZES[args.mode]
    output = Path(args.output) if args.output else Path("output") / f"final_{args.mode}_{width}x{height}.mp4"
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
            print(f"处理: {src.name} ({duration_seconds(src):.1f}s) -> {width}x{height}")
            render_clip(src, dst, args.max_seconds, (width, height))
            clips.append(dst)
        concat_clips(clips, output)
        print(f"完成: {output.resolve()}")
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
