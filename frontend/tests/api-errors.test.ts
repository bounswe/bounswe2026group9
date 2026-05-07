import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, apiRequest, isApiError } from "@/lib/api";
import { setAuthenticatedSession, setGuestSession } from "@/lib/session";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("apiRequest error handling", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    setGuestSession();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("parses { detail } error envelope from FastAPI 4xx responses", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: "Event not found" }, 404));
    await expect(apiRequest("/events/nope")).rejects.toThrowError("Event not found");
  });

  it("preserves the HTTP status on the thrown ApiError", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: "Forbidden" }, 403));
    try {
      await apiRequest("/events/x");
    } catch (err: unknown) {
      expect(isApiError(err)).toBe(true);
      if (err instanceof ApiError) {
        expect(err.status).toBe(403);
        expect(err.message).toBe("Forbidden");
      }
      return;
    }
    throw new Error("apiRequest should have thrown");
  });

  it("falls back to a generic message when the body has no detail", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response("Internal Server Error", {
        status: 500,
        headers: { "Content-Type": "text/plain" },
      }),
    );
    try {
      await apiRequest("/events/x");
    } catch (err: unknown) {
      expect(isApiError(err)).toBe(true);
      if (err instanceof ApiError) {
        expect(err.status).toBe(500);
      }
      return;
    }
    throw new Error("apiRequest should have thrown");
  });

  it("attaches an Authorization header for auth='required' when a token is set", async () => {
    setAuthenticatedSession({
      access_token: "secret",
      token_type: "bearer",
      user: {
        id: "u",
        username: "tester",
        email: "t@example.com",
        phone_number: null,
        date_of_birth: null,
        email_visibility: false,
        phone_visibility: false,
        role: "registered",
        auth_provider: "local",
        email_verified: true,
        is_active: true,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      },
    });
    fetchMock.mockResolvedValueOnce(jsonResponse({}));
    await apiRequest("/protected", { auth: "required" });
    const headers = new Headers((fetchMock.mock.calls[0][1] as RequestInit).headers);
    expect(headers.get("Authorization")).toBe("Bearer secret");
  });

  it("does not send Authorization for auth='none'", async () => {
    setAuthenticatedSession({
      access_token: "secret",
      token_type: "bearer",
      user: {
        id: "u",
        username: "tester",
        email: "t@example.com",
        phone_number: null,
        date_of_birth: null,
        email_visibility: false,
        phone_visibility: false,
        role: "registered",
        auth_provider: "local",
        email_verified: true,
        is_active: true,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      },
    });
    fetchMock.mockResolvedValueOnce(jsonResponse({}));
    await apiRequest("/public", { auth: "none" });
    const headers = new Headers((fetchMock.mock.calls[0][1] as RequestInit).headers);
    expect(headers.has("Authorization")).toBe(false);
  });
});
