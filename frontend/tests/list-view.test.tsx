import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ListView } from "@/components/discovery/list-view";
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

function makeEvent(id: string, title: string): EventListItem {
  return {
    id,
    host_id: "host",
    title,
    description: null,
    start_datetime: "2026-06-01T18:00:00Z",
    end_datetime: "2026-06-01T20:00:00Z",
    visibility: "public",
    is_age_restricted: false,
    attendee_limit: null,
    attendee_count: 0,
    status: "published",
    is_bookmarked: false,
    attendance_status: null,
    access_request_status: null,
    has_access: null,
    going_count: 0,
    bookmark_count: 0,
    is_full: false,
    categories: [],
    primary_location: null,
    primary_image_url: null,
  };
}

afterEach(() => {
  cleanup();
});

describe("ListView", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(new Response(null, { status: 204 }))),
    );
  });

  it("shows the 'No events found' empty state when there are no items", () => {
    render(
      <ListView
        events={[]}
        currentUserId={null}
        isAuthenticated={false}
        total={0}
        page={1}
        totalPages={0}
        onPageChange={vi.fn()}
      />,
    );
    expect(screen.getByText(/no events found/i)).toBeInTheDocument();
    expect(screen.getByText(/adjust(ing)? your filters/i)).toBeInTheDocument();
  });

  it("renders one card per event and a result count summary", () => {
    const events = [makeEvent("a", "Alpha"), makeEvent("b", "Bravo")];
    render(
      <ListView
        events={events}
        currentUserId={null}
        isAuthenticated={false}
        total={2}
        page={1}
        totalPages={1}
        onPageChange={vi.fn()}
      />,
    );
    expect(screen.getByRole("heading", { name: "Alpha" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Bravo" })).toBeInTheDocument();
    expect(screen.getByText(/showing/i)).toHaveTextContent("Showing 2 of 2 events");
  });

  it("does not render pagination controls when there is a single page", () => {
    render(
      <ListView
        events={[makeEvent("a", "Alpha")]}
        currentUserId={null}
        isAuthenticated={false}
        total={1}
        page={1}
        totalPages={1}
        onPageChange={vi.fn()}
      />,
    );
    expect(screen.queryByRole("button", { name: /^1$/ })).toBeNull();
  });

  it("calls onPageChange when a page number is clicked", async () => {
    const onPageChange = vi.fn();
    render(
      <ListView
        events={[makeEvent("a", "Alpha")]}
        currentUserId={null}
        isAuthenticated={false}
        total={36}
        page={1}
        totalPages={3}
        onPageChange={onPageChange}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Go to page 2" }));
    expect(onPageChange).toHaveBeenCalledWith(2);
  });
});
