import { create } from "zustand";
import { authService } from "@/services/auth";
import { apiRequest } from "@/lib/api-client";
import { tokenStore } from "@/lib/tokens";
import type { Role, UserResponse } from "@/types/api";

interface AuthState {
  user: UserResponse | null;
  status: "loading" | "authenticated" | "anonymous";
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  bootstrap: () => Promise<void>;
  hasRole: (...roles: Role[]) => boolean;
}

/** Decode a JWT payload without verifying (client-side display only). */
function decodeJwt(token: string): Record<string, unknown> | null {
  try {
    const [, payload] = token.split(".");
    return JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/")));
  } catch {
    return null;
  }
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  status: "loading",

  login: async (email, password) => {
    const tokens = await authService.login(email, password);
    tokenStore.setAccess(tokens.access_token);
    tokenStore.setRefresh(tokens.refresh_token);
    // The /auth/me endpoint is not in the current backend; derive identity
    // from the login response + JWT claims. Role is refined server-side on
    // each request (RBAC is enforced by the backend, not the client).
    const claims = decodeJwt(tokens.access_token);
    set({
      status: "authenticated",
      user: {
        id: String(claims?.sub ?? ""),
        email,
        status: "active",
        role: (claims?.role as Role) ?? "ANALYST",
        created_at: new Date().toISOString(),
      },
    });
  },

  logout: () => {
    tokenStore.clear();
    set({ user: null, status: "anonymous" });
  },

  bootstrap: async () => {
    const refresh = tokenStore.getRefresh();
    if (!refresh) {
      set({ status: "anonymous" });
      return;
    }
    try {
      // exchange the stored refresh token for a fresh access token
      const tokens = await apiRequest<{ access_token: string; refresh_token: string }>(
        "/auth/refresh",
        { method: "POST", body: { refresh_token: refresh }, anonymous: true },
      );
      tokenStore.setAccess(tokens.access_token);
      tokenStore.setRefresh(tokens.refresh_token);
      const claims = decodeJwt(tokens.access_token);
      set({
        status: "authenticated",
        user: {
          id: String(claims?.sub ?? ""),
          email: get().user?.email ?? "",
          status: "active",
          role: (claims?.role as Role) ?? "ANALYST",
          created_at: new Date().toISOString(),
        },
      });
    } catch {
      tokenStore.clear();
      set({ status: "anonymous", user: null });
    }
  },

  hasRole: (...roles) => {
    const u = get().user;
    return !!u && roles.includes(u.role);
  },
}));
