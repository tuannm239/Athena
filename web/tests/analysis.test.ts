import { describe, expect, it } from "vitest";
import { backtestBuyHold, bayesianUpdate, scenarioImpact } from "@/lib/analysis";

describe("bayesianUpdate", () => {
  it("raises the posterior for confirming evidence", () => {
    const steps = bayesianUpdate(0.5, [{ label: "beat", ifTrue: 0.8, ifFalse: 0.2 }]);
    expect(steps[0].likelihoodRatio).toBeCloseTo(4);
    expect(steps[0].posterior).toBeCloseTo(0.8);
  });

  it("lowers the posterior for disconfirming evidence and chains", () => {
    const steps = bayesianUpdate(0.5, [
      { label: "up", ifTrue: 0.9, ifFalse: 0.3 },
      { label: "down", ifTrue: 0.2, ifFalse: 0.8 },
    ]);
    expect(steps[1].posterior).toBeLessThan(steps[0].posterior);
  });
});

describe("backtestBuyHold", () => {
  it("computes total return and drawdown on a known path", () => {
    const r = backtestBuyHold([100, 110, 99, 120], 252);
    expect(r.totalReturn).toBeCloseTo(0.2);
    expect(r.equity[0]).toBe(1);
    expect(r.maxDrawdown).toBeLessThan(0); // saw a dip to 99
  });

  it("is safe on degenerate input", () => {
    const r = backtestBuyHold([100]);
    expect(r.totalReturn).toBe(0);
  });
});

describe("scenarioImpact", () => {
  it("shocks equity but preserves cash", () => {
    const r = scenarioImpact({ marketValue: 1_000_000, marketShock: -0.1, cash: 200_000 });
    expect(r.after).toBe(900_000 + 200_000);
    expect(r.change).toBe(-100_000);
    expect(r.changePct).toBeCloseTo(-100_000 / 1_200_000);
  });
});
