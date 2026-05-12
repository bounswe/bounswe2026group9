import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright config for end-to-end acceptance tests.
 *
 * Test cases here map directly to the Lab 9 acceptance test catalog
 * (TC-WEB-ACC-06, TC-ACC-EVENT-CAPACITY-01, TC-ACC-EVT-LIFECYCLE-05, ...).
 *
 * Environment variables consumed:
 *   BASE_URL                — frontend URL under test          (default http://localhost:3000)
 *   API_BASE_URL            — backend URL for direct probes    (default http://localhost:8888)
 *   E2E_USER_EMAIL / E2E_USER_PASSWORD          — primary seeded registered user
 *   E2E_HOST_EMAIL  / E2E_HOST_PASSWORD         — host account used in capacity / lifecycle tests
 *   E2E_USER_A_EMAIL / E2E_USER_A_PASSWORD      — capacity test, joins event first
 *   E2E_USER_B_EMAIL / E2E_USER_B_PASSWORD      — capacity test, blocked by FULL
 *   E2E_EVENT_FULL_ID                           — id of seeded `attendeeLimit=2, going=1` event
 *   E2E_EVENT_FUTURE_ID                         — id of seeded future event for lifecycle edit
 *   E2E_EVENT_ONGOING_ID                        — id of seeded ongoing event for lifecycle lock
 *   E2E_EVENT_PRIVATE_ID                        — id of seeded private event the user does NOT host
 *
 * See e2e/README.md for the expected seed.
 */

const BASE_URL = process.env.BASE_URL ?? "http://localhost:3000";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false, // these tests mutate shared backend state
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [["list"], ["html", { outputFolder: "playwright-report", open: "never" }]],
  use: {
    baseURL: BASE_URL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    actionTimeout: 10_000,
    navigationTimeout: 30_000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: process.env.PLAYWRIGHT_NO_WEBSERVER
    ? undefined
    : {
        command: "npm run dev",
        url: BASE_URL,
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      },
});
