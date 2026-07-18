import { expect, test } from "@playwright/test";

/**
 * E2E: unauthenticated access is redirected to /login, and a stubbed
 * login flow reaches the dashboard. The backend is intercepted at the
 * network layer so the test is hermetic (no live backend required).
 */

test("unauthenticated user is redirected to login", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/login/);
  await expect(page.getByRole("button", { name: /sign in/i })).toBeVisible();
});

test("login flow reaches the dashboard", async ({ page }) => {
  // a fake JWT with an ANALYST role claim
  const payload = Buffer.from(JSON.stringify({ sub: "u1", role: "ANALYST" })).toString("base64url");
  const jwt = `${Buffer.from('{"alg":"HS256"}').toString("base64url")}.${payload}.sig`;

  await page.route("**/api/v1/auth/login", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        request_id: "r", timestamp: "", status: "ok",
        data: { access_token: jwt, refresh_token: "refresh", token_type: "bearer" },
      }),
    }),
  );
  // stub the dashboard's data calls so it renders without a backend
  await page.route("**/api/v1/decisions**", (route) =>
    route.fulfill({
      status: 200, contentType: "application/json",
      body: JSON.stringify({ request_id: "r", timestamp: "", status: "ok", data: { items: [], total: 0, limit: 5, offset: 0 } }),
    }),
  );
  await page.route("**/api/v1/market/context", (route) => route.fulfill({ status: 501, contentType: "application/json", body: JSON.stringify({ status: "error", errors: [{ code: "NotImplemented", detail: "x" }] }) }));
  await page.route("**/api/health/full", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "ok", version: "1", components: {} }) }));

  await page.goto("/login");
  await page.getByLabel("Email").fill("analyst@example.com");
  await page.getByLabel("Password").fill("s3cret-pass");
  await page.getByRole("button", { name: /sign in/i }).click();

  await expect(page).toHaveURL(/\/$|\/dashboard/);
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
});
