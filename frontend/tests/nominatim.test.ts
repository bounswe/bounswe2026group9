import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { reverseGeocode, suggestPlaces } from "@/lib/nominatim";

function jsonOk(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("suggestPlaces", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("hits the local proxy with the encoded query and the requested limit", async () => {
    fetchMock.mockResolvedValueOnce(jsonOk([]));
    await suggestPlaces("Kadıköy, Istanbul", 4);
    const call = fetchMock.mock.calls[0];
    expect(String(call[0])).toBe("/api/geo/search?q=Kad%C4%B1k%C3%B6y%2C%20Istanbul&limit=4");
  });

  it("returns an empty list for blank queries without calling fetch", async () => {
    const result = await suggestPlaces("   ");
    expect(result).toEqual([]);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("maps Nominatim entries into typed results and prefers a short, friendly name", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonOk([
        {
          display_name: "Bebek Park, Beşiktaş, Istanbul, Türkiye",
          lat: "41.0763",
          lon: "29.0395",
          address: { amenity: "Bebek Park", suburb: "Beşiktaş", city: "Istanbul" },
        },
      ]),
    );
    const result = await suggestPlaces("Bebek");
    expect(result).toHaveLength(1);
    expect(result[0]).toMatchObject({
      shortName: "Bebek Park, Beşiktaş",
      lat: 41.0763,
      lng: 29.0395,
    });
  });

  it("filters out entries with non-numeric coordinates", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonOk([
        { display_name: "good", lat: "1.0", lon: "2.0" },
        { display_name: "broken", lat: "abc", lon: "2.0" },
      ]),
    );
    const result = await suggestPlaces("anything");
    expect(result).toHaveLength(1);
    expect(result[0].lat).toBe(1.0);
  });

  it("returns an empty list on upstream error responses", async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 500 }));
    expect(await suggestPlaces("anything")).toEqual([]);
  });

  it("returns an empty list when fetch throws", async () => {
    fetchMock.mockRejectedValueOnce(new Error("network"));
    expect(await suggestPlaces("anything")).toEqual([]);
  });
});

describe("reverseGeocode", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("hits /api/geo/reverse with both coordinates", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonOk({ display_name: "Beşiktaş Sahili, Beşiktaş, Istanbul" }),
    );
    const result = await reverseGeocode(41.04, 29.005);
    expect(String(fetchMock.mock.calls[0][0])).toBe("/api/geo/reverse?lat=41.04&lng=29.005");
    expect(result).toBe("Beşiktaş Sahili, Beşiktaş, Istanbul");
  });

  it("trims to the first three comma-separated parts and caps length at 100", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonOk({
        display_name: `${"a".repeat(60)}, ${"b".repeat(60)}, ${"c".repeat(60)}, more, parts`,
      }),
    );
    const result = await reverseGeocode(0, 0);
    expect(result).not.toBeNull();
    expect(result!.length).toBeLessThanOrEqual(100);
    // We took the first three segments only — `more` should be excluded.
    expect(result).not.toMatch(/more/);
  });

  it("returns null when the upstream returns an empty display_name", async () => {
    fetchMock.mockResolvedValueOnce(jsonOk({ display_name: null }));
    expect(await reverseGeocode(0, 0)).toBeNull();
  });

  it("returns null on fetch error", async () => {
    fetchMock.mockRejectedValueOnce(new Error("network"));
    expect(await reverseGeocode(0, 0)).toBeNull();
  });
});
