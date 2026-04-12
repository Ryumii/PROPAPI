// ── Hazard types ──────────────────────────────────────────

export interface FloodDetail {
  risk_level: string;
  risk_score: number;
  depth_m?: number | null;
  depth_range?: string | null;
  return_period_years?: number | null;
  source: string;
  source_updated_at?: string | null;
}

export interface LandslideDetail {
  risk_level: string;
  risk_score: number;
  zone_type?: string | null;
  source: string;
  source_updated_at?: string | null;
}

export interface TsunamiDetail {
  risk_level: string;
  risk_score: number;
  depth_m?: number | null;
  source: string;
  source_updated_at?: string | null;
}

export interface LiquefactionDetail {
  risk_level: string;
  risk_score?: number | null;
  data_available: boolean;
  map_url?: string | null;
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

// ── Zoning types ─────────────────────────────────────────

export interface ZoningResponse {
  use_district: string;
  use_district_code: string;
  building_coverage_pct?: number | null;
  floor_area_ratio_pct?: number | null;
  fire_prevention?: string | null;
  fire_prevention_code?: string | null;
  height_district?: string | null;
  scenic_district?: string | null;
  source: string;
  source_updated_at?: string | null;
}

// ── Inspect types ────────────────────────────────────────

export interface LocationInfo {
  lat: number;
  lng: number;
  prefecture?: string | null;
  city?: string | null;
  town?: string | null;
}

export interface InspectMeta {
  confidence: number;
  geocoding_method: string;
  processing_time_ms: number;
  api_version: string;
  data_updated_at?: string | null;
}

export interface InspectResponse {
  request_id: string;
  address_normalized?: string | null;
  location: LocationInfo;
  hazard?: HazardResponse | null;
  zoning?: ZoningResponse | null;
  meta: InspectMeta;
}

// ── Client options ───────────────────────────────────────

export interface PropAPIOptions {
  apiKey: string;
  baseUrl?: string;
  timeout?: number;
}

export interface InspectParams {
  address?: string;
  lat?: number;
  lng?: number;
  includeHazard?: boolean;
  includeZoning?: boolean;
}

export interface HazardParams {
  lat: number;
  lng: number;
  types?: string;
}

export interface ZoningParams {
  lat: number;
  lng: number;
}

// ── Error types ──────────────────────────────────────────

export interface APIErrorBody {
  code: string;
  message: string;
}
