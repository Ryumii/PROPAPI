"""Inspect endpoint request / response schemas."""

from pydantic import BaseModel, Field, model_validator

from app.schemas.hazard import HazardResponse
from app.schemas.land_price import LandPriceResponse
from app.schemas.zoning import ZoningResponse


class InspectOptions(BaseModel):
    include_hazard: bool = True
    include_zoning: bool = True
    include_land_price: bool = True


class InspectRequest(BaseModel):
    address: str | None = Field(None, examples=["東京都渋谷区渋谷2-24-12"])
    lat: float | None = Field(None, ge=20.0, le=46.0, examples=[35.6595])
    lng: float | None = Field(None, ge=122.0, le=154.0, examples=[139.7004])
    options: InspectOptions = Field(default_factory=InspectOptions)

    @model_validator(mode="after")
    def require_location(self) -> "InspectRequest":
        if not self.address and (self.lat is None or self.lng is None):
            raise ValueError("address または lat/lng のいずれかを指定してください")
        return self


class LocationInfo(BaseModel):
    lat: float
    lng: float
    prefecture: str | None = None
    city: str | None = None
    town: str | None = None


class InspectMeta(BaseModel):
    data_updated_at: str | None = None
    confidence: float = Field(..., ge=0, le=1, examples=[0.97])
    geocoding_method: str = Field(..., examples=["address_match"])
    processing_time_ms: int
    api_version: str = "1.0.0"


class InspectResponse(BaseModel):
    request_id: str
    address_normalized: str | None = None
    location: LocationInfo
    hazard: HazardResponse | None = None
    zoning: ZoningResponse | None = None
    land_price: LandPriceResponse | None = None
    meta: InspectMeta
