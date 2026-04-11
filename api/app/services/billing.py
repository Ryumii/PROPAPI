"""Usage tracking / billing service.

Responsibilities:
  - Record every API request to usage_log (async, non-blocking)
  - Aggregate monthly usage per API key
  - Trigger 80% quota alert
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usage import UsageLog

logger = logging.getLogger(__name__)

QUOTA_ALERT_THRESHOLD = 0.80


async def record_usage(
    db: AsyncSession,
    *,
    api_key_id: int,
    endpoint: str,
    request_address: str | None = None,
    response_status: int,
    processing_time_ms: int | None = None,
) -> None:
    """Insert a usage log entry.  Designed to be called in a background task."""
    try:
        log = UsageLog(
            api_key_id=api_key_id,
            endpoint=endpoint,
            request_address=request_address,
            response_status=response_status,
            processing_time_ms=processing_time_ms,
        )
        db.add(log)
        await db.commit()
    except Exception:
        logger.warning("Failed to record usage log", exc_info=True)
        await db.rollback()


async def get_monthly_usage(db: AsyncSession, api_key_id: int) -> int:
    """Return total request count for the current month."""
    now = datetime.now(UTC)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    stmt = (
        select(func.count(UsageLog.id))
        .where(
            UsageLog.api_key_id == api_key_id,
            UsageLog.created_at >= month_start,
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one() or 0


async def check_quota_alert(
    db: AsyncSession,
    api_key_id: int,
    monthly_limit: int,
) -> bool:
    """Return True if usage >= 80% of monthly limit."""
    usage = await get_monthly_usage(db, api_key_id)
    threshold = monthly_limit * QUOTA_ALERT_THRESHOLD
    if usage >= threshold:
        logger.info(
            "Quota alert: api_key_id=%d usage=%d threshold=%.0f limit=%d",
            api_key_id, usage, threshold, monthly_limit,
        )
        return True
    return False
