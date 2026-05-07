import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { EventCard } from "@/components/discovery/event-card";
import type { EventListItem } from "@/lib/events-api";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
}));

vi.mock("@/hooks/use-event-interaction", () => ({
  useEventInteraction: () => ({
    bookmarked: false,
    bookmarkCount: 0,
    going: false,
    goingCount: 0,
    toggleBookmark: vi.fn(),
    toggleGoing: vi.fn(),
  }),
}));

function makeEvent(overrides: Partial<EventListItem> = {}): EventListItem {
  return {
    id: "ev-1",
    host_id: "host-1",
    title: "Bebek Sahil Yürüyüşü",
    description: "A scenic walk along the Bosphorus.",
    start_datetime: "2026-06-01T18:00:00Z",
    end_datetime: "2026-06-01T20:00:00Z",
    visibility: "public",
    is_age_restricted: false,
    attendee_limit: 20,
    attendee_count: 5,
    status: "published",
    is_bookmarked: false,
    attendance_status: null,
    access_request_status: null,
    has_access: null,
    going_count: 5,
    bookmark_count: 1,
    is_full: false,
    categories: [{ id: "cat-1", name: "Outdoor", is_predefined: true, is_approved: true }],
    primary_location: null,
    primary_image_url: null,
    ...overrides,
  };
}

afterEach(() => {
  cleanup();
});

describe("EventCard", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(new Response(null, { status: 204 }))),
    );
  });

  it("renders the event title and category chip", () => {
    render(<EventCard event={makeEvent()} currentUserId={null} isAuthenticated={false} />);
    expect(screen.getByRole("heading", { name: "Bebek Sahil Yürüyüşü" })).toBeInTheDocument();
    expect(screen.getByText("Outdoor")).toBeInTheDocument();
  });

  it("links to the event detail page", () => {
    render(<EventCard event={makeEvent()} currentUserId={null} isAuthenticated={false} />);
    const link = screen.getAllByRole("link")[0];
    expect(link).toHaveAttribute("href", "/event/ev-1");
  });

  it("hides Going / Bookmark actions for guests", () => {
    render(<EventCard event={makeEvent()} currentUserId={null} isAuthenticated={false} />);
    expect(screen.queryByRole("button", { name: /going/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /bookmark/i })).toBeNull();
  });

  it("shows Going + Bookmark for authenticated non-host users", () => {
    render(
      <EventCard
        event={makeEvent({ host_id: "someone-else" })}
        currentUserId="me"
        isAuthenticated
      />,
    );
    expect(screen.getByRole("button", { name: /going/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /bookmark/i })).toBeInTheDocument();
  });

  it("shows Edit instead of Going when the viewer is the host", () => {
    render(<EventCard event={makeEvent({ host_id: "me" })} currentUserId="me" isAuthenticated />);
    expect(screen.getByRole("button", { name: /edit/i })).toBeInTheDocument();
  });

  it("renders the Private badge for private events", () => {
    render(
      <EventCard
        event={makeEvent({ visibility: "private" })}
        currentUserId={null}
        isAuthenticated={false}
      />,
    );
    expect(screen.getByText(/private/i)).toBeInTheDocument();
  });

  it("renders the Full badge when capacity is reached", () => {
    render(
      <EventCard
        event={makeEvent({ is_full: true, attendee_count: 20 })}
        currentUserId={null}
        isAuthenticated={false}
      />,
    );
    expect(screen.getByText(/full/i)).toBeInTheDocument();
  });
});
