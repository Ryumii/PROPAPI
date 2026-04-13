"""Spatial query service — ST_Intersects lookups against PostGIS hazard/zoning tables.

Notes:
  - We use ST_Intersects(geom, point) instead of ST_Contains because:
    1. ST_Contains silently returns false for invalid geometries
    2. ST_Intersects is more tolerant of edge cases and invalid geoms
  - Invalid geometries are fixed at ETL insert time via ST_MakeValid
  - Existing data was repaired via UPDATE SET geom = ST_MakeValid(geom)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from geoalchemy2.functions import ST_Contains, ST_DWithin, ST_Intersects
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.hazard import HazardFlood, HazardLandslide, HazardTsunami
from app.models.land_price import LandPrice
from app.models.zoning import ZoningDistrict

logger = logging.getLogger(__name__)


def _point_wkt(lat: float, lng: float) -> str:
    return f"SRID=4326;POINT({lng} {lat})"


# ---------- individual query helpers ------------------------------------


@dataclass
class FloodResult:
    depth_rank: int = 0
    depth_range: str = ""
    return_period: int | None = None
    river_name: str | None = None
    source_name: str = "国土交通省 洪水浸水想定区域図"
    source_updated_at: str | None = None


@dataclass
class LandslideResult:
    zone_type: str | None = None
    source_name: str = "国土交通省 土砂災害警戒区域"
    source_updated_at: str | None = None


@dataclass
class TsunamiResult:
    depth_m: float | None = None
    source_name: str = "内閣府 津波浸水想定"
    source_updated_at: str | None = None


@dataclass
class LiquefactionMapInfo:
    """Liquefaction data is not available as structured polygons.

    Instead we provide a link to the J-SHIS hazard map for the queried location.
    """

    map_url: str = ""
    source_name: str = "J-SHIS 地震ハザードステーション（防災科学技術研究所）"


def build_liquefaction_map_url(lat: float, lng: float) -> str:
    """Build a J-SHIS map URL centred on the given coordinates."""
    return f"https://www.j-shis.bosai.go.jp/map/?lat={lat}&lon={lng}&zoom=14&transparent=1&layer=liquefaction"


@dataclass
class ZoningResult:
    use_district: str = ""
    use_code: str = ""
    coverage_pct: int | None = None
    floor_ratio_pct: int | None = None
    fire_prevention: str | None = None
    fire_code: str | None = None
    height_district: str | None = None
    scenic_district: str | None = None
    source_name: str = "国土数値情報 用途地域データ"
    source_updated_at: str | None = None


@dataclass
class LandPricePoint:
    """Single nearby land price point."""
    price_per_sqm: int = 0
    year: int = 0
    yoy_change_pct: float | None = None
    land_use: str | None = None
    address: str | None = None
    area_sqm: int | None = None
    structure: str | None = None
    nearest_station: str | None = None
    station_distance_m: int | None = None
    distance_m: int = 0
    lat: float = 0.0
    lng: float = 0.0


@dataclass
class LandPriceResult:
    nearest: LandPricePoint | None = None
    nearby: list[LandPricePoint] = field(default_factory=list)
    source_name: str = "国土数値情報 地価公示データ (L01)"
    source_updated_at: str | None = None


@dataclass
class SpatialQueryResult:
    flood: FloodResult | None = None
    landslide: LandslideResult | None = None
    tsunami: TsunamiResult | None = None
    liquefaction: LiquefactionMapInfo | None = None
    zoning: ZoningResult | None = None
    land_price: LandPriceResult | None = None


async def _query_flood(db: AsyncSession, point_wkt: str) -> FloodResult | None:
    stmt = (
        select(HazardFlood)
        .where(ST_Intersects(
            HazardFlood.geom,
            func.ST_GeomFromEWKT(point_wkt),
        ))
        .order_by(HazardFlood.depth_rank.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return FloodResult(
        depth_rank=row.depth_rank,
        depth_range=row.depth_range,
        return_period=row.return_period,
        river_name=row.river_name,
        source_name=row.source.name if row.source else "国土交通省 洪水浸水想定区域図",
        source_updated_at=row.source.last_updated_at if row.source else None,
    )


async def _query_landslide(db: AsyncSession, point_wkt: str) -> LandslideResult | None:
    stmt = (
        select(HazardLandslide)
        .where(ST_Intersects(
            HazardLandslide.geom,
            func.ST_GeomFromEWKT(point_wkt),
        ))
        .limit(1)
    )
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return LandslideResult(
        zone_type=row.zone_type,
        source_name=row.source.name if row.source else "国土交通省 土砂災害警戒区域",
        source_updated_at=row.source.last_updated_at if row.source else None,
    )


async def _query_tsunami(db: AsyncSession, point_wkt: str) -> TsunamiResult | None:
    stmt = (
        select(HazardTsunami)
        .where(ST_Intersects(
            HazardTsunami.geom,
            func.ST_GeomFromEWKT(point_wkt),
        ))
        .order_by(HazardTsunami.depth_m.desc().nulls_last())
        .limit(1)
    )
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return TsunamiResult(
        depth_m=float(row.depth_m) if row.depth_m is not None else None,
        source_name=row.source.name if row.source else "内閣府 津波浸水想定",
        source_updated_at=row.source.last_updated_at if row.source else None,
    )


def _build_liquefaction_info(lat: float, lng: float) -> LiquefactionMapInfo:
    """Build a map-link reference for liquefaction (no DB query)."""
    return LiquefactionMapInfo(map_url=build_liquefaction_map_url(lat, lng))


async def _query_zoning(db: AsyncSession, point_wkt: str) -> ZoningResult | None:
    stmt = (
        select(ZoningDistrict)
        .where(ST_Intersects(
            ZoningDistrict.geom,
            func.ST_GeomFromEWKT(point_wkt),
        ))
        .limit(1)
    )
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return ZoningResult(
        use_district=row.use_district,
        use_code=row.use_code.strip(),
        coverage_pct=row.coverage_pct,
        floor_ratio_pct=row.floor_ratio_pct,
        fire_prevention=row.fire_prevention,
        fire_code=row.fire_code.strip() if row.fire_code else None,
        height_district=row.height_district,
        scenic_district=row.scenic_district,
        source_name=row.source.name if row.source else "国土数値情報 用途地域データ",
        source_updated_at=row.source.last_updated_at if row.source else None,
    )


# ---------- land price (nearest neighbour KNN) --------------------------

# Search radius: 2 km
_LAND_PRICE_RADIUS_M = 2000
_LAND_PRICE_LIMIT = 5


async def _query_land_price(
    db: AsyncSession, lat: float, lng: float,
) -> LandPriceResult | None:
    """Find nearest land price points within 2 km using PostGIS geography distance."""
    point_geog = func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326)

    stmt = (
        select(
            LandPrice,
            func.ST_Distance(
                func.Geography(LandPrice.geom),
                func.Geography(point_geog),
            ).label("dist_m"),
            func.ST_Y(LandPrice.geom).label("pt_lat"),
            func.ST_X(LandPrice.geom).label("pt_lng"),
        )
        .where(
            ST_DWithin(
                func.Geography(LandPrice.geom),
                func.Geography(point_geog),
                _LAND_PRICE_RADIUS_M,
            )
        )
        .order_by("dist_m")
        .limit(_LAND_PRICE_LIMIT)
    )
    result = await db.execute(stmt)
    rows = result.all()
    if not rows:
        return None

    points = []
    for row_obj, dist_m, pt_lat, pt_lng in rows:
        points.append(LandPricePoint(
            price_per_sqm=row_obj.price_per_sqm,
            year=row_obj.year,
            yoy_change_pct=row_obj.yoy_change_pct,
            land_use=row_obj.land_use,
            address=row_obj.address,
            area_sqm=row_obj.area_sqm,
            structure=row_obj.structure,
            nearest_station=row_obj.nearest_station,
            station_distance_m=row_obj.station_distance_m,
            distance_m=int(dist_m) if dist_m else 0,
            lat=float(pt_lat),
            lng=float(pt_lng),
        ))

    source_name = "国土数値情報 地価公示データ (L01)"
    source_updated = None
    if rows[0][0].source:
        source_name = rows[0][0].source.name
        source_updated = rows[0][0].source.last_updated_at

    return LandPriceResult(
        nearest=points[0] if points else None,
        nearby=points,
        source_name=source_name,
        source_updated_at=source_updated,
    )


# ---------- public orchestrator -----------------------------------------


async def spatial_query(
    db: AsyncSession,
    lat: float,
    lng: float,
    *,
    include_hazard: bool = True,
    include_zoning: bool = True,
    include_land_price: bool = True,
) -> SpatialQueryResult:
    """Run parallel spatial queries against PostGIS tables."""
    point = _point_wkt(lat, lng)
    result = SpatialQueryResult()

    # Build task list based on options
    tasks: list[tuple[str, Any]] = []
    if include_hazard:
        tasks.append(("flood", _query_flood(db, point)))
        tasks.append(("landslide", _query_landslide(db, point)))
        tasks.append(("tsunami", _query_tsunami(db, point)))
        # Liquefaction: map link only (no DB query)
        result.liquefaction = _build_liquefaction_info(lat, lng)
    if include_zoning:
        tasks.append(("zoning", _query_zoning(db, point)))

    if not tasks:
        return result

    # Note: asyncio.gather with DB queries on the same session is sequential
    # in practice due to SQLAlchemy's session not being thread-safe.
    # For true parallelism, use separate sessions or raw connections.
    for name, coro in tasks:
        try:
            value = await coro
            setattr(result, name, value)
        except Exception:
            logger.warning("Spatial query failed for %s at (%s, %s)", name, lat, lng, exc_info=True)

    # Land price uses KNN (lat/lng directly, not point_wkt)
    if include_land_price:
        try:
            result.land_price = await _query_land_price(db, lat, lng)
        except Exception:
            logger.warning("Land price query failed at (%s, %s)", lat, lng, exc_info=True)

    return result
