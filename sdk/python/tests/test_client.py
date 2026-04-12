"""Tests for PropAPI sync client."""

import httpx
import pytest
import respx

from propapi import PropAPI, AuthenticationError, PropAPIError, RateLimitError

BASE = "https://api.propapi.jp"

INSPECT_RESPONSE = {
    "request_id": "req_abc",
    "address_normalized": "東京都渋谷区渋谷二丁目24-12",
    "location": {"lat": 35.6595, "lng": 139.7004, "prefecture": "東京都", "city": "渋谷区", "town": "渋谷二丁目"},
    "hazard": {
        "flood": {"risk_level": "low", "risk_score": 1, "depth_m": 0.5, "depth_range": "0.0m〜0.5m", "return_period_years": 1000, "source": "srca"},
        "landslide": {"risk_level": "none", "risk_score": 0, "source": "srcb"},
        "tsunami": {"risk_level": "none", "risk_score": 0, "source": "srcc"},
        "liquefaction": {"risk_level": "unavailable", "data_available": False, "source": "srcd", "note": "N/A"},
        "composite_score": {"score": 0.4, "level": "very_low", "description": "総合的なリスクは非常に低いです"},
    },
    "zoning": {
        "use_district": "商業地域",
        "use_district_code": "09",
        "building_coverage_pct": 80,
        "floor_area_ratio_pct": 600,
        "fire_prevention": "防火地域",
        "fire_prevention_code": "01",
        "source": "国土数値情報 用途地域データ",
    },
    "meta": {
        "confidence": 0.97,
        "geocoding_method": "address_match",
        "processing_time_ms": 123,
        "api_version": "1.0.0",
    },
}


HAZARD_RESPONSE = INSPECT_RESPONSE["hazard"]

ZONING_RESPONSE = INSPECT_RESPONSE["zoning"]


@respx.mock
def test_inspect_by_address() -> None:
    respx.post(f"{BASE}/v1/land/inspect").mock(
        return_value=httpx.Response(200, json=INSPECT_RESPONSE)
    )
    with PropAPI(api_key="test_key") as client:
        result = client.inspect(address="東京都渋谷区渋谷2-24-12")

    assert result.request_id == "req_abc"
    assert result.address_normalized == "東京都渋谷区渋谷二丁目24-12"
    assert result.location.lat == 35.6595
    assert result.location.prefecture == "東京都"
    assert result.hazard is not None
    assert result.hazard.flood.risk_score == 1
    assert result.hazard.composite_score.level == "very_low"
    assert result.zoning is not None
    assert result.zoning.use_district == "商業地域"
    assert result.zoning.building_coverage_pct == 80
    assert result.meta.processing_time_ms == 123


@respx.mock
def test_inspect_by_coords() -> None:
    respx.post(f"{BASE}/v1/land/inspect").mock(
        return_value=httpx.Response(200, json=INSPECT_RESPONSE)
    )
    with PropAPI(api_key="k") as client:
        result = client.inspect(lat=35.6595, lng=139.7004)

    assert result.location.lng == 139.7004


@respx.mock
def test_hazard() -> None:
    respx.get(f"{BASE}/v1/hazard").mock(
        return_value=httpx.Response(200, json=HAZARD_RESPONSE)
    )
    with PropAPI(api_key="k") as client:
        h = client.hazard(lat=35.6595, lng=139.7004)

    assert h.flood.risk_level == "low"
    assert h.tsunami.risk_score == 0
    assert h.liquefaction.data_available is False


@respx.mock
def test_zoning() -> None:
    respx.get(f"{BASE}/v1/zoning").mock(
        return_value=httpx.Response(200, json=ZONING_RESPONSE)
    )
    with PropAPI(api_key="k") as client:
        z = client.zoning(lat=35.6595, lng=139.7004)

    assert z.use_district == "商業地域"
    assert z.floor_area_ratio_pct == 600


@respx.mock
def test_health() -> None:
    respx.get(f"{BASE}/v1/health").mock(
        return_value=httpx.Response(200, json={"status": "healthy"})
    )
    with PropAPI(api_key="k") as client:
        h = client.health()

    assert h["status"] == "healthy"


@respx.mock
def test_auth_error() -> None:
    respx.post(f"{BASE}/v1/land/inspect").mock(
        return_value=httpx.Response(401, json={"error": {"code": "invalid_api_key", "message": "Invalid API key"}})
    )
    with PropAPI(api_key="bad") as client:
        with pytest.raises(AuthenticationError) as exc:
            client.inspect(address="test")
    assert exc.value.status_code == 401


@respx.mock
def test_rate_limit_error() -> None:
    respx.post(f"{BASE}/v1/land/inspect").mock(
        return_value=httpx.Response(
            429,
            json={"error": {"code": "rate_limit", "message": "Too many requests"}},
            headers={"Retry-After": "30"},
        )
    )
    with PropAPI(api_key="k") as client:
        with pytest.raises(RateLimitError) as exc:
            client.inspect(address="test")
    assert exc.value.retry_after == 30


@respx.mock
def test_server_error() -> None:
    respx.post(f"{BASE}/v1/land/inspect").mock(
        return_value=httpx.Response(500, json={"error": {"code": "internal", "message": "oops"}})
    )
    with PropAPI(api_key="k") as client:
        with pytest.raises(PropAPIError) as exc:
            client.inspect(address="test")
    assert exc.value.status_code == 500


@respx.mock
def test_api_key_header() -> None:
    route = respx.get(f"{BASE}/v1/health").mock(
        return_value=httpx.Response(200, json={"status": "healthy"})
    )
    with PropAPI(api_key="my_secret_key") as client:
        client.health()

    assert route.calls[0].request.headers["X-API-Key"] == "my_secret_key"
