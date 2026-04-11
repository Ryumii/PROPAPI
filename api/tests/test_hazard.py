"""Tests for GET /v1/hazard — requires auth, validates query params."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_hazard_no_auth_returns_401() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/v1/hazard", params={"address": "東京都渋谷区渋谷2-24-12"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_hazard_no_auth_no_params_returns_401() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/v1/hazard")
    assert resp.status_code == 401
