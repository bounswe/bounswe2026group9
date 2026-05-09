import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { checkInAttendee, fetchEventAttendees, fetchMyAttendeeQr } from "@/lib/events-api";
import { setAuthenticatedSession } from "@/lib/session";

const EVENT_ID = "11111111-1111-1111-1111-111111111111";
const USER_ID = "22222222-2222-2222-2222-222222222222";
const ATTENDEE_ID = "33333333-3333-3333-3333-333333333333";

function jsonOk(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function lastCall(fetchMock: ReturnType<typeof vi.fn>) {
  const call = fetchMock.mock.calls.at(-1);
  if (!call) throw new Error("fetch was not called");
  const [url, init] = call as [string, RequestInit];
  return { url: String(url), init };
}

describe("QR check-in endpoints", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    setAuthenticatedSession({
      access_token: "tok",
      token_type: "bearer",
      user: {
        id: USER_ID,
        username: "host",
        email: "host@example.com",
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

  it("fetchMyAttendeeQr GETs /attendances/me/{event_id}/qr with the auth header", async () => {
    fetchMock.mockResolvedValueOnce(jsonOk({ token: "signed.payload.value", expires_at: null }));
    const result = await fetchMyAttendeeQr(EVENT_ID);
    const { url, init } = lastCall(fetchMock);
    expect(url).toContain(`/attendances/me/${EVENT_ID}/qr`);
    expect(init.method ?? "GET").toBe("GET");
    const headers = new Headers(init.headers);
    expect(headers.get("Authorization")).toBe("Bearer tok");
    expect(result.token).toBe("signed.payload.value");
  });

  it("fetchEventAttendees GETs /events/{event_id}/attendees", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonOk([
        { user_id: ATTENDEE_ID, username: "alice", checked_in_at: null },
        { user_id: USER_ID, username: "bob", checked_in_at: "2026-06-01T18:00:00Z" },
      ]),
    );
    const result = await fetchEventAttendees(EVENT_ID);
    const { url } = lastCall(fetchMock);
    expect(url).toContain(`/events/${EVENT_ID}/attendees`);
    expect(result).toHaveLength(2);
    expect(result[1].checked_in_at).toBe("2026-06-01T18:00:00Z");
  });

  it("checkInAttendee POSTs the user_id manual fallback body", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonOk({
        user_id: ATTENDEE_ID,
        username: "alice",
        checked_in_at: "2026-06-01T18:00:00Z",
      }),
    );
    const result = await checkInAttendee(EVENT_ID, { user_id: ATTENDEE_ID });
    const { url, init } = lastCall(fetchMock);
    expect(url).toContain(`/events/${EVENT_ID}/check-in`);
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({ user_id: ATTENDEE_ID });
    expect(result.checked_in_at).toBe("2026-06-01T18:00:00Z");
  });

  it("checkInAttendee forwards the scanned token when given", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonOk({
        user_id: ATTENDEE_ID,
        username: "alice",
        checked_in_at: "2026-06-01T18:00:00Z",
      }),
    );
    await checkInAttendee(EVENT_ID, { token: "signed.payload" });
    const { init } = lastCall(fetchMock);
    expect(JSON.parse(init.body as string)).toEqual({ token: "signed.payload" });
  });
});
