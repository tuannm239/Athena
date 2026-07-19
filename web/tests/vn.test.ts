import { describe, expect, it } from "vitest";
import { ratioPct, upcomingEvents, vnd, VN_PRICE_LIMIT } from "@/lib/vn";

describe("vn formatting", () => {
  it("formats VND compactly", () => {
    expect(vnd(2_500_000_000)).toBe("2.5 tỷ ₫");
    expect(vnd(3_400_000)).toBe("3.4 tr ₫");
    expect(vnd(null)).toBe("—");
  });

  it("formats fraction ratios as percent", () => {
    expect(ratioPct(0.171)).toBe("17.1%");
    expect(ratioPct(null)).toBe("—");
  });

  it("encodes VN daily price limits", () => {
    expect(VN_PRICE_LIMIT.HOSE).toBe(0.07);
    expect(VN_PRICE_LIMIT.HNX).toBe(0.1);
    expect(VN_PRICE_LIMIT.UPCOM).toBe(0.15);
  });
});

describe("upcomingEvents", () => {
  it("returns only future events, sorted ascending", () => {
    const from = new Date(Date.UTC(2026, 0, 15)); // 2026-01-15
    const events = upcomingEvents("HPG", from);
    expect(events.length).toBeGreaterThan(0);
    for (const e of events) expect(e.date >= "2026-01-15").toBe(true);
    const dates = events.map((e) => e.date);
    expect(dates).toEqual([...dates].sort());
    expect(events.every((e) => e.ticker === "HPG")).toBe(true);
  });

  it("drops events already passed this year", () => {
    const from = new Date(Date.UTC(2026, 10, 1)); // Nov 1 — Q1/Q2/Q3/AGM/div passed
    const events = upcomingEvents("VCB", from);
    expect(events.every((e) => e.kind === "annual")).toBe(true);
  });
});
