"""Tests for rate limiter — graceful degradation."""

import pytest

from app.services.rate_limiter import RateLimiter, RateLimitResult


class TestRateLimitResult:
    def test_allowed_headers(self) -> None:
        r = RateLimitResult(
            allowed=True,
            remaining_second=9,
            remaining_month=999,
            monthly_limit=1000,
            rate_per_sec=10,
        )
        h = r.headers
        assert h["X-RateLimit-Limit-Second"] == "10"
        assert h["X-RateLimit-Remaining-Second"] == "9"
        assert h["X-RateLimit-Limit-Month"] == "1000"
        assert h["X-RateLimit-Remaining-Month"] == "999"
        assert "Retry-After" not in h

    def test_denied_headers_include_retry_after(self) -> None:
        r = RateLimitResult(
            allowed=False,
            remaining_second=0,
            remaining_month=999,
            monthly_limit=1000,
            rate_per_sec=10,
            retry_after=1,
        )
        assert r.headers["Retry-After"] == "1"


class TestRateLimiterDegradation:
    """With no Redis available the limiter should allow requests."""

    @pytest.fixture
    def limiter(self) -> RateLimiter:
        return RateLimiter(redis_url="redis://localhost:19999/0")

    @pytest.mark.asyncio
    async def test_allows_on_redis_failure(self, limiter: RateLimiter) -> None:
        result = await limiter.check("cs_live_test", rate_per_sec=10, monthly_limit=1000)
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_monthly_usage_zero_on_failure(self, limiter: RateLimiter) -> None:
        usage = await limiter.get_monthly_usage("cs_live_test")
        assert usage == 0
