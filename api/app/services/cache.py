"""Redis cache service with graceful degradation.

Key schema:
  reapi:inspect:{sha256(addr+opts)}   – API response cache   (TTL 24 h)
  reapi:geocode:{sha256(addr)}        – geocoding results     (TTL 30 d)
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

# Default TTLs (seconds)
DEFAULT_INSPECT_TTL: int = 60 * 60 * 24       # 24 hours
DEFAULT_GEOCODE_TTL: int = 60 * 60 * 24 * 30  # 30 days


def _build_key(prefix: str, raw: str) -> str:
    digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"reapi:{prefix}:{digest}"


class CacheService:
    """Thin Redis wrapper.  All methods degrade gracefully on connection error."""

    def __init__(self, redis_url: str | None = None) -> None:
        url = redis_url or settings.redis_url
        self._redis: aioredis.Redis = aioredis.from_url(
            url, decode_responses=True, socket_connect_timeout=2
        )

    # ---------- low-level helpers -----------------------------------------

    async def _safe_get(self, key: str) -> str | None:
        try:
            return await self._redis.get(key)
        except Exception:
            logger.warning("Redis GET failed for %s – skipping cache", key, exc_info=True)
            return None

    async def _safe_set(self, key: str, value: str, ttl: int) -> None:
        try:
            await self._redis.set(key, value, ex=ttl)
        except Exception:
            logger.warning("Redis SET failed for %s – skipping cache", key, exc_info=True)

    async def _safe_delete(self, key: str) -> None:
        try:
            await self._redis.delete(key)
        except Exception:
            logger.warning("Redis DELETE failed for %s", key, exc_info=True)

    # ---------- inspect cache ---------------------------------------------

    def inspect_key(self, address_normalized: str, options_hash: str = "") -> str:
        return _build_key("inspect", address_normalized + options_hash)

    async def get_inspect(self, address_normalized: str, options_hash: str = "") -> dict[str, Any] | None:
        key = self.inspect_key(address_normalized, options_hash)
        raw = await self._safe_get(key)
        if raw is None:
            logger.debug("Cache MISS: %s", key)
            return None
        logger.debug("Cache HIT: %s", key)
        return json.loads(raw)

    async def set_inspect(
        self, address_normalized: str, data: dict[str, Any], options_hash: str = "", ttl: int = DEFAULT_INSPECT_TTL
    ) -> None:
        key = self.inspect_key(address_normalized, options_hash)
        await self._safe_set(key, json.dumps(data, ensure_ascii=False), ttl)

    # ---------- geocode cache ---------------------------------------------

    def geocode_key(self, address: str) -> str:
        return _build_key("geocode", address)

    async def get_geocode(self, address: str) -> dict[str, Any] | None:
        raw = await self._safe_get(self.geocode_key(address))
        if raw is None:
            return None
        return json.loads(raw)

    async def set_geocode(self, address: str, data: dict[str, Any], ttl: int = DEFAULT_GEOCODE_TTL) -> None:
        await self._safe_set(self.geocode_key(address), json.dumps(data, ensure_ascii=False), ttl)

    # ---------- admin / invalidation --------------------------------------

    async def invalidate_inspect(self, address_normalized: str, options_hash: str = "") -> None:
        await self._safe_delete(self.inspect_key(address_normalized, options_hash))

    async def invalidate_geocode(self, address: str) -> None:
        await self._safe_delete(self.geocode_key(address))

    async def ping(self) -> bool:
        try:
            return await self._redis.ping()
        except Exception:
            return False

    async def close(self) -> None:
        await self._redis.aclose()


# Module-level singleton (lazy)
_cache: CacheService | None = None


def get_cache() -> CacheService:
    global _cache  # noqa: PLW0603
    if _cache is None:
        _cache = CacheService()
    return _cache
