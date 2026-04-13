"""Zoning response schema."""

from pydantic import BaseModel, Field


class ZoningResponse(BaseModel):
    use_district: str = Field(..., examples=["商業地域"])
    use_district_code: str = Field(..., examples=["09"])
    building_coverage_pct: int | None = Field(None, examples=[80])
    floor_area_ratio_pct: int | None = Field(None, examples=[600])
    fire_prevention: str | None = Field(None, examples=["防火地域"])
    fire_prevention_code: str | None = Field(None, examples=["01"])
    height_district: str | None = Field(None, examples=["第三種高度地区"])
    scenic_district: str | None = None
    source: str = Field(..., examples=["国土数値情報 用途地域データ"])
    source_updated_at: str | None = None
    source_url: str | None = Field(None, description="データソースのURL")
