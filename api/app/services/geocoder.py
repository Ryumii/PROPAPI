"""Geocoding service — address → (lat, lng, confidence).

Lookup chain:
  1. address_master exact match (confidence 0.95-1.0)
  2. address_master partial match at town level (confidence 0.60-0.80)
  3. External geocoder fallback — 国土地理院 API (confidence 0.40-0.60)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.address import AddressMaster
from app.services.cache import get_cache
from app.utils.address_normalizer import NormalizedAddress, normalize_address

logger = logging.getLogger(__name__)

_GSI_GEOCODE_URL = "https://msearch.gsi.go.jp/address-search/AddressSearch?q="


@dataclass
class GeocodingResult:
    lat: float
    lng: float
    confidence: float
    method: str  # "address_match" | "town_match" | "external_geocoder" | "coordinates"
    prefecture: str | None = None
    city: str | None = None
    town: str | None = None
    normalized_address: str | None = None


async def geocode(
    db: AsyncSession,
    *,
    address: str | None = None,
    lat: float | None = None,
    lng: float | None = None,
) -> GeocodingResult | None:
    """Resolve location.  Returns None if address can't be resolved and no coords given."""

    # If coordinates already supplied, use them directly
    if lat is not None and lng is not None and address is None:
        return GeocodingResult(
            lat=lat, lng=lng, confidence=1.0, method="coordinates"
        )

    if address is None:
        return None

    # Normalize address
    parsed: NormalizedAddress = normalize_address(address)
    norm = parsed.normalized or address

    # Check cache
    cache = get_cache()
    cached = await cache.get_geocode(norm)
    if cached is not None:
        return GeocodingResult(
            lat=cached["lat"],
            lng=cached["lng"],
            confidence=cached.get("confidence", 0.95),
            method="address_match",
            prefecture=cached.get("prefecture"),
            city=cached.get("city"),
            town=cached.get("town"),
            normalized_address=norm,
        )

    # 1. Exact match in address_master
    result = await _exact_match(db, parsed, norm)
    if result is not None:
        await _cache_result(cache, norm, result)
        return result

    # 2. Partial match (town level)
    result = await _town_match(db, parsed)
    if result is not None:
        result.normalized_address = norm
        await _cache_result(cache, norm, result)
        return result

    # 3. External geocoder fallback
    result = await _external_geocode(norm)
    if result is not None:
        result.normalized_address = norm
        await _cache_result(cache, norm, result)
        return result

    # 4. If lat/lng also supplied, use as last resort
    if lat is not None and lng is not None:
        return GeocodingResult(
            lat=lat, lng=lng, confidence=0.5, method="coordinates",
            normalized_address=norm,
            prefecture=parsed.prefecture or None,
            city=parsed.city or None,
            town=parsed.town or None,
        )

    return None


# ---------- internal lookup methods --------------------------------------


async def _exact_match(
    db: AsyncSession, parsed: NormalizedAddress, norm: str
) -> GeocodingResult | None:
    stmt = select(AddressMaster).where(AddressMaster.normalized_addr == norm).limit(1)
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None

    # Extract lat/lng from Point geometry
    lat, lng = await _extract_point(db, row)
    if lat is None:
        return None

    return GeocodingResult(
        lat=lat,
        lng=lng,
        confidence=0.97,
        method="address_match",
        prefecture=row.prefecture,
        city=row.city,
        town=row.town,
        normalized_address=norm,
    )


async def _town_match(
    db: AsyncSession, parsed: NormalizedAddress
) -> GeocodingResult | None:
    if not parsed.prefecture or not parsed.city or not parsed.town:
        return None

    # Match on prefecture + city + town prefix
    town_base = parsed.town.split("丁目")[0] if "丁目" in parsed.town else parsed.town
    stmt = (
        select(AddressMaster)
        .where(
            AddressMaster.prefecture == parsed.prefecture,
            AddressMaster.city == parsed.city,
            AddressMaster.town.startswith(town_base),
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None

    lat, lng = await _extract_point(db, row)
    if lat is None:
        return None

    return GeocodingResult(
        lat=lat,
        lng=lng,
        confidence=0.70,
        method="town_match",
        prefecture=row.prefecture,
        city=row.city,
        town=row.town,
    )


async def _extract_point(db: AsyncSession, row: AddressMaster) -> tuple[float | None, float | None]:
    """Extract lat/lng from a PostGIS Point geometry."""
    from geoalchemy2.functions import ST_X, ST_Y
    from sqlalchemy import select as sa_select

    stmt = sa_select(
        ST_Y(AddressMaster.geom).label("lat"),
        ST_X(AddressMaster.geom).label("lng"),
    ).where(AddressMaster.id == row.id)
    result = await db.execute(stmt)
    coords = result.one_or_none()
    if coords is None:
        return None, None
    return float(coords.lat), float(coords.lng)


async def _external_geocode(address: str) -> GeocodingResult | None:
    """Fallback to 国土地理院 geocoding API."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{_GSI_GEOCODE_URL}{address}")
            if resp.status_code != 200:
                return None
            data = resp.json()
            if not data:
                return None
            # GSI returns list of [{"geometry": {"coordinates": [lng, lat]}, ...}]
            first = data[0]
            coords = first.get("geometry", {}).get("coordinates", [])
            if len(coords) < 2:
                return None
            lng, lat = float(coords[0]), float(coords[1])
            return GeocodingResult(
                lat=lat,
                lng=lng,
                confidence=0.50,
                method="external_geocoder",
            )
    except Exception:
        logger.warning("External geocoder failed for %s", address, exc_info=True)
        return None


async def _cache_result(cache: object, norm: str, result: GeocodingResult) -> None:
    from app.services.cache import CacheService

    if isinstance(cache, CacheService):
        await cache.set_geocode(norm, {
            "lat": result.lat,
            "lng": result.lng,
            "confidence": result.confidence,
            "prefecture": result.prefecture,
            "city": result.city,
            "town": result.town,
        })
