import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SimilarEventsSection } from "@/components/event/similar-events";
import type * as EventsApiModule from "@/lib/events-api";
import type { EventListItem } from "@/lib/events-api";

const { fetchSimilarEventsMock } = vi.hoisted(() => ({
  fetchSimilarEventsMock: vi.fn<typeof EventsApiModule.fetchSimilarEvents>(),
}));

vi.mock("@/lib/events-api", async () => {
  const actual = await vi.importActual<typeof EventsApiModule>("@/lib/events-api");
  return { ...actual, fetchSimilarEvents: fetchSimilarEventsMock };
});

function makeEvent(overrides: Partial<EventListItem> = {}): EventListItem {
  return {
    id: "ev-similar-1",
    host_id: "host-1",
    title: "Galata Tower Sunset Walk",
    description: null,
    start_datetime: "2026-07-04T18:00:00Z",
    end_datetime: "2026-07-04T20:00:00Z",
    visibility: "public",
    is_age_restricted: false,
    attendee_limit: 30,
    attendee_count: 4,
    status: "published",
    is_bookmarked: null,
    attendance_status: null,
    access_request_status: null,
    has_access: null,
    going_count: 4,
    bookmark_count: 2,
    is_full: false,
    categories: [{ id: "c-1", name: "Outdoor", is_predefined: true, is_approved: true }],
    primary_location: null,
    primary_image_url: null,
    ...overrides,
  };
}

afterEach(() => {
  cleanup();
  fetchSimilarEventsMock.mockReset();
});

describe("SimilarEventsSection", () => {
  beforeEach(() => {
    fetchSimilarEventsMock.mockResolvedValue([]);
  });

  it("renders nothing once an empty list resolves", async () => {
    fetchSimilarEventsMock.mockResolvedValueOnce([]);
    const { container } = render(<SimilarEventsSection eventId="src-event" />);
    await waitFor(() => expect(container.querySelector("section")).toBeNull());
  });

  it("hides the section when the request fails", async () => {
    fetchSimilarEventsMock.mockRejectedValueOnce(new Error("boom"));
    const { container } = render(<SimilarEventsSection eventId="src-event" />);
    await waitFor(() => expect(container.querySelector("section")).toBeNull());
  });

  it("renders a card per similar event with the correct detail link", async () => {
    fetchSimilarEventsMock.mockResolvedValueOnce([
      makeEvent({ id: "a", title: "Alpha event" }),
      makeEvent({ id: "b", title: "Beta event" }),
    ]);
    render(<SimilarEventsSection eventId="src-event" />);

    expect(await screen.findByRole("heading", { name: /similar events/i })).toBeInTheDocument();
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(2);
    const links = screen.getAllByRole("link");
    expect(links[0]).toHaveAttribute("href", "/event/a");
    expect(links[1]).toHaveAttribute("href", "/event/b");
    expect(screen.getByText("Alpha event")).toBeInTheDocument();
    expect(screen.getByText("Beta event")).toBeInTheDocument();
  });

  it("shows the primary category when present, otherwise the location name", async () => {
    fetchSimilarEventsMock.mockResolvedValueOnce([
      makeEvent({
        id: "with-cat",
        title: "With category",
        categories: [{ id: "c-1", name: "Music", is_predefined: true, is_approved: true }],
      }),
      makeEvent({
        id: "no-cat",
        title: "No category",
        categories: [],
        primary_location: {
          id: "loc-1",
          name: "Karaköy",
          latitude: 41.0,
          longitude: 28.9,
          is_primary: true,
          order_index: 0,
        },
      }),
    ]);
    render(<SimilarEventsSection eventId="src-event" />);

    expect(await screen.findByText("Music")).toBeInTheDocument();
    expect(screen.getByText("Karaköy")).toBeInTheDocument();
  });
});
