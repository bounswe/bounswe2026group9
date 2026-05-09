import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AttendeeRoster } from "@/components/event/attendee-roster";
import type { AttendeeStatus } from "@/lib/events-api";

const PENDING: AttendeeStatus = {
  user_id: "u-pending",
  username: "alice",
  checked_in_at: null,
};

const CHECKED_IN: AttendeeStatus = {
  user_id: "u-checked",
  username: "bob",
  checked_in_at: "2026-06-01T18:00:00Z",
};

afterEach(() => cleanup());

describe("AttendeeRoster", () => {
  it("renders the empty state when no one is going", () => {
    render(
      <AttendeeRoster
        attendees={[]}
        currentUserId={null}
        markError={null}
        markingId={null}
        onMarkIn={vi.fn()}
      />,
    );
    expect(screen.getByText(/Going \(0\)/)).toBeInTheDocument();
    expect(screen.getByText(/No attendees yet\./)).toBeInTheDocument();
    expect(screen.queryByText(/checked in/i)).toBeNull();
  });

  it("shows the per-row check-in status and the counter line", () => {
    render(
      <AttendeeRoster
        attendees={[PENDING, CHECKED_IN]}
        currentUserId="host-id"
        markError={null}
        markingId={null}
        onMarkIn={vi.fn()}
      />,
    );
    expect(screen.getByText(/Going \(2\)/)).toBeInTheDocument();
    // Mobile parity: "{checked} / {total} checked in"
    expect(screen.getByText(/1 \/ 2 checked in/)).toBeInTheDocument();
    expect(screen.getByText(/Pending/)).toBeInTheDocument();
    expect(screen.getByText(/Checked in/)).toBeInTheDocument();
  });

  it("renders Mark in only for pending rows and triggers onMarkIn with the user id", () => {
    const onMarkIn = vi.fn();
    render(
      <AttendeeRoster
        attendees={[PENDING, CHECKED_IN]}
        currentUserId="host-id"
        markError={null}
        markingId={null}
        onMarkIn={onMarkIn}
      />,
    );
    const buttons = screen.getAllByRole("button", { name: /Manually mark/ });
    expect(buttons).toHaveLength(1);
    fireEvent.click(buttons[0]);
    expect(onMarkIn).toHaveBeenCalledWith("u-pending");
  });

  it("disables the Mark in button while a manual call is in flight for that user", () => {
    render(
      <AttendeeRoster
        attendees={[PENDING]}
        currentUserId="host-id"
        markError={null}
        markingId="u-pending"
        onMarkIn={vi.fn()}
      />,
    );
    const button = screen.getByRole("button", { name: /Manually mark/ });
    expect(button).toBeDisabled();
  });

  it("surfaces a top-level error message when the manual mark call fails", () => {
    render(
      <AttendeeRoster
        attendees={[PENDING]}
        currentUserId="host-id"
        markError="Already checked in"
        markingId={null}
        onMarkIn={vi.fn()}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Already checked in");
  });
});
