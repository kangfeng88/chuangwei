"""Product limits and subscription settings for the video SaaS MVP."""

MONTHLY_PRICE_CNY = 5
MONTHLY_VIDEO_QUOTA = 500
MAX_VIDEOS_PER_BATCH = 20
MAX_UPLOAD_SECONDS = 180


def validate_batch_size(count: int) -> None:
    if count < 1:
        raise ValueError("至少需要 1 个视频。")
    if count > MAX_VIDEOS_PER_BATCH:
        raise ValueError(f"单次最多生成 {MAX_VIDEOS_PER_BATCH} 个视频。")


def validate_duration(seconds: float) -> None:
    if seconds <= 0:
        raise ValueError("视频时长必须大于 0 秒。")
    if seconds > MAX_UPLOAD_SECONDS:
        raise ValueError("单个上传视频不能超过 3 分钟（180 秒）。")
