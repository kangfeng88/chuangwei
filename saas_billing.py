"""Stripe Sandbox subscription helpers for the SaaS MVP.

Only verified Stripe webhook events should activate or renew local access.
The Stripe secret key is read from STRIPE_SECRET_KEY and never stored in the repo.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

import stripe

from app_config import MONTHLY_VIDEO_QUOTA

STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID", "price_1UBCmM2OvFbFhpsnFV8EUEMW")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")


def _client() -> stripe.StripeClient:
    key = os.getenv("STRIPE_SECRET_KEY")
    if not key:
        raise RuntimeError("未配置 STRIPE_SECRET_KEY。")
    return stripe.StripeClient(key)


def create_checkout_session(account_id: str, success_url: str, cancel_url: str):
    client = _client()
    return client.v1.checkout.sessions.create({
        "mode": "subscription",
        "line_items": [{"price": STRIPE_PRICE_ID, "quantity": 1}],
        "client_reference_id": account_id,
        "metadata": {"account_id": account_id, "plan": "monthly"},
        "subscription_data": {"metadata": {"account_id": account_id, "plan": "monthly"}},
        "success_url": success_url,
        "cancel_url": cancel_url,
        "integration_identifier": "chuangwei_saas_checkout_9fKxQpLm",
    })


def parse_webhook(payload: bytes, signature: str):
    if not STRIPE_WEBHOOK_SECRET:
        raise RuntimeError("未配置 STRIPE_WEBHOOK_SECRET。")
    return stripe.Webhook.construct_event(payload, signature, STRIPE_WEBHOOK_SECRET)


def period_end_from_subscription(subscription) -> datetime | None:
    timestamp = subscription.get("current_period_end")
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def subscription_is_active(subscription) -> bool:
    return subscription.get("status") in {"active", "trialing"}


def quota_for_new_period() -> int:
    return MONTHLY_VIDEO_QUOTA
