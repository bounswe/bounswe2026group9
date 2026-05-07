import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  addBookmark,
  changeEventStatus,
  deleteComment,
  deleteEvent,
  fetchComments,
  fetchEventDetail,
  fetchHostProfile,
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  postComment,
  removeAttendance,
  removeBookmark,
  setAttendance,
} from "@/lib/events-api";
import { setAuthenticatedSession } from "@/lib/session";

const EVENT_ID = "11111111-1111-1111-1111-111111111111";
const USER_ID = "22222222-2222-2222-2222-222222222222";
const NOTIF_ID = "33333333-3333-3333-3333-333333333333";

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

describe("events-api endpoints", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn().mockImplementation(() => Promise.resolve(jsonOk({})));
    vi.stubGlobal("fetch", fetchMock);
    setAuthenticatedSession({
      access_token: "tok",
      token_type: "bearer",
      user: {
        id: USER_ID,
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

  it("fetchEventDetail issues a GET against /events/{id}", async () => {
    fetchMock.mockImplementationOnce(() =>
      Promise.resolve(jsonOk({ id: EVENT_ID, host_id: USER_ID, title: "x" })),
    );
    await fetchEventDetail(EVENT_ID);
    const { url, init } = lastCall(fetchMock);
    expect(url).toContain(`/events/${EVENT_ID}`);
    expect(init.method ?? "GET").toBe("GET");
  });

  it("setAttendance posts {status: 'going'} to the attendance endpoint", async () => {
    await setAttendance(EVENT_ID, "going");
    const { url, init } = lastCall(fetchMock);
    expect(url).toContain(`/events/${EVENT_ID}/attendance`);
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({ status: "going" });
  });

  it("removeAttendance issues a DELETE", async () => {
    await removeAttendance(EVENT_ID);
    const { url, init } = lastCall(fetchMock);
    expect(url).toContain(`/events/${EVENT_ID}/attendance`);
    expect(init.method).toBe("DELETE");
  });

  it("addBookmark and removeBookmark hit /events/{id}/bookmark with POST/DELETE", async () => {
    await addBookmark(EVENT_ID);
    let call = lastCall(fetchMock);
    expect(call.url).toContain(`/events/${EVENT_ID}/bookmark`);
    expect(call.init.method).toBe("POST");

    await removeBookmark(EVENT_ID);
    call = lastCall(fetchMock);
    expect(call.url).toContain(`/events/${EVENT_ID}/bookmark`);
    expect(call.init.method).toBe("DELETE");
  });

  it("changeEventStatus PATCHes /events/{id}/status with the requested status", async () => {
    await changeEventStatus(EVENT_ID, "cancelled");
    const { url, init } = lastCall(fetchMock);
    expect(url).toContain(`/events/${EVENT_ID}/status`);
    expect(init.method).toBe("PATCH");
    expect(JSON.parse(init.body as string)).toEqual({ status: "cancelled" });
  });

  it("deleteEvent DELETEs /events/{id}", async () => {
    await deleteEvent(EVENT_ID);
    const { url, init } = lastCall(fetchMock);
    expect(url).toContain(`/events/${EVENT_ID}`);
    expect(init.method).toBe("DELETE");
  });

  it("fetchComments GETs /events/{id}/comments", async () => {
    fetchMock.mockImplementationOnce(() => Promise.resolve(jsonOk({ items: [], total: 0 })));
    await fetchComments(EVENT_ID);
    const { url } = lastCall(fetchMock);
    expect(url).toContain(`/events/${EVENT_ID}/comments`);
  });

  it("postComment POSTs the text and forwards parent_id when given", async () => {
    fetchMock.mockImplementation(() =>
      Promise.resolve(
        jsonOk({
          id: "c",
          user: { id: USER_ID, username: "t" },
          text: "hi",
          created_at: "x",
          event_id: EVENT_ID,
          parent_id: null,
          replies: [],
        }),
      ),
    );
    await postComment(EVENT_ID, "hi");
    expect(JSON.parse(lastCall(fetchMock).init.body as string)).toEqual({ text: "hi" });

    await postComment(EVENT_ID, "reply", "parent-id");
    expect(JSON.parse(lastCall(fetchMock).init.body as string)).toEqual({
      text: "reply",
      parent_id: "parent-id",
    });
  });

  it("deleteComment DELETEs /events/{id}/comments/{commentId}", async () => {
    await deleteComment(EVENT_ID, "comment-1");
    const { url, init } = lastCall(fetchMock);
    expect(url).toContain(`/events/${EVENT_ID}/comments/comment-1`);
    expect(init.method).toBe("DELETE");
  });

  it("fetchHostProfile GETs /users/{id}/profile", async () => {
    fetchMock.mockImplementationOnce(() =>
      Promise.resolve(
        jsonOk({ id: USER_ID, username: "host", hosted_events: [], can_rate: false }),
      ),
    );
    await fetchHostProfile(USER_ID);
    const { url } = lastCall(fetchMock);
    expect(url).toContain(`/users/${USER_ID}/profile`);
  });

  it("fetchNotifications passes pagination and requires auth", async () => {
    fetchMock.mockImplementationOnce(() =>
      Promise.resolve(
        jsonOk({ items: [], total: 0, unread_count: 0, page: 2, page_size: 5, total_pages: 0 }),
      ),
    );
    await fetchNotifications(2, 5);
    const { url, init } = lastCall(fetchMock);
    expect(url).toContain("/notifications?page=2&page_size=5");
    const headers = new Headers(init.headers);
    expect(headers.get("Authorization")).toBe("Bearer tok");
  });

  it("markNotificationRead PATCHes /notifications/{id}/read", async () => {
    fetchMock.mockImplementationOnce(() =>
      Promise.resolve(jsonOk({ id: NOTIF_ID, is_read: true })),
    );
    await markNotificationRead(NOTIF_ID);
    const { url, init } = lastCall(fetchMock);
    expect(url).toContain(`/notifications/${NOTIF_ID}/read`);
    expect(init.method).toBe("PATCH");
  });

  it("markAllNotificationsRead PATCHes /notifications/read-all", async () => {
    fetchMock.mockImplementationOnce(() => Promise.resolve(jsonOk({ updated_count: 3 })));
    await markAllNotificationsRead();
    const { url, init } = lastCall(fetchMock);
    expect(url).toContain("/notifications/read-all");
    expect(init.method).toBe("PATCH");
  });
});
