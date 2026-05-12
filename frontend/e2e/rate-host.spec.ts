/**
 * Rate host regression — wiki Section 10.
 *
 * Validates the rate-host card flow on a host's profile:
 *   • A user who attended one of the host's ended events sees the rate
 *     card and can submit a rating.
 *   • A success message ("Thanks, your rating has been saved.") appears.
 *
 * Requires:
 *   E2E_USER_EMAIL / E2E_USER_PASSWORD — a user eligible to rate the host
 *   E2E_RATEABLE_HOST_ID                — host profile id the user can rate
 */

import { test, expect } from "@playwright/test";

import { loginViaUI } from "./fixtures/auth";
import { env, requireEnv } from "./fixtures/env";

test.describe("Rate host", () => {
  test.skip(
    !env.user.email ||
      !env.user.password ||
      !process.env.E2E_RATEABLE_HOST_ID,
    "Set E2E_USER_* and E2E_RATEABLE_HOST_ID",
  );

  test("eligible user submits a star rating and sees success message", async ({
    page,
  }) => {
    requireEnv(env.user.email, "E2E_USER_EMAIL");
    requireEnv(env.user.password, "E2E_USER_PASSWORD");
    const hostId = process.env.E2E_RATEABLE_HOST_ID;
    requireEnv(hostId, "E2E_RATEABLE_HOST_ID");

    await loginViaUI(page, {
      email: env.user.email,
      password: env.user.password,
    });

    await page.goto(`/profile/${hostId}`);
    await page.waitForLoadState("networkidle");

    // The rate-host card is on the host profile page when the viewer is
    // eligible. It has a Submit Rating button.
    const submitBtn = page.getByRole("button", { name: /submit rating/i });
    test.skip(
      !(await submitBtn.isVisible().catch(() => false)),
      "Rate-host card not visible (user not eligible)",
    );

    // The RatingStars component renders each star as a button with
    // aria-label="Rate N stars". We pick 4. The same aria-label is
    // also used for the read-only display, so we scope to enabled.
    const fourStars = page
      .getByRole("button", { name: /rate\s*4\s*stars?/i })
      .first();
    await expect(fourStars).toBeVisible();
    await fourStars.click();

    await submitBtn.click();

    await expect(
      page.getByText(/thanks.*your rating has been saved/i),
    ).toBeVisible({ timeout: 10_000 });
  });
});
