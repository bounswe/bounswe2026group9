import { afterEach, describe, expect, it, vi } from "vitest";

import {
  getSessionState,
  resetSessionState,
  setAuthenticatedSession,
  setGuestSession,
  subscribeToSession,
} from "@/lib/session";

describe("session store", () => {
  afterEach(() => {
    resetSessionState();
  });

  it("stores authenticated session data and notifies subscribers", () => {
    const listener = vi.fn();
    const unsubscribe = subscribeToSession(listener);

    setAuthenticatedSession({
      access_token: "access-token",
      token_type: "bearer",
      user: {
        auth_provider: "local",
        created_at: "2026-03-27T00:00:00Z",
        date_of_birth: null,
        email: "test@example.com",
        email_verified: true,
        email_visibility: false,
        id: "user-1",
        is_active: true,
        phone_number: null,
        role: "registered",
        updated_at: "2026-03-27T00:00:00Z",
        username: "test-user",
      },
    });

    expect(getSessionState()).toMatchObject({
      accessToken: "access-token",
      isInitialized: true,
      status: "authenticated",
      user: {
        email: "test@example.com",
        username: "test-user",
      },
    });
    expect(listener).toHaveBeenCalledTimes(1);

    unsubscribe();
  });

  it("resets to guest state after logout", () => {
    setAuthenticatedSession({
      access_token: "access-token",
      token_type: "bearer",
      user: {
        auth_provider: "local",
        created_at: "2026-03-27T00:00:00Z",
        date_of_birth: null,
        email: "test@example.com",
        email_verified: true,
        email_visibility: false,
        id: "user-1",
        is_active: true,
        phone_number: null,
        role: "registered",
        updated_at: "2026-03-27T00:00:00Z",
        username: "test-user",
      },
    });

    setGuestSession();

    expect(getSessionState()).toEqual({
      accessToken: null,
      isInitialized: true,
      status: "guest",
      user: null,
    });
  });
});
