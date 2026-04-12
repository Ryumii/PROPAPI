/** API client — calls the PropAPI backend. */

import type { InspectResponse, ErrorResponse } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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
  const res = await fetch(`${API_BASE}/v1/land/inspect`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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
