"""Tests for CacheService — graceful degradation & basic ops."""


import pytest

from app.services.cache import CacheService, _build_key


class TestBuildKey:
    def test_key_format(self) -> None:
        key = _build_key("inspect", "東京都渋谷区渋谷二丁目24番12号")
        assert key.startswith("reapi:inspect:")
        assert len(key.split(":")) == 3

    def test_deterministic(self) -> None:
        a = _build_key("geocode", "test")
        b = _build_key("geocode", "test")
        assert a == b

    def test_different_input_different_key(self) -> None:
        a = _build_key("inspect", "addr1")
        b = _build_key("inspect", "addr2")
        assert a != b


class TestCacheServiceGracefulDegradation:
    """Verify the service doesn't crash when Redis is unavailable."""

    @pytest.fixture
    def cache(self) -> CacheService:
        # Point to an unreachable Redis to test degradation
        return CacheService(redis_url="redis://localhost:19999/0")

    @pytest.mark.asyncio
    async def test_get_inspect_returns_none(self, cache: CacheService) -> None:
        result = await cache.get_inspect("test-addr")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_inspect_does_not_raise(self, cache: CacheService) -> None:
        await cache.set_inspect("test-addr", {"status": "ok"})

    @pytest.mark.asyncio
    async def test_get_geocode_returns_none(self, cache: CacheService) -> None:
        result = await cache.get_geocode("test-addr")
        assert result is None

    @pytest.mark.asyncio
    async def test_ping_returns_false(self, cache: CacheService) -> None:
        assert await cache.ping() is False

    @pytest.mark.asyncio
    async def test_invalidate_does_not_raise(self, cache: CacheService) -> None:
        await cache.invalidate_inspect("test")
        await cache.invalidate_geocode("test")
