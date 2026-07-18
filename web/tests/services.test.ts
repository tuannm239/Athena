import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { decisionsService } from "@/services/decisions";
import { portfolioService } from "@/services/portfolio";
import { marketService, companiesService } from "@/services/market";
import { opsService } from "@/services/ops";
import { authService } from "@/services/auth";
import { tokenStore } from "@/lib/tokens";

function ok<T>(data: T) {
  return {
    ok: true, status: 200, headers: new Headers(),
    json: async () => ({ status: "ok", data, request_id: "r", timestamp: "", errors: null }),
  } as unknown as Response;
}

describe("services", () => {
  beforeEach(() => { tokenStore.clear(); vi.restoreAllMocks(); });
  afterEach(() => vi.restoreAllMocks());

  it("decisions.list builds the query string", async () => {
    const fetchMock = vi.fn(async () => ok({ items: [], total: 0, limit: 20, offset: 0 }));
    vi.stubGlobal("fetch", fetchMock);
    await decisionsService.list({ limit: 10, offset: 5, status: "APPROVED" });
    const url = fetchMock.mock.calls[0][0] as string;
    expect(url).toContain("limit=10");
    expect(url).toContain("offset=5");
    expect(url).toContain("status=APPROVED");
  });

  it("decisions.review sends a PATCH with status + note", async () => {
    const fetchMock = vi.fn(async () => ok({ id: "1" }));
    vi.stubGlobal("fetch", fetchMock);
    await decisionsService.review("1", "APPROVED", "looks good");
    const init = fetchMock.mock.calls[0][1];
    expect(init.method).toBe("PATCH");
    expect(JSON.parse(init.body)).toMatchObject({ status: "APPROVED", review_note: "looks good" });
  });

  it("decisions.create/get/update hit the right paths", async () => {
    const fetchMock = vi.fn(async () => ok({ id: "1" }));
    vi.stubGlobal("fetch", fetchMock);
    await decisionsService.get("1");
    await decisionsService.create({ hypothesis: "h", probability: 0.5, confidence: 0.5 });
    await decisionsService.update("1", { review_note: "x" });
    expect((fetchMock.mock.calls[0][0] as string)).toContain("/decisions/1");
    expect(fetchMock.mock.calls[1][1].method).toBe("POST");
    expect(fetchMock.mock.calls[2][1].method).toBe("PATCH");
  });

  it("portfolio.list and get", async () => {
    const fetchMock = vi.fn(async () => ok({ items: [] }));
    vi.stubGlobal("fetch", fetchMock);
    await portfolioService.list();
    await portfolioService.get("p1");
    expect((fetchMock.mock.calls[1][0] as string)).toContain("/portfolios/p1");
  });

  it("market.context falls back to mock on 501", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: false, status: 501, headers: new Headers(),
      json: async () => ({ status: "error", errors: [{ code: "NotImplemented", detail: "x" }] }),
    }) as unknown as Response);
    vi.stubGlobal("fetch", fetchMock);
    const res = await marketService.context();
    expect(res.mocked).toBe(true);
    expect(res.data.regime).toBeTruthy();
  });

  it("companies.get returns real data when available (mocked:false)", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ok({
      id: "1", ticker: "VNM", name: "Vinamilk", exchange: "HOSE",
      sector: "ConsumerStaples", industry: "Dairy", currency: "VND", status: "active", created_at: "",
    })));
    const res = await companiesService.get("vnm");
    expect(res.mocked).toBe(false);
    expect(res.data.ticker).toBe("VNM");
  });

  it("ops.health fetches the raw health endpoint", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: true, status: 200, json: async () => ({ status: "ok", version: "1", components: {} }),
    }) as unknown as Response));
    const h = await opsService.health();
    expect(h.status).toBe("ok");
  });

  it("ops.health throws on non-ok", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: false, status: 503 }) as unknown as Response));
    await expect(opsService.health()).rejects.toThrow();
  });

  it("auth.login/register/api-keys", async () => {
    const fetchMock = vi.fn(async () => ok({ access_token: "a", refresh_token: "r", token_type: "bearer" }));
    vi.stubGlobal("fetch", fetchMock);
    await authService.login("a@x.com", "pw");
    await authService.register("a@x.com", "pw");
    await authService.listApiKeys();
    await authService.createApiKey("ci");
    await authService.revokeApiKey("k1");
    expect(fetchMock).toHaveBeenCalledTimes(5);
  });
});
