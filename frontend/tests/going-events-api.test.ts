import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { fetchMyGoingEvents } from "@/lib/events-api";
import { setAuthenticatedSession } from "@/lib/session";

const USER_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";

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

function makeEventListItem(overrides: Record<string, unknown> = {}) {
  return {
    id: "ev-1",
    host_id: "host-1",
    title: "Yoga in the Park",
    description: null,
    start_datetime: "2026-07-10T09:00:00Z",
    end_datetime: "2026-07-10T10:00:00Z",
    visibility: "public",
    is_age_restricted: false,
    attendee_limit: 20,
    attendee_count: 5,
    status: "published",
    is_bookmarked: null,
    attendance_status: "going",
    access_request_status: null,
    has_access: null,
    going_count: 5,
    bookmark_count: 1,
    is_full: false,
    categories: [{ id: "c-1", name: "Sport", is_predefined: true, is_approved: true }],
    primary_location: {
      id: "loc-1",
      name: "Central Park",
      latitude: 40.78,
      longitude: -73.96,
      is_primary: true,
      order_index: 0,
    },
    primary_image_url: null,
    ...overrides,
  };
}

describe("fetchMyGoingEvents", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    setAuthenticatedSession({
      access_token: "test-token",
      token_type: "bearer",
      user: {
        id: USER_ID,
        username: "testuser",
        email: "test@example.com",
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

  it("GETs /attendances/me/events with the auth header", async () => {
    fetchMock.mockResolvedValueOnce(jsonOk([]));
    await fetchMyGoingEvents();
    const { url, init } = lastCall(fetchMock);
    expect(url).toContain("/attendances/me/events");
    expect(init.method ?? "GET").toBe("GET");
    const headers = new Headers(init.headers);
    expect(headers.get("Authorization")).toBe("Bearer test-token");
  });

  it("returns the parsed list of going events", async () => {
    const events = [
      makeEventListItem({ id: "ev-1", title: "Yoga in the Park" }),
      makeEventListItem({ id: "ev-2", title: "Evening Run" }),
    ];
    fetchMock.mockResolvedValueOnce(jsonOk(events));
    const result = await fetchMyGoingEvents();
    expect(result).toHaveLength(2);
    expect(result[0].title).toBe("Yoga in the Park");
    expect(result[1].title).toBe("Evening Run");
  });

  it("returns an empty array when the user has no going events", async () => {
    fetchMock.mockResolvedValueOnce(jsonOk([]));
    const result = await fetchMyGoingEvents();
    expect(result).toEqual([]);
  });
});
