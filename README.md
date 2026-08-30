# Python 视频自动剪辑器

一个基于 Python + FFmpeg 的简单视频批处理工具。

## 功能

- 自动读取 `input/` 中的视频
- 按文件名顺序处理
- 可选限制每个视频的最大时长
- 合并为一个 MP4
- 输出到 `output/final.mp4`

## 环境

Windows 安装 FFmpeg，并确保 `ffmpeg` 和 `ffprobe` 可以在终端直接运行。

## 使用

把视频放进 `input/`，然后运行：

```bash
python video_auto_editor.py
```

每个视频最多保留 30 秒：

```bash
python video_auto_editor.py --max-seconds 30
```

指定目录：

```bash
python video_auto_editor.py --input input --output output/final.mp4
```

下一步可以继续加入：自动去静音、字幕、BGM、横竖屏转换、片头片尾和 AI 精彩片段检测。
