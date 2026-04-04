import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { GuestOnlyRoute } from "@/components/auth/guest-only-route";
import { useAuth } from "@/hooks/use-auth";

const { replaceMock, useSearchParamsMock } = vi.hoisted(() => ({
  replaceMock: vi.fn<(href: string) => void>(),
  useSearchParamsMock: vi.fn<() => URLSearchParams>(),
}));

vi.mock("@/hooks/use-auth", () => ({
  useAuth: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: replaceMock,
  }),
  useSearchParams: useSearchParamsMock,
}));

describe("GuestOnlyRoute", () => {
  beforeEach(() => {
    replaceMock.mockReset();
    useSearchParamsMock.mockReturnValue(new URLSearchParams("next=/create-event"));
  });

  afterEach(() => {
    cleanup();
  });

  it("renders children for guests", () => {
    vi.mocked(useAuth).mockReturnValue({
      accessToken: null,
      isAuthenticated: false,
      isInitialized: true,
      isLoggingOut: false,
      login: vi.fn(),
      logout: vi.fn(),
      refreshSession: vi.fn(),
      register: vi.fn(),
      status: "guest",
      user: null,
    });

    render(
      <GuestOnlyRoute>
        <div>Register form</div>
      </GuestOnlyRoute>,
    );

    expect(screen.getByText("Register form")).toBeInTheDocument();
    expect(replaceMock).not.toHaveBeenCalled();
  });

  it("redirects authenticated users to the next path", async () => {
    vi.mocked(useAuth).mockReturnValue({
      accessToken: "access-token",
      isAuthenticated: true,
      isInitialized: true,
      isLoggingOut: false,
      login: vi.fn(),
      logout: vi.fn(),
      refreshSession: vi.fn(),
      register: vi.fn(),
      status: "authenticated",
      user: {
        auth_provider: "local",
        created_at: "2026-03-27T00:00:00Z",
        date_of_birth: null,
        email: "test@example.com",
        email_verified: true,
        email_visibility: false,
        id: "user-1",
        is_active: true,
        phone_number: null,
        role: "registered",
        updated_at: "2026-03-27T00:00:00Z",
        username: "test-user",
      },
    });

    render(
      <GuestOnlyRoute>
        <div>Register form</div>
      </GuestOnlyRoute>,
    );

    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith("/create-event");
    });
  });
});
