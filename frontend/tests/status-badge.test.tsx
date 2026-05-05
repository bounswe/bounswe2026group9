import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { StatusBadge, eventStatusVariant } from "@/components/event/status-badge";

afterEach(() => {
  cleanup();
});

describe("eventStatusVariant", () => {
  it("returns cancelled when the event is cancelled", () => {
    expect(eventStatusVariant("cancelled", false)).toBe("cancelled");
  });

  it("returns ended when the event has ended", () => {
    expect(eventStatusVariant("ended", false)).toBe("ended");
  });

  it("prefers full over published when capacity is reached on a live event", () => {
    expect(eventStatusVariant("published", true)).toBe("full");
  });

  it("returns draft for draft events that aren't full", () => {
    expect(eventStatusVariant("draft", false)).toBe("draft");
  });

  it("returns published for active events that aren't full", () => {
    expect(eventStatusVariant("published", false)).toBe("published");
    expect(eventStatusVariant("updated", null)).toBe("published");
  });
});

describe("StatusBadge", () => {
  it("renders the human label for each variant", () => {
    render(<StatusBadge variant="published" />);
    expect(screen.getByText("Published")).toBeInTheDocument();
  });

  it("renders Cancelled for the cancelled variant", () => {
    render(<StatusBadge variant="cancelled" />);
    expect(screen.getByText("Cancelled")).toBeInTheDocument();
  });

  it("renders Private for private events", () => {
    render(<StatusBadge variant="private" />);
    expect(screen.getByText("Private")).toBeInTheDocument();
  });

  it("renders Full for at-capacity events", () => {
    render(<StatusBadge variant="full" />);
    expect(screen.getByText("Full")).toBeInTheDocument();
  });
});
