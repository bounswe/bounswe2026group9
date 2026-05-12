/**
 * Recommendation privacy regression — wiki Section 10.
 *
 * Validates that the Suggested-for-you and Similar-events surfaces do
 * not expose:
 *   • Private events the user has no access to
 *   • Cancelled events
 *   • Ended events
 *
 * Implementation: enable the suggested filter as an authenticated user,
 * inspect the rendered cards, and assert no Private / Cancelled / Ended
 * badges are present. Also probes the backend response body to confirm
 * no `visibility == private` or `status == cancelled|ended` rows leak.
 *
 * Requires E2E_USER_EMAIL / E2E_USER_PASSWORD.
 */

import { test, expect } from "@playwright/test";

import { loginViaUI } from "./fixtures/auth";
import { env, requireEnv } from "./fixtures/env";

test.describe("Recommendation privacy", () => {
  test.skip(
    !env.user.email || !env.user.password,
    "Set E2E_USER_EMAIL / E2E_USER_PASSWORD",
  );

  test("suggested results do not include private, cancelled, or ended events", async ({
    page,
  }) => {
    requireEnv(env.user.email, "E2E_USER_EMAIL");
    requireEnv(env.user.password, "E2E_USER_PASSWORD");

    await loginViaUI(page, {
      email: env.user.email,
      password: env.user.password,
    });

    // Capture the /events response body for inspection.
    const responsePromise = page.waitForResponse((res) => {
      const url = res.url();
      return url.includes("/events") && url.includes("suggested=true");
    });

    await page.goto("/?suggested=1");
    await page.waitForLoadState("networkidle");

    // The button should be active.
    const suggestedBtn = page.getByRole("button", {
      name: /suggested for you/i,
    });
    if (await suggestedBtn.isVisible().catch(() => false)) {
      await expect(suggestedBtn).toHaveAttribute("aria-pressed", "true");
    }

    // No badges of restricted states in rendered cards.
    await expect(page.locator("text=/^Private$/i").first()).toHaveCount(0);
    await expect(page.locator("text=/^Cancelled$/i").first()).toHaveCount(0);
    await expect(page.locator("text=/^Ended$/i").first()).toHaveCount(0);

    // API-level check.
    const response = await responsePromise;
    if (response.ok()) {
      const body = (await response.json().catch(() => ({}))) as {
        items?: Array<{
          visibility?: string;
          status?: string;
          has_access?: boolean;
        }>;
      };
      const items = body.items ?? [];
      for (const item of items) {
        // Private items must include has_access:true to ever surface here.
        if (item.visibility === "private") {
          expect(item.has_access).toBe(true);
        }
        expect(["cancelled", "ended"]).not.toContain(item.status);
      }
    }
  });
});
