"""Hazard response schemas."""

from pydantic import BaseModel, Field


class FloodDetail(BaseModel):
    risk_level: str = Field(..., examples=["low"])
    risk_score: int = Field(..., ge=0, le=5)
    depth_m: float | None = Field(None, examples=[0.5])
    depth_range: str | None = Field(None, examples=["0.0m〜0.5m"])
    return_period_years: int | None = Field(None, examples=[1000])
    source: str = Field(..., examples=["国土交通省 洪水浸水想定区域図"])
    source_updated_at: str | None = None


class LandslideDetail(BaseModel):
    risk_level: str = Field(..., examples=["none"])
    risk_score: int = Field(..., ge=0, le=5)
    zone_type: str | None = Field(None, examples=["警戒区域"])
    source: str = Field(..., examples=["国土交通省 土砂災害警戒区域"])
    source_updated_at: str | None = None


class TsunamiDetail(BaseModel):
    risk_level: str = Field(..., examples=["none"])
    risk_score: int = Field(..., ge=0, le=5)
    depth_m: float | None = None
    source: str = Field(..., examples=["内閣府 津波浸水想定"])
    source_updated_at: str | None = None


class LiquefactionDetail(BaseModel):
    risk_level: str = Field(..., examples=["medium"])
    risk_score: int = Field(..., ge=0, le=5)
    pl_value: float | None = Field(None, examples=[12.5])
    source: str = Field(..., examples=["東京都 液状化予測図"])
    source_updated_at: str | None = None


class CompositeScore(BaseModel):
    score: float = Field(..., ge=0, le=5, examples=[2.1])
    level: str = Field(..., examples=["low"])
    description: str = Field(..., examples=["総合的なリスクは低めです"])


class HazardResponse(BaseModel):
    flood: FloodDetail
    landslide: LandslideDetail
    tsunami: TsunamiDetail
    liquefaction: LiquefactionDetail
    composite_score: CompositeScore
