import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ItineraryTimeline } from "@/components/event/itinerary-timeline";
import type { EventLocation, EventSegment } from "@/lib/events-api";

// The route map pulls MapLibre + WebGL via dynamic import, which jsdom can't
// render. Stub it with a placeholder so the timeline rows are the focus.
vi.mock("@/components/events/route-map", () => ({
  RouteMap: ({ stops }: { stops: { id: string }[] }) => (
    <div data-testid="route-map" data-stop-count={stops.length} />
  ),
}));

afterEach(() => cleanup());

const HOST_LOC: EventLocation = {
  id: "loc-1",
  name: "Taksim Square",
  latitude: 41.0369,
  longitude: 28.9851,
  is_primary: true,
  order_index: 0,
  location_address: "Taksim, Istanbul",
};

const STOP_LOC: EventLocation = {
  id: "loc-2",
  name: "Galata Tower",
  latitude: 41.0256,
  longitude: 28.9742,
  is_primary: false,
  order_index: 1,
};

const STOP_SEGMENT: EventSegment = {
  id: "seg-1",
  location_id: "loc-2",
  order_index: 1,
  start_datetime: "2026-06-01T10:00:00Z",
  end_datetime: "2026-06-01T10:45:00Z",
  description: "Tower visit",
};

describe("ItineraryTimeline", () => {
  it("renders one row per stop, in order_index order", () => {
    render(<ItineraryTimeline locations={[STOP_LOC, HOST_LOC]} segments={[]} />);
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(within(items[0]).getByText("Taksim Square")).toBeInTheDocument();
    expect(within(items[1]).getByText("Galata Tower")).toBeInTheDocument();
  });

  it("marks the primary stop with a Primary badge", () => {
    render(<ItineraryTimeline locations={[HOST_LOC, STOP_LOC]} segments={[]} />);
    expect(screen.getByText(/primary/i)).toBeInTheDocument();
  });

  it("shows the segment description when a matching segment exists", () => {
    render(<ItineraryTimeline locations={[HOST_LOC, STOP_LOC]} segments={[STOP_SEGMENT]} />);
    expect(screen.getByText("Tower visit")).toBeInTheDocument();
  });

  it("renders the address when location_address is present", () => {
    render(<ItineraryTimeline locations={[HOST_LOC]} segments={[]} />);
    expect(screen.getByText("Taksim, Istanbul")).toBeInTheDocument();
  });

  it("forwards every stop to the route map preview", () => {
    render(<ItineraryTimeline locations={[HOST_LOC, STOP_LOC]} segments={[]} />);
    const map = screen.getByTestId("route-map");
    expect(map).toHaveAttribute("data-stop-count", "2");
  });

  it("hides the route map when hideMap is set", () => {
    render(<ItineraryTimeline locations={[HOST_LOC]} segments={[]} hideMap />);
    expect(screen.queryByTestId("route-map")).toBeNull();
  });
});
