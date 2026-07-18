import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiRequest, ApiRequestError } from "@/lib/api-client";
import { tokenStore } from "@/lib/tokens";

function envelope<T>(data: T, status: "ok" | "error" = "ok", errors: unknown = null) {
  return {
    ok: status === "ok",
    status: 200,
    headers: new Headers({ "X-Request-ID": "req-1" }),
    json: async () => ({ request_id: "req-1", timestamp: "", status, data, errors }),
  } as unknown as Response;
}

describe("api-client", () => {
  beforeEach(() => {
    tokenStore.clear();
    vi.restoreAllMocks();
  });
  afterEach(() => vi.restoreAllMocks());

  it("unwraps the envelope data", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => envelope({ hello: "world" })));
    const data = await apiRequest<{ hello: string }>("/x");
    expect(data).toEqual({ hello: "world" });
  });

  it("attaches the bearer token when present", async () => {
    tokenStore.setAccess("tok-123");
    const fetchMock = vi.fn(async () => envelope({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);
    await apiRequest("/secure");
    const headers = fetchMock.mock.calls[0][1].headers as Record<string, string>;
    expect(headers["Authorization"]).toBe("Bearer tok-123");
  });

  it("omits the bearer token for anonymous calls", async () => {
    tokenStore.setAccess("tok-123");
    const fetchMock = vi.fn(async () => envelope({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);
    await apiRequest("/auth/login", { anonymous: true });
    const headers = fetchMock.mock.calls[0][1].headers as Record<string, string>;
    expect(headers["Authorization"]).toBeUndefined();
  });

  it("throws a typed ApiRequestError on error envelope", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: false,
        status: 422,
        headers: new Headers(),
        json: async () => ({
          request_id: "r",
          timestamp: "",
          status: "error",
          data: null,
          errors: [{ code: "BusinessRuleViolation", detail: "bad" }],
        }),
      })) as unknown as typeof fetch,
    );
    await expect(apiRequest("/x")).rejects.toMatchObject({
      status: 422,
      code: "BusinessRuleViolation",
    });
  });

  it("refreshes the access token on 401 then retries", async () => {
    tokenStore.setAccess("expired");
    tokenStore.setRefresh("refresh-token");
    let call = 0;
    const fetchMock = vi.fn(async (url: string) => {
      call += 1;
      if (url.endsWith("/auth/refresh")) {
        return envelope({ access_token: "new", refresh_token: "new-r", token_type: "bearer" });
      }
      if (call === 1) {
        return { ok: false, status: 401, headers: new Headers(), json: async () => ({ status: "error", errors: [] }) } as unknown as Response;
      }
      return envelope({ done: true });
    });
    vi.stubGlobal("fetch", fetchMock);
    const data = await apiRequest<{ done: boolean }>("/protected");
    expect(data).toEqual({ done: true });
    expect(tokenStore.getAccess()).toBe("new");
  });

  it("does not throw for 204 no-content", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: true, status: 204, headers: new Headers(), json: async () => ({}) })) as unknown as typeof fetch,
    );
    await expect(apiRequest("/x", { method: "DELETE" })).resolves.toBeUndefined();
  });

  it("surfaces network errors as ApiRequestError", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new Error("offline"); }));
    await expect(apiRequest("/x")).rejects.toBeInstanceOf(ApiRequestError);
  });
});
