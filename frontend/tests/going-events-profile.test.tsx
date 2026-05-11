import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type * as EventsApiModule from "@/lib/events-api";
import type { EventListItem } from "@/lib/events-api";

// ── Module mocks ──────────────────────────────────────────────────────────────

const { fetchMyGoingEventsMock } = vi.hoisted(() => ({
  fetchMyGoingEventsMock: vi.fn<typeof EventsApiModule.fetchMyGoingEvents>(),
}));

vi.mock("@/lib/events-api", async () => {
  const actual = await vi.importActual<typeof EventsApiModule>("@/lib/events-api");
  return { ...actual, fetchMyGoingEvents: fetchMyGoingEventsMock };
});

// next/navigation
const { pushMock } = vi.hoisted(() => ({ pushMock: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
  useParams: () => ({}),
  usePathname: () => "/profile",
  useSearchParams: () => new URLSearchParams(),
}));

// Auth — authenticated user
vi.mock("@/hooks/use-auth", () => ({
  useAuth: () => ({
    isInitialized: true,
    status: "authenticated",
    user: {
      id: "user-1",
      username: "testuser",
      email: "test@example.com",
      phone_number: null,
      date_of_birth: null,
      email_visibility: false,
      phone_visibility: false,
      role: "registered",
      auth_provider: "local",
      email_verified: true,
      is_active: true,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
  }),
}));

// Stub out the other API calls the page makes so they don't interfere
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<Record<string, unknown>>("@/lib/api");
  return {
    ...actual,
    getCurrentUser: vi.fn().mockResolvedValue({
      id: "user-1",
      username: "testuser",
      email: "test@example.com",
      phone_number: null,
      date_of_birth: null,
      email_visibility: false,
      phone_visibility: false,
      role: "registered",
      auth_provider: "local",
      email_verified: true,
      is_active: true,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    }),
    getHostProfileSummary: vi.fn().mockResolvedValue({
      id: "user-1",
      username: "testuser",
      average_rating: null,
      hosted_events: [],
      hosted_events_count: 0,
    }),
    getMyBookmarks: vi.fn().mockResolvedValue({ items: [], total: 0, total_pages: 0 }),
  };
});

// ── Helpers ───────────────────────────────────────────────────────────────────

function makeEvent(overrides: Partial<EventListItem> = {}): EventListItem {
  return {
    id: "ev-1",
    host_id: "host-1",
    title: "Sunset Yoga",
    description: null,
    start_datetime: "2099-08-01T17:00:00Z",
    end_datetime: "2099-08-01T18:00:00Z",
    visibility: "public",
    is_age_restricted: false,
    attendee_limit: 20,
    attendee_count: 5,
    status: "published",
    is_bookmarked: null,
    attendance_status: "going",
    access_request_status: null,
    has_access: null,
    going_count: 5,
    bookmark_count: 1,
    is_full: false,
    categories: [{ id: "c-1", name: "Wellness", is_predefined: true, is_approved: true }],
    primary_location: null,
    primary_image_url: null,
    ...overrides,
  };
}

async function renderProfileAndOpenGoingTab() {
  // Lazy import so mocks are registered first
  const { MyProfilePage } = await import("@/components/profile/my-profile-page");
  render(<MyProfilePage />);
  const goingTab = await screen.findByRole("button", { name: /going events/i });
  await userEvent.click(goingTab);
}

// ── Tests ─────────────────────────────────────────────────────────────────────

afterEach(() => {
  cleanup();
  fetchMyGoingEventsMock.mockReset();
  vi.resetModules();
});

describe("Going Events tab — navigation", () => {
  beforeEach(() => {
    fetchMyGoingEventsMock.mockResolvedValue([]);
  });

  it("renders the Going Events nav button", async () => {
    const { MyProfilePage } = await import("@/components/profile/my-profile-page");
    render(<MyProfilePage />);
    expect(await screen.findByRole("button", { name: /going events/i })).toBeInTheDocument();
  });

  it("shows the Going Events section when the tab is clicked", async () => {
    await renderProfileAndOpenGoingTab();
    expect(await screen.findByText(/going & attended/i)).toBeInTheDocument();
  });
});

describe("Going Events tab — upcoming sub-tab", () => {
  it("renders a card for each upcoming going event", async () => {
    fetchMyGoingEventsMock.mockResolvedValue([
      makeEvent({ id: "ev-1", title: "Morning Run" }),
      makeEvent({ id: "ev-2", title: "Evening Yoga" }),
    ]);
    await renderProfileAndOpenGoingTab();

    expect(await screen.findByText("Morning Run")).toBeInTheDocument();
    expect(screen.getByText("Evening Yoga")).toBeInTheDocument();
  });

  it("shows 'Going' badge on upcoming events", async () => {
    fetchMyGoingEventsMock.mockResolvedValue([makeEvent()]);
    await renderProfileAndOpenGoingTab();

    const badges = await screen.findAllByText(/going/i);
    // At least one badge with "Going" text (the card badge)
    expect(badges.length).toBeGreaterThan(0);
  });

  it("shows the empty state when there are no upcoming going events", async () => {
    fetchMyGoingEventsMock.mockResolvedValue([]);
    await renderProfileAndOpenGoingTab();

    expect(await screen.findByText(/no upcoming events/i)).toBeInTheDocument();
  });

  it("links each card to the event detail page", async () => {
    fetchMyGoingEventsMock.mockResolvedValue([makeEvent({ id: "ev-abc" })]);
    await renderProfileAndOpenGoingTab();

    const link = await screen.findByRole("link", { name: /sunset yoga/i });
    expect(link).toHaveAttribute("href", "/event/ev-abc");
  });

  it("renders the event category badge", async () => {
    fetchMyGoingEventsMock.mockResolvedValue([
      makeEvent({
        categories: [{ id: "c-1", name: "Wellness", is_predefined: true, is_approved: true }],
      }),
    ]);
    await renderProfileAndOpenGoingTab();
    expect(await screen.findByText("Wellness")).toBeInTheDocument();
  });
});

describe("Going Events tab — past sub-tab", () => {
  it("shows 'Attended' badge and event on the past tab", async () => {
    fetchMyGoingEventsMock.mockResolvedValue([
      makeEvent({
        id: "ev-past",
        title: "Beach Volleyball",
        start_datetime: "2024-06-01T10:00:00Z",
        end_datetime: "2024-06-01T12:00:00Z",
        status: "ended",
      }),
    ]);
    await renderProfileAndOpenGoingTab();

    // Switch to the Past tab
    const pastTab = await screen.findByRole("button", { name: /past/i });
    await userEvent.click(pastTab);

    expect(await screen.findByText("Beach Volleyball")).toBeInTheDocument();
    expect(screen.getByText(/attended/i)).toBeInTheDocument();
  });

  it("shows the empty state when there are no attended events", async () => {
    fetchMyGoingEventsMock.mockResolvedValue([]);
    await renderProfileAndOpenGoingTab();

    const pastTab = await screen.findByRole("button", { name: /past/i });
    await userEvent.click(pastTab);

    expect(await screen.findByText(/no attended events yet/i)).toBeInTheDocument();
  });
});

describe("Going Events tab — error state", () => {
  it("shows an error message when the fetch fails", async () => {
    fetchMyGoingEventsMock.mockRejectedValue(new Error("Network error"));
    await renderProfileAndOpenGoingTab();

    expect(await screen.findByText(/we could not load your going events/i)).toBeInTheDocument();
  });
});
