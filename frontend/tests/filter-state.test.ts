import { describe, expect, it } from "vitest";

import {
  DEFAULT_FILTER_STATE,
  countActiveFilters,
  type FilterState,
} from "@/components/discovery/filter-sidebar";

function withDefaults(overrides: Partial<FilterState>): FilterState {
  return { ...DEFAULT_FILTER_STATE, ...overrides };
}

describe("countActiveFilters", () => {
  it("returns 0 for the default state", () => {
    expect(countActiveFilters(DEFAULT_FILTER_STATE)).toBe(0);
  });

  it("counts each category id once", () => {
    expect(countActiveFilters(withDefaults({ categoryIds: ["a", "b", "c"] }))).toBe(3);
  });

  it("counts temporal, personal and showPast each as 1", () => {
    expect(
      countActiveFilters(
        withDefaults({
          temporal: "today",
          personal: "going",
          showPast: true,
        }),
      ),
    ).toBe(3);
  });

  it("counts a non-default sort as 1, but ignores start_time", () => {
    expect(countActiveFilters(withDefaults({ sort: "start_time" }))).toBe(0);
    expect(countActiveFilters(withDefaults({ sort: "distance" }))).toBe(1);
  });

  it("counts each truthy accessibility flag", () => {
    expect(
      countActiveFilters(
        withDefaults({
          accessibility: { wheelchair: true, captions: true, quiet_friendly: true },
        }),
      ),
    ).toBe(3);
  });
});
