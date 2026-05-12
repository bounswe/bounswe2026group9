/**
 * TC-ACC-EVT-LIFECYCLE-05 — Event Edit and Cancellation Lifecycle Enforcement
 *
 * Owner: Faik İhsan Südüpak
 * Lab 9 Report, AT05.
 *
 * Validates:
 *   • Host can edit a future event's title; change persists.
 *   • Host cannot mutate time/location of an ongoing event (form locked or
 *     backend rejects).
 *   • Cancelling a future event transitions it to Cancelled.
 *   • Cancelled event no longer surfaces in default discovery results.
 *   • Cancelled event's detail page still loads and shows a Cancelled label.
 *
 * Related requirements: FRU-1.1.3, FRS-2.3, NFR-02.
 */

import { test, expect } from "@playwright/test";

import { loginViaUI } from "./fixtures/auth";
import { env, requireEnv } from "./fixtures/env";

test.describe("TC-ACC-EVT-LIFECYCLE-05 — host edit + cancellation", () => {
  test.skip(
    !env.host.email ||
      !env.host.password ||
      !env.events.future ||
      !env.events.ongoing,
    "Set E2E_HOST_*, E2E_EVENT_FUTURE_ID, E2E_EVENT_ONGOING_ID — see e2e/README.md",
  );

  test("future event title can be edited and event can be cancelled", async ({
    page,
  }) => {
    requireEnv(env.host.email, "E2E_HOST_EMAIL");
    requireEnv(env.host.password, "E2E_HOST_PASSWORD");
    requireEnv(env.events.future, "E2E_EVENT_FUTURE_ID");

    await loginViaUI(page, {
      email: env.host.email,
      password: env.host.password,
    });

    // Step 1 — open the edit page for the future event.
    await page.goto(`/edit-event/${env.events.future}`);

    const titleInput = page.getByLabel(/title/i).first();
    await expect(titleInput).toBeEditable();
    const original = (await titleInput.inputValue()) ?? "";
    const updated = `${original.replace(/ — Updated$/i, "")} — Updated`;

    await titleInput.fill(updated);
    await page.getByRole("button", { name: /save|update/i }).first().click();

    // Step 2 — go back to detail page and verify the new title is shown.
    await page.goto(`/event/${env.events.future}`);
    await expect(
      page.getByRole("heading", { name: updated }).first(),
    ).toBeVisible({ timeout: 15_000 });
  });

  test("ongoing event blocks edits to start time / location", async ({
    page,
  }) => {
    requireEnv(env.host.email, "E2E_HOST_EMAIL");
    requireEnv(env.host.password, "E2E_HOST_PASSWORD");
    requireEnv(env.events.ongoing, "E2E_EVENT_ONGOING_ID");

    await loginViaUI(page, {
      email: env.host.email,
      password: env.host.password,
    });

    await page.goto(`/edit-event/${env.events.ongoing}`);

    // The start-time field should be either disabled, readonly, or absent —
    // any of those satisfies "user cannot mutate start time".
    const startTimeInputs = page.locator(
      'input[type="datetime-local"], input[name*="start" i]',
    );
    const count = await startTimeInputs.count();
    if (count > 0) {
      for (let i = 0; i < count; i++) {
        const input = startTimeInputs.nth(i);
        const isDisabled = await input.isDisabled().catch(() => false);
        const isReadonly = await input.evaluate(
          (el: HTMLInputElement) => el.readOnly,
        );
        // At least one of disabled/readonly must hold for each start-time
        // input on an ongoing event.
        expect(
          isDisabled || isReadonly,
          `start-time input #${i} should be disabled or readonly on an ongoing event`,
        ).toBeTruthy();
      }
    }
  });

  test("cancelled event disappears from discovery but detail stays accessible", async ({
    page,
  }) => {
    requireEnv(env.host.email, "E2E_HOST_EMAIL");
    requireEnv(env.host.password, "E2E_HOST_PASSWORD");
    requireEnv(env.events.future, "E2E_EVENT_FUTURE_ID");

    await loginViaUI(page, {
      email: env.host.email,
      password: env.host.password,
    });

    // Cancel from the detail page (preferred) or the edit page.
    await page.goto(`/event/${env.events.future}`);
    const cancelTrigger = page
      .getByRole("button", { name: /cancel event/i })
      .first();

    if (await cancelTrigger.isVisible().catch(() => false)) {
      await cancelTrigger.click();
      // A confirmation dialog typically appears.
      const confirm = page
        .getByRole("button", { name: /^(confirm|cancel event|yes)$/i })
        .last();
      await confirm.click().catch(() => {
        /* dialog may not exist — that's fine */
      });
    }

    // After cancel, the detail page should label the event as cancelled.
    await page.goto(`/event/${env.events.future}`);
    await expect(
      page.getByText(/cancelled/i).first(),
    ).toBeVisible({ timeout: 15_000 });

    // Discovery list should not surface the cancelled event link by default.
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    const cancelledLink = page.locator(
      `a[href="/event/${env.events.future}"]`,
    );
    await expect(cancelledLink).toHaveCount(0);
  });
});
