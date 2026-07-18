import { apiRequest } from "@/lib/api-client";
import type { CompanyResponse, MarketContextResponse } from "@/types/api";
import { withMockFallback, type Sourced } from "./mock-provider";

/**
 * Market data endpoints are 501 until real data feeds land (R1 / RFC-0024).
 * Each call tries the real endpoint and falls back to clearly-labelled
 * sample data via the MockProvider; the fallback stops firing automatically
 * once the backend serves the endpoint.
 */
export const marketService = {
  context: (): Promise<Sourced<MarketContextResponse>> =>
    withMockFallback(
      () => apiRequest<MarketContextResponse>("/market/context"),
      () => ({
        regime: "EXPANSION",
        confidence: "0.72",
        liquidity_score: "68",
        breadth_score: "61",
        volatility_score: "34",
        rotation_score: "55",
        timestamp: new Date().toISOString(),
      }),
    ),
};

export const companiesService = {
  get: (ticker: string): Promise<Sourced<CompanyResponse>> =>
    withMockFallback(
      () => apiRequest<CompanyResponse>(`/companies/${ticker}`),
      () => ({
        id: "00000000-0000-0000-0000-000000000000",
        ticker: ticker.toUpperCase(),
        name: `${ticker.toUpperCase()} (sample)`,
        exchange: "HOSE",
        sector: "Financials",
        industry: "Banks",
        currency: "VND",
        status: "active",
        created_at: new Date().toISOString(),
      }),
    ),
};
