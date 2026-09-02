from datetime import datetime, timedelta, timezone

import pytest

from app_config import MAX_UPLOAD_SECONDS, MAX_VIDEOS_PER_BATCH, validate_batch_size, validate_duration
from saas_quota import Account


def test_batch_limit():
    validate_batch_size(MAX_VIDEOS_PER_BATCH)
    with pytest.raises(ValueError):
        validate_batch_size(MAX_VIDEOS_PER_BATCH + 1)


def test_three_minute_upload_limit():
    validate_duration(MAX_UPLOAD_SECONDS)
    with pytest.raises(ValueError):
        validate_duration(MAX_UPLOAD_SECONDS + 0.01)


def test_quota_reservation():
    account = Account("demo")
    account.reserve_generation(20)
    assert account.quota_remaining == 480


def test_cannot_reserve_more_than_remaining():
    account = Account("demo", quota_total=10)
    with pytest.raises(ValueError):
        account.reserve_generation(11)


def test_expired_subscription_cannot_generate():
    now = datetime.now(timezone.utc)
    account = Account("expired", period_end=now - timedelta(seconds=1))
    assert not account.is_active_now(now)
    assert not account.can_generate(1, now)
    with pytest.raises(PermissionError):
        account.reserve_generation(1, now)


def test_failed_generation_can_refund_quota():
    account = Account("demo")
    account.reserve_generation(5)
    account.refund_generation(5)
    assert account.quota_used == 0
    assert account.quota_remaining == 500
