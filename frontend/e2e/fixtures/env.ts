/**
 * Centralised access to the environment variables the e2e suite expects.
 *
 * Tests skip themselves when the required seed values are missing, so the
 * suite never produces false negatives on a fresh checkout. CI should set
 * everything explicitly to actually exercise the scenarios.
 */
export const env = {
  baseUrl: process.env.BASE_URL ?? "http://localhost:3000",
  apiBaseUrl: process.env.API_BASE_URL ?? "http://localhost:8888",

  user: {
    email: process.env.E2E_USER_EMAIL,
    password: process.env.E2E_USER_PASSWORD,
  },
  host: {
    email: process.env.E2E_HOST_EMAIL,
    password: process.env.E2E_HOST_PASSWORD,
  },
  userA: {
    email: process.env.E2E_USER_A_EMAIL,
    password: process.env.E2E_USER_A_PASSWORD,
  },
  userB: {
    email: process.env.E2E_USER_B_EMAIL,
    password: process.env.E2E_USER_B_PASSWORD,
  },

  events: {
    full: process.env.E2E_EVENT_FULL_ID,
    future: process.env.E2E_EVENT_FUTURE_ID,
    ongoing: process.env.E2E_EVENT_ONGOING_ID,
    private: process.env.E2E_EVENT_PRIVATE_ID,
  },
} as const;

export function requireEnv<T>(
  value: T | undefined,
  name: string,
): asserts value is T {
  if (value === undefined || value === null || value === "") {
    throw new Error(
      `[e2e] Required env variable ${name} is not set — see frontend/e2e/README.md`,
    );
  }
}
