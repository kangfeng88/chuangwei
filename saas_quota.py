"""Subscription quota rules for the first SaaS backend slice."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app_config import MONTHLY_VIDEO_QUOTA, MAX_VIDEOS_PER_BATCH


@dataclass
class Account:
    account_id: str
    active: bool = True
    quota_total: int = MONTHLY_VIDEO_QUOTA
    quota_used: int = 0
    period_end: datetime | None = None

    @property
    def quota_remaining(self) -> int:
        return max(0, self.quota_total - self.quota_used)

    def can_generate(self, count: int) -> bool:
        return 1 <= count <= MAX_VIDEOS_PER_BATCH and self.active and count <= self.quota_remaining

    def reserve_generation(self, count: int) -> None:
        if count > MAX_VIDEOS_PER_BATCH:
            raise ValueError(f"单次最多生成 {MAX_VIDEOS_PER_BATCH} 个视频。")
        if not self.active:
            raise PermissionError("订阅未生效，无法生成视频。")
        if count > self.quota_remaining:
            raise ValueError(f"本月剩余额度不足：只剩 {self.quota_remaining} 个视频。")
        self.quota_used += count

    def reset_period(self, period_end: datetime) -> None:
        self.quota_used = 0
        self.period_end = period_end.astimezone(timezone.utc)
