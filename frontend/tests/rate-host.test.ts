import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { rateHost } from "@/lib/events-api";
import { setAuthenticatedSession } from "@/lib/session";

const HOST_ID = "11111111-1111-1111-1111-111111111111";

function lastFetchBody(fetchMock: ReturnType<typeof vi.fn>): unknown {
  const call = fetchMock.mock.calls.at(-1);
  if (!call) throw new Error("fetch was not called");
  const init = call[1] as RequestInit;
  return JSON.parse(String(init.body));
}

describe("rateHost", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn().mockResolvedValue(
      new Response(null, { status: 201 }),
    );
    vi.stubGlobal("fetch", fetchMock);
    setAuthenticatedSession({
      access_token: "tok",
      user: {
        id: "u1",
        username: "tester",
        email: "t@example.com",
        phone_number: null,
        date_of_birth: null,
        email_visibility: false,
        phone_visibility: false,
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
