import { afterEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement, type ReactNode } from "react";
import { useDecisions, useMarketContext, useHealth, useCompany } from "@/hooks/queries";

function ok<T>(data: T) {
  return {
    ok: true, status: 200, headers: new Headers(),
    json: async () => ({ status: "ok", data, request_id: "r", timestamp: "", errors: null }),
  } as unknown as Response;
}

function wrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, children);
}

describe("query hooks", () => {
  afterEach(() => vi.restoreAllMocks());

  it("useDecisions fetches a page", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ok({ items: [{ id: "1" }], total: 1, limit: 20, offset: 0 })));
    const { result } = renderHook(() => useDecisions(), { wrapper: wrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.total).toBe(1);
  });

  it("useMarketContext returns a Sourced result", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ok({
      regime: "EXPANSION", confidence: "0.7", liquidity_score: "1",
      breadth_score: "1", volatility_score: "1", rotation_score: "1", timestamp: "",
    })));
    const { result } = renderHook(() => useMarketContext(), { wrapper: wrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.data.regime).toBe("EXPANSION");
    expect(result.current.data?.mocked).toBe(false);
  });

  it("useHealth polls the raw health endpoint", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: true, status: 200, json: async () => ({ status: "ok", version: "1", components: {} }),
    }) as unknown as Response));
    const { result } = renderHook(() => useHealth(), { wrapper: wrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.status).toBe("ok");
  });

  it("useCompany is disabled without a ticker", () => {
    const { result } = renderHook(() => useCompany(""), { wrapper: wrapper() });
    expect(result.current.fetchStatus).toBe("idle");
  });
});

describe("more query hooks", () => {
  afterEach(() => vi.restoreAllMocks());
  it("useDecision, usePortfolios and useReviewDecision", async () => {
    const { useDecision, usePortfolios, useReviewDecision } = await import("@/hooks/queries");
    vi.stubGlobal("fetch", vi.fn(async () => ok({ items: [], id: "1", status: "APPROVED" })));
    const w = wrapper();
    const d = renderHook(() => useDecision("1"), { wrapper: w });
    await waitFor(() => expect(d.result.current.isSuccess).toBe(true));
    const p = renderHook(() => usePortfolios(), { wrapper: w });
    await waitFor(() => expect(p.result.current.isSuccess).toBe(true));
    const r = renderHook(() => useReviewDecision("1"), { wrapper: w });
    expect(typeof r.result.current.mutate).toBe("function");
  });
});
