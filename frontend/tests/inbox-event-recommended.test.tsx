import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { NotificationItem, getNotificationIcon } from "@/app/inbox/page";
import type { Notification } from "@/lib/events-api";

const { pushMock } = vi.hoisted(() => ({ pushMock: vi.fn<(href: string) => void>() }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

function makeNotification(overrides: Partial<Notification> = {}): Notification {
  return {
    id: "n-1",
    user_id: "u-1",
    event_id: "ev-42",
    type: "event_recommended",
    message: "Based on events you attended in Music",
    is_read: false,
    created_at: "2026-05-09T10:00:00Z",
    ...overrides,
  };
}

afterEach(() => {
  cleanup();
  pushMock.mockReset();
});

describe("getNotificationIcon", () => {
  it("returns the Sparkles-decorated styling for event_recommended", () => {
    const unread = getNotificationIcon("event_recommended", false);
    expect(unread.bg).toBe("bg-brand-dark");
    expect(unread.fg).toBe("text-white");

    const read = getNotificationIcon("event_recommended", true);
    expect(read.bg).toContain("brand-dark");
    expect(read.fg).toContain("brand-dark");
  });

  it("falls back to the bell icon for unknown types", () => {
    const fallback = getNotificationIcon("totally_made_up_type", false);
    expect(fallback.bg).toContain("brand-mid");
  });
});

describe("NotificationItem", () => {
  beforeEach(() => {
    pushMock.mockReset();
  });

  it("renders the 'Recommended for you' pill for event_recommended", () => {
    render(<NotificationItem notification={makeNotification()} onMarkRead={vi.fn()} />);
    expect(screen.getByText(/recommended for you/i)).toBeInTheDocument();
    expect(screen.getByText("Based on events you attended in Music")).toBeInTheDocument();
  });

  it("does NOT render the pill for non-recommendation notification types", () => {
    render(
      <NotificationItem
        notification={makeNotification({ type: "event_updated", message: "Event updated" })}
        onMarkRead={vi.fn()}
      />,
    );
    expect(screen.queryByText(/recommended for you/i)).toBeNull();
    expect(screen.getByText("Event updated")).toBeInTheDocument();
  });

  it("marks the notification as read and navigates to the event on click", () => {
    const onMarkRead = vi.fn();
    render(<NotificationItem notification={makeNotification()} onMarkRead={onMarkRead} />);
    screen.getByText("Based on events you attended in Music").click();
    expect(onMarkRead).toHaveBeenCalledWith("n-1");
    expect(pushMock).toHaveBeenCalledWith("/event/ev-42");
  });

  it("skips navigation when event_id is null but still marks as read", () => {
    const onMarkRead = vi.fn();
    render(
      <NotificationItem
        notification={makeNotification({ event_id: null })}
        onMarkRead={onMarkRead}
      />,
    );
    screen.getByText("Based on events you attended in Music").click();
    expect(onMarkRead).toHaveBeenCalledWith("n-1");
    expect(pushMock).not.toHaveBeenCalled();
  });
});
