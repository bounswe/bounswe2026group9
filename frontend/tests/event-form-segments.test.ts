import { describe, expect, it } from "vitest";

import {
  buildBestEffortEventUpdatePayload,
  buildEventCreatePayload,
  buildEventUpdatePayload,
  buildSegments,
  createDefaultEventFormValues,
  createEmptyLocation,
  mapEventToFormValues,
  validateStep,
  type EventFormValues,
  type EventLocationFormValue,
} from "@/lib/event-form";

function locationFixture(overrides: Partial<EventLocationFormValue> = {}): EventLocationFormValue {
  return createEmptyLocation({
    isPrimary: true,
    latitude: "41.0082",
    longitude: "28.9784",
    name: "Taksim Square",
    ...overrides,
  });
}

function valuesWithLocations(locations: EventLocationFormValue[]): EventFormValues {
  return {
    ...createDefaultEventFormValues(),
    locations,
    title: "Sample event",
    description: "Sample description",
    categoryIds: ["cat-1"],
  };
}

describe("event-form segments", () => {
  it("emits no segments when no stop has the timing toggle enabled", () => {
    const values = valuesWithLocations([locationFixture()]);
    expect(buildSegments(values)).toEqual([]);
  });

  it("ignores the timing payload when the toggle is off, even if dates are filled in", () => {
    const values = valuesWithLocations([
      locationFixture({
        segmentEnabled: false,
        segmentStartDate: "2026-06-01",
        segmentStartTime: "10:00",
        segmentEndDate: "2026-06-01",
        segmentEndTime: "11:00",
      }),
    ]);
    expect(buildSegments(values)).toEqual([]);
  });

  it("emits a segment with positional indices when timing is filled in", () => {
    const stop1 = locationFixture({ name: "Start" });
    const stop2 = locationFixture({
      isPrimary: false,
      name: "Coffee",
      segmentEnabled: true,
      segmentStartDate: "2026-06-01",
      segmentStartTime: "10:30",
      segmentEndDate: "2026-06-01",
      segmentEndTime: "11:00",
      segmentDescription: "Espresso break",
    });
    const values = valuesWithLocations([stop1, stop2]);

    const segments = buildSegments(values);
    expect(segments).toHaveLength(1);
    expect(segments[0]).toMatchObject({
      location_index: 1,
      order_index: 1,
      description: "Espresso break",
    });
    // ISO 8601, includes a T separator
    expect(segments[0].start_datetime).toMatch(/^2026-06-01T/);
    expect(segments[0].end_datetime).toMatch(/^2026-06-01T/);
  });

  it("drops empty descriptions to null", () => {
    const values = valuesWithLocations([
      locationFixture({
        segmentEnabled: true,
        segmentStartDate: "2026-06-01",
        segmentStartTime: "10:00",
        segmentEndDate: "2026-06-01",
        segmentEndTime: "11:00",
        segmentDescription: "   ",
      }),
    ]);
    expect(buildSegments(values)[0]?.description).toBeNull();
  });

  it("buildEventCreatePayload sends segments=null when none exist", () => {
    const values = valuesWithLocations([locationFixture()]);
    const payload = buildEventCreatePayload(values);
    expect(payload.segments).toBeNull();
  });

  it("buildEventCreatePayload sends segments[] when at least one stop has timing", () => {
    const values = valuesWithLocations([
      locationFixture({
        segmentEnabled: true,
        segmentStartDate: "2026-06-01",
        segmentStartTime: "09:00",
        segmentEndDate: "2026-06-01",
        segmentEndTime: "10:00",
      }),
    ]);
    const payload = buildEventCreatePayload(values);
    expect(payload.segments).not.toBeNull();
    expect(payload.segments?.[0].location_index).toBe(0);
  });

  it("buildEventUpdatePayload sends segments=null to clear an existing itinerary", () => {
    const values = valuesWithLocations([locationFixture()]);
    const payload = buildEventUpdatePayload(values);
    expect(payload.segments).toBeNull();
  });

  it("buildBestEffortEventUpdatePayload omits segments when itinerary is invalid", () => {
    const values = valuesWithLocations([
      locationFixture({
        segmentEnabled: true,
        // Reversed — invalid.
        segmentStartDate: "2026-06-01",
        segmentStartTime: "12:00",
        segmentEndDate: "2026-06-01",
        segmentEndTime: "11:00",
      }),
    ]);
    values.startDate = "2026-06-01";
    values.startTime = "08:00";
    values.endDate = "2026-06-01";
    values.endTime = "14:00";
    const payload = buildBestEffortEventUpdatePayload(values, 1);
    // Locations may still be emitted (no location-level error) but segments
    // must be skipped so the server-side itinerary isn't clobbered.
    expect(payload.segments).toBeUndefined();
  });

  it("buildBestEffortEventUpdatePayload emits segments when itinerary is valid", () => {
    const values = valuesWithLocations([
      locationFixture({
        segmentEnabled: true,
        segmentStartDate: "2026-06-01",
        segmentStartTime: "10:00",
        segmentEndDate: "2026-06-01",
        segmentEndTime: "11:00",
      }),
    ]);
    values.startDate = "2026-06-01";
    values.startTime = "08:00";
    values.endDate = "2026-06-01";
    values.endTime = "14:00";
    const payload = buildBestEffortEventUpdatePayload(values, 1);
    expect(payload.segments).toHaveLength(1);
    expect(payload.segments?.[0].location_index).toBe(0);
  });
});

describe("event-form step 2 validation", () => {
  it("flags partial stop timing as an error", () => {
    const values = valuesWithLocations([
      locationFixture({
        segmentEnabled: true,
        segmentStartDate: "2026-06-01",
        segmentStartTime: "",
        segmentEndDate: "",
        segmentEndTime: "",
      }),
    ]);
    const errors = validateStep(2, values, 1);
    expect(Object.keys(errors)).toContain(`segment-${values.locations[0].id}`);
  });

  it("flags reversed stop timing", () => {
    const values = valuesWithLocations([
      locationFixture({
        segmentEnabled: true,
        segmentStartDate: "2026-06-01",
        segmentStartTime: "12:00",
        segmentEndDate: "2026-06-01",
        segmentEndTime: "11:00",
      }),
    ]);
    const errors = validateStep(2, values, 1);
    expect(errors[`segment-${values.locations[0].id}`]).toMatch(/end must be after/i);
  });

  it("accepts a complete and ordered stop timing", () => {
    const values = valuesWithLocations([
      locationFixture({
        segmentEnabled: true,
        segmentStartDate: "2026-06-01",
        segmentStartTime: "09:00",
        segmentEndDate: "2026-06-01",
        segmentEndTime: "10:00",
      }),
    ]);
    // Set the event window so the segment falls inside it.
    values.startDate = "2026-06-01";
    values.startTime = "08:00";
    values.endDate = "2026-06-01";
    values.endTime = "12:00";
    const errors = validateStep(2, values, 1);
    expect(errors[`segment-${values.locations[0].id}`]).toBeUndefined();
  });

  it("rejects a segment that starts before the event start", () => {
    const values = valuesWithLocations([
      locationFixture({
        segmentEnabled: true,
        segmentStartDate: "2026-06-01",
        segmentStartTime: "07:00",
        segmentEndDate: "2026-06-01",
        segmentEndTime: "08:00",
      }),
    ]);
    values.startDate = "2026-06-01";
    values.startTime = "08:00";
    values.endDate = "2026-06-01";
    values.endTime = "12:00";
    const errors = validateStep(2, values, 1);
    expect(errors[`segment-${values.locations[0].id}`]).toMatch(/start after the event start/i);
  });

  it("rejects a segment that ends after the event end", () => {
    const values = valuesWithLocations([
      locationFixture({
        segmentEnabled: true,
        segmentStartDate: "2026-06-01",
        segmentStartTime: "11:00",
        segmentEndDate: "2026-06-01",
        segmentEndTime: "13:00",
      }),
    ]);
    values.startDate = "2026-06-01";
    values.startTime = "08:00";
    values.endDate = "2026-06-01";
    values.endTime = "12:00";
    const errors = validateStep(2, values, 1);
    expect(errors[`segment-${values.locations[0].id}`]).toMatch(/end before the event end/i);
  });

  it("flags two consecutive stops whose timings overlap", () => {
    const values = valuesWithLocations([
      locationFixture({
        name: "First",
        segmentEnabled: true,
        segmentStartDate: "2026-06-01",
        segmentStartTime: "09:00",
        segmentEndDate: "2026-06-01",
        segmentEndTime: "10:00",
      }),
      locationFixture({
        name: "Second",
        isPrimary: false,
        segmentEnabled: true,
        // Overlaps the first stop (09:30 < 10:00).
        segmentStartDate: "2026-06-01",
        segmentStartTime: "09:30",
        segmentEndDate: "2026-06-01",
        segmentEndTime: "10:30",
      }),
    ]);
    values.startDate = "2026-06-01";
    values.startTime = "08:00";
    values.endDate = "2026-06-01";
    values.endTime = "12:00";
    const errors = validateStep(2, values, 1);
    expect(errors[`segment-${values.locations[1].id}`]).toMatch(
      /Stop 2 must start at or after Stop 1 ends/i,
    );
  });

  it("does not clobber the per-stop error with the overlap error", () => {
    const values = valuesWithLocations([
      locationFixture({
        name: "First",
        segmentEnabled: true,
        segmentStartDate: "2026-06-01",
        segmentStartTime: "09:00",
        segmentEndDate: "2026-06-01",
        segmentEndTime: "10:00",
      }),
      locationFixture({
        name: "Second",
        isPrimary: false,
        segmentEnabled: true,
        // Both reversed (end < start) AND overlapping with stop 1.
        segmentStartDate: "2026-06-01",
        segmentStartTime: "11:00",
        segmentEndDate: "2026-06-01",
        segmentEndTime: "09:30",
      }),
    ]);
    values.startDate = "2026-06-01";
    values.startTime = "08:00";
    values.endDate = "2026-06-01";
    values.endTime = "12:00";
    const errors = validateStep(2, values, 1);
    // The reversed-timing message should win — overlap can't be assessed
    // when end < start, and it's the more actionable error.
    expect(errors[`segment-${values.locations[1].id}`]).toMatch(/end must be after/i);
  });

  it("flags missing primary location lat/lng", () => {
    const values = valuesWithLocations([locationFixture({ latitude: "", longitude: "" })]);
    const errors = validateStep(2, values, 1);
    expect(errors[`location-latitude-${values.locations[0].id}`]).toBeTruthy();
    expect(errors[`location-longitude-${values.locations[0].id}`]).toBeTruthy();
  });
});

describe("event-form mapping", () => {
  it("rehydrates segment timing per location when reopening an event for editing", () => {
    const values = mapEventToFormValues({
      id: "evt",
      host_id: "host",
      title: "Walk",
      description: "A short walk",
      start_datetime: "2026-06-01T09:00:00Z",
      end_datetime: "2026-06-01T12:00:00Z",
      visibility: "public",
      is_age_restricted: false,
      attendee_limit: null,
      attendee_count: 0,
      status: "draft",
      created_at: "2026-05-01T00:00:00Z",
      updated_at: "2026-05-01T00:00:00Z",
      is_bookmarked: null,
      attendance_status: null,
      going_count: 0,
      bookmark_count: 0,
      is_full: null,
      categories: [{ id: "c1", name: "Outdoor", is_predefined: true, is_approved: true }],
      images: [],
      equipment_requirements: [],
      venue_metadata: null,
      locations: [
        {
          id: "loc-a",
          is_primary: true,
          latitude: 41.0,
          longitude: 28.9,
          name: "Start",
          order_index: 0,
        },
        {
          id: "loc-b",
          is_primary: false,
          latitude: 41.05,
          longitude: 28.95,
          name: "End",
          order_index: 1,
        },
      ],
      segments: [
        {
          id: "seg-1",
          location_id: "loc-b",
          order_index: 1,
          start_datetime: "2026-06-01T10:00:00Z",
          end_datetime: "2026-06-01T11:00:00Z",
          description: "Park stop",
        },
      ],
    });

    expect(values.locations).toHaveLength(2);
    expect(values.locations[0].segmentEnabled).toBe(false);
    expect(values.locations[1].segmentEnabled).toBe(true);
    expect(values.locations[1].segmentDescription).toBe("Park stop");
    expect(values.locations[1].segmentStartDate).toBe("2026-06-01");
  });
});
