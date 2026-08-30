"""Video batch editor using FFmpeg; supports landscape and portrait output."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
SIZES = {"landscape": (1920, 1080), "portrait": (1080, 1920)}
ProgressCallback = Callable[[int, int, str], None]


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
    raise FileNotFoundError(
        f"未找到 {name}。请安装 FFmpeg，或将 FFmpeg 放到软件目录的 ffmpeg 文件夹。"
    )


def duration_seconds(path: Path, ffprobe: str | None = None) -> float:
    ffprobe = ffprobe or _binary("ffprobe")
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(json.loads(result.stdout)["format"]["duration"])


def render_clip(
    src: Path,
    dst: Path,
    max_seconds: float | None,
    size: tuple[int, int],
    ffmpeg: str,
    progress_callback: ProgressCallback | None = None,
    clip_index: int = 1,
    clip_total: int = 1,
) -> None:
    width, height = size
    vf = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(src),
    ]
    if max_seconds is not None:
        cmd += ["-t", str(max_seconds)]
    cmd += [
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        "-progress",
        "pipe:1",
        "-nostats",
        str(dst),
    ]

    expected_duration = max_seconds
    if expected_duration is None:
        try:
            expected_duration = duration_seconds(src)
        except (OSError, ValueError, KeyError, subprocess.CalledProcessError, json.JSONDecodeError):
            expected_duration = None

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    stderr_chunks: list[str] = []
    try:
        assert process.stdout is not None
        for line in process.stdout:
            line = line.strip()
            if line.startswith("out_time_ms=") and expected_duration and progress_callback:
                try:
                    elapsed = int(line.split("=", 1)[1]) / 1_000_000
                    ratio = min(1.0, max(0.0, elapsed / expected_duration))
                    overall = ((clip_index - 1) + ratio) / clip_total
                    progress_callback(int(overall * 100), clip_index, src.name)
                except ValueError:
                    pass
        if process.stderr is not None:
            stderr_chunks.append(process.stderr.read())
        return_code = process.wait()
    except Exception:
        process.kill()
        process.wait()
        raise

    if return_code != 0:
        details = "".join(stderr_chunks).strip()
        raise subprocess.CalledProcessError(return_code, cmd, output=None, stderr=details)
    if progress_callback:
        progress_callback(int(clip_index / clip_total * 100), clip_index, src.name)


def concat_clips(
    clips: list[Path],
    output: Path,
    ffmpeg: str,
    progress_callback: ProgressCallback | None = None,
) -> None:
    concat_file = output.parent / "concat_list.txt"
    concat_file.write_text(
        "".join(f"file '{p.resolve().as_posix().replace(chr(39), chr(39) + chr(39))}'\n" for p in clips),
        encoding="utf-8",
    )
    try:
        process = subprocess.Popen(
            [
                ffmpeg,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_file),
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                "-progress",
                "pipe:1",
                "-nostats",
                str(output),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        stderr_chunks: list[str] = []
        assert process.stdout is not None
        for line in process.stdout:
            line = line.strip()
            if line.startswith("progress=") and line == "progress=end" and progress_callback:
                progress_callback(100, len(clips), "合并视频")
        if process.stderr is not None:
            stderr_chunks.append(process.stderr.read())
        return_code = process.wait()
        if return_code != 0:
            details = "".join(stderr_chunks).strip()
            raise subprocess.CalledProcessError(return_code, [ffmpeg, "concat"], stderr=details)
    finally:
        concat_file.unlink(missing_ok=True)


def run_editor(
    sources: list[Path],
    output: Path,
    mode: str = "landscape",
    max_seconds: float | None = None,
    progress_callback: ProgressCallback | None = None,
) -> Path:
    if mode not in SIZES:
        raise ValueError(f"未知输出模式: {mode}")
    if not sources:
        raise ValueError("没有可处理的视频文件。")

    ffmpeg = _binary("ffmpeg")
    output.parent.mkdir(parents=True, exist_ok=True)
    work_dir = output.parent / ".work"
    work_dir.mkdir(parents=True, exist_ok=True)
    clips: list[Path] = []
    try:
        total = len(sources)
        for index, src in enumerate(sources, start=1):
            dst = work_dir / f"clip_{index:04d}.mp4"
            if progress_callback:
                progress_callback(int((index - 1) / total * 100), index, src.name)
            render_clip(
                src,
                dst,
                max_seconds,
                SIZES[mode],
                ffmpeg,
                progress_callback,
                index,
                total,
            )
            clips.append(dst)
        if progress_callback:
            progress_callback(99, total, "正在合并视频")
        concat_clips(clips, output, ffmpeg, progress_callback)
        if progress_callback:
            progress_callback(100, total, output.name)
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
    if not input_dir.exists():
        raise SystemExit(f"输入文件夹不存在：{input_dir}")
    sources = sorted(p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS)
    if not sources:
        raise SystemExit(f"{input_dir} 中没有找到视频文件。")
    width, height = SIZES[args.mode]
    output = Path(args.output) if args.output else Path("output") / f"final_{args.mode}_{width}x{height}.mp4"
    run_editor(sources, output, args.mode, args.max_seconds)
    print(f"完成: {output.resolve()}")


if __name__ == "__main__":
    main()
