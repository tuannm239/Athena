/**
 * Client-side analysis helpers (Phase 8). Real, pure computations that power
 * the Probability, Backtest and Scenario workspaces — no server round-trip and
 * no mock: given inputs, these produce genuine results. Kept pure so they are
 * unit-tested. Decision-making stays with the human; these are analysis aids.
 */

// --- Bayesian probability (Probability workspace) ---

export interface EvidenceLikelihood {
  label: string;
  /** P(evidence | hypothesis true), 0..1 */
  ifTrue: number;
  /** P(evidence | hypothesis false), 0..1 */
  ifFalse: number;
}

export interface PosteriorStep {
  label: string;
  likelihoodRatio: number;
  posterior: number;
}

/** Sequentially update a prior by each evidence item's likelihood ratio. */
export function bayesianUpdate(prior: number, evidence: EvidenceLikelihood[]): PosteriorStep[] {
  const p0 = clamp01(prior);
  let odds = p0 <= 0 ? 0 : p0 >= 1 ? Infinity : p0 / (1 - p0);
  const steps: PosteriorStep[] = [];
  for (const e of evidence) {
    const lr = e.ifFalse <= 0 ? Infinity : e.ifTrue / e.ifFalse;
    odds = odds * lr;
    const posterior = odds === Infinity ? 1 : odds / (1 + odds);
    steps.push({ label: e.label, likelihoodRatio: lr, posterior });
  }
  return steps;
}

export function clamp01(x: number): number {
  return Math.max(0, Math.min(1, Number.isFinite(x) ? x : 0));
}

// --- Backtest (Backtest workspace) ---

export interface BacktestResult {
  equity: number[]; // normalized to start = 1
  totalReturn: number;
  cagr: number;
  maxDrawdown: number; // negative fraction
  volatility: number; // stddev of period returns
  periods: number;
}

/**
 * Buy-and-hold backtest of a price series (long-only, no leverage — matching
 * the VN edition). Returns an equity curve normalized to 1 plus summary stats.
 */
export function backtestBuyHold(prices: number[], periodsPerYear = 252): BacktestResult {
  const clean = prices.filter((p) => Number.isFinite(p) && p > 0);
  if (clean.length < 2) {
    return { equity: [1], totalReturn: 0, cagr: 0, maxDrawdown: 0, volatility: 0, periods: clean.length };
  }
  const base = clean[0];
  const equity = clean.map((p) => p / base);
  const rets: number[] = [];
  for (let i = 1; i < clean.length; i++) rets.push(clean[i] / clean[i - 1] - 1);

  const totalReturn = equity[equity.length - 1] - 1;
  const years = (clean.length - 1) / periodsPerYear;
  const cagr = years > 0 ? Math.pow(1 + totalReturn, 1 / years) - 1 : totalReturn;

  let peak = equity[0];
  let maxDd = 0;
  for (const e of equity) {
    if (e > peak) peak = e;
    const dd = e / peak - 1;
    if (dd < maxDd) maxDd = dd;
  }

  const mean = rets.reduce((a, b) => a + b, 0) / rets.length;
  const variance = rets.reduce((a, b) => a + (b - mean) ** 2, 0) / rets.length;
  const volatility = Math.sqrt(variance) * Math.sqrt(periodsPerYear);

  return { equity, totalReturn, cagr, maxDrawdown: maxDd, volatility, periods: clean.length };
}

// --- Scenario what-if (Scenario workspace) ---

export interface ScenarioInput {
  /** Current portfolio market value. */
  marketValue: number;
  /** Shock applied to the whole portfolio, e.g. -0.1 for −10%. */
  marketShock: number;
  /** Optional cash held (unaffected by the shock). */
  cash?: number;
}

export interface ScenarioResult {
  before: number;
  after: number;
  change: number;
  changePct: number;
}

/** Apply a market shock to the equity portion; cash is preserved. */
export function scenarioImpact(input: ScenarioInput): ScenarioResult {
  const cash = input.cash ?? 0;
  const before = input.marketValue + cash;
  const equityAfter = input.marketValue * (1 + input.marketShock);
  const after = equityAfter + cash;
  const change = after - before;
  return { before, after, change, changePct: before > 0 ? change / before : 0 };
}

/** A deterministic sample price path (labelled sample where no live feed). */
export function samplePriceSeries(start = 25_000, n = 120, seed = 7): number[] {
  const out: number[] = [];
  let price = start;
  let s = seed;
  for (let i = 0; i < n; i++) {
    // simple LCG for a reproducible pseudo-random walk with slight upward drift
    s = (s * 1103515245 + 12345) & 0x7fffffff;
    const shock = (s / 0x7fffffff - 0.48) * 0.03;
    price = Math.max(1000, price * (1 + shock));
    out.push(Math.round(price));
  }
  return out;
}
