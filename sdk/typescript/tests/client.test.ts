import { describe, it, expect, vi, beforeEach } from "vitest";
import { PropAPI } from "../src/client.js";
import { AuthenticationError, RateLimitError, PropAPIError } from "../src/errors.js";

const BASE = "https://api.propapi.jp";

const INSPECT_RESPONSE = {
  request_id: "req_abc",
  address_normalized: "東京都渋谷区渋谷二丁目24-12",
  location: { lat: 35.6595, lng: 139.7004, prefecture: "東京都", city: "渋谷区" },
  hazard: {
    flood: { risk_level: "low", risk_score: 1, depth_m: 0.5, source: "s" },
    landslide: { risk_level: "none", risk_score: 0, source: "s" },
    tsunami: { risk_level: "none", risk_score: 0, source: "s" },
    liquefaction: { risk_level: "unavailable", data_available: false, source: "s", note: "" },
    composite_score: { score: 0.4, level: "very_low", description: "" },
  },
  zoning: {
    use_district: "商業地域",
    use_district_code: "09",
    building_coverage_pct: 80,
    floor_area_ratio_pct: 600,
    source: "国土数値情報 用途地域データ",
  },
  meta: { confidence: 0.97, geocoding_method: "address_match", processing_time_ms: 123, api_version: "1.0.0" },
};

function mockFetch(status: number, body: unknown, headers?: Record<string, string>) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 400,
    status,
    headers: new Headers(headers ?? {}),
    json: () => Promise.resolve(body),
  });
}

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("PropAPI client", () => {
  it("inspect by address", async () => {
    globalThis.fetch = mockFetch(200, INSPECT_RESPONSE);
    const client = new PropAPI({ apiKey: "test_key" });
    const result = await client.inspect({ address: "東京都渋谷区渋谷2-24-12" });

    expect(result.request_id).toBe("req_abc");
    expect(result.hazard?.flood.risk_score).toBe(1);
    expect(result.zoning?.use_district).toBe("商業地域");
    expect(result.meta.processing_time_ms).toBe(123);

    const call = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toBe(`${BASE}/v1/land/inspect`);
    expect(call[1].headers["X-API-Key"]).toBe("test_key");
  });

  it("inspect by coords", async () => {
    globalThis.fetch = mockFetch(200, INSPECT_RESPONSE);
    const client = new PropAPI({ apiKey: "k" });
    const result = await client.inspect({ lat: 35.6595, lng: 139.7004 });

    const body = JSON.parse((globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][1].body);
    expect(body.lat).toBe(35.6595);
    expect(body.lng).toBe(139.7004);
    expect(result.location.lng).toBe(139.7004);
  });

  it("hazard", async () => {
    globalThis.fetch = mockFetch(200, INSPECT_RESPONSE.hazard);
    const client = new PropAPI({ apiKey: "k" });
    const h = await client.hazard({ lat: 35.66, lng: 139.70 });

    expect(h.flood.risk_level).toBe("low");
    expect(h.tsunami.risk_score).toBe(0);
  });

  it("zoning", async () => {
    globalThis.fetch = mockFetch(200, INSPECT_RESPONSE.zoning);
    const client = new PropAPI({ apiKey: "k" });
    const z = await client.zoning({ lat: 35.66, lng: 139.70 });

    expect(z.use_district).toBe("商業地域");
    expect(z.floor_area_ratio_pct).toBe(600);
  });

  it("health", async () => {
    globalThis.fetch = mockFetch(200, { status: "healthy" });
    const client = new PropAPI({ apiKey: "k" });
    const h = await client.health();

    expect(h.status).toBe("healthy");
  });

  it("throws AuthenticationError on 401", async () => {
    globalThis.fetch = mockFetch(401, { error: { code: "invalid_api_key", message: "Bad key" } });
    const client = new PropAPI({ apiKey: "bad" });

    await expect(client.inspect({ address: "test" })).rejects.toThrow(AuthenticationError);
  });

  it("throws RateLimitError on 429", async () => {
    globalThis.fetch = mockFetch(
      429,
      { error: { code: "rate_limit", message: "Too many" } },
      { "Retry-After": "30" },
    );
    const client = new PropAPI({ apiKey: "k" });

    try {
      await client.inspect({ address: "test" });
      expect.fail("should throw");
    } catch (e) {
      expect(e).toBeInstanceOf(RateLimitError);
      expect((e as RateLimitError).retryAfter).toBe(30);
    }
  });

  it("throws PropAPIError on 500", async () => {
    globalThis.fetch = mockFetch(500, { error: { code: "internal", message: "oops" } });
    const client = new PropAPI({ apiKey: "k" });

    await expect(client.inspect({ address: "test" })).rejects.toThrow(PropAPIError);
  });
});
