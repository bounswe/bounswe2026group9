/**
 * Smoke tests for the authentication surface.
 *
 * These do not consume seeded test data; they verify only static page
 * structure and guest-route enforcement, so they always run.
 */

import { test, expect } from "@playwright/test";

test.describe("Auth smoke", () => {
  test("login page renders the form and CTA", async ({ page }) => {
    await page.goto("/login");
    // CardTitle renders as a <div>, not a heading, so match by visible text.
    await expect(page.getByText(/welcome back/i)).toBeVisible();
    await expect(page.getByRole("textbox", { name: "Email" })).toBeVisible();
    await expect(
      page.getByRole("textbox", { name: "Password" }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /sign in/i }),
    ).toBeVisible();
  });

  test("register page renders the form", async ({ page }) => {
    await page.goto("/register");
    await expect(
      page.getByRole("textbox", { name: /email/i }).first(),
    ).toBeVisible();
    await expect(
      page.getByRole("textbox", { name: /password/i }).first(),
    ).toBeVisible();
  });

  test("protected page (create-event) redirects guest to login", async ({
    page,
  }) => {
    await page.goto("/create-event");
    await expect(page).toHaveURL(/\/login(\?|$)/);
  });

  test("invalid credentials surface an error message", async ({ page }) => {
    await page.goto("/login");
    await page
      .getByRole("textbox", { name: "Email" })
      .fill("nope@example.invalid");
    await page
      .getByRole("textbox", { name: "Password" })
      .fill("wrong-password-123");
    await page.getByRole("button", { name: /sign in/i }).click();

    // The login page shows a banner with the API error. We don't pin
    // exact text — just that the user stays on /login and an error is shown.
    await expect(page).toHaveURL(/\/login/);
    await expect(
      page.locator("[class*='destructive'], [role='alert']").first(),
    ).toBeVisible({ timeout: 10_000 });
  });
});
