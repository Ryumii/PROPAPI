"""POST /v1/land/inspect — unified land survey endpoint."""

from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

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
from app.schemas.inspect import InspectMeta, InspectRequest, InspectResponse, LocationInfo
from app.schemas.zoning import ZoningResponse
from app.services.billing import record_usage
from app.services.cache import get_cache
from app.services.geocoder import geocode
from app.services.scoring import _level_for_score, calculate_scores
from app.services.spatial import spatial_query

router = APIRouter()


@router.post(
    "/v1/land/inspect",
    response_model=InspectResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
    summary="土地調査統合",
    description="住所または緯度経度からハザードリスク・用途地域を一括取得",
)
async def land_inspect(
    body: InspectRequest,
    background_tasks: BackgroundTasks,
    api_key: AuthenticatedKey,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> InspectResponse:
    start = time.monotonic()
    request_id = f"req_{uuid.uuid4().hex[:16]}"

    # --- cache check (by normalized address + options) ---
    cache = get_cache()
    cache_key_input = ""
    if body.address:
        from app.utils.address_normalizer import normalize_address

        parsed = normalize_address(body.address)
        cache_key_input = parsed.normalized or body.address
    options_hash = f"h={body.options.include_hazard}&z={body.options.include_zoning}"

    if cache_key_input:
        cached = await cache.get_inspect(cache_key_input, options_hash)
        if cached is not None:
            elapsed = int((time.monotonic() - start) * 1000)
            cached["request_id"] = request_id
            if "meta" in cached:
                cached["meta"]["processing_time_ms"] = elapsed
            _schedule_usage_log(
                background_tasks, db, api_key.id, "/v1/land/inspect",
                body.address, 200, elapsed,
            )
            return InspectResponse(**cached)

    # --- geocoding ---
    geo = await geocode(db, address=body.address, lat=body.lat, lng=body.lng)
    if geo is None:
        raise HTTPException(status_code=400, detail=MISSING_LOCATION.model_dump())

    # --- spatial queries ---
    sq = await spatial_query(
        db, geo.lat, geo.lng,
        include_hazard=body.options.include_hazard,
        include_zoning=body.options.include_zoning,
    )

    # --- scoring ---
    scores = calculate_scores(sq)

    # --- build response ---
    hazard_resp: HazardResponse | None = None
    if body.options.include_hazard:
        hazard_resp = HazardResponse(
            flood=FloodDetail(
                risk_level=_level_for_score(scores.flood_score),
                risk_score=scores.flood_score,
                depth_m=sq.flood.depth_rank if sq.flood else None,  # approximate
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
                source=sq.liquefaction.source_name if sq.liquefaction else "J-SHIS 地震ハザードステーション（防災科学技術研究所）",
            ),
            composite_score=CompositeScore(
                score=scores.composite_score,
                level=scores.composite_level,
                description=scores.composite_description,
            ),
        )

    zoning_resp: ZoningResponse | None = None
    if body.options.include_zoning and sq.zoning:
        zoning_resp = ZoningResponse(
            use_district=sq.zoning.use_district,
            use_district_code=sq.zoning.use_code,
            building_coverage_pct=sq.zoning.coverage_pct,
            floor_area_ratio_pct=sq.zoning.floor_ratio_pct,
            fire_prevention=sq.zoning.fire_prevention,
            fire_prevention_code=sq.zoning.fire_code,
            height_district=sq.zoning.height_district,
            scenic_district=sq.zoning.scenic_district,
            source=sq.zoning.source_name,
            source_updated_at=sq.zoning.source_updated_at,
        )

    elapsed_ms = int((time.monotonic() - start) * 1000)

    response = InspectResponse(
        request_id=request_id,
        address_normalized=geo.normalized_address,
        location=LocationInfo(
            lat=geo.lat,
            lng=geo.lng,
            prefecture=geo.prefecture,
            city=geo.city,
            town=geo.town,
        ),
        hazard=hazard_resp,
        zoning=zoning_resp,
        meta=InspectMeta(
            confidence=geo.confidence,
            geocoding_method=geo.method,
            processing_time_ms=elapsed_ms,
        ),
    )

    # --- cache store ---
    if cache_key_input:
        await cache.set_inspect(cache_key_input, response.model_dump(), options_hash)

    # --- usage log (background) ---
    _schedule_usage_log(
        background_tasks, db, api_key.id, "/v1/land/inspect",
        body.address, 200, elapsed_ms,
    )

    return response


def _schedule_usage_log(
    bg: BackgroundTasks,
    db: AsyncSession,
    api_key_id: int,
    endpoint: str,
    address: str | None,
    status: int,
    ms: int,
) -> None:
    bg.add_task(
        record_usage,
        db,
        api_key_id=api_key_id,
        endpoint=endpoint,
        request_address=address,
        response_status=status,
        processing_time_ms=ms,
    )
