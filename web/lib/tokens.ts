/**
 * Access/refresh token storage. Access token is kept in memory (XSS-safer);
 * the refresh token is persisted to localStorage so a reload can re-auth.
 * A production hardening (documented in the frontend ADRs) is to move the
 * refresh token to an httpOnly cookie once the backend sets one.
 */
const REFRESH_KEY = "athena.refresh";

let accessToken: string | null = null;

export const tokenStore = {
  getAccess: () => accessToken,
  setAccess: (t: string | null) => {
    accessToken = t;
  },
  getRefresh: (): string | null => {
    if (typeof window === "undefined") return null;
    return window.localStorage.getItem(REFRESH_KEY);
  },
  setRefresh: (t: string | null) => {
    if (typeof window === "undefined") return;
    if (t) window.localStorage.setItem(REFRESH_KEY, t);
    else window.localStorage.removeItem(REFRESH_KEY);
  },
  clear: () => {
    accessToken = null;
    if (typeof window !== "undefined") window.localStorage.removeItem(REFRESH_KEY);
  },
};
