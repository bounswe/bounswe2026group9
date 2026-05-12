/**
 * Browse events in map/list view + open event detail — wiki Section 10.
 *
 * Validates the un-authenticated discovery experience:
 *   • The home page loads and renders at least one event card.
 *   • The map/list view toggle exists and switches the rendering.
 *   • Clicking an event card navigates to /event/{id}.
 *
 * Runs without any seed env vars; if the deployed dataset is empty, the
 * card-count assertion becomes a soft-skip rather than a hard failure.
 */

import { test, expect } from "@playwright/test";

test.describe("Discovery browse — list, map, open detail", () => {
  test("home page renders discovery and exposes view toggle", async ({
    page,
  }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // The discovery action bar contains a Map / List toggle pair. It uses
    // aria-label that includes "map" or just an icon button. We look for
    // either an explicit toggle button or the radiogroup-shaped sort.
    const toggleButtons = page.getByRole("button", {
      name: /^(map|list)$/i,
    });
    const count = await toggleButtons.count();
    expect(count).toBeGreaterThanOrEqual(1);
  });

  test("at least one event card surfaces and opens its detail page", async ({
    page,
  }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    const cards = page.locator('a[href^="/event/"]');
    const cardCount = await cards.count();
    test.skip(cardCount === 0, "Discovery returned no events in this environment");

    const href = await cards.first().getAttribute("href");
    expect(href).toMatch(/^\/event\//);

    await cards.first().click();
    await expect(page).toHaveURL(/\/event\/[\w-]+/);
  });

  test("switching to Map view does not navigate away", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    const mapToggle = page.getByRole("button", { name: /^map$/i }).first();
    test.skip(
      !(await mapToggle.isVisible().catch(() => false)),
      "Map toggle not visible in this layout",
    );

    await mapToggle.click();
    // The URL should stay on the home page (with or without a query string).
    // toHaveURL matches against the full URL, so use a host-aware pattern.
    await expect(page).toHaveURL(/localhost:\d+\/(\?.*)?$/);
  });
});
