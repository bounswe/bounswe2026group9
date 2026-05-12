/**
 * Comment on event regression — wiki Section 10.
 *
 * Authenticated user can leave a comment on an event detail page and
 * see it appear in the comment list. Guests should see the textarea
 * disabled with the "Sign in to leave a comment" placeholder.
 */

import { test, expect } from "@playwright/test";

import { loginViaUI } from "./fixtures/auth";
import { env, requireEnv } from "./fixtures/env";

test.describe("Comment on event", () => {
  test("guest sees the textarea disabled with a sign-in placeholder", async ({
    page,
  }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    const links = page.locator('a[href^="/event/"]');
    test.skip((await links.count()) === 0, "Discovery is empty");
    await links.first().click();
    await expect(page).toHaveURL(/\/event\/[\w-]+/);

    const textarea = page
      .getByPlaceholder(/sign in to leave a comment/i)
      .first();
    test.skip(
      !(await textarea.isVisible().catch(() => false)),
      "Comment textarea not present on this event",
    );
    await expect(textarea).toBeDisabled();
  });

  test("authenticated user can post a comment and see it appear", async ({
    page,
  }) => {
    test.skip(!env.user.email || !env.user.password, "Need E2E_USER_*");
    requireEnv(env.user.email, "E2E_USER_EMAIL");
    requireEnv(env.user.password, "E2E_USER_PASSWORD");

    await loginViaUI(page, {
      email: env.user.email,
      password: env.user.password,
    });

    const targetId = process.env.E2E_EVENT_COMMENT_ID;
    if (targetId) {
      await page.goto(`/event/${targetId}`);
    } else {
      await page.goto("/");
      await page.waitForLoadState("networkidle");
      const links = page.locator('a[href^="/event/"]');
      test.skip((await links.count()) === 0, "Discovery is empty");
      await links.first().click();
    }
    await page.waitForLoadState("networkidle");

    const textarea = page.getByPlaceholder(/write a comment/i).first();
    test.skip(
      !(await textarea.isVisible().catch(() => false)),
      "Comments closed on this event",
    );

    const marker = `e2e-comment-${Date.now()}`;
    await textarea.fill(marker);

    // The submit button is the icon-only send button right after the textarea.
    // We submit via Enter (the component supports it).
    await textarea.press("Enter");

    await expect(page.getByText(marker, { exact: false }).first()).toBeVisible({
      timeout: 10_000,
    });
  });
});
