"""PropAPI response models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FloodDetail:
    risk_level: str
    risk_score: int
    depth_m: float | None = None
    depth_range: str | None = None
    return_period_years: int | None = None
    source: str = ""
    source_updated_at: str | None = None


@dataclass(frozen=True)
class LandslideDetail:
    risk_level: str
    risk_score: int
    zone_type: str | None = None
    source: str = ""
    source_updated_at: str | None = None


@dataclass(frozen=True)
class TsunamiDetail:
    risk_level: str
    risk_score: int
    depth_m: float | None = None
    source: str = ""
    source_updated_at: str | None = None


@dataclass(frozen=True)
class LiquefactionDetail:
    risk_level: str = "unavailable"
    risk_score: int | None = None
    data_available: bool = False
    map_url: str | None = None
    source: str = ""
    note: str = ""


@dataclass(frozen=True)
class CompositeScore:
    score: float
    level: str
    description: str = ""


@dataclass(frozen=True)
class HazardResponse:
    flood: FloodDetail
    landslide: LandslideDetail
    tsunami: TsunamiDetail
    liquefaction: LiquefactionDetail
    composite_score: CompositeScore


@dataclass(frozen=True)
class ZoningResponse:
    use_district: str
    use_district_code: str
    building_coverage_pct: int | None = None
    floor_area_ratio_pct: int | None = None
    fire_prevention: str | None = None
    fire_prevention_code: str | None = None
    height_district: str | None = None
    scenic_district: str | None = None
    source: str = ""
    source_updated_at: str | None = None


@dataclass(frozen=True)
class LocationInfo:
    lat: float
    lng: float
    prefecture: str | None = None
    city: str | None = None
    town: str | None = None


@dataclass(frozen=True)
class InspectMeta:
    confidence: float
    geocoding_method: str
    processing_time_ms: int
    api_version: str = ""
    data_updated_at: str | None = None


@dataclass(frozen=True)
class InspectResponse:
    request_id: str
    location: LocationInfo
    meta: InspectMeta
    address_normalized: str | None = None
    hazard: HazardResponse | None = None
    zoning: ZoningResponse | None = None


# ── Parsing helpers ──────────────────────────────────────


def _parse_flood(d: dict[str, Any]) -> FloodDetail:
    return FloodDetail(**{k: v for k, v in d.items() if k in FloodDetail.__dataclass_fields__})


def _parse_landslide(d: dict[str, Any]) -> LandslideDetail:
    return LandslideDetail(**{k: v for k, v in d.items() if k in LandslideDetail.__dataclass_fields__})


def _parse_tsunami(d: dict[str, Any]) -> TsunamiDetail:
    return TsunamiDetail(**{k: v for k, v in d.items() if k in TsunamiDetail.__dataclass_fields__})


def _parse_liquefaction(d: dict[str, Any]) -> LiquefactionDetail:
    return LiquefactionDetail(**{k: v for k, v in d.items() if k in LiquefactionDetail.__dataclass_fields__})


def _parse_composite(d: dict[str, Any]) -> CompositeScore:
    return CompositeScore(**{k: v for k, v in d.items() if k in CompositeScore.__dataclass_fields__})


def _parse_hazard(d: dict[str, Any]) -> HazardResponse:
    return HazardResponse(
        flood=_parse_flood(d["flood"]),
        landslide=_parse_landslide(d["landslide"]),
        tsunami=_parse_tsunami(d["tsunami"]),
        liquefaction=_parse_liquefaction(d["liquefaction"]),
        composite_score=_parse_composite(d["composite_score"]),
    )


def _parse_zoning(d: dict[str, Any]) -> ZoningResponse:
    return ZoningResponse(**{k: v for k, v in d.items() if k in ZoningResponse.__dataclass_fields__})


def _parse_location(d: dict[str, Any]) -> LocationInfo:
    return LocationInfo(**{k: v for k, v in d.items() if k in LocationInfo.__dataclass_fields__})


def _parse_meta(d: dict[str, Any]) -> InspectMeta:
    return InspectMeta(**{k: v for k, v in d.items() if k in InspectMeta.__dataclass_fields__})


def parse_inspect_response(data: dict[str, Any]) -> InspectResponse:
    hazard = _parse_hazard(data["hazard"]) if data.get("hazard") else None
    zoning = _parse_zoning(data["zoning"]) if data.get("zoning") else None
    return InspectResponse(
        request_id=data["request_id"],
        address_normalized=data.get("address_normalized"),
        location=_parse_location(data["location"]),
        hazard=hazard,
        zoning=zoning,
        meta=_parse_meta(data["meta"]),
    )


def parse_hazard_response(data: dict[str, Any]) -> HazardResponse:
    return _parse_hazard(data)


def parse_zoning_response(data: dict[str, Any]) -> ZoningResponse:
    return _parse_zoning(data)
