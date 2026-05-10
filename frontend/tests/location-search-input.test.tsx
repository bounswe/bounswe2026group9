import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { LocationSearchInput } from "@/components/events/location-search-input";
import type * as NominatimModule from "@/lib/nominatim";

const { suggestPlacesMock } = vi.hoisted(() => ({
  suggestPlacesMock: vi.fn<typeof NominatimModule.suggestPlaces>(),
}));

vi.mock("@/lib/nominatim", async () => {
  const actual = await vi.importActual<typeof NominatimModule>("@/lib/nominatim");
  return { ...actual, suggestPlaces: suggestPlacesMock };
});

afterEach(() => {
  cleanup();
  suggestPlacesMock.mockReset();
  vi.useRealTimers();
});

describe("LocationSearchInput", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  it("does not call suggestPlaces for queries shorter than 2 characters", () => {
    render(<LocationSearchInput value="" onChange={vi.fn()} onPick={vi.fn()} />);
    vi.advanceTimersByTime(1000);
    expect(suggestPlacesMock).not.toHaveBeenCalled();
  });

  it("debounces the suggest request to 400ms after value change", () => {
    suggestPlacesMock.mockResolvedValue([
      {
        displayName: "Bebek Park, Istanbul",
        shortName: "Bebek Park",
        lat: 41.07,
        lng: 29.04,
      },
    ]);

    const { rerender } = render(
      <LocationSearchInput value="Be" onChange={vi.fn()} onPick={vi.fn()} />,
    );
    vi.advanceTimersByTime(200);
    expect(suggestPlacesMock).not.toHaveBeenCalled();

    rerender(<LocationSearchInput value="Bebek" onChange={vi.fn()} onPick={vi.fn()} />);
    vi.advanceTimersByTime(399);
    expect(suggestPlacesMock).not.toHaveBeenCalled();

    vi.advanceTimersByTime(2);
    expect(suggestPlacesMock).toHaveBeenCalledTimes(1);
    expect(suggestPlacesMock).toHaveBeenCalledWith("Bebek", 5, expect.any(AbortSignal));
  });

  it("renders the suggestion list and calls onPick when a result is clicked", async () => {
    vi.useRealTimers();
    const onPick = vi.fn();
    suggestPlacesMock.mockResolvedValue([
      {
        displayName: "Galata Tower, Istanbul",
        shortName: "Galata Tower",
        lat: 41.0256,
        lng: 28.9742,
      },
    ]);

    render(<LocationSearchInput value="Galata" onChange={vi.fn()} onPick={onPick} />);
    const option = await waitFor(() => screen.getByRole("option"), { timeout: 2000 });
    expect(option).toHaveTextContent("Galata Tower");

    fireEvent.click(screen.getByRole("button", { name: /Galata Tower/ }));
    expect(onPick).toHaveBeenCalledTimes(1);
    expect(onPick).toHaveBeenCalledWith({
      displayName: "Galata Tower, Istanbul",
      shortName: "Galata Tower",
      lat: 41.0256,
      lng: 28.9742,
    });
  });
});
