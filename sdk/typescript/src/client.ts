import { raiseForError } from "./errors.js";
import type {
  HazardParams,
  HazardResponse,
  InspectParams,
  InspectResponse,
  PropAPIOptions,
  ZoningParams,
  ZoningResponse,
} from "./types.js";

const DEFAULT_BASE = "https://api.propapi.jp";
const DEFAULT_TIMEOUT = 30_000;

/**
 * PropAPI client for land hazard and zoning inspection.
 *
 * @example
 * ```ts
 * import { PropAPI } from "propapi";
 *
 * const client = new PropAPI({ apiKey: "cs_live_..." });
 * const result = await client.inspect({ address: "東京都渋谷区渋谷2-24-12" });
 * console.log(result.hazard?.flood.risk_level);
 * ```
 */
export class PropAPI {
  private readonly baseUrl: string;
  private readonly headers: Record<string, string>;
  private readonly timeout: number;

  constructor(options: PropAPIOptions) {
    this.baseUrl = (options.baseUrl ?? DEFAULT_BASE).replace(/\/$/, "");
    this.timeout = options.timeout ?? DEFAULT_TIMEOUT;
    this.headers = {
      "X-API-Key": options.apiKey,
      "User-Agent": "propapi-js/0.1.0",
      "Content-Type": "application/json",
    };
  }

  private async request<T>(
    method: string,
    path: string,
    options?: { body?: unknown; params?: Record<string, string> },
  ): Promise<T> {
    let url = `${this.baseUrl}${path}`;
    if (options?.params) {
      const qs = new URLSearchParams(options.params).toString();
      url += `?${qs}`;
    }

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeout);

    try {
      const resp = await fetch(url, {
        method,
        headers: this.headers,
        body: options?.body ? JSON.stringify(options.body) : undefined,
        signal: controller.signal,
      });

      const data = await resp.json();

      if (!resp.ok) {
        raiseForError(resp.status, data, resp.headers);
      }

      return data as T;
    } finally {
      clearTimeout(timer);
    }
  }

  /** POST /v1/land/inspect — full land inspection. */
  async inspect(params: InspectParams): Promise<InspectResponse> {
    const body: Record<string, unknown> = {
      options: {
        include_hazard: params.includeHazard ?? true,
        include_zoning: params.includeZoning ?? true,
      },
    };
    if (params.address != null) body.address = params.address;
    if (params.lat != null && params.lng != null) {
      body.lat = params.lat;
      body.lng = params.lng;
    }
    return this.request<InspectResponse>("POST", "/v1/land/inspect", { body });
  }

  /** GET /v1/hazard — hazard-only query. */
  async hazard(params: HazardParams): Promise<HazardResponse> {
    const qs: Record<string, string> = {
      lat: String(params.lat),
      lng: String(params.lng),
    };
    if (params.types) qs.types = params.types;
    return this.request<HazardResponse>("GET", "/v1/hazard", { params: qs });
  }

  /** GET /v1/zoning — zoning-only query. */
  async zoning(params: ZoningParams): Promise<ZoningResponse> {
    return this.request<ZoningResponse>("GET", "/v1/zoning", {
      params: { lat: String(params.lat), lng: String(params.lng) },
    });
  }

  /** GET /v1/health */
  async health(): Promise<{ status: string }> {
    return this.request<{ status: string }>("GET", "/v1/health");
  }
}
