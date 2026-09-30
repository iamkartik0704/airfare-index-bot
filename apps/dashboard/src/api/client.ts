import type { ErrorBody } from "./types";

/**
 * Typed fetch wrapper for the SAFAR FastAPI service.
 *
 * The base URL comes from `VITE_API_BASE_URL`; empty (the default) means same
 * origin — the Vite dev server and the production nginx both proxy `/api`.
 */
export const API_BASE_URL: string = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
export const API_PREFIX = "/api/v1";

/** Error raised for any non-2xx response; carries the API's error envelope. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId: string | null;
  readonly details: Record<string, unknown>;
  readonly path: string;

  constructor(status: number, body: Partial<ErrorBody>, path: string) {
    super(body.message || `Request failed with HTTP ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.code = body.code || `HTTP_${status}`;
    this.requestId = body.request_id ?? null;
    this.details = body.details ?? {};
    this.path = path;
  }

  get isNotFound(): boolean {
    return this.status === 404;
  }
}

export type QueryParams = Record<string, string | number | boolean | null | undefined>;

export function buildUrl(path: string, params?: QueryParams): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const qs = search.toString();
  return `${API_BASE_URL}${API_PREFIX}${path}${qs ? `?${qs}` : ""}`;
}

export async function apiGet<T>(path: string, params?: QueryParams, signal?: AbortSignal): Promise<T> {
  const url = buildUrl(path, params);
  let response: Response;
  try {
    response = await fetch(url, { headers: { Accept: "application/json" }, signal });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw new ApiError(0, { code: "NETWORK_ERROR", message: `Could not reach the SAFAR API (${url}).` }, path);
  }

  if (!response.ok) {
    let body: Partial<ErrorBody> = {};
    try {
      const json: unknown = await response.json();
      if (json && typeof json === "object" && "error" in json) {
        body = (json as { error: Partial<ErrorBody> }).error;
      } else if (json && typeof json === "object" && "detail" in json) {
        // FastAPI's default envelope, in case a handler bypasses the custom one.
        body = { code: `HTTP_${response.status}`, message: JSON.stringify((json as { detail: unknown }).detail) };
      }
    } catch {
      /* non-JSON error page (e.g. proxy 502) */
    }
    body.request_id ??= response.headers.get("x-request-id");
    throw new ApiError(response.status, body, path);
  }

  return (await response.json()) as T;
}

/** Absolute URL of a same-origin, non-/api/v1 resource (e.g. `/docs`). */
export function rootUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}
