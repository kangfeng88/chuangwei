# 创维视频剪辑器

一个基于 Python + FFmpeg 的 Windows 视频批处理工具。

## 第一阶段功能

- Windows 图形界面
- 添加单个或多个视频，也可以直接选择视频文件夹
- 横屏 / 竖屏选择
- 自动等比缩放并居中裁切，避免画面变形
- 多个视频按列表顺序合并
- 实时显示处理进度和当前视频
- 输出 MP4（H.264 + AAC）
- FFmpeg 缺失、输入错误、处理失败时弹窗提示
- 一键打开输出文件夹

## 输出尺寸

- **横屏**：1920 × 1080（16:9）
- **竖屏**：1080 × 1920（9:16）

## Windows 使用

### 直接运行 Python

确保已安装 Python 3.12 和 FFmpeg，并让 `ffmpeg` / `ffprobe` 可以在终端运行：

```bash
python video_editor_gui.py
```

### Windows 便携版

GitHub Actions 会自动构建 Windows EXE，并把 FFmpeg 一起打包。运行 `ChuangeiVideoEditor.exe` 即可，不需要另外安装 FFmpeg。

程序界面中：

1. 点击 **添加视频**，可一次选择多个视频。
2. 或点击 **选择视频文件夹** 批量加入视频。
3. 选择 **横屏** 或 **竖屏**。
4. 可选填写“每段最长（秒）”。留空表示保留完整视频。
5. 选择输出文件夹，点击 **开始剪辑**。
6. 完成后点击 **打开输出文件夹**。

输出文件名示例：

- `final_landscape_1920x1080.mp4`
- `final_portrait_1080x1920.mp4`

## 命令行模式

把视频放进 `input/`：

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

## 第二阶段计划

第一阶段先保证稳定的基础剪辑能力；后续再加入真正的“智能剪辑”：

- 自动去静音 / 空白
- AI 精彩片段识别
- 自动字幕
- BGM
- 片头片尾
