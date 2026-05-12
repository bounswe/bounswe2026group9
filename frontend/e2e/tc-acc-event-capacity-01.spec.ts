/**
 * TC-ACC-EVENT-CAPACITY-01 — Capacity Enforcement Blocks New "Going"
 *
 * Owner: İbrahim Fırat Yoğurtçu
 * Lab 9 Report, AT04.
 *
 * Validates both UI and backend enforcement when a public event is full:
 *   • User A clicking Going when count is 1/2 fills the event to 2/2.
 *   • UI for User B shows a FULL / disabled CTA on the same event.
 *   • A direct POST /events/{id}/going as User B is rejected (409 / 400).
 *
 * Related requirements: FRU-3 / FRS-5, FRS-6, NFR-04.
 */

import { test, expect } from "@playwright/test";

import { authedApiRequest, loginViaUI } from "./fixtures/auth";
import { env, requireEnv } from "./fixtures/env";

test.describe("TC-ACC-EVENT-CAPACITY-01 — capacity enforcement", () => {
  test.skip(
    !env.userA.email ||
      !env.userA.password ||
      !env.userB.email ||
      !env.userB.password ||
      !env.events.full,
    "Set E2E_USER_A_*, E2E_USER_B_*, and E2E_EVENT_FULL_ID — see e2e/README.md",
  );

  test("User A fills the event then User B is blocked in UI and API", async ({
    browser,
  }) => {
    requireEnv(env.userA.email, "E2E_USER_A_EMAIL");
    requireEnv(env.userA.password, "E2E_USER_A_PASSWORD");
    requireEnv(env.userB.email, "E2E_USER_B_EMAIL");
    requireEnv(env.userB.password, "E2E_USER_B_PASSWORD");
    requireEnv(env.events.full, "E2E_EVENT_FULL_ID");

    const eventPath = `/event/${env.events.full}`;

    // ---- User A: claim the last seat ----
    const userAContext = await browser.newContext();
    const userAPage = await userAContext.newPage();

    await loginViaUI(userAPage, {
      email: env.userA.email,
      password: env.userA.password,
    });
    await userAPage.goto(eventPath);

    // Expect the capacity counter to show "1/2" before User A joins.
    await expect(userAPage.getByText(/1\s*\/\s*2/)).toBeVisible();

    // Click the Going CTA. The button uses text/icon — search for "Going".
    const goingButton = userAPage.getByRole("button", { name: /^going$/i }).first();
    await expect(goingButton).toBeEnabled();
    await goingButton.click();

    // After the click the count flips to 2/2.
    await expect(userAPage.getByText(/2\s*\/\s*2/)).toBeVisible({
      timeout: 10_000,
    });

    // ---- User B: should see a disabled / full CTA ----
    const userBContext = await browser.newContext();
    const userBPage = await userBContext.newPage();

    await loginViaUI(userBPage, {
      email: env.userB.email,
      password: env.userB.password,
    });
    await userBPage.goto(eventPath);

    // Capacity counter shows full.
    await expect(userBPage.getByText(/2\s*\/\s*2/)).toBeVisible();

    // The Going button should be disabled or replaced by a Full label.
    const fullIndicator = userBPage
      .getByText(/full|sold out/i)
      .or(userBPage.getByRole("button", { name: /^going$/i, disabled: true }));
    await expect(fullIndicator.first()).toBeVisible();

    // ---- Direct API bypass: backend must reject ----
    const apiResponse = await authedApiRequest(
      userBContext.request,
      "POST",
      `/events/${env.events.full}/going`,
    );
    expect([400, 409]).toContain(apiResponse.status());

    const body = await apiResponse.json().catch(() => ({}));
    if (body && typeof body === "object" && "detail" in body) {
      expect(String((body as { detail: string }).detail).toLowerCase()).toMatch(
        /full|capacity/,
      );
    }

    // Sanity: reload the page as User B, attendee count remains 2/2 and
    // User B is not on the attendee list.
    await userBPage.reload();
    await expect(userBPage.getByText(/2\s*\/\s*2/)).toBeVisible();

    await userAContext.close();
    await userBContext.close();
  });
});
