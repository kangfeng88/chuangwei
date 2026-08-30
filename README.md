# Python 视频自动剪辑器

一个基于 Python + FFmpeg 的视频批处理工具。

## 输出尺寸

支持两种模式：

- **横屏**：1920 × 1080（16:9）
- **竖屏**：1080 × 1920（9:16）

程序会自动缩放并居中裁切，避免画面被拉伸。

## 使用

把视频放进 `input/`。

横屏：

```bash
python video_auto_editor.py --mode landscape
```

竖屏：

```bash
python video_auto_editor.py --mode portrait
```

每个视频最多保留 30 秒：

```bash
python video_auto_editor.py --mode landscape --max-seconds 30
```

默认输出：

- `output/final_landscape_1920x1080.mp4`
- `output/final_portrait_1080x1920.mp4`

## 环境

Windows 安装 FFmpeg，并确保 `ffmpeg` 和 `ffprobe` 可以在终端直接运行。

## 后续计划

- 自动去除静音/空白
- 自动字幕
- BGM
- AI 精彩片段检测
- 片头片尾
- 更友好的 Windows 图形界面
