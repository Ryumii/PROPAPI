"""GET /v1/hazard — lightweight hazard-only endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import AsyncSession, get_db
from app.dependencies import AuthenticatedKey
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
            source=sq.flood.source_name if sq.flood else "国土交通省 洪水浸水想定区域図",
            source_updated_at=sq.flood.source_updated_at if sq.flood else None,
        ),
        landslide=LandslideDetail(
            risk_level=_level_for_score(scores.landslide_score),
            risk_score=scores.landslide_score,
            zone_type=sq.landslide.zone_type if sq.landslide else None,
            source=sq.landslide.source_name if sq.landslide else "国土交通省 土砂災害警戒区域",
            source_updated_at=sq.landslide.source_updated_at if sq.landslide else None,
        ),
        tsunami=TsunamiDetail(
            risk_level=_level_for_score(scores.tsunami_score),
            risk_score=scores.tsunami_score,
            depth_m=float(sq.tsunami.depth_m) if sq.tsunami and sq.tsunami.depth_m else None,
            source=sq.tsunami.source_name if sq.tsunami else "内閣府 津波浸水想定",
            source_updated_at=sq.tsunami.source_updated_at if sq.tsunami else None,
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
