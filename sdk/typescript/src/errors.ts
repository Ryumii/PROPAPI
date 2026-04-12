import type { APIErrorBody } from "./types.js";

export class PropAPIError extends Error {
  readonly statusCode: number;
  readonly code: string;

  constructor(statusCode: number, code: string, message: string) {
    super(`[${statusCode}] ${code}: ${message}`);
    this.name = "PropAPIError";
    this.statusCode = statusCode;
    this.code = code;
  }
}

export class AuthenticationError extends PropAPIError {
  constructor(statusCode: number, code: string, message: string) {
    super(statusCode, code, message);
    this.name = "AuthenticationError";
  }
}

export class RateLimitError extends PropAPIError {
  readonly retryAfter: number | null;

  constructor(
    statusCode: number,
    code: string,
    message: string,
    retryAfter: number | null = null,
  ) {
    super(statusCode, code, message);
    this.name = "RateLimitError";
    this.retryAfter = retryAfter;
  }
}

export function raiseForError(
  status: number,
  body: unknown,
  headers: Headers,
): never {
  let code = "unknown";
  let message = "Unknown error";

  if (body && typeof body === "object") {
    const err = (body as { error?: APIErrorBody }).error ?? (body as APIErrorBody);
    code = err.code ?? code;
    message = err.message ?? message;
  }

  if (status === 401 || status === 403) {
    throw new AuthenticationError(status, code, message);
  }
  if (status === 429) {
    const retry = headers.get("Retry-After");
    throw new RateLimitError(
      status,
      code,
      message,
      retry ? parseInt(retry, 10) : null,
    );
  }
  throw new PropAPIError(status, code, message);
}
