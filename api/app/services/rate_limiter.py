"""Sliding-window rate limiter backed by Redis.

Uses two counters per API key:
  - Per-second  : reapi:rate:{prefix}:{epoch_sec}     TTL 2 s
  - Per-month   : reapi:rate:{prefix}:{YYYYMM}        TTL 35 d
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)


class RateLimitResult:
    __slots__ = ("allowed", "remaining_second", "remaining_month", "monthly_limit", "rate_per_sec", "retry_after", "degraded")

    def __init__(
        self,
        *,
        allowed: bool,
        remaining_second: int = 0,
        remaining_month: int = 0,
        monthly_limit: int = 0,
        rate_per_sec: int = 0,
        retry_after: int | None = None,
        degraded: bool = False,
    ) -> None:
        self.allowed = allowed
        self.remaining_second = remaining_second
        self.remaining_month = remaining_month
        self.monthly_limit = monthly_limit
        self.rate_per_sec = rate_per_sec
        self.retry_after = retry_after
        self.degraded = degraded

    @property
    def headers(self) -> dict[str, str]:
        h: dict[str, str] = {
            "X-RateLimit-Limit-Second": str(self.rate_per_sec),
            "X-RateLimit-Remaining-Second": str(max(0, self.remaining_second)),
            "X-RateLimit-Limit-Month": str(self.monthly_limit),
            "X-RateLimit-Remaining-Month": str(max(0, self.remaining_month)),
        }
        if self.retry_after is not None:
            h["Retry-After"] = str(self.retry_after)
        return h


class RateLimiter:
    def __init__(self, redis_url: str | None = None) -> None:
        url = redis_url or settings.redis_url
        self._redis: aioredis.Redis = aioredis.from_url(
            url, decode_responses=True, socket_connect_timeout=2
        )

    async def check(
        self,
        key_prefix: str,
        rate_per_sec: int,
        monthly_limit: int,
    ) -> RateLimitResult:
        """Increment counters and return whether the request is allowed."""
        now = time.time()
        sec_key = f"reapi:rate:{key_prefix}:{int(now)}"
        month_key = f"reapi:rate:{key_prefix}:{datetime.now(UTC).strftime('%Y%m')}"

        try:
            pipe = self._redis.pipeline(transaction=True)
            pipe.incr(sec_key)
            pipe.expire(sec_key, 2)
            pipe.incr(month_key)
            pipe.expire(month_key, 60 * 60 * 24 * 35)
            results = await pipe.execute()

            sec_count: int = results[0]
            month_count: int = results[2]
        except Exception:
            # Redis down → allow but mark as degraded (caller decides policy)
            logger.warning("Rate limiter Redis error — degraded mode", exc_info=True)
            return RateLimitResult(
                allowed=True,
                remaining_second=rate_per_sec,
                remaining_month=monthly_limit,
                monthly_limit=monthly_limit,
                rate_per_sec=rate_per_sec,
                degraded=True,
            )

        if sec_count > rate_per_sec:
            return RateLimitResult(
                allowed=False,
                remaining_second=0,
                remaining_month=monthly_limit - month_count,
                monthly_limit=monthly_limit,
                rate_per_sec=rate_per_sec,
                retry_after=1,
            )

        if month_count > monthly_limit:
            return RateLimitResult(
                allowed=False,
                remaining_second=rate_per_sec - sec_count,
                remaining_month=0,
                monthly_limit=monthly_limit,
                rate_per_sec=rate_per_sec,
            )

        return RateLimitResult(
            allowed=True,
            remaining_second=rate_per_sec - sec_count,
            remaining_month=monthly_limit - month_count,
            monthly_limit=monthly_limit,
            rate_per_sec=rate_per_sec,
        )

    async def get_monthly_usage(self, key_prefix: str) -> int:
        month_key = f"reapi:rate:{key_prefix}:{datetime.now(UTC).strftime('%Y%m')}"
        try:
            val = await self._redis.get(month_key)
            return int(val) if val else 0
        except Exception:
            return 0

    async def close(self) -> None:
        await self._redis.aclose()


_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    global _limiter  # noqa: PLW0603
    if _limiter is None:
        _limiter = RateLimiter()
    return _limiter
