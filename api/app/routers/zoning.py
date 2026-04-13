"""GET /v1/zoning — lightweight zoning-only endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import AsyncSession, get_db
from app.dependencies import AuthenticatedKey
from app.schemas.errors import MISSING_LOCATION, NOT_FOUND, ErrorResponse
from app.schemas.zoning import ZoningResponse
from app.services.geocoder import geocode
from app.services.spatial import spatial_query

router = APIRouter()


@router.get(
    "/v1/zoning",
    response_model=ZoningResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
    summary="用途地域情報取得",
    description="住所または緯度経度から用途地域情報のみを取得",
)
async def get_zoning(
    api_key: AuthenticatedKey,
    address: str | None = Query(None, description="住所"),
    lat: float | None = Query(None, ge=20.0, le=46.0, description="緯度"),
    lng: float | None = Query(None, ge=122.0, le=154.0, description="経度"),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> ZoningResponse:
    geo = await geocode(db, address=address, lat=lat, lng=lng)
    if geo is None:
        raise HTTPException(status_code=400, detail=MISSING_LOCATION.model_dump())

    sq = await spatial_query(db, geo.lat, geo.lng, include_hazard=False, include_zoning=True)

    if sq.zoning is None:
        raise HTTPException(status_code=404, detail=NOT_FOUND.model_dump())

    return ZoningResponse(
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
