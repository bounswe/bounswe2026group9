/**
 * Mark event as Going regression — wiki Section 10.
 *
 * Distinct from the capacity test: this just verifies the basic happy
 * path of toggling Going on a non-full public event.
 *
 * Requires:
 *   E2E_USER_EMAIL / E2E_USER_PASSWORD
 *   E2E_EVENT_GOING_ID — a public, non-full, future event the user does
 *                       not yet attend. Falls back to discovery scan.
 */

import { test, expect } from "@playwright/test";

import { loginViaUI } from "./fixtures/auth";
import { env, requireEnv } from "./fixtures/env";

test.describe("Mark event as Going", () => {
  test.skip(!env.user.email || !env.user.password, "Set E2E_USER_EMAIL / E2E_USER_PASSWORD");

  test("user toggles Going on the event detail page", async ({ page }) => {
    requireEnv(env.user.email, "E2E_USER_EMAIL");
    requireEnv(env.user.password, "E2E_USER_PASSWORD");

    await loginViaUI(page, {
      email: env.user.email,
      password: env.user.password,
    });

    const targetId = process.env.E2E_EVENT_GOING_ID;
    if (targetId) {
      await page.goto(`/event/${targetId}`);
    } else {
      await page.goto("/");
      await page.waitForLoadState("networkidle");
      const links = page.locator('a[href^="/event/"]');
      const count = await links.count();
      test.skip(count === 0, "Discovery returned no events");
      await links.first().click();
    }

    await page.waitForLoadState("networkidle");
    await expect(page).toHaveURL(/\/event\/[\w-]+/);

    // The button label flips between "Going" and "Attended ✓" after click,
    // so use a single locator that matches either state — otherwise the
    // post-click textContent() call would fail to resolve the element.
    const goingBtn = page.getByRole("button", { name: /going|attended/i }).first();
    test.skip(
      !(await goingBtn.isVisible().catch(() => false)),
      "Going CTA not present (event may be private without access or user owns it)",
    );
    test.skip(
      !(await goingBtn.isEnabled().catch(() => false)),
      "Going CTA is disabled (event likely full)",
    );

    const beforeText = (await goingBtn.textContent())?.toLowerCase() ?? "";

    await goingBtn.click();
    await page.waitForTimeout(750); // wait for optimistic UI + round trip

    const afterText = (await goingBtn.textContent())?.toLowerCase() ?? "";
    expect(afterText).not.toEqual(beforeText);
  });
});
