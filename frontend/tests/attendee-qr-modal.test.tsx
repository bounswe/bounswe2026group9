import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AttendeeQrModal } from "@/components/event/attendee-qr-modal";
import type * as EventsApi from "@/lib/events-api";

const { fetchMyAttendeeQrMock } = vi.hoisted(() => ({
  fetchMyAttendeeQrMock: vi.fn<typeof EventsApi.fetchMyAttendeeQr>(),
}));

vi.mock("@/lib/events-api", async () => {
  const actual = await vi.importActual<typeof EventsApi>("@/lib/events-api");
  return { ...actual, fetchMyAttendeeQr: fetchMyAttendeeQrMock };
});

vi.mock("qrcode.react", () => ({
  QRCodeCanvas: ({ value }: { value: string }) => (
    <div data-testid="qr-canvas" data-value={value} />
  ),
}));

afterEach(() => {
  cleanup();
  fetchMyAttendeeQrMock.mockReset();
});

describe("AttendeeQrModal", () => {
  beforeEach(() => {
    fetchMyAttendeeQrMock.mockReset();
  });

  it("renders nothing when closed and skips the fetch", () => {
    render(<AttendeeQrModal eventId="ev-1" eventTitle="Event" onClose={vi.fn()} open={false} />);
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(fetchMyAttendeeQrMock).not.toHaveBeenCalled();
  });

  it("fetches the QR token on open and renders it inside the canvas", async () => {
    fetchMyAttendeeQrMock.mockResolvedValueOnce({
      token: "signed.payload.token",
      expires_at: null,
    });
    render(
      <AttendeeQrModal eventId="ev-1" eventTitle="Bebek Sunset" onClose={vi.fn()} open={true} />,
    );
    expect(fetchMyAttendeeQrMock).toHaveBeenCalledWith("ev-1");
    const canvas = await waitFor(() => screen.getByTestId("qr-canvas"));
    expect(canvas).toHaveAttribute("data-value", "signed.payload.token");
    expect(screen.getByText("Bebek Sunset")).toBeInTheDocument();
  });

  it("shows the upstream error message when the fetch rejects", async () => {
    fetchMyAttendeeQrMock.mockRejectedValueOnce(new Error("You are not Going for this event"));
    render(<AttendeeQrModal eventId="ev-1" eventTitle="Bebek" onClose={vi.fn()} open={true} />);
    expect(await waitFor(() => screen.getByRole("alert"))).toHaveTextContent(/Going/);
    expect(screen.queryByTestId("qr-canvas")).toBeNull();
  });
});
