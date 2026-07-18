/**
 * Typed Athena API client (SPEC-08). Every call returns the unwrapped
 * `data` from the standard envelope, or throws a typed `ApiRequestError`.
 *
 * Features:
 *  - JWT bearer auth from the in-memory token store
 *  - transparent refresh-token rotation on 401 (single-flight)
 *  - retry with backoff for transient network/5xx errors
 *  - X-Request-ID surfaced on errors for backend log correlation
 */
import type { Envelope, TokenResponse } from "@/types/api";
import { tokenStore } from "./tokens";

const BASE = "/api/v1";
const MAX_RETRIES = 2;

export class ApiRequestError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public requestId?: string,
  ) {
    super(message);
    this.name = "ApiRequestError";
  }
}

export interface RequestOptions {
  method?: string;
  body?: unknown;
  signal?: AbortSignal;
  /** skip the auth header (login/refresh) */
  anonymous?: boolean;
  /** skip the 401→refresh retry (used by refresh itself) */
  noRefresh?: boolean;
}

let refreshInFlight: Promise<boolean> | null = null;

async function doRefresh(): Promise<boolean> {
  const refresh = tokenStore.getRefresh();
  if (!refresh) return false;
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      try {
        const res = await fetch(`${BASE}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refresh }),
        });
        if (!res.ok) return false;
        const env = (await res.json()) as Envelope<TokenResponse>;
        if (env.status !== "ok" || !env.data) return false;
        tokenStore.setAccess(env.data.access_token);
        tokenStore.setRefresh(env.data.refresh_token);
        return true;
      } catch {
        return false;
      } finally {
        refreshInFlight = null;
      }
    })();
  }
  return refreshInFlight;
}

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

export async function apiRequest<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const method = opts.method ?? "GET";
  let attempt = 0;

  while (true) {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    const access = tokenStore.getAccess();
    if (!opts.anonymous && access) headers["Authorization"] = `Bearer ${access}`;

    let res: Response;
    try {
      res = await fetch(`${BASE}${path}`, {
        method,
        headers,
        body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
        signal: opts.signal,
      });
    } catch (err) {
      // network error: retry with backoff
      if (attempt < MAX_RETRIES) {
        await sleep(2 ** attempt * 250);
        attempt += 1;
        continue;
      }
      throw new ApiRequestError(0, "NetworkError", (err as Error).message);
    }

    // transparent refresh on 401
    if (res.status === 401 && !opts.anonymous && !opts.noRefresh) {
      const ok = await doRefresh();
      if (ok) {
        opts.noRefresh = true; // only try once
        continue;
      }
    }

    // retry transient 5xx
    if (res.status >= 500 && attempt < MAX_RETRIES) {
      await sleep(2 ** attempt * 250);
      attempt += 1;
      continue;
    }

    const requestId = res.headers.get("X-Request-ID") ?? undefined;

    if (res.status === 204) return undefined as T;

    let env: Envelope<T>;
    try {
      env = (await res.json()) as Envelope<T>;
    } catch {
      throw new ApiRequestError(res.status, "InvalidResponse", "Malformed response", requestId);
    }

    if (!res.ok || env.status === "error") {
      const first = env.errors?.[0];
      throw new ApiRequestError(
        res.status,
        first?.code ?? "Error",
        first?.detail ?? res.statusText,
        env.request_id ?? requestId,
      );
    }
    return env.data as T;
  }
}
