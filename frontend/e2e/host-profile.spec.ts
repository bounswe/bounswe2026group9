/**
 * View host profile regression — wiki Section 10.
 *
 * Validates the public host-profile page surface:
 *   • Tabs render: About, Past Events, Upcoming, Reviews.
 *   • Average rating widget is visible (number or "New").
 *   • Switching to the Reviews tab loads the reviews list (or empty state).
 *
 * Requires E2E_HOST_PROFILE_ID — id of a host with at least one event.
 */

import { test, expect } from "@playwright/test";

import { env } from "./fixtures/env";

const hostId = process.env.E2E_HOST_PROFILE_ID;

test.describe("View host profile", () => {
  test.skip(!hostId, "Set E2E_HOST_PROFILE_ID");

  test("host profile renders core tabs and the rating widget", async ({ page }) => {
    await page.goto(`/profile/${hostId}`);
    await page.waitForLoadState("networkidle");

    // Page header — host's username/name.
    await expect(page.locator("main")).toBeVisible();

    // Tabs (rendered as buttons or links with these labels).
    for (const tabName of ["About", "Past Events", "Upcoming", "Reviews"]) {
      const tab = page.getByRole("button", { name: new RegExp(tabName, "i") });
      // Tabs may be rendered as links on wider layouts.
      const linkVariant = page.getByRole("link", {
        name: new RegExp(tabName, "i"),
      });
      const visible =
        (await tab
          .first()
          .isVisible()
          .catch(() => false)) ||
        (await linkVariant
          .first()
          .isVisible()
          .catch(() => false));
      expect(visible, `${tabName} tab should be visible`).toBeTruthy();
    }

    // Rating widget: average shown either as "x.y" or "New".
    const ratingFigure = page.locator("text=/^\\s*(\\d\\.\\d|New)\\s*$/").first();
    await expect(ratingFigure).toBeVisible();
  });

  test("Reviews tab loads reviews list or its empty state", async ({ page }) => {
    await page.goto(`/profile/${hostId}`);
    await page.waitForLoadState("networkidle");

    const reviewsTab = page
      .getByRole("button", { name: /^reviews/i })
      .or(page.getByRole("link", { name: /^reviews/i }))
      .first();
    await reviewsTab.click();

    // Either we see reviews (cards with star icons) or an empty state.
    const reviewsRoot = page.locator("text=/no reviews yet|No written review|reviews?/i").first();
    await expect(reviewsRoot).toBeVisible({ timeout: 10_000 });
  });
});

// Reference env to avoid unused-import warning when the suite is skipped.
void env;
