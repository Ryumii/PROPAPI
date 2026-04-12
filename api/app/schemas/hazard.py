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
    risk_level: str = Field(default="unavailable", examples=["unavailable"])
    risk_score: int | None = Field(default=None, ge=0, le=5)
    data_available: bool = Field(default=False)
    map_url: str | None = Field(
        None,
        examples=["https://www.j-shis.bosai.go.jp/map/?lat=35.6595&lon=139.7004&zoom=14"],
        description="該当地区の液状化リスク地図へのリンク",
    )
    source: str = Field(
        default="J-SHIS 地震ハザードステーション（防災科学技術研究所）",
        examples=["J-SHIS 地震ハザードステーション（防災科学技術研究所）"],
    )
    note: str = Field(
        default="液状化リスクの詳細は地図リンクからご確認ください",
        description="データが外部参照であることの説明",
    )


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
