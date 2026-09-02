# 创维视频剪辑器

一个基于 Python + FFmpeg 的 Windows 视频批处理工具，并已增加可运行的自动视频 SaaS MVP。

## 桌面版

第一阶段能力：

- Windows 图形界面
- 添加单个或多个视频，也可以直接选择视频文件夹
- 横屏 / 竖屏选择
- 自动等比缩放并居中裁切，避免画面变形
- 多个视频按列表顺序合并
- 实时显示处理进度和当前视频
- 输出 MP4（H.264 + AAC）
- FFmpeg 缺失、输入错误、处理失败时弹窗提示

## SaaS MVP

产品规则已经固定为：

- **¥5 / 月**
- **500 个视频 / 月**
- **1 个生成视频 = 1 个额度**
- **单次最多生成 20 个**
- **单个上传源视频最多 3 分钟（180 秒）**
- 默认输出竖屏 9:16，也支持横屏 16:9
- 页面显示已用额度、剩余额度和订阅到期时间
- 失败任务会退回预扣额度

自动视频 MVP 的工作流是：**上传一个源视频 → 校验 ≤3 分钟 → 预扣额度 → 后台自动生成 1–20 个不同时间窗口的短视频 → 提供逐个下载**。

当前自动剪辑采用低成本 FFmpeg 本地处理：从源视频中分布式选择不同片段，并自动裁切成指定画幅。这样先把“上传→排队→处理→下载→额度”完整跑通，再接入更昂贵的 AI 精彩片段、字幕和 BGM 模块。

### 启动 SaaS 网站

安装依赖：

```bash
pip install -r requirements-saas.txt
```

启动：

```bash
python run_saas.py
```

浏览器打开 `http://localhost:8000`。

也可以直接：

```bash
uvicorn saas_web:app --host 0.0.0.0 --port 8000
```

### API

- `GET /health`：健康检查
- `GET /plan`：产品规则
- `GET /accounts/{account_id}/quota`：额度和到期时间
- `POST /generate`：上传视频并创建生成任务
- `GET /jobs/{job_id}`：查询任务状态
- `GET /jobs/{job_id}/files/{filename}`：下载生成结果

## Windows 便携版

GitHub Actions 会自动构建 Windows EXE，并把 FFmpeg 一起打包。运行 `ChuangeiVideoEditor.exe` 即可，不需要另外安装 FFmpeg。

## 命令行模式

把视频放进 `input/`：

```bash
python video_auto_editor.py --mode landscape
```

竖屏：

```bash
python video_auto_editor.py --mode portrait
```

## 测试

```bash
pytest -q
```

## 下一步：商业化支付

Stripe 沙盒账号已经连接，但**当前代码没有把真实收款 webhook 接入生成权限**。上线前需要配置可用的循环订阅价格、Checkout、Webhook 签名校验、数据库持久化，以及订阅取消/付款失败后的停用逻辑。生产环境还需要对象存储、任务队列和登录系统。

原有桌面编辑器保持不变；SaaS 入口独立在 `saas_web.py`。
