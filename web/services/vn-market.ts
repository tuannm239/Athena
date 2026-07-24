/**
 * Vietnam market snapshot + fundamentals services (Phase 7). Each tries the
 * real endpoint and falls back to clearly-labelled VN sample data via the
 * MockProvider until the live feed lands — the same pattern used across the
 * app. No new backend contract is assumed; the fallback stops firing once the
 * endpoint serves data.
 */
import { apiRequest } from "@/lib/api-client";
import { withMockFallback, type Sourced } from "./mock-provider";
import type { VnFundamentals, VnMarketSnapshot } from "@/lib/vn";

/** An explicit *empty* snapshot — shown only if the backend is unreachable.
 *  Never sample values: the Market page and dashboard read persisted data or
 *  render an empty state (Phase (b): VnstockProvider → pipeline → API). */
function emptySnapshot(): VnMarketSnapshot {
  return {
    as_of: new Date().toISOString(),
    indices: [],
    breadth: { advancers: 0, decliners: 0, unchanged: 0 },
    sector_heatmap: [],
    foreign: { buy_value: 0, sell_value: 0, net_value: 0 },
    proprietary: { buy_value: 0, sell_value: 0, net_value: 0 },
    liquidity_value: 0,
    top_gainers: [],
    top_losers: [],
    top_volume: [],
    new_high: 0,
    new_low: 0,
  };
}

export const vnMarketService = {
  // Consume the real backend endpoint only. The backend returns real data from
  // the database (or an empty snapshot when nothing is synced), so there is no
  // sample fallback; on a transport error we still show an empty state, not
  // sample values.
  snapshot: async (): Promise<Sourced<VnMarketSnapshot>> => {
    try {
      const data = await apiRequest<VnMarketSnapshot>("/market/vn/snapshot");
      return { data, mocked: false };
    } catch {
      return { data: emptySnapshot(), mocked: false };
    }
  },
};

function sampleFundamentals(ticker: string): VnFundamentals {
  const t = ticker.toUpperCase();
  return {
    ticker: t,
    exchange: "HOSE",
    sector: "Materials",
    ratios: {
      roe: 0.171,
      roa: 0.082,
      gross_margin: 0.214,
      operating_margin: 0.163,
      net_margin: 0.128,
      debt_to_equity: 0.62,
      current_ratio: 1.42,
      free_cash_flow: 3_200_000_000_000,
      eps: 3_150,
      bvps: 18_400,
      pe: 8.7,
      pb: 1.49,
      ev_ebitda: 6.8,
    },
    quality_score: 78.5,
    valuation_score: 64.2,
    growth_score: 71.0,
    revenue_growth_yoy: 0.184,
    eps_growth_yoy: 0.093,
  };
}

export const vnFundamentalsService = {
  get: (ticker: string): Promise<Sourced<VnFundamentals>> =>
    withMockFallback(
      () => apiRequest<VnFundamentals>(`/companies/${ticker}/fundamentals`),
      () => sampleFundamentals(ticker),
    ),
};

export interface VnPricePoint {
  day: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number;
  volume: number | null;
}
export interface VnCompanyPrices {
  ticker: string;
  points: VnPricePoint[];
}

// Persisted daily closes for a company. No mock fallback — an empty series is
// honest (nothing synced yet), so the workspace never shows sample prices.
export const vnCompanyPricesService = {
  get: (ticker: string): Promise<VnCompanyPrices> =>
    apiRequest<VnCompanyPrices>(`/companies/${ticker}/prices`),
};
