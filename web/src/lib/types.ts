/** API response types matching backend Pydantic schemas. */

// ── Hazard ──────────────────────────────────────────────

export interface FloodDetail {
  risk_level: string;
  risk_score: number;
  depth_m: number | null;
  depth_range: string | null;
  return_period_years: number | null;
  source: string;
  source_updated_at: string | null;
}

export interface LandslideDetail {
  risk_level: string;
  risk_score: number;
  zone_type: string | null;
  source: string;
  source_updated_at: string | null;
}

export interface TsunamiDetail {
  risk_level: string;
  risk_score: number;
  depth_m: number | null;
  source: string;
  source_updated_at: string | null;
}

export interface LiquefactionDetail {
  risk_level: string;
  risk_score: number | null;
  data_available: boolean;
  map_url: string | null;
  source: string;
  note: string;
}

export interface CompositeScore {
  score: number;
  level: string;
  description: string;
}

export interface HazardResponse {
  flood: FloodDetail;
  landslide: LandslideDetail;
  tsunami: TsunamiDetail;
  liquefaction: LiquefactionDetail;
  composite_score: CompositeScore;
}

// ── Zoning ──────────────────────────────────────────────

export interface ZoningResponse {
  use_district: string;
  use_district_code: string;
  building_coverage_pct: number | null;
  floor_area_ratio_pct: number | null;
  fire_prevention: string | null;
  fire_prevention_code: string | null;
  height_district: string | null;
  scenic_district: string | null;
  source: string;
  source_updated_at: string | null;
}

// ── Land Price ──────────────────────────────────────────

export interface NearbyLandPrice {
  price_per_sqm: number;
  year: number;
  yoy_change_pct: number | null;
  land_use: string | null;
  address: string | null;
  area_sqm: number | null;
  structure: string | null;
  nearest_station: string | null;
  station_distance_m: number | null;
  distance_m: number;
  lat: number;
  lng: number;
}

export interface LandPriceResponse {
  nearest: NearbyLandPrice | null;
  nearby: NearbyLandPrice[];
  source: string;
  source_updated_at: string | null;
}

// ── Inspect ─────────────────────────────────────────────

export interface LocationInfo {
  lat: number;
  lng: number;
  prefecture: string | null;
  city: string | null;
  town: string | null;
}

export interface InspectMeta {
  data_updated_at: string | null;
  confidence: number;
  geocoding_method: string;
  processing_time_ms: number;
  api_version: string;
}

export interface InspectResponse {
  request_id: string;
  address_normalized: string | null;
  location: LocationInfo;
  hazard: HazardResponse | null;
  zoning: ZoningResponse | null;
  land_price: LandPriceResponse | null;
  meta: InspectMeta;
}

// ── Error ───────────────────────────────────────────────

export interface ErrorDetail {
  code: string;
  message: string;
  field: string | null;
}

export interface ErrorResponse {
  error: ErrorDetail;
}
