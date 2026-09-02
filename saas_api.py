"""Small FastAPI slice exposing the subscription/quota contract.

This is intentionally payment-provider agnostic. The billing webhook must activate an
account only after a verified recurring-payment event from the selected provider.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app_config import MAX_VIDEOS_PER_BATCH, MONTHLY_PRICE_CNY, MONTHLY_VIDEO_QUOTA
from saas_quota import Account

app = FastAPI(title="创维视频 SaaS API", version="0.1.0")
accounts: dict[str, Account] = {}


class AccountCreate(BaseModel):
    account_id: str | None = Field(default=None, min_length=1, max_length=128)


class GenerateRequest(BaseModel):
    count: int = Field(ge=1, le=MAX_VIDEOS_PER_BATCH)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/plan")
def plan() -> dict[str, int]:
    return {
        "price_cny_per_month": MONTHLY_PRICE_CNY,
        "monthly_video_quota": MONTHLY_VIDEO_QUOTA,
        "max_videos_per_batch": MAX_VIDEOS_PER_BATCH,
    }


@app.post("/accounts")
def create_account(payload: AccountCreate) -> dict[str, str]:
    account_id = payload.account_id or uuid4().hex
    if account_id in accounts:
        raise HTTPException(status_code=409, detail="账号已存在。")
    accounts[account_id] = Account(account_id=account_id, period_end=datetime.now(timezone.utc))
    return {"account_id": account_id}


@app.get("/accounts/{account_id}/quota")
def quota(account_id: str) -> dict[str, int | bool | str | None]:
    account = accounts.get(account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="账号不存在。")
    return {
        "active": account.active,
        "quota_total": account.quota_total,
        "quota_used": account.quota_used,
        "quota_remaining": account.quota_remaining,
        "period_end": account.period_end.isoformat() if account.period_end else None,
    }


@app.post("/accounts/{account_id}/generate/reserve")
def reserve_generation(account_id: str, payload: GenerateRequest) -> dict[str, int]:
    account = accounts.get(account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="账号不存在。")
    try:
        account.reserve_generation(payload.count)
    except PermissionError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"reserved": payload.count, "quota_remaining": account.quota_remaining}
