import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { fetchEvents, fetchGeoJsonEvents, type DiscoveryParams } from "@/lib/events-api";

function lastFetchUrl(fetchMock: ReturnType<typeof vi.fn>): string {
  const call = fetchMock.mock.calls.at(-1);
  if (!call) throw new Error("fetch was not called");
  return String(call[0]);
}

function emptyOk(): Response {
  return new Response(JSON.stringify({ items: [], total: 0, page: 1, page_size: 20, total_pages: 0 }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

function emptyGeo(): Response {
  return new Response(JSON.stringify({ type: "FeatureCollection", features: [] }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("fetchEvents URL construction", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn().mockImplementation(() => Promise.resolve(emptyOk()));
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("omits all params when none are set", async () => {
    await fetchEvents();
    expect(lastFetchUrl(fetchMock)).toMatch(/\/events$/);
  });

  it("serialises quick_filter, sort and pagination", async () => {
    await fetchEvents({
      quick_filter: "weekend",
      sort: "category",
      page: 2,
      page_size: 50,
    });
    const url = new URL(lastFetchUrl(fetchMock), "http://localhost");
    expect(url.searchParams.get("quick_filter")).toBe("weekend");
    expect(url.searchParams.get("sort")).toBe("category");
    expect(url.searchParams.get("page")).toBe("2");
    expect(url.searchParams.get("page_size")).toBe("50");
  });

  it("treats temporal_filter as an alias for quick_filter", async () => {
    await fetchEvents({ temporal_filter: "today" });
    const url = new URL(lastFetchUrl(fetchMock), "http://localhost");
    expect(url.searchParams.get("quick_filter")).toBe("today");
    expect(url.searchParams.has("temporal_filter")).toBe(false);
  });

  it("only includes truthy accessibility flags", async () => {
    const params: DiscoveryParams = {
      accessibility: {
        wheelchair: true,
        accessible_restroom: false,
        elevator: true,
        seating: undefined,
        captions: false,
        quiet_friendly: true,
      },
    };
    await fetchEvents(params);
    const url = new URL(lastFetchUrl(fetchMock), "http://localhost");
    expect(url.searchParams.get("wheelchair")).toBe("true");
    expect(url.searchParams.get("elevator")).toBe("true");
    expect(url.searchParams.get("quiet_friendly")).toBe("true");
    expect(url.searchParams.has("accessible_restroom")).toBe(false);
    expect(url.searchParams.has("seating")).toBe(false);
    expect(url.searchParams.has("captions")).toBe(false);
  });

  it("forwards proximity coords and use_default_area", async () => {
    await fetchEvents({ near_lat: 41.01, near_lng: 28.97, radius_km: 5 });
    let url = new URL(lastFetchUrl(fetchMock), "http://localhost");
    expect(url.searchParams.get("near_lat")).toBe("41.01");
    expect(url.searchParams.get("near_lng")).toBe("28.97");
    expect(url.searchParams.get("radius_km")).toBe("5");

    await fetchEvents({ use_default_area: true });
    url = new URL(lastFetchUrl(fetchMock), "http://localhost");
    expect(url.searchParams.get("use_default_area")).toBe("true");
  });

  it("trims whitespace-only search to nothing", async () => {
    await fetchEvents({ search: "   " });
    const url = new URL(lastFetchUrl(fetchMock), "http://localhost");
    expect(url.searchParams.has("search")).toBe(false);
  });
});

describe("fetchGeoJsonEvents URL construction", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn().mockImplementation(() => Promise.resolve(emptyGeo()));
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("forwards quick_filter and accessibility flags to /events/geojson", async () => {
    await fetchGeoJsonEvents({
      quick_filter: "this_week",
      accessibility: { wheelchair: true },
      sort: "distance",
    });
    const url = new URL(lastFetchUrl(fetchMock), "http://localhost");
    expect(url.pathname).toContain("/events/geojson");
    expect(url.searchParams.get("quick_filter")).toBe("this_week");
    expect(url.searchParams.get("wheelchair")).toBe("true");
    expect(url.searchParams.get("sort")).toBe("distance");
  });
});
