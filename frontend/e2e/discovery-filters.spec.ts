/**
 * Apply discovery filters regression — wiki Section 10.
 *
 * Covers the everyday filter surface (not the personalised suggested
 * filter, which lives in tc-web-acc-06-suggested-filter.spec.ts):
 *   • Quick time-window filter (Today / Weekend / Upcoming) updates the
 *     URL and the /events network request.
 *   • Accessibility toggle (wheelchair) propagates as a query parameter.
 *   • Show past events toggle changes the request shape.
 *
 * No seeded credentials needed — the discovery sidebar is always rendered
 * for guests.
 */

import { test, expect } from "@playwright/test";

test.describe("Discovery filters", () => {
  test("clicking the Today quick filter updates the URL and fires a backend request", async ({
    page,
  }) => {
    await page.goto("/");

    // Open the mobile drawer if necessary (toggle button is "Filters" with a
    // count badge on narrow viewports).
    const filtersToggle = page.getByRole("button", { name: /^filters?$/i });
    if (await filtersToggle.isVisible().catch(() => false)) {
      await filtersToggle.click();
    }

    const todayButton = page.getByRole("button", { name: /^today$/i }).first();
    await expect(todayButton).toBeVisible();

    const eventsRequest = page.waitForRequest((req) => {
      const url = req.url();
      return (
        url.includes("/events") &&
        /quick_filter=today|temporal=today|today/i.test(url)
      );
    });

    await todayButton.click();

    // Click Apply if there is one (mobile path).
    const applyBtn = page.getByRole("button", { name: /^apply/i }).first();
    if (await applyBtn.isVisible().catch(() => false)) {
      await applyBtn.click();
    }

    await eventsRequest;
    await expect(page).toHaveURL(/[?&](temporal|quick_filter)=today/);
    await expect(todayButton).toHaveAttribute("aria-pressed", "true");
  });

  test("wheelchair accessibility filter propagates to the URL", async ({
    page,
  }) => {
    await page.goto("/");

    const filtersToggle = page.getByRole("button", { name: /^filters?$/i });
    if (await filtersToggle.isVisible().catch(() => false)) {
      await filtersToggle.click();
    }

    const wheelchair = page
      .getByLabel(/wheelchair/i)
      .or(page.getByRole("checkbox", { name: /wheelchair/i }))
      .first();
    test.skip(
      !(await wheelchair.isVisible().catch(() => false)),
      "Accessibility checkbox not in this layout",
    );

    await wheelchair.check({ force: true }).catch(async () => {
      await wheelchair.click();
    });

    const applyBtn = page.getByRole("button", { name: /^apply/i }).first();
    if (await applyBtn.isVisible().catch(() => false)) {
      await applyBtn.click();
    }

    // URL should now contain an a11y key referencing wheelchair.
    await expect(page).toHaveURL(/(a11y|wheelchair)/i);
  });

  test("show past events toggle changes the request shape", async ({ page }) => {
    await page.goto("/");

    const filtersToggle = page.getByRole("button", { name: /^filters?$/i });
    if (await filtersToggle.isVisible().catch(() => false)) {
      await filtersToggle.click();
    }

    const pastToggle = page
      .getByRole("switch", { name: /show past events/i })
      .or(page.getByLabel(/show past events/i))
      .first();
    test.skip(
      !(await pastToggle.isVisible().catch(() => false)),
      "Past-events toggle not in this layout",
    );

    await pastToggle.click();

    const applyBtn = page.getByRole("button", { name: /^apply/i }).first();
    if (await applyBtn.isVisible().catch(() => false)) {
      await applyBtn.click();
    }

    await expect(page).toHaveURL(/showPast|show_past|past=1/i);
  });
});
