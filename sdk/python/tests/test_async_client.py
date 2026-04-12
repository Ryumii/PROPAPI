"""Tests for PropAPI async client."""

import httpx
import pytest
import respx

from propapi import AsyncPropAPI

BASE = "https://api.propapi.jp"

INSPECT_RESPONSE = {
    "request_id": "req_async",
    "address_normalized": "東京都千代田区丸の内一丁目",
    "location": {"lat": 35.6816, "lng": 139.7672, "prefecture": "東京都", "city": "千代田区"},
    "hazard": {
        "flood": {"risk_level": "very_low", "risk_score": 0, "source": "s"},
        "landslide": {"risk_level": "none", "risk_score": 0, "source": "s"},
        "tsunami": {"risk_level": "none", "risk_score": 0, "source": "s"},
        "liquefaction": {"risk_level": "unavailable", "data_available": False, "source": "s", "note": ""},
        "composite_score": {"score": 0.4, "level": "very_low", "description": ""},
    },
    "zoning": {
        "use_district": "商業地域",
        "use_district_code": "09",
        "building_coverage_pct": 80,
        "floor_area_ratio_pct": 800,
        "source": "国土数値情報 用途地域データ",
    },
    "meta": {"confidence": 0.5, "geocoding_method": "address_match", "processing_time_ms": 143, "api_version": "1.0.0"},
}


@pytest.mark.asyncio
@respx.mock
async def test_async_inspect() -> None:
    respx.post(f"{BASE}/v1/land/inspect").mock(
        return_value=httpx.Response(200, json=INSPECT_RESPONSE)
    )
    async with AsyncPropAPI(api_key="k") as client:
        result = await client.inspect(address="東京都千代田区丸の内一丁目")

    assert result.request_id == "req_async"
    assert result.zoning.floor_area_ratio_pct == 800


@pytest.mark.asyncio
@respx.mock
async def test_async_hazard() -> None:
    respx.get(f"{BASE}/v1/hazard").mock(
        return_value=httpx.Response(200, json=INSPECT_RESPONSE["hazard"])
    )
    async with AsyncPropAPI(api_key="k") as client:
        h = await client.hazard(lat=35.68, lng=139.77)

    assert h.flood.risk_level == "very_low"


@pytest.mark.asyncio
@respx.mock
async def test_async_zoning() -> None:
    respx.get(f"{BASE}/v1/zoning").mock(
        return_value=httpx.Response(200, json=INSPECT_RESPONSE["zoning"])
    )
    async with AsyncPropAPI(api_key="k") as client:
        z = await client.zoning(lat=35.68, lng=139.77)

    assert z.use_district == "商業地域"
