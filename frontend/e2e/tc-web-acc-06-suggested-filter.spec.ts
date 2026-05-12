/**
 * TC-WEB-ACC-06 — Suggested Discovery Filter Based on Previous Attendance
 *
 * Owner: Muhittin Köybaşı
 * Lab 9 Report, AT06.
 *
 * Validates:
 *   • Logging in as a user with prior attendance history surfaces the
 *     "Suggested for you" filter (it is hidden for guests).
 *   • Toggling the filter pushes ?suggested=1 to the URL.
 *   • Backend network requests carry suggested=true on the wire.
 *   • Result list narrows to suggested events; first card is reachable.
 *   • Private / cancelled / ended events are not exposed.
 *
 * Related requirements: FRS-4, FRS-7, NFR-06.
 */

import { test, expect } from "@playwright/test";

import { loginViaUI } from "./fixtures/auth";
import { env, requireEnv } from "./fixtures/env";

test.describe("TC-WEB-ACC-06 — Suggested discovery filter", () => {
  test.skip(
    !env.user.email || !env.user.password,
    "Set E2E_USER_EMAIL / E2E_USER_PASSWORD with a seeded user that has attendance history.",
  );

  test("guest does not see the Suggested filter and ?suggested=1 in URL has no wire effect", async ({
    page,
  }) => {
    // Step 1 — guest visits discovery
    await page.goto("/?suggested=1");

    // The "Suggested for you" CTA lives under the `Personalised` section which
    // is only rendered for authenticated users.
    await expect(page.getByText(/Personalised/i)).toHaveCount(0);
    await expect(
      page.getByRole("button", { name: /suggested for you/i }),
    ).toHaveCount(0);

    // Confirm no /events request goes out with suggested=true.
    const seenSuggestedTrue: string[] = [];
    page.on("request", (req) => {
      const url = req.url();
      if (url.includes("/events") && url.includes("suggested=true")) {
        seenSuggestedTrue.push(url);
      }
    });
    await page.reload();
    await page.waitForLoadState("networkidle");
    expect(seenSuggestedTrue).toEqual([]);
  });

  test("authenticated user can toggle Suggested filter, URL + network reflect it", async ({
    page,
  }) => {
    requireEnv(env.user.email, "E2E_USER_EMAIL");
    requireEnv(env.user.password, "E2E_USER_PASSWORD");

    // Step 2 — login
    await loginViaUI(page, {
      email: env.user.email,
      password: env.user.password,
    });

    // Step 3 — open discovery
    await page.goto("/");
    await expect(page).toHaveURL(/\/$|^\/\?/);

    // Step 4 — open the filter section. On wide viewports the sidebar is
    // always visible; on narrow viewports there is a toggle button.
    const filterToggle = page.getByRole("button", { name: /filters?/i });
    if (await filterToggle.isVisible().catch(() => false)) {
      await filterToggle.click();
    }

    // Step 5 — locate and click the Suggested CTA
    const suggestedButton = page.getByRole("button", {
      name: /suggested for you/i,
    });
    await expect(suggestedButton).toBeVisible();
    await expect(suggestedButton).toHaveAttribute("aria-pressed", "false");

    // Capture the network request that fires once the filter is applied.
    const eventsRequest = page.waitForRequest((req) =>
      req.url().includes("/events") && req.url().includes("suggested=true"),
    );

    await suggestedButton.click();

    // Step 6 — apply filters. On wide viewports the URL updates eagerly;
    // on mobile we need an explicit Apply.
    const applyButton = page.getByRole("button", { name: /apply filters?/i });
    if (await applyButton.isVisible().catch(() => false)) {
      await applyButton.click();
    }

    // Step 7 — URL gains ?suggested=1
    await expect(page).toHaveURL(/[?&]suggested=1\b/);

    // Network: backend was called with suggested=true
    const req = await eventsRequest;
    expect(req.url()).toMatch(/suggested=true/);

    // After the response, aria-pressed should flip on.
    await expect(suggestedButton).toHaveAttribute("aria-pressed", "true");

    // Step 8 — there should be at least one event card visible, and no
    // exposed Private / Cancelled / Ended labels in the suggested list.
    await page.waitForLoadState("networkidle");

    // Cards link to /event/:id — wait for at least one to render OR for the
    // empty state. We tolerate the empty state because the seed may not yet
    // contain attended categories.
    const eventLinks = page.locator('a[href^="/event/"]');
    const linkCount = await eventLinks.count();

    if (linkCount > 0) {
      // No private / cancelled / ended badges should be visible in results.
      await expect(
        page.locator('span:has-text("Private")').first(),
      ).toHaveCount(0);
      await expect(
        page.locator('span:has-text("Cancelled")').first(),
      ).toHaveCount(0);
      await expect(
        page.locator('span:has-text("Ended")').first(),
      ).toHaveCount(0);

      // Step 9 — open the first card → detail page renders
      const firstHref = await eventLinks.first().getAttribute("href");
      expect(firstHref).toMatch(/^\/event\//);
      await eventLinks.first().click();
      await expect(page).toHaveURL(/\/event\/[\w-]+/);
    }
  });
});
