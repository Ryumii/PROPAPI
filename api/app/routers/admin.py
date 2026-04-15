"""Admin router — user management, system stats, operational overview."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy import case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.auth import ApiKey, UserAccount
from app.models.usage import UsageLog

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/admin", tags=["admin"])

JWT_ALGORITHM = "HS256"


# ---------- Admin auth dependency -----------------------------------------


def _admin_emails() -> set[str]:
    if not settings.admin_emails:
        return set()
    return {e.strip().lower() for e in settings.admin_emails.split(",") if e.strip()}


async def require_admin(
    db: AsyncSession = Depends(get_db),
    authorization: str = Header(..., alias="Authorization"),
) -> UserAccount:
    """JWT auth + admin email whitelist check."""
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

    allowed = _admin_emails()
    if not allowed or user.email.lower() not in allowed:
        raise HTTPException(status_code=403, detail="管理者権限がありません")

    return user


# ---------- Schemas -------------------------------------------------------


class AdminUserItem(BaseModel):
    id: int
    email: str
    plan: str
    company_name: str | None
    stripe_customer_id: str | None
    stripe_subscription_id: str | None
    api_key_count: int
    month_usage: int
    created_at: str
    updated_at: str


class UserListResponse(BaseModel):
    users: list[AdminUserItem]
    total: int


class SystemStatsResponse(BaseModel):
    total_users: int
    plan_breakdown: dict[str, int]
    total_api_keys: int
    active_api_keys: int
    total_requests_today: int
    total_requests_month: int
    avg_response_ms: float | None


class AdminUserDetail(BaseModel):
    user: AdminUserItem
    keys: list[AdminKeyInfo]
    recent_usage: list[RecentUsageItem]


class AdminKeyInfo(BaseModel):
    id: int
    key_prefix: str
    plan: str
    monthly_limit: int
    rate_per_sec: int
    is_active: bool
    created_at: str


class RecentUsageItem(BaseModel):
    endpoint: str
    request_address: str | None
    response_status: int
    processing_time_ms: int | None
    created_at: str


class UpdateUserRequest(BaseModel):
    plan: str | None = None
    company_name: str | None = None


# ---------- Endpoints -----------------------------------------------------


@router.get("/stats", response_model=SystemStatsResponse)
async def system_stats(
    _admin: UserAccount = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> SystemStatsResponse:
    """Platform-wide statistics."""
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # User counts
    total_users = (await db.execute(select(func.count(UserAccount.id)))).scalar_one() or 0

    # Plan breakdown
    plan_rows = (
        await db.execute(
            select(UserAccount.plan, func.count(UserAccount.id))
            .group_by(UserAccount.plan)
        )
    ).all()
    plan_breakdown = {row[0]: row[1] for row in plan_rows}

    # API key counts
    total_keys = (await db.execute(select(func.count(ApiKey.id)))).scalar_one() or 0
    active_keys = (
        await db.execute(select(func.count(ApiKey.id)).where(ApiKey.is_active.is_(True)))
    ).scalar_one() or 0

    # Today's requests
    today_reqs = (
        await db.execute(
            select(func.count(UsageLog.id)).where(UsageLog.created_at >= today_start)
        )
    ).scalar_one() or 0

    # Month requests
    month_reqs = (
        await db.execute(
            select(func.count(UsageLog.id)).where(UsageLog.created_at >= month_start)
        )
    ).scalar_one() or 0

    # Avg response time (today)
    avg_ms = (
        await db.execute(
            select(func.avg(UsageLog.processing_time_ms)).where(
                UsageLog.created_at >= today_start,
                UsageLog.processing_time_ms.isnot(None),
            )
        )
    ).scalar_one()

    return SystemStatsResponse(
        total_users=total_users,
        plan_breakdown=plan_breakdown,
        total_api_keys=total_keys,
        active_api_keys=active_keys,
        total_requests_today=today_reqs,
        total_requests_month=month_reqs,
        avg_response_ms=round(avg_ms, 1) if avg_ms else None,
    )


@router.get("/users", response_model=UserListResponse)
async def list_users(
    page: int = 1,
    per_page: int = 50,
    plan: str | None = None,
    search: str | None = None,
    _admin: UserAccount = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserListResponse:
    """List all users with usage stats."""
    now = datetime.now(UTC)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Base query
    base = select(UserAccount)
    count_base = select(func.count(UserAccount.id))

    if plan:
        base = base.where(UserAccount.plan == plan)
        count_base = count_base.where(UserAccount.plan == plan)
    if search:
        like = f"%{search}%"
        base = base.where(
            UserAccount.email.ilike(like) | UserAccount.company_name.ilike(like)
        )
        count_base = count_base.where(
            UserAccount.email.ilike(like) | UserAccount.company_name.ilike(like)
        )

    total = (await db.execute(count_base)).scalar_one() or 0

    offset = (max(page, 1) - 1) * per_page
    users = (
        await db.execute(
            base.order_by(UserAccount.created_at.desc())
            .offset(offset)
            .limit(min(per_page, 100))
        )
    ).scalars().all()

    # Monthly usage per user (subquery via api_key)
    items: list[AdminUserItem] = []
    for u in users:
        key_ids = [k.id for k in u.api_keys]
        month_usage = 0
        if key_ids:
            month_usage = (
                await db.execute(
                    select(func.count(UsageLog.id)).where(
                        UsageLog.api_key_id.in_(key_ids),
                        UsageLog.created_at >= month_start,
                    )
                )
            ).scalar_one() or 0

        items.append(
            AdminUserItem(
                id=u.id,
                email=u.email,
                plan=u.plan,
                company_name=u.company_name,
                stripe_customer_id=u.stripe_customer_id,
                stripe_subscription_id=u.stripe_subscription_id,
                api_key_count=len(u.api_keys),
                month_usage=month_usage,
                created_at=u.created_at.isoformat(),
                updated_at=u.updated_at.isoformat(),
            )
        )

    return UserListResponse(users=items, total=total)


@router.get("/users/{user_id}", response_model=AdminUserDetail)
async def get_user_detail(
    user_id: int,
    _admin: UserAccount = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminUserDetail:
    """Detailed view of a single user."""
    now = datetime.now(UTC)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    stmt = select(UserAccount).where(UserAccount.id == user_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

    key_ids = [k.id for k in user.api_keys]
    month_usage = 0
    if key_ids:
        month_usage = (
            await db.execute(
                select(func.count(UsageLog.id)).where(
                    UsageLog.api_key_id.in_(key_ids),
                    UsageLog.created_at >= month_start,
                )
            )
        ).scalar_one() or 0

    # Recent usage logs (last 50)
    recent: list[RecentUsageItem] = []
    if key_ids:
        rows = (
            await db.execute(
                select(UsageLog)
                .where(UsageLog.api_key_id.in_(key_ids))
                .order_by(UsageLog.created_at.desc())
                .limit(50)
            )
        ).scalars().all()
        recent = [
            RecentUsageItem(
                endpoint=r.endpoint,
                request_address=r.request_address,
                response_status=r.response_status,
                processing_time_ms=r.processing_time_ms,
                created_at=r.created_at.isoformat(),
            )
            for r in rows
        ]

    return AdminUserDetail(
        user=AdminUserItem(
            id=user.id,
            email=user.email,
            plan=user.plan,
            company_name=user.company_name,
            stripe_customer_id=user.stripe_customer_id,
            stripe_subscription_id=user.stripe_subscription_id,
            api_key_count=len(user.api_keys),
            month_usage=month_usage,
            created_at=user.created_at.isoformat(),
            updated_at=user.updated_at.isoformat(),
        ),
        keys=[
            AdminKeyInfo(
                id=k.id,
                key_prefix=k.key_prefix,
                plan=k.plan,
                monthly_limit=k.monthly_limit,
                rate_per_sec=k.rate_per_sec,
                is_active=k.is_active,
                created_at=k.created_at.isoformat(),
            )
            for k in user.api_keys
        ],
        recent_usage=recent,
    )


@router.patch("/users/{user_id}")
async def update_user(
    user_id: int,
    body: UpdateUserRequest,
    _admin: UserAccount = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Update user plan or company name (admin override)."""
    stmt = select(UserAccount).where(UserAccount.id == user_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

    if body.plan is not None:
        from app.services.stripe_service import get_plan_config
        plan_cfg = get_plan_config(body.plan)
        user.plan = body.plan
        # Also update all active keys
        for k in user.api_keys:
            if k.is_active:
                k.plan = body.plan
                k.monthly_limit = plan_cfg.monthly_limit
                k.rate_per_sec = plan_cfg.rate_per_sec

    if body.company_name is not None:
        user.company_name = body.company_name

    await db.flush()
    return {"status": "updated"}


@router.post("/users/{user_id}/disable-keys")
async def disable_user_keys(
    user_id: int,
    _admin: UserAccount = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Disable all API keys for a user (emergency kill switch)."""
    result = await db.execute(
        update(ApiKey)
        .where(ApiKey.user_id == user_id, ApiKey.is_active.is_(True))
        .values(is_active=False)
    )
    count = result.rowcount
    await db.flush()
    return {"status": f"{count} keys disabled"}
