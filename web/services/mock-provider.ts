/**
 * MockProvider — isolates temporary mock data for backend endpoints that
 * are not yet implemented (they return 501 until their engine/data lands,
 * e.g. /market, /companies/{t}/factors, /backtests).
 *
 * Contract (per the web-app directive): a service tries the real endpoint
 * first; on a 501 "NotImplemented" it transparently falls back to the mock
 * and flags `mocked: true` so the UI can show a "sample data" badge. When
 * the backend endpoint goes live, the real path succeeds and the mock is
 * never used — no code change required, the fallback simply stops firing.
 */
import { ApiRequestError } from "@/lib/api-client";

export interface Sourced<T> {
  data: T;
  mocked: boolean;
}

/** Run a real fetch; on 501 (NotImplemented) fall back to the mock. */
export async function withMockFallback<T>(
  real: () => Promise<T>,
  mock: () => T,
): Promise<Sourced<T>> {
  try {
    const data = await real();
    return { data, mocked: false };
  } catch (err) {
    if (err instanceof ApiRequestError && (err.status === 501 || err.code === "NotImplemented")) {
      return { data: mock(), mocked: true };
    }
    throw err;
  }
}
