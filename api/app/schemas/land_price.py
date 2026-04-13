"""Land price response schemas."""

from pydantic import BaseModel, Field


class NearbyLandPrice(BaseModel):
    """A single nearby land price point."""
    price_per_sqm: int = Field(..., examples=[450000], description="公示価格 (円/m²)")
    year: int = Field(..., examples=[2026])
    yoy_change_pct: float | None = Field(None, examples=[3.1], description="前年変動率 (%)")
    land_use: str | None = Field(None, examples=["住宅"])
    address: str | None = Field(None, examples=["東京都渋谷区渋谷二丁目24番12号"])
    area_sqm: int | None = Field(None, examples=[495])
    structure: str | None = Field(None, examples=["RC"])
    nearest_station: str | None = Field(None, examples=["渋谷"])
    station_distance_m: int | None = Field(None, examples=[200])
    distance_m: int = Field(..., examples=[150], description="検索地点からの距離 (m)")
    lat: float = Field(..., examples=[35.6595])
    lng: float = Field(..., examples=[139.7004])


class LandPriceResponse(BaseModel):
    """Land price data for the queried location."""
    nearest: NearbyLandPrice | None = Field(None, description="最寄りの公示地価地点")
    nearby: list[NearbyLandPrice] = Field(default_factory=list, description="近隣の公示地価地点 (5件まで)")
    source: str = Field(default="国土数値情報 地価公示データ (L01)", examples=["国土数値情報 地価公示データ (L01)"])
    source_updated_at: str | None = None
    source_url: str | None = Field(None, description="データソースのURL")
