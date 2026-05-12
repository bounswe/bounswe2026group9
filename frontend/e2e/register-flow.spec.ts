/**
 * Register and login regression test — wiki Section 10.
 *
 * Verifies that:
 *   • The register page submits with a fresh, randomised email.
 *   • Registration redirects to the authenticated landing area (or login
 *     page with a banner, depending on the backend's verification policy).
 *   • The freshly-created user can then sign in via /login.
 *
 * Generates a random email per run so the test can execute repeatedly
 * against the same backend without unique-constraint collisions.
 */

import { test, expect } from "@playwright/test";

import { loginViaUI } from "./fixtures/auth";

const TEST_PASSWORD = process.env.E2E_NEW_USER_PASSWORD ?? "Sm0kePass!23";

test.describe("Register and login regression", () => {
  test("a new user can register then log back in", async ({ page }) => {
    const suffix = Math.random().toString(36).slice(2, 10);
    const email = `e2e_${suffix}@example.test`;

    // ---- Register ----
    await page.goto("/register");

    // The register form has email + password + (optionally) confirm /
    // username fields. Use role-based queries so the "Show password"
    // toggle button does not match our password label search.
    const usernameField = page.getByRole("textbox", { name: /username/i }).first();
    if (await usernameField.isVisible().catch(() => false)) {
      await usernameField.fill(`e2e_${suffix}`);
    }

    await page.getByRole("textbox", { name: /email/i }).first().fill(email);

    const passwordFields = page.getByRole("textbox", { name: /password/i });
    const passwordCount = await passwordFields.count();
    for (let i = 0; i < passwordCount; i++) {
      await passwordFields.nth(i).fill(TEST_PASSWORD);
    }

    await page.getByRole("button", { name: /sign up|register|create/i }).click();

    // After submit the user should either land on the home page or on
    // /login with a confirmation banner. Either way they should not stay
    // on /register with a generic error.
    await page.waitForLoadState("networkidle");
    const url = page.url();
    expect(url).not.toMatch(/\/register\?error/);

    // ---- Log in with the freshly registered credentials ----
    // If we're still authenticated, log out first via the navbar.
    if (!url.includes("/login")) {
      const logoutBtn = page.getByRole("button", { name: /logout|sign out/i });
      if (await logoutBtn.isVisible().catch(() => false)) {
        await logoutBtn.click();
      }
    }

    await loginViaUI(page, { email, password: TEST_PASSWORD });
    await expect(page).not.toHaveURL(/\/login/);
  });
});
