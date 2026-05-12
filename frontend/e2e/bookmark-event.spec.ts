/**
 * Bookmark event regression — wiki Section 10.
 *
 * Signed-in user can bookmark an event from the discovery card and from
 * the event detail page. The bookmarked state persists across reloads.
 */

import { test, expect } from "@playwright/test";

import { loginViaUI } from "./fixtures/auth";
import { env, requireEnv } from "./fixtures/env";

test.describe("Bookmark event", () => {
  test.skip(
    !env.user.email || !env.user.password,
    "Set E2E_USER_EMAIL / E2E_USER_PASSWORD",
  );

  test("toggle bookmark from discovery card and verify persistence", async ({
    page,
  }) => {
    requireEnv(env.user.email, "E2E_USER_EMAIL");
    requireEnv(env.user.password, "E2E_USER_PASSWORD");

    await loginViaUI(page, {
      email: env.user.email,
      password: env.user.password,
    });
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    const eventLinks = page.locator('a[href^="/event/"]');
    test.skip(
      (await eventLinks.count()) === 0,
      "No events on discovery to bookmark",
    );

    // Identify a card. Each card has a Bookmark / Saved button.
    const firstCard = eventLinks.first();
    const cardHref = await firstCard.getAttribute("href");
    expect(cardHref).toBeTruthy();

    const cardContainer = firstCard.locator("..");
    const bookmarkBtn = cardContainer
      .getByRole("button", { name: /^(bookmark|saved)$/i })
      .first();

    test.skip(
      !(await bookmarkBtn.isVisible().catch(() => false)),
      "Bookmark CTA not exposed on this card (user may own the event)",
    );

    const initial = (await bookmarkBtn.textContent())?.toLowerCase() ?? "";
    await bookmarkBtn.click();

    // Wait for the optimistic UI flip + backend round-trip.
    await page.waitForTimeout(500);
    const after = (await bookmarkBtn.textContent())?.toLowerCase() ?? "";
    expect(after).not.toEqual(initial);

    // Reload and confirm the state stuck.
    await page.reload();
    await page.waitForLoadState("networkidle");
    const persisted = page.locator(`a[href="${cardHref}"]`).first();
    const persistedBtn = persisted
      .locator("..")
      .getByRole("button", { name: /^(bookmark|saved)$/i })
      .first();
    const persistedText = (await persistedBtn.textContent())?.toLowerCase() ?? "";
    expect(persistedText).toEqual(after);
  });
});
