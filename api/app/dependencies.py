"""FastAPI dependency: API Key authentication + rate limiting."""

from __future__ import annotations

import hashlib
import logging
import secrets
from typing import Annotated

import bcrypt
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select

from app.database import AsyncSession, get_db
from app.models.auth import ApiKey
from app.services.rate_limiter import RateLimitResult, get_rate_limiter
from app.services.stripe_service import get_plan_config, report_meter_event

logger = logging.getLogger(__name__)

# ---------- key generation helpers ----------------------------------------


def generate_api_key(*, sandbox: bool = False) -> tuple[str, str, str]:
    """Return (plain_key, key_prefix, key_hash).

    Format: cs_live_<random32> or cs_test_<random32>
    key_prefix is the first 12 characters, matching _key_prefix() lookup.
    """
    prefix = "cs_test_" if sandbox else "cs_live_"
    random_part = secrets.token_urlsafe(32)
    plain_key = f"{prefix}{random_part}"
    key_hash = bcrypt.hashpw(plain_key.encode(), bcrypt.gensalt()).decode()
    return plain_key, _key_prefix(plain_key), key_hash


def verify_api_key(plain_key: str, key_hash: str) -> bool:
    return bcrypt.checkpw(plain_key.encode(), key_hash.encode())


def _key_prefix(plain_key: str) -> str:
    """Extract the first 12 characters (e.g. 'cs_live_xxxx')."""
    return plain_key[:12]


def _lookup_hash(plain_key: str) -> str:
    """SHA-256 of the full key for fast DB lookup."""
    return hashlib.sha256(plain_key.encode()).hexdigest()


# ---------- FastAPI dependencies ------------------------------------------


async def _resolve_api_key(
    request: Request,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> ApiKey:
    """Validate X-API-Key header and return the ApiKey row."""
    raw_key = request.headers.get("X-API-Key")
    if not raw_key:
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "API Key が必要です"})

    prefix = _key_prefix(raw_key)

    # Look up candidates by prefix for bcrypt verification
    stmt = select(ApiKey).where(ApiKey.key_prefix == prefix, ApiKey.is_active.is_(True))
    result = await db.execute(stmt)
    candidates = result.scalars().all()

    for candidate in candidates:
        if verify_api_key(raw_key, candidate.key_hash):
            return candidate

    raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "API Key が無効です"})


async def require_api_key(
    request: Request,
    api_key: ApiKey = Depends(_resolve_api_key),  # noqa: B008
) -> ApiKey:
    """Authenticate + enforce rate limits.  Injects rate-limit headers."""
    limiter = get_rate_limiter()

    try:
        plan_cfg = get_plan_config(api_key.plan)
    except ValueError:
        plan_cfg = None

    # Flex plan: no monthly limit, pure usage-based (meter every request)
    is_flex = plan_cfg is not None and plan_cfg.monthly_limit == 0

    if is_flex:
        # Only enforce per-second rate limit, skip monthly
        rl: RateLimitResult = await limiter.check(
            key_prefix=api_key.key_prefix,
            rate_per_sec=api_key.rate_per_sec,
            monthly_limit=999_999_999,  # effectively unlimited
        )
        request.state.rate_limit_headers = rl.headers

        if not rl.allowed:
            raise HTTPException(
                status_code=429,
                detail={"code": "RATE_LIMITED", "message": "レートリミットを超過しました"},
                headers=rl.headers,
            )

        # Report every request to Stripe meter (Flex always meters)
        if api_key.user and api_key.user.stripe_customer_id:
            report_meter_event(api_key.user.stripe_customer_id)

        return api_key

    # Light / Pro / Max: monthly limit + overage billing
    rl = await limiter.check(
        key_prefix=api_key.key_prefix,
        rate_per_sec=api_key.rate_per_sec,
        monthly_limit=api_key.monthly_limit,
    )

    request.state.rate_limit_headers = rl.headers

    # Redis degraded: paid plans fail-closed to prevent billing gaps
    if rl.degraded:
        logger.warning("Redis degraded — blocking paid plan request for key %s", api_key.key_prefix)
        raise HTTPException(
            status_code=503,
            detail={"code": "SERVICE_DEGRADED", "message": "レート制限サービスが一時的に利用できません。しばらくお待ちください。"},
        )

    if not rl.allowed:
        # Per-second rate limit always blocks
        if rl.remaining_month > 0:
            raise HTTPException(
                status_code=429,
                detail={"code": "RATE_LIMITED", "message": "レートリミットを超過しました"},
                headers=rl.headers,
            )

        # Monthly quota exceeded — allow through as overage
        if plan_cfg and plan_cfg.overage_price_yen > 0:
            rl.headers["X-Overage"] = "true"
            rl.headers["X-Overage-Price-Yen"] = str(plan_cfg.overage_price_yen)
            request.state.rate_limit_headers = rl.headers

            # Report overage to Stripe meter
            if api_key.user and api_key.user.stripe_customer_id:
                report_meter_event(api_key.user.stripe_customer_id)

            return api_key

        # No overage allowed: hard block
        raise HTTPException(
            status_code=429,
            detail={"code": "QUOTA_EXCEEDED", "message": "月間リクエスト上限を超過しました"},
            headers=rl.headers,
        )

    return api_key


# Annotated alias for route signatures
AuthenticatedKey = Annotated[ApiKey, Depends(require_api_key)]
