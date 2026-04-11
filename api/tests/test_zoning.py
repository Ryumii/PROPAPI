"""Tests for GET /v1/zoning — requires auth."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_zoning_no_auth_returns_401() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/v1/zoning", params={"address": "東京都渋谷区渋谷2-24-12"})
    assert resp.status_code == 401
