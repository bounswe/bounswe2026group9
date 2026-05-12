/**
 * Notifications regression — wiki Section 10.
 *
 * Validates that an authenticated user can open /inbox and that the
 * inbox surface renders either notifications or an empty state. To
 * fully exercise the update/cancellation pipeline you need to seed the
 * backend with a notification of each type targeted at the test user.
 *
 * Requires E2E_USER_EMAIL / E2E_USER_PASSWORD. Optionally:
 *   E2E_EXPECT_UPDATE_NOTIFICATION=1       — assert at least one update
 *   E2E_EXPECT_CANCELLATION_NOTIFICATION=1 — assert at least one cancel
 */

import { test, expect } from "@playwright/test";

import { loginViaUI } from "./fixtures/auth";
import { env, requireEnv } from "./fixtures/env";

test.describe("Notifications inbox", () => {
  test.skip(
    !env.user.email || !env.user.password,
    "Set E2E_USER_EMAIL / E2E_USER_PASSWORD",
  );

  test("inbox page renders for authenticated user", async ({ page }) => {
    requireEnv(env.user.email, "E2E_USER_EMAIL");
    requireEnv(env.user.password, "E2E_USER_PASSWORD");

    await loginViaUI(page, {
      email: env.user.email,
      password: env.user.password,
    });

    await page.goto("/inbox");
    await page.waitForLoadState("networkidle");

    // Page heading — either "Inbox" or "Notifications".
    await expect(
      page.getByRole("heading", { name: /inbox|notifications/i }).first(),
    ).toBeVisible();
  });

  test("if seeded, update notification is present in inbox", async ({
    page,
  }) => {
    test.skip(
      process.env.E2E_EXPECT_UPDATE_NOTIFICATION !== "1",
      "Seed an event-updated notification and set E2E_EXPECT_UPDATE_NOTIFICATION=1",
    );

    requireEnv(env.user.email, "E2E_USER_EMAIL");
    requireEnv(env.user.password, "E2E_USER_PASSWORD");

    await loginViaUI(page, {
      email: env.user.email,
      password: env.user.password,
    });
    await page.goto("/inbox");
    await page.waitForLoadState("networkidle");

    await expect(
      page.getByText(/updated|changed|new (time|location|date)/i).first(),
    ).toBeVisible();
  });

  test("if seeded, cancellation notification is present in inbox", async ({
    page,
  }) => {
    test.skip(
      process.env.E2E_EXPECT_CANCELLATION_NOTIFICATION !== "1",
      "Seed an event-cancelled notification and set E2E_EXPECT_CANCELLATION_NOTIFICATION=1",
    );

    requireEnv(env.user.email, "E2E_USER_EMAIL");
    requireEnv(env.user.password, "E2E_USER_PASSWORD");

    await loginViaUI(page, {
      email: env.user.email,
      password: env.user.password,
    });
    await page.goto("/inbox");
    await page.waitForLoadState("networkidle");

    await expect(page.getByText(/cancelled|canceled/i).first()).toBeVisible();
  });
});
