/**
 * Vietnam market reference + types (Phase 7). Mirrors the backend
 * `market.domain.vietnam` reference so the UI speaks the same VN vocabulary
 * (exchanges, indices, sectors). Athena VN Edition is optimized exclusively
 * for the Vietnamese market — long-term investing, no derivatives, no margin.
 */

export const VN_EXCHANGES = ["HOSE", "HNX", "UPCOM"] as const;
export type VnExchange = (typeof VN_EXCHANGES)[number];

export const VN_INDICES = ["VNINDEX", "VN30", "HNXINDEX", "HNX30", "UPCOMINDEX"] as const;
export type VnIndexCode = (typeof VN_INDICES)[number];

export const VN_SECTORS = [
  "Financials",
  "Real Estate",
  "Industrials",
  "Consumer Staples",
  "Consumer Discretionary",
  "Materials",
  "Energy",
  "Utilities",
  "Health Care",
  "Information Technology",
  "Communication Services",
] as const;
export type VnSector = (typeof VN_SECTORS)[number];

/** Daily price-limit band per exchange (matches the backend). */
export const VN_PRICE_LIMIT: Record<VnExchange, number> = {
  HOSE: 0.07,
  HNX: 0.1,
  UPCOM: 0.15,
};

export interface IndexQuote {
  code: VnIndexCode | string;
  value: number;
  change: number;
  change_pct: number;
}

export interface MoverQuote {
  ticker: string;
  price: number;
  change_pct: number;
  volume: number;
}

export interface SectorPerf {
  sector: VnSector | string;
  change_pct: number;
}

export interface FlowSummary {
  buy_value: number; // VND
  sell_value: number;
  net_value: number;
}

export interface VnMarketSnapshot {
  as_of: string;
  indices: IndexQuote[];
  breadth: { advancers: number; decliners: number; unchanged: number };
  sector_heatmap: SectorPerf[];
  foreign: FlowSummary;
  proprietary: FlowSummary;
  liquidity_value: number; // total matched value, VND
  top_gainers: MoverQuote[];
  top_losers: MoverQuote[];
  top_volume: MoverQuote[];
  new_high: number;
  new_low: number;
}

// --- fundamentals (mirrors backend company.domain.fundamentals) ---
export interface VnRatios {
  roe: number | null;
  roa: number | null;
  gross_margin: number | null;
  operating_margin: number | null;
  net_margin: number | null;
  debt_to_equity: number | null;
  current_ratio: number | null;
  free_cash_flow: number | null;
  eps: number | null;
  bvps: number | null;
  pe: number | null;
  pb: number | null;
  ev_ebitda: number | null;
}

export interface VnFundamentals {
  ticker: string;
  exchange: VnExchange | string;
  sector: VnSector | string;
  ratios: VnRatios;
  quality_score: number | null;
  valuation_score: number | null;
  growth_score: number | null;
  revenue_growth_yoy: number | null;
  eps_growth_yoy: number | null;
}

/** Format a VND amount compactly (₫, tỷ = billion, tr = million). */
export function vnd(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const abs = Math.abs(value);
  if (abs >= 1e9) return `${(value / 1e9).toFixed(1)} tỷ ₫`;
  if (abs >= 1e6) return `${(value / 1e6).toFixed(1)} tr ₫`;
  return `${value.toLocaleString("vi-VN")} ₫`;
}

/** Format a ratio that is stored as a fraction (0.15) into a percent string. */
export function ratioPct(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

// --- watchlist corporate calendar (Phase 7, WS7) ---
export type EventKind = "quarterly" | "annual" | "agm" | "dividend";

export interface CorporateEvent {
  ticker: string;
  kind: EventKind;
  label: string;
  date: string; // ISO date
}

export const EVENT_LABELS: Record<EventKind, string> = {
  quarterly: "Quarterly report",
  annual: "Annual report",
  agm: "AGM",
  dividend: "Dividend",
};

/**
 * Upcoming VN corporate-calendar events for a ticker, relative to `from`.
 * A transparent, rules-based schedule (VN filing cadence) until a live
 * corporate-actions feed is connected — clearly a projection, not a promise.
 */
export function upcomingEvents(ticker: string, from = new Date()): CorporateEvent[] {
  const y = from.getUTCFullYear();
  const iso = (mo: number, day: number, yr = y) =>
    new Date(Date.UTC(yr, mo, day)).toISOString().slice(0, 10);
  // VN quarterly filing deadlines ~30 days after quarter-end; annual ~90 days;
  // AGM season Mar–Jun; dividends commonly mid-year.
  const candidates: CorporateEvent[] = [
    { ticker, kind: "quarterly", label: "Q1 report", date: iso(3, 30) },
    { ticker, kind: "quarterly", label: "Q2 report", date: iso(6, 30) },
    { ticker, kind: "quarterly", label: "Q3 report", date: iso(9, 30) },
    { ticker, kind: "annual", label: "Annual report", date: iso(2, 31, y + 1) },
    { ticker, kind: "agm", label: "Annual General Meeting", date: iso(3, 25) },
    { ticker, kind: "dividend", label: "Dividend record date", date: iso(6, 15) },
  ];
  const today = from.toISOString().slice(0, 10);
  return candidates
    .filter((e) => e.date >= today)
    .sort((a, b) => a.date.localeCompare(b.date));
}
