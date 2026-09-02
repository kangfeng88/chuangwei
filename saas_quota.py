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

    def is_active_now(self, now: datetime | None = None) -> bool:
        """Return whether the subscription is enabled and its current period has not expired."""
        if not self.active:
            return False
        if self.period_end is None:
            return True
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        return current < self.period_end.astimezone(timezone.utc)

    @property
    def quota_remaining(self) -> int:
        return max(0, self.quota_total - self.quota_used)

    def can_generate(self, count: int, now: datetime | None = None) -> bool:
        return 1 <= count <= MAX_VIDEOS_PER_BATCH and self.is_active_now(now) and count <= self.quota_remaining

    def reserve_generation(self, count: int, now: datetime | None = None) -> None:
        if count < 1 or count > MAX_VIDEOS_PER_BATCH:
            raise ValueError(f"单次最多生成 {MAX_VIDEOS_PER_BATCH} 个视频。")
        if not self.is_active_now(now):
            raise PermissionError("订阅已失效，无法生成视频。")
        if count > self.quota_remaining:
            raise ValueError(f"本月剩余额度不足：只剩 {self.quota_remaining} 个视频。")
        self.quota_used += count

    def refund_generation(self, count: int) -> None:
        if count < 1:
            raise ValueError("退款额度必须大于 0。")
        self.quota_used = max(0, self.quota_used - count)

    def reset_period(self, period_end: datetime) -> None:
        self.quota_used = 0
        self.period_end = period_end.astimezone(timezone.utc)
