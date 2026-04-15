"""Dashboard router — API key management, usage stats, profile."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import generate_api_key
from app.models.auth import ApiKey, UserAccount
from app.models.usage import UsageLog
from app.services.stripe_service import PLANS, get_plan_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/dashboard", tags=["dashboard"])

JWT_ALGORITHM = "HS256"


# ---------- JWT auth dependency -------------------------------------------


async def require_user(
    db: AsyncSession = Depends(get_db),  # noqa: B008
    authorization: str = Header(..., alias="Authorization"),  # noqa: B008
) -> UserAccount:
    """Extract and verify JWT from Authorization: Bearer <token>."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization ヘッダーが不正です")

    token = authorization[7:]
    try:
        payload = jwt.decode(token, settings.api_secret_key, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="トークンの有効期限が切れています")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="無効なトークンです")

    user_id = int(payload["sub"])
    stmt = select(UserAccount).where(UserAccount.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="ユーザーが見つかりません")
    return user


# ---------- Schemas -------------------------------------------------------


class ApiKeyInfo(BaseModel):
    id: int
    key_prefix: str
    plan: str
    monthly_limit: int
    rate_per_sec: int
    is_active: bool
    created_at: str


class CreateKeyResponse(BaseModel):
    api_key: str  # plain key, shown only once
    key_info: ApiKeyInfo


class OverviewResponse(BaseModel):
    user: UserSummary
    plan: PlanDetail
    usage: UsageSummary
    keys: list[ApiKeyInfo]


class UserSummary(BaseModel):
    id: int
    email: str
    plan: str
    company_name: str | None
    stripe_subscription_id: str | None


class PlanDetail(BaseModel):
    name: str
    monthly_limit: int
    rate_per_sec: int
    burst: int
    overage_price_yen: int


class UsageSummary(BaseModel):
    month_total: int
    monthly_limit: int
    percent_used: float


class DailyUsage(BaseModel):
    date: str
    count: int


class UsageChartResponse(BaseModel):
    daily: list[DailyUsage]
    total: int
    monthly_limit: int


# ---------- Endpoints -----------------------------------------------------


@router.get("/overview", response_model=OverviewResponse)
async def get_overview(
    user: UserAccount = Depends(require_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> OverviewResponse:
    """Dashboard overview: user info, plan, usage summary, API keys."""
    plan_cfg = get_plan_config(user.plan)

    # Get all API keys
    stmt = select(ApiKey).where(ApiKey.user_id == user.id).order_by(ApiKey.created_at.desc())
    result = await db.execute(stmt)
    keys = result.scalars().all()

    # Calculate monthly usage (sum across all keys)
    now = datetime.now(UTC)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    key_ids = [k.id for k in keys]

    month_total = 0
    if key_ids:
        usage_stmt = (
            select(func.count(UsageLog.id))
            .where(UsageLog.api_key_id.in_(key_ids), UsageLog.created_at >= month_start)
        )
        usage_result = await db.execute(usage_stmt)
        month_total = usage_result.scalar_one() or 0

    monthly_limit = plan_cfg.monthly_limit
    percent_used = (month_total / monthly_limit * 100) if monthly_limit > 0 else 0

    return OverviewResponse(
        user=UserSummary(
            id=user.id,
            email=user.email,
            plan=user.plan,
            company_name=user.company_name,
            stripe_subscription_id=user.stripe_subscription_id,
        ),
        plan=PlanDetail(
            name=plan_cfg.name,
            monthly_limit=plan_cfg.monthly_limit,
            rate_per_sec=plan_cfg.rate_per_sec,
            burst=plan_cfg.burst,
            overage_price_yen=plan_cfg.overage_price_yen,
        ),
        usage=UsageSummary(
            month_total=month_total,
            monthly_limit=monthly_limit,
            percent_used=round(percent_used, 1),
        ),
        keys=[
            ApiKeyInfo(
                id=k.id,
                key_prefix=k.key_prefix,
                plan=k.plan,
                monthly_limit=k.monthly_limit,
                rate_per_sec=k.rate_per_sec,
                is_active=k.is_active,
                created_at=k.created_at.isoformat(),
            )
            for k in keys
        ],
    )


@router.get("/keys", response_model=list[ApiKeyInfo])
async def list_keys(
    user: UserAccount = Depends(require_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[ApiKeyInfo]:
    """List all API keys for the authenticated user."""
    stmt = select(ApiKey).where(ApiKey.user_id == user.id).order_by(ApiKey.created_at.desc())
    result = await db.execute(stmt)
    keys = result.scalars().all()
    return [
        ApiKeyInfo(
            id=k.id,
            key_prefix=k.key_prefix,
            plan=k.plan,
            monthly_limit=k.monthly_limit,
            rate_per_sec=k.rate_per_sec,
            is_active=k.is_active,
            created_at=k.created_at.isoformat(),
        )
        for k in keys
    ]


@router.post("/keys", response_model=CreateKeyResponse, status_code=201)
async def create_key(
    user: UserAccount = Depends(require_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> CreateKeyResponse:
    """Create a new API key. The plain key is returned only once."""
    # Limit keys per user
    stmt = select(func.count(ApiKey.id)).where(ApiKey.user_id == user.id, ApiKey.is_active.is_(True))
    result = await db.execute(stmt)
    active_count = result.scalar_one() or 0
    if active_count >= 5:
        raise HTTPException(status_code=400, detail="API Key は最大5つまでです")

    plan_cfg = get_plan_config(user.plan)
    plain_key, key_prefix, key_hash = generate_api_key()
    api_key = ApiKey(
        user_id=user.id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        plan=user.plan,
        monthly_limit=plan_cfg.monthly_limit,
        rate_per_sec=plan_cfg.rate_per_sec,
    )
    db.add(api_key)
    await db.flush()

    return CreateKeyResponse(
        api_key=plain_key,
        key_info=ApiKeyInfo(
            id=api_key.id,
            key_prefix=key_prefix,
            plan=api_key.plan,
            monthly_limit=api_key.monthly_limit,
            rate_per_sec=api_key.rate_per_sec,
            is_active=True,
            created_at=api_key.created_at.isoformat(),
        ),
    )


@router.delete("/keys/{key_id}")
async def revoke_key(
    key_id: int,
    user: UserAccount = Depends(require_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, str]:
    """Revoke (deactivate) an API key."""
    stmt = select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user.id)
    result = await db.execute(stmt)
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="API Key が見つかりません")

    key.is_active = False
    await db.flush()
    return {"status": "revoked"}


@router.get("/usage", response_model=UsageChartResponse)
async def get_usage(
    days: int = 30,
    user: UserAccount = Depends(require_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> UsageChartResponse:
    """Daily usage data for the chart (last N days)."""
    if days < 1 or days > 90:
        days = 30

    # Get all key IDs for user
    key_stmt = select(ApiKey.id).where(ApiKey.user_id == user.id)
    key_result = await db.execute(key_stmt)
    key_ids = [row[0] for row in key_result.all()]

    plan_cfg = get_plan_config(user.plan)
    now = datetime.now(UTC)
    start_date = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)

    daily: list[DailyUsage] = []
    total = 0

    if key_ids:
        stmt = (
            select(
                func.date_trunc("day", UsageLog.created_at).label("day"),
                func.count(UsageLog.id).label("cnt"),
            )
            .where(
                UsageLog.api_key_id.in_(key_ids),
                UsageLog.created_at >= start_date,
            )
            .group_by("day")
            .order_by("day")
        )
        result = await db.execute(stmt)
        rows = result.all()

        for row in rows:
            d = row.day.strftime("%Y-%m-%d") if row.day else ""
            daily.append(DailyUsage(date=d, count=row.cnt))
            total += row.cnt

    return UsageChartResponse(
        daily=daily,
        total=total,
        monthly_limit=plan_cfg.monthly_limit,
    )
