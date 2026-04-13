"""GET /v1/hazard — lightweight hazard-only endpoint."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from geoalchemy2.functions import ST_Intersects, ST_MakeEnvelope
from sqlalchemy import func, select

from app.database import AsyncSession, get_db
from app.dependencies import AuthenticatedKey
from app.models.hazard import HazardFlood, HazardLandslide, HazardTsunami
from app.schemas.errors import MISSING_LOCATION, ErrorResponse
from app.schemas.hazard import (
    CompositeScore,
    FloodDetail,
    HazardResponse,
    LandslideDetail,
    LiquefactionDetail,
    TsunamiDetail,
)
from app.services.geocoder import geocode
from app.services.scoring import _level_for_score, calculate_scores
from app.services.spatial import spatial_query

router = APIRouter()


@router.get(
    "/v1/hazard",
    response_model=HazardResponse,
    responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}},
    summary="ハザード情報取得",
    description="住所または緯度経度からハザードリスク情報のみを取得",
)
async def get_hazard(
    api_key: AuthenticatedKey,
    address: str | None = Query(None, description="住所"),
    lat: float | None = Query(None, ge=20.0, le=46.0, description="緯度"),
    lng: float | None = Query(None, ge=122.0, le=154.0, description="経度"),
    types: str | None = Query(None, description="カンマ区切りで絞り込み: flood,landslide,tsunami,liquefaction"),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> HazardResponse:
    geo = await geocode(db, address=address, lat=lat, lng=lng)
    if geo is None:
        raise HTTPException(status_code=400, detail=MISSING_LOCATION.model_dump())

    sq = await spatial_query(db, geo.lat, geo.lng, include_hazard=True, include_zoning=False)
    scores = calculate_scores(sq)

    return HazardResponse(
        flood=FloodDetail(
            risk_level=_level_for_score(scores.flood_score),
            risk_score=scores.flood_score,
            depth_m=sq.flood.depth_rank if sq.flood else None,
            depth_range=sq.flood.depth_range if sq.flood else None,
            return_period_years=sq.flood.return_period if sq.flood else None,
            river_name=sq.flood.river_name if sq.flood else None,
            source=sq.flood.source_name if sq.flood else "国土交通省 洪水浸水想定区域図",
            source_updated_at=sq.flood.source_updated_at if sq.flood else None,
            source_url=sq.flood.source_url if sq.flood else None,
        ),
        landslide=LandslideDetail(
            risk_level=_level_for_score(scores.landslide_score),
            risk_score=scores.landslide_score,
            zone_type=sq.landslide.zone_type if sq.landslide else None,
            source=sq.landslide.source_name if sq.landslide else "国土交通省 土砂災害警戒区域",
            source_updated_at=sq.landslide.source_updated_at if sq.landslide else None,
            source_url=sq.landslide.source_url if sq.landslide else None,
        ),
        tsunami=TsunamiDetail(
            risk_level=_level_for_score(scores.tsunami_score),
            risk_score=scores.tsunami_score,
            depth_m=float(sq.tsunami.depth_m) if sq.tsunami and sq.tsunami.depth_m else None,
            source=sq.tsunami.source_name if sq.tsunami else "内閣府 津波浸水想定",
            source_updated_at=sq.tsunami.source_updated_at if sq.tsunami else None,
            source_url=sq.tsunami.source_url if sq.tsunami else None,
        ),
        liquefaction=LiquefactionDetail(
            risk_level="unavailable",
            risk_score=None,
            data_available=False,
            map_url=sq.liquefaction.map_url if sq.liquefaction else None,
            source=(
                sq.liquefaction.source_name
                if sq.liquefaction
                else "J-SHIS 地震ハザードステーション（防災科学技術研究所）"
            ),
        ),
        composite_score=CompositeScore(
            score=scores.composite_score,
            level=scores.composite_level,
            description=scores.composite_description,
        ),
    )


# ── GeoJSON overlay endpoint for map ──────────────────────


_LAYER_MODELS = {
    "flood": HazardFlood,
    "landslide": HazardLandslide,
    "tsunami": HazardTsunami,
}

_FLOOD_COLORS: dict[int, str] = {
    0: "#ffffff",
    1: "#ffffb2",  # ~0.5m
    2: "#fecc5c",  # 0.5-1m
    3: "#fd8d3c",  # 1-2m
    4: "#f03b20",  # 2-5m
    5: "#bd0026",  # 5m+
}


def _build_features(rows: list, layer: str) -> list[dict]:
    """Convert DB rows to GeoJSON features."""
    features = []
    for row in rows:
        geom_json = json.loads(row.geom_geojson)
        props: dict = {"layer": layer}
        if layer == "flood":
            props["depth_rank"] = row.depth_rank
            props["depth_range"] = row.depth_range
            props["color"] = _FLOOD_COLORS.get(row.depth_rank, "#cccccc")
        elif layer == "landslide":
            props["zone_type"] = row.zone_type
            props["color"] = "#bd0026" if row.zone_type == "特別警戒区域" else "#fd8d3c"
        elif layer == "tsunami":
            props["depth_m"] = float(row.depth_m) if row.depth_m else None
            props["color"] = "#0c4a6e"
        features.append(
            {"type": "Feature", "geometry": geom_json, "properties": props}
        )
    return features


@router.get(
    "/v1/hazard/geojson",
    summary="ハザードゾーン GeoJSON",
    description="指定地点周辺のハザードポリゴンを GeoJSON FeatureCollection で返す（地図オーバーレイ用）",
)
async def get_hazard_geojson(
    api_key: AuthenticatedKey,
    lat: float = Query(..., ge=20.0, le=46.0, description="緯度"),
    lng: float = Query(..., ge=122.0, le=154.0, description="経度"),
    layers: str = Query("flood,landslide,tsunami", description="カンマ区切り: flood,landslide,tsunami"),
    radius_km: float = Query(2.0, ge=0.1, le=10.0, description="検索半径 (km)"),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> JSONResponse:
    # Convert km to approx degrees (1 degree ≈ 111km)
    delta = radius_km / 111.0
    bbox = ST_MakeEnvelope(lng - delta, lat - delta, lng + delta, lat + delta, 4326)

    requested = [lyr.strip() for lyr in layers.split(",") if lyr.strip() in _LAYER_MODELS]
    all_features: list[dict] = []

    for layer_name in requested:
        model = _LAYER_MODELS[layer_name]
        stmt = (
            select(
                model,
                func.ST_AsGeoJSON(func.ST_SimplifyPreserveTopology(model.geom, 0.0001)).label(
                    "geom_geojson"
                ),
            )
            .where(ST_Intersects(model.geom, bbox))
            .limit(500)
        )
        result = await db.execute(stmt)
        rows = result.all()
        fakes = [
            type(
                "R", (),
                {"geom_geojson": r.geom_geojson, **{c: getattr(r[0], c) for c in _props_for(layer_name)}},
            )()
            for r in rows
        ]
        all_features.extend(_build_features(fakes, layer_name))

    fc = {"type": "FeatureCollection", "features": all_features}
    return JSONResponse(content=fc, headers={"Cache-Control": "public, max-age=3600"})


def _props_for(layer: str) -> list[str]:
    """Column names to extract per layer."""
    if layer == "flood":
        return ["depth_rank", "depth_range"]
    if layer == "landslide":
        return ["zone_type"]
    if layer == "tsunami":
        return ["depth_m"]
    return []
