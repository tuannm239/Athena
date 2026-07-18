import { defineConfig, devices } from "@playwright/test";

/**
 * E2E config. Uses the pre-installed Chromium (PLAYWRIGHT_BROWSERS_PATH).
 * `webServer` builds+starts the production app; tests run against it with
 * the backend stubbed at the network layer inside each test where needed.
 */
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: "http://localhost:3100",
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "pnpm start -p 3100",
    url: "http://localhost:3100/login",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
