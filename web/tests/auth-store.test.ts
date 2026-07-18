import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAuthStore } from "@/stores/auth-store";
import { tokenStore } from "@/lib/tokens";

// a JWT with role ADMIN in the payload (unsigned; client only decodes)
function jwt(payload: Record<string, unknown>) {
  const b64 = (o: unknown) => Buffer.from(JSON.stringify(o)).toString("base64url");
  return `${b64({ alg: "HS256" })}.${b64(payload)}.sig`;
}

describe("auth store", () => {
  beforeEach(() => {
    tokenStore.clear();
    useAuthStore.setState({ user: null, status: "loading" });
    vi.restoreAllMocks();
  });

  it("login stores tokens and decodes role from the JWT", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true, status: 200, headers: new Headers(),
        json: async () => ({
          status: "ok", data: {
            access_token: jwt({ sub: "u1", role: "ADMIN" }),
            refresh_token: "r", token_type: "bearer",
          },
        }),
      })) as unknown as typeof fetch,
    );
    await useAuthStore.getState().login("a@x.com", "pw");
    const s = useAuthStore.getState();
    expect(s.status).toBe("authenticated");
    expect(s.user?.role).toBe("ADMIN");
    expect(tokenStore.getAccess()).toBeTruthy();
  });

  it("hasRole reflects the current user's role", () => {
    useAuthStore.setState({
      status: "authenticated",
      user: { id: "u", email: "a", status: "active", role: "VIEWER", created_at: "" },
    });
    expect(useAuthStore.getState().hasRole("ADMIN", "ANALYST")).toBe(false);
    expect(useAuthStore.getState().hasRole("VIEWER")).toBe(true);
  });

  it("logout clears tokens and user", () => {
    tokenStore.setAccess("x");
    useAuthStore.setState({
      status: "authenticated",
      user: { id: "u", email: "a", status: "active", role: "ADMIN", created_at: "" },
    });
    useAuthStore.getState().logout();
    expect(useAuthStore.getState().status).toBe("anonymous");
    expect(tokenStore.getAccess()).toBeNull();
  });

  it("bootstrap with no refresh token becomes anonymous", async () => {
    await useAuthStore.getState().bootstrap();
    expect(useAuthStore.getState().status).toBe("anonymous");
  });
});

describe("auth store bootstrap", () => {
  it("bootstrap exchanges a stored refresh token for a session", async () => {
    tokenStore.setRefresh("stored-refresh");
    useAuthStore.setState({ user: null, status: "loading" });
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true, status: 200, headers: new Headers(),
        json: async () => ({
          status: "ok",
          data: { access_token: jwt({ sub: "u2", role: "ANALYST" }), refresh_token: "r2", token_type: "bearer" },
        }),
      })) as unknown as typeof fetch,
    );
    await useAuthStore.getState().bootstrap();
    expect(useAuthStore.getState().status).toBe("authenticated");
    expect(useAuthStore.getState().user?.role).toBe("ANALYST");
  });

  it("bootstrap clears state when refresh fails", async () => {
    tokenStore.setRefresh("bad");
    useAuthStore.setState({ user: null, status: "loading" });
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: false, status: 401, headers: new Headers(),
        json: async () => ({ status: "error", errors: [{ code: "Unauthorized", detail: "x" }] }),
      })) as unknown as typeof fetch,
    );
    await useAuthStore.getState().bootstrap();
    expect(useAuthStore.getState().status).toBe("anonymous");
  });
});
