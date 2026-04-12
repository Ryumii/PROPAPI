"""PropAPI client — sync and async."""

from __future__ import annotations

from typing import Any

import httpx

from propapi.exceptions import AuthenticationError, PropAPIError, RateLimitError
from propapi.models import (
    HazardResponse,
    InspectResponse,
    ZoningResponse,
    parse_hazard_response,
    parse_inspect_response,
    parse_zoning_response,
)

_DEFAULT_BASE = "https://api.propapi.jp"
_DEFAULT_TIMEOUT = 30.0


def _raise_for_error(resp: httpx.Response) -> None:
    if resp.status_code < 400:
        return
    try:
        body = resp.json()
        err = body.get("error", body)
        code = err.get("code", "unknown")
        message = err.get("message", resp.text)
    except Exception:
        code, message = "unknown", resp.text

    if resp.status_code in (401, 403):
        raise AuthenticationError(resp.status_code, code, message)
    if resp.status_code == 429:
        retry = resp.headers.get("Retry-After")
        raise RateLimitError(
            resp.status_code, code, message, retry_after=int(retry) if retry else None
        )
    raise PropAPIError(resp.status_code, code, message)


class PropAPI:
    """Synchronous PropAPI client.

    Usage::

        from propapi import PropAPI

        client = PropAPI(api_key="cs_live_...")
        result = client.inspect(address="東京都渋谷区渋谷2-24-12")
        print(result.hazard.flood.risk_level)
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = _DEFAULT_BASE,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url,
            headers={"X-API-Key": api_key, "User-Agent": "propapi-python/0.1.0"},
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "PropAPI":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    # ── endpoints ────────────────────────────────────────

    def inspect(
        self,
        *,
        address: str | None = None,
        lat: float | None = None,
        lng: float | None = None,
        include_hazard: bool = True,
        include_zoning: bool = True,
    ) -> InspectResponse:
        """POST /v1/land/inspect — full land inspection."""
        body: dict[str, Any] = {
            "options": {"include_hazard": include_hazard, "include_zoning": include_zoning},
        }
        if address is not None:
            body["address"] = address
        if lat is not None and lng is not None:
            body["lat"] = lat
            body["lng"] = lng
        resp = self._client.post("/v1/land/inspect", json=body)
        _raise_for_error(resp)
        return parse_inspect_response(resp.json())

    def hazard(
        self,
        *,
        lat: float,
        lng: float,
        types: str | None = None,
    ) -> HazardResponse:
        """GET /v1/hazard — hazard-only query."""
        params: dict[str, Any] = {"lat": lat, "lng": lng}
        if types is not None:
            params["types"] = types
        resp = self._client.get("/v1/hazard", params=params)
        _raise_for_error(resp)
        return parse_hazard_response(resp.json())

    def zoning(self, *, lat: float, lng: float) -> ZoningResponse:
        """GET /v1/zoning — zoning-only query."""
        resp = self._client.get("/v1/zoning", params={"lat": lat, "lng": lng})
        _raise_for_error(resp)
        return parse_zoning_response(resp.json())

    def health(self) -> dict[str, str]:
        """GET /v1/health."""
        resp = self._client.get("/v1/health")
        _raise_for_error(resp)
        return resp.json()


class AsyncPropAPI:
    """Asynchronous PropAPI client.

    Usage::

        import asyncio
        from propapi import AsyncPropAPI

        async def main():
            async with AsyncPropAPI(api_key="cs_live_...") as client:
                result = await client.inspect(address="東京都千代田区丸の内一丁目")
                print(result.hazard.composite_score.level)

        asyncio.run(main())
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = _DEFAULT_BASE,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"X-API-Key": api_key, "User-Agent": "propapi-python/0.1.0"},
            timeout=timeout,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncPropAPI":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.aclose()

    async def inspect(
        self,
        *,
        address: str | None = None,
        lat: float | None = None,
        lng: float | None = None,
        include_hazard: bool = True,
        include_zoning: bool = True,
    ) -> InspectResponse:
        body: dict[str, Any] = {
            "options": {"include_hazard": include_hazard, "include_zoning": include_zoning},
        }
        if address is not None:
            body["address"] = address
        if lat is not None and lng is not None:
            body["lat"] = lat
            body["lng"] = lng
        resp = await self._client.post("/v1/land/inspect", json=body)
        _raise_for_error(resp)
        return parse_inspect_response(resp.json())

    async def hazard(
        self,
        *,
        lat: float,
        lng: float,
        types: str | None = None,
    ) -> HazardResponse:
        params: dict[str, Any] = {"lat": lat, "lng": lng}
        if types is not None:
            params["types"] = types
        resp = await self._client.get("/v1/hazard", params=params)
        _raise_for_error(resp)
        return parse_hazard_response(resp.json())

    async def zoning(self, *, lat: float, lng: float) -> ZoningResponse:
        resp = await self._client.get("/v1/zoning", params={"lat": lat, "lng": lng})
        _raise_for_error(resp)
        return parse_zoning_response(resp.json())

    async def health(self) -> dict[str, str]:
        resp = await self._client.get("/v1/health")
        _raise_for_error(resp)
        return resp.json()
