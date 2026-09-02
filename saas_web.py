"""Runnable FastAPI web MVP for automatic video generation."""
from __future__ import annotations

import shutil
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from app_config import MAX_UPLOAD_SECONDS, MAX_VIDEOS_PER_BATCH, MONTHLY_PRICE_CNY, MONTHLY_VIDEO_QUOTA, validate_duration
from saas_billing import create_checkout_session, parse_webhook, period_end_from_subscription, subscription_is_active
from saas_quota import Account
from saas_video_engine import probe_duration, render_variants

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "saas_data"
UPLOADS = DATA / "uploads"
OUTPUTS = DATA / "outputs"
for directory in (UPLOADS, OUTPUTS):
    directory.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="创维自动视频", version="0.3.0")
accounts: dict[str, Account] = {}
jobs: dict[str, dict] = {}
lock = threading.Lock()


def _account(account_id: str) -> Account:
    with lock:
        account = accounts.get(account_id)
        if account is None:
            account = Account(
                account_id=account_id,
                active=True,
                period_end=datetime.now(timezone.utc) + timedelta(days=30),
            )
            accounts[account_id] = account
        return account


def _billing_account(account_id: str) -> Account:
    with lock:
        account = accounts.get(account_id)
        if account is None:
            account = Account(account_id=account_id, active=False, period_end=None)
            accounts[account_id] = account
        return account


def _run_job(job_id: str, account_id: str, source: Path, count: int, mode: str) -> None:
    job = jobs[job_id]
    try:
        job["status"] = "processing"
        outputs = render_variants(source, OUTPUTS / job_id, count, mode)
        job["status"] = "completed"
        job["outputs"] = [f"/jobs/{job_id}/files/{p.name}" for p in outputs]
        job["finished_at"] = datetime.now(timezone.utc).isoformat()
    except Exception as exc:
        job["status"] = "failed"
        job["error"] = str(exc)[:500]
        account = _account(account_id)
        with lock:
            account.refund_generation(count)
    finally:
        source.unlink(missing_ok=True)


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>创维自动视频</title><style>body{{font-family:system-ui;max-width:760px;margin:40px auto;padding:0 20px}}.card{{border:1px solid #ddd;border-radius:16px;padding:24px;margin:16px 0}}button{{padding:12px 18px;border:0;border-radius:10px;cursor:pointer}}input,select{{padding:10px;margin:8px 0;width:100%;box-sizing:border-box}}small{{color:#666}}#result{{white-space:pre-wrap}}</style></head><body><h1>创维自动视频</h1><div class="card"><b>¥{MONTHLY_PRICE_CNY}/月</b> · {MONTHLY_VIDEO_QUOTA} 个视频/月 · 单次最多 {MAX_VIDEOS_PER_BATCH} 个 · 单个源视频 ≤ {MAX_UPLOAD_SECONDS//60} 分钟</div><div class="card"><label>账号 ID</label><input id="account" value="demo"><button onclick="pay()">订阅 ¥{MONTHLY_PRICE_CNY}/月</button><label>上传视频</label><input id="video" type="file" accept="video/*"><label>生成数量（1-{MAX_VIDEOS_PER_BATCH}）</label><input id="count" type="number" min="1" max="{MAX_VIDEOS_PER_BATCH}" value="5"><label>画面</label><select id="mode"><option value="portrait">竖屏 9:16</option><option value="landscape">横屏 16:9</option></select><button onclick="go()">开始自动生成</button><div id="result"></div></div><div class="card"><button onclick="quota()">查看额度</button><div id="quota"></div></div><script>async function pay(){{let id=document.getElementById('account').value;let r=await fetch('/billing/checkout?account_id='+encodeURIComponent(id));let j=await r.json();if(r.ok) location.href=j.url; else alert(j.detail||'无法创建支付页面')}}async function quota(){{let id=document.getElementById('account').value;let r=await fetch('/accounts/'+encodeURIComponent(id)+'/quota');document.getElementById('quota').textContent=await r.text()}}async function go(){{let f=document.getElementById('video').files[0];if(!f) return alert('请选择视频');let d=new FormData();d.append('account_id',document.getElementById('account').value);d.append('count',document.getElementById('count').value);d.append('mode',document.getElementById('mode').value);d.append('video',f);let r=await fetch('/generate',{{method:'POST',body:d}});let t=await r.text();document.getElementById('result').textContent=t;if(r.ok){{let j=JSON.parse(t);poll(j.job_id)}}}}async function poll(id){{let r=await fetch('/jobs/'+id);let j=await r.json();document.getElementById('result').textContent=JSON.stringify(j,null,2);if(j.status==='waiting'||j.status==='processing')setTimeout(()=>poll(id),1000)}}quota()</script></body></html>'''


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/plan")
def plan() -> dict[str, int]:
    return {"price_cny_per_month": MONTHLY_PRICE_CNY, "monthly_video_quota": MONTHLY_VIDEO_QUOTA, "max_videos_per_batch": MAX_VIDEOS_PER_BATCH, "max_upload_seconds": MAX_UPLOAD_SECONDS}


@app.get("/billing/checkout")
def billing_checkout(request: Request, account_id: str) -> dict[str, str]:
    if not account_id:
        raise HTTPException(400, "缺少账号 ID。")
    base = str(request.base_url).rstrip("/")
    try:
        session = create_checkout_session(account_id, f"{base}/billing/success?session_id={{CHECKOUT_SESSION_ID}}", f"{base}/")
    except Exception as exc:
        raise HTTPException(503, f"Stripe 支付暂不可用：{exc}") from exc
    return {"url": session.url, "session_id": session.id}


@app.get("/billing/success", response_class=HTMLResponse)
def billing_success() -> str:
    return "<h2>支付流程已返回</h2><p>Stripe 会通过 webhook 确认订阅状态。请稍后刷新额度。</p><p><a href='/'>返回首页</a></p>"


@app.post("/billing/webhook")
async def billing_webhook(request: Request, stripe_signature: str | None = Header(default=None, alias="Stripe-Signature")) -> dict[str, bool]:
    payload = await request.body()
    if not stripe_signature:
        raise HTTPException(400, "缺少 Stripe-Signature。")
    try:
        event = parse_webhook(payload, stripe_signature)
    except Exception as exc:
        raise HTTPException(400, f"Webhook 验证失败：{exc}") from exc

    event_type = event.get("type")
    obj = event.get("data", {}).get("object", {})
    account_id = (obj.get("metadata") or {}).get("account_id") or obj.get("client_reference_id")
    if event_type == "checkout.session.completed" and account_id:
        account = _billing_account(account_id)
        subscription_id = obj.get("subscription")
        if subscription_id:
            account.active = True
            account.quota_used = 0
            account.period_end = datetime.now(timezone.utc) + timedelta(days=30)
            account.stripe_subscription_id = subscription_id
    elif event_type in {"customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"} and account_id:
        account = _billing_account(account_id)
        account.active = subscription_is_active(obj)
        end = period_end_from_subscription(obj)
        if end:
            account.period_end = end
        account.stripe_subscription_id = obj.get("id")
        if event_type == "customer.subscription.deleted":
            account.active = False
    elif event_type == "invoice.paid" and account_id:
        account = _billing_account(account_id)
        account.active = True
        subscription_id = obj.get("subscription")
        if subscription_id:
            account.stripe_subscription_id = subscription_id
    elif event_type == "invoice.payment_failed" and account_id:
        account = _billing_account(account_id)
        account.active = False
    return {"received": True}


@app.get("/accounts/{account_id}/quota")
def quota(account_id: str) -> dict:
    account = _account(account_id)
    return {"active": account.is_active_now(), "quota_total": account.quota_total, "quota_used": account.quota_used, "quota_remaining": account.quota_remaining, "period_end": account.period_end.isoformat() if account.period_end else None}


@app.post("/generate")
def generate(background_tasks: BackgroundTasks, account_id: str = Form(...), count: int = Form(...), mode: str = Form("portrait"), video: UploadFile = File(...)) -> dict:
    if not 1 <= count <= MAX_VIDEOS_PER_BATCH:
        raise HTTPException(400, f"单次最多生成 {MAX_VIDEOS_PER_BATCH} 个视频。")
    if mode not in {"portrait", "landscape"}:
        raise HTTPException(400, "输出模式不正确。")
    if not video.filename:
        raise HTTPException(400, "缺少视频文件。")
    account = _account(account_id)
    if not account.is_active_now():
        raise HTTPException(402, "订阅已失效，请续费后再生成。")
    if count > account.quota_remaining:
        raise HTTPException(400, f"额度不足，剩余 {account.quota_remaining} 个。")

    job_id = uuid4().hex
    suffix = Path(video.filename).suffix.lower()
    if suffix not in {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}:
        raise HTTPException(400, "暂不支持该视频格式。")
    source = UPLOADS / f"{job_id}{suffix}"
    with source.open("wb") as target:
        shutil.copyfileobj(video.file, target)
    try:
        duration = probe_duration(source)
        validate_duration(duration)
    except Exception as exc:
        source.unlink(missing_ok=True)
        raise HTTPException(400, f"视频校验失败：{exc}") from exc

    with lock:
        try:
            account.reserve_generation(count)
        except PermissionError as exc:
            source.unlink(missing_ok=True)
            raise HTTPException(402, str(exc)) from exc
        except ValueError as exc:
            source.unlink(missing_ok=True)
            raise HTTPException(400, str(exc)) from exc
        jobs[job_id] = {"job_id": job_id, "account_id": account_id, "status": "waiting", "count": count, "mode": mode, "created_at": datetime.now(timezone.utc).isoformat(), "outputs": []}
    background_tasks.add_task(_run_job, job_id, account_id, source, count, mode)
    return {"job_id": job_id, "status": "waiting", "reserved": count, "quota_remaining": account.quota_remaining}


@app.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(404, "任务不存在。")
    return job


@app.get("/jobs/{job_id}/files/{filename}")
def download_output(job_id: str, filename: str):
    path = (OUTPUTS / job_id / filename).resolve()
    root = (OUTPUTS / job_id).resolve()
    if root not in path.parents or not path.is_file():
        raise HTTPException(404, "文件不存在。")
    return FileResponse(path, media_type="video/mp4", filename=path.name)
