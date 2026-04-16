"""POST /v1/batch — batch land inspection endpoint."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends

from app.database import AsyncSession, async_session, get_db
from app.dependencies import AuthenticatedKey
from app.schemas.batch import (
    BatchItem,
    BatchRequest,
    BatchResponse,
    BatchResultItem,
)
from app.schemas.errors import ErrorResponse
from app.schemas.hazard import (
    CompositeScore,
    FloodDetail,
    HazardResponse,
    LandslideDetail,
    LiquefactionDetail,
    TsunamiDetail,
)
from app.schemas.inspect import InspectMeta, InspectResponse, LocationInfo
from app.schemas.school_district import SchoolDistrictInfo, SchoolDistrictResponse
from app.schemas.zoning import ZoningResponse
from app.services.billing import record_usage
from app.services.geocoder import geocode
from app.services.scoring import _level_for_score, calculate_scores, flood_depth_m
from app.services.spatial import spatial_query

logger = logging.getLogger(__name__)

router = APIRouter()

# Max concurrent inspections to avoid overwhelming DB connections
_MAX_CONCURRENCY = 20


async def _process_item(
    item: BatchItem,
    options: BatchRequest,
    db: AsyncSession,
) -> BatchResultItem:
    """Process a single batch item; never raises."""
    start = time.monotonic()
    request_id = f"req_{uuid.uuid4().hex[:16]}"

    try:
        geo = await geocode(db, address=item.address, lat=item.lat, lng=item.lng)
        if geo is None:
            return BatchResultItem(
                id=item.id,
                status="error",
                error="住所のジオコーディングに失敗しました",
            )

        sq = await spatial_query(
            db,
            geo.lat,
            geo.lng,
            include_hazard=options.options.include_hazard,
            include_zoning=options.options.include_zoning,
            include_school_district=options.options.include_school_district,
        )

        scores = calculate_scores(sq)

        hazard_resp: HazardResponse | None = None
        if options.options.include_hazard:
            hazard_resp = HazardResponse(
                flood=FloodDetail(
                    risk_level=_level_for_score(scores.flood_score),
                    risk_score=scores.flood_score,
                    depth_m=flood_depth_m(sq.flood.depth_rank) if sq.flood else None,
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

        zoning_resp: ZoningResponse | None = None
        if options.options.include_zoning and sq.zoning:
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
                source_url=sq.zoning.source_url,
            )

        # --- school district ---
        school_resp: SchoolDistrictResponse | None = None
        if options.options.include_school_district:
            elem_info = None
            if sq.elementary_school:
                elem_info = SchoolDistrictInfo(
                    school_type=sq.elementary_school.school_type,
                    school_name=sq.elementary_school.school_name,
                    administrator=sq.elementary_school.administrator,
                    address=sq.elementary_school.address,
                    source=sq.elementary_school.source_name,
                    source_url=sq.elementary_school.source_url,
                )
            jh_info = None
            if sq.junior_high_school:
                jh_info = SchoolDistrictInfo(
                    school_type=sq.junior_high_school.school_type,
                    school_name=sq.junior_high_school.school_name,
                    administrator=sq.junior_high_school.administrator,
                    address=sq.junior_high_school.address,
                    source=sq.junior_high_school.source_name,
                    source_url=sq.junior_high_school.source_url,
                )
            if elem_info or jh_info:
                school_resp = SchoolDistrictResponse(
                    elementary=elem_info,
                    junior_high=jh_info,
                )

        elapsed_ms = int((time.monotonic() - start) * 1000)

        inspect_resp = InspectResponse(
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
            school_district=school_resp,
            meta=InspectMeta(
                confidence=geo.confidence,
                geocoding_method=geo.method,
                processing_time_ms=elapsed_ms,
            ),
        )

        return BatchResultItem(id=item.id, status="success", result=inspect_resp)

    except Exception as e:
        logger.exception("Batch item %s failed", item.id)
        return BatchResultItem(id=item.id, status="error", error=str(e))


@router.post(
    "/v1/batch",
    response_model=BatchResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
    summary="バッチ土地調査",
    description="最大 1,000 件の住所/座標を一括調査",
)
async def batch_inspect(
    body: BatchRequest,
    background_tasks: BackgroundTasks,
    api_key: AuthenticatedKey,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> BatchResponse:
    start = time.monotonic()
    job_id = f"job_{uuid.uuid4().hex[:16]}"

    sem = asyncio.Semaphore(_MAX_CONCURRENCY)

    async def _with_sem(item: BatchItem) -> BatchResultItem:
        async with sem:
            # Each worker gets its own session to avoid shared-state corruption
            async with async_session() as worker_db:
                return await _process_item(item, body, worker_db)

    results = await asyncio.gather(*[_with_sem(item) for item in body.items])

    succeeded = sum(1 for r in results if r.status == "success")
    failed = len(results) - succeeded
    elapsed_ms = int((time.monotonic() - start) * 1000)

    # Usage log: use independent session for background task
    async def _log_usage() -> None:
        async with async_session() as log_db:
            await record_usage(
                log_db,
                api_key_id=api_key.id,
                endpoint="/v1/batch",
                request_address=f"batch:{len(body.items)}items",
                response_status=200,
                processing_time_ms=elapsed_ms,
            )

    background_tasks.add_task(_log_usage)

    return BatchResponse(
        job_id=job_id,
        status="completed" if failed == 0 else "partial",
        total=len(results),
        succeeded=succeeded,
        failed=failed,
        results=list(results),
    )
