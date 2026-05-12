import { expect, type Page, type APIRequestContext } from "@playwright/test";

import { env } from "./env";

/**
 * Log in via the real `/login` page so we exercise the same code path
 * the user does (form submit → cookie set → redirect).
 */
export async function loginViaUI(
  page: Page,
  credentials: { email: string; password: string },
) {
  await page.goto("/login");
  await expect(page.getByText(/welcome back/i)).toBeVisible();

  await page.getByRole("textbox", { name: "Email" }).fill(credentials.email);
  await page
    .getByRole("textbox", { name: "Password" })
    .fill(credentials.password);

  await Promise.all([
    page.waitForURL((url) => !url.pathname.startsWith("/login"), {
      timeout: 15_000,
    }),
    page.getByRole("button", { name: /sign in/i }).click(),
  ]);
}

/**
 * Issue an authenticated POST against the backend directly. Used to verify
 * that backend-level access control rejects requests even when the UI has
 * disabled the corresponding button (capacity, private events, etc.).
 *
 * Reuses the cookies Playwright has already gathered for the user, so the
 * caller must log in via the UI first.
 */
export async function authedApiRequest(
  request: APIRequestContext,
  method: "GET" | "POST" | "PATCH" | "DELETE",
  path: string,
  body?: unknown,
) {
  const url = `${env.apiBaseUrl}${path.startsWith("/") ? path : `/${path}`}`;
  return await request.fetch(url, {
    method,
    headers: body
      ? { "Content-Type": "application/json" }
      : undefined,
    data: body ? JSON.stringify(body) : undefined,
  });
}
