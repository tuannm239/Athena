import { test, type Page } from "@playwright/test";
import { mkdirSync } from "node:fs";

/**
 * Screenshot catalog generator (Athena V1). Authenticates via a stubbed
 * refresh token and stubs the backend at the network layer so every page
 * renders hermetically, then captures a screenshot of each route into
 * tests/e2e/screenshots/. Run: pnpm exec playwright test screenshots
 */

const OUT = "tests/e2e/screenshots";
mkdirSync(OUT, { recursive: true });

function jwt(role = "ANALYST") {
  const header = Buffer.from('{"alg":"HS256"}').toString("base64url");
  const payload = Buffer.from(JSON.stringify({ sub: "u1", role })).toString("base64url");
  return `${header}.${payload}.sig`;
}

const ok = (data: unknown) => ({
  status: 200,
  contentType: "application/json",
  body: JSON.stringify({ request_id: "r", timestamp: "", status: "ok", data, errors: null }),
});
const notImpl = {
  status: 501,
  contentType: "application/json",
  body: JSON.stringify({ status: "error", errors: [{ code: "NotImplemented", detail: "x" }] }),
};

async function stub(page: Page) {
  await page.addInitScript(() => window.localStorage.setItem("athena.refresh", "refresh-token"));
  await page.route("**/api/v1/auth/refresh", (r) =>
    r.fulfill(ok({ access_token: jwt(), refresh_token: "refresh-token", token_type: "bearer" })),
  );
  await page.route("**/api/v1/auth/api-keys**", (r) => r.fulfill(ok([])));
  await page.route("**/api/v1/decisions**", (r) =>
    r.fulfill(ok({ items: [], total: 0, limit: 50, offset: 0 })),
  );
  await page.route("**/api/v1/portfolios**", (r) =>
    r.fulfill(ok({ items: [], total: 0, limit: 20, offset: 0 })),
  );
  await page.route("**/api/v1/companies/**", (r) => r.fulfill(notImpl));
  await page.route("**/api/v1/market/**", (r) => r.fulfill(notImpl));
  await page.route("**/api/health/full", (r) =>
    r.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ status: "ok", version: "1", components: { database: "ok" } }),
    }),
  );
}

const ROUTES: [string, string][] = [
  ["login", "/login"],
  ["dashboard", "/"],
  ["market", "/market"],
  ["companies", "/companies"],
  ["company-workspace", "/companies/HPG"],
  ["research", "/research"],
  ["evidence", "/evidence"],
  ["decisions", "/decisions"],
  ["portfolio", "/portfolio"],
  ["watchlist", "/watchlist"],
  ["knowledge-graph", "/knowledge-graph"],
  ["probability", "/probability"],
  ["backtest", "/backtest"],
  ["scenario", "/scenario"],
  ["feature-store", "/feature-store"],
  ["reports", "/reports"],
  ["notifications", "/notifications"],
  ["settings", "/settings"],
  ["profile", "/profile"],
  ["help", "/help"],
  ["about", "/about"],
  ["feedback", "/feedback"],
  ["release-notes", "/release-notes"],
];

for (const [name, path] of ROUTES) {
  test(`screenshot: ${name}`, async ({ page }) => {
    await stub(page);
    await page.goto(path);
    // let auth bootstrap + first paint settle
    await page.waitForTimeout(1400);
    await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: true });
  });
}
