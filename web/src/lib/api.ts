/** API client — calls the PropAPI backend. */

import type { InspectResponse, ErrorResponse } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY ?? "";

export class ApiError extends Error {
  code: string;
  status: number;

  constructor(status: number, detail: ErrorResponse["error"]) {
    super(detail.message);
    this.name = "ApiError";
    this.status = status;
    this.code = detail.code;
  }
}

export async function inspect(address: string): Promise<InspectResponse> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (API_KEY) headers["X-API-Key"] = API_KEY;

  const res = await fetch(`${API_BASE}/v1/land/inspect`, {
    method: "POST",
    headers,
    body: JSON.stringify({ address }),
  });

  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as ErrorResponse | null;
    throw new ApiError(
      res.status,
      body?.error ?? { code: "UNKNOWN", message: res.statusText, field: null },
    );
  }

  return (await res.json()) as InspectResponse;
}

export async function inspectByCoords(lat: number, lng: number): Promise<InspectResponse> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (API_KEY) headers["X-API-Key"] = API_KEY;

  const res = await fetch(`${API_BASE}/v1/land/inspect`, {
    method: "POST",
    headers,
    body: JSON.stringify({ lat, lng }),
  });

  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as ErrorResponse | null;
    throw new ApiError(
      res.status,
      body?.error ?? { code: "UNKNOWN", message: res.statusText, field: null },
    );
  }

  return (await res.json()) as InspectResponse;
}

/**
 * Parse a coordinate string (e.g. "35.6595, 139.7004" from Google Maps).
 * Returns { lat, lng } or null if the string is not coordinates.
 */
export function parseCoordinates(input: string): { lat: number; lng: number } | null {
  const trimmed = input.trim();
  // Match patterns: "35.6595, 139.7004" or "35.6595 139.7004"
  const match = trimmed.match(/^(-?\d+\.?\d*)[,\s]+(-?\d+\.?\d*)$/);
  if (!match) return null;

  const a = parseFloat(match[1]);
  const b = parseFloat(match[2]);
  if (isNaN(a) || isNaN(b)) return null;

  // Japan bounds: lat 20-46, lng 122-154
  if (a >= 20 && a <= 46 && b >= 122 && b <= 154) {
    return { lat: a, lng: b };
  }
  // Reversed order (lng, lat)
  if (b >= 20 && b <= 46 && a >= 122 && a <= 154) {
    return { lat: b, lng: a };
  }
  return null;
}

export async function fetchHazardGeoJSON(
  lat: number,
  lng: number,
  layers = "flood,landslide,tsunami",
): Promise<GeoJSON.FeatureCollection> {
  const headers: Record<string, string> = {};
  if (API_KEY) headers["X-API-Key"] = API_KEY;

  const params = new URLSearchParams({ lat: String(lat), lng: String(lng), layers });
  const res = await fetch(`${API_BASE}/v1/hazard/geojson?${params}`, { headers });

  if (!res.ok) return { type: "FeatureCollection", features: [] };
  return (await res.json()) as GeoJSON.FeatureCollection;
}
