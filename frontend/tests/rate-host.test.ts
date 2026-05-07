import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { rateHost } from "@/lib/events-api";
import { setAuthenticatedSession } from "@/lib/session";

const HOST_ID = "11111111-1111-1111-1111-111111111111";

function lastFetchBody(fetchMock: ReturnType<typeof vi.fn>): unknown {
  const call = fetchMock.mock.calls.at(-1);
  if (!call) throw new Error("fetch was not called");
  const init = call[1] as RequestInit;
  if (typeof init.body !== "string") throw new Error("expected fetch body to be a JSON string");
  return JSON.parse(init.body) as unknown;
}

describe("rateHost", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 201 }));
    vi.stubGlobal("fetch", fetchMock);
    setAuthenticatedSession({
      access_token: "tok",
      token_type: "bearer",
      user: {
        id: "u1",
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
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sends only score when no review text is provided", async () => {
    await rateHost(HOST_ID, 4);
    expect(lastFetchBody(fetchMock)).toEqual({ score: 4 });
  });

  it("includes the review text when provided", async () => {
    await rateHost(HOST_ID, 5, "Great host, very organised.");
    expect(lastFetchBody(fetchMock)).toEqual({
      score: 5,
      review_text: "Great host, very organised.",
    });
  });

  it("trims surrounding whitespace and drops empty review text", async () => {
    await rateHost(HOST_ID, 3, "   ");
    expect(lastFetchBody(fetchMock)).toEqual({ score: 3 });

    await rateHost(HOST_ID, 3, "  thanks  ");
    expect(lastFetchBody(fetchMock)).toEqual({ score: 3, review_text: "thanks" });
  });
});
