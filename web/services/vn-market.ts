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

function sampleSnapshot(): VnMarketSnapshot {
  return {
    as_of: new Date().toISOString(),
    indices: [
      { code: "VNINDEX", value: 1284.56, change: 8.42, change_pct: 0.0066 },
      { code: "VN30", value: 1327.11, change: 11.03, change_pct: 0.0084 },
      { code: "HNXINDEX", value: 236.18, change: -0.44, change_pct: -0.0019 },
      { code: "HNX30", value: 512.7, change: 1.2, change_pct: 0.0023 },
      { code: "UPCOMINDEX", value: 94.31, change: 0.12, change_pct: 0.0013 },
    ],
    breadth: { advancers: 214, decliners: 168, unchanged: 61 },
    sector_heatmap: [
      { sector: "Financials", change_pct: 0.012 },
      { sector: "Real Estate", change_pct: -0.006 },
      { sector: "Industrials", change_pct: 0.004 },
      { sector: "Consumer Staples", change_pct: 0.008 },
      { sector: "Materials", change_pct: 0.017 },
      { sector: "Information Technology", change_pct: 0.021 },
      { sector: "Utilities", change_pct: -0.002 },
      { sector: "Energy", change_pct: -0.011 },
    ],
    foreign: { buy_value: 1_240_000_000_000, sell_value: 980_000_000_000, net_value: 260_000_000_000 },
    proprietary: {
      buy_value: 410_000_000_000,
      sell_value: 470_000_000_000,
      net_value: -60_000_000_000,
    },
    liquidity_value: 18_600_000_000_000,
    top_gainers: [
      { ticker: "HPG", price: 27_500, change_pct: 0.069, volume: 21_400_000 },
      { ticker: "SSI", price: 34_200, change_pct: 0.055, volume: 15_100_000 },
      { ticker: "FPT", price: 138_400, change_pct: 0.041, volume: 4_900_000 },
    ],
    top_losers: [
      { ticker: "NVL", price: 11_050, change_pct: -0.062, volume: 18_800_000 },
      { ticker: "PDR", price: 21_300, change_pct: -0.043, volume: 9_600_000 },
      { ticker: "GEX", price: 19_950, change_pct: -0.031, volume: 7_200_000 },
    ],
    top_volume: [
      { ticker: "HPG", price: 27_500, change_pct: 0.069, volume: 21_400_000 },
      { ticker: "NVL", price: 11_050, change_pct: -0.062, volume: 18_800_000 },
      { ticker: "STB", price: 33_700, change_pct: 0.018, volume: 16_500_000 },
    ],
    new_high: 42,
    new_low: 13,
  };
}

export const vnMarketService = {
  snapshot: (): Promise<Sourced<VnMarketSnapshot>> =>
    withMockFallback(() => apiRequest<VnMarketSnapshot>("/market/vn/snapshot"), sampleSnapshot),
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
