"""Video batch editor using FFmpeg; supports landscape and portrait output."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
SIZES = {"landscape": (1920, 1080), "portrait": (1080, 1920)}


def _binary(name: str) -> str:
    names = [name + ".exe", name]
    roots = []
    if getattr(sys, "frozen", False):
        roots.append(Path(sys.executable).resolve().parent / "ffmpeg")
    roots.append(Path(__file__).resolve().parent / "ffmpeg")
    for root in roots:
        for n in names:
            p = root / n
            if p.exists():
                return str(p)
    found = shutil.which(name)
    if found:
        return found
    raise SystemExit(f"未找到 {name}。请安装 FFmpeg，或将 FFmpeg 放到软件目录的 ffmpeg 文件夹。")


def duration_seconds(path: Path, ffprobe: str | None = None) -> float:
    ffprobe = ffprobe or _binary("ffprobe")
    result = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)], capture_output=True, text=True, check=True)
    return float(json.loads(result.stdout)["format"]["duration"])


def render_clip(src: Path, dst: Path, max_seconds: float | None, size: tuple[int, int], ffmpeg: str) -> None:
    width, height = size
    vf = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"
    cmd = [ffmpeg, "-y", "-i", str(src)]
    if max_seconds is not None:
        cmd += ["-t", str(max_seconds)]
    cmd += ["-vf", vf, "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(dst)]
    subprocess.run(cmd, check=True)


def concat_clips(clips: list[Path], output: Path, ffmpeg: str) -> None:
    concat_file = output.parent / "concat_list.txt"
    concat_file.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in clips), encoding="utf-8")
    try:
        subprocess.run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(output)], check=True)
    finally:
        concat_file.unlink(missing_ok=True)


def run_editor(sources: list[Path], output: Path, mode: str = "landscape", max_seconds: float | None = None) -> Path:
    if mode not in SIZES:
        raise ValueError(f"未知输出模式: {mode}")
    ffmpeg = _binary("ffmpeg")
    ffprobe = _binary("ffprobe")
    output.parent.mkdir(parents=True, exist_ok=True)
    work_dir = output.parent / ".work"
    work_dir.mkdir(parents=True, exist_ok=True)
    clips: list[Path] = []
    try:
        for index, src in enumerate(sources, start=1):
            dst = work_dir / f"clip_{index:04d}.mp4"
            render_clip(src, dst, max_seconds, SIZES[mode], ffmpeg)
            clips.append(dst)
        concat_clips(clips, output, ffmpeg)
        return output
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="input")
    parser.add_argument("--output", default=None)
    parser.add_argument("--mode", choices=SIZES, default="landscape")
    parser.add_argument("--max-seconds", type=float, default=None)
    args = parser.parse_args()
    input_dir = Path(args.input)
    sources = sorted(p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS)
    if not sources:
        raise SystemExit(f"{input_dir} 中没有找到视频文件。")
    width, height = SIZES[args.mode]
    output = Path(args.output) if args.output else Path("output") / f"final_{args.mode}_{width}x{height}.mp4"
    run_editor(sources, output, args.mode, args.max_seconds)
    print(f"完成: {output.resolve()}")


if __name__ == "__main__":
    main()
