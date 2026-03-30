import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { buildProtectedRedirectUrl, ProtectedRoute } from "@/components/auth/protected-route";
import { useAuth } from "@/hooks/use-auth";

const { replaceMock, usePathnameMock, useSearchParamsMock } = vi.hoisted(() => ({
  replaceMock: vi.fn<(href: string) => void>(),
  usePathnameMock: vi.fn<() => string | null>(),
  useSearchParamsMock: vi.fn<() => URLSearchParams>(),
}));

vi.mock("@/hooks/use-auth", () => ({
  useAuth: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  usePathname: usePathnameMock,
  useRouter: () => ({
    replace: replaceMock,
  }),
  useSearchParams: useSearchParamsMock,
}));

describe("buildProtectedRedirectUrl", () => {
  it("adds the reason and next path", () => {
    expect(
      buildProtectedRedirectUrl({
        nextPath: "/dashboard?tab=members",
        redirectReason: "protected",
      }),
    ).toBe("/login?reason=protected&next=%2Fdashboard%3Ftab%3Dmembers");
  });

  it("keeps existing login query parameters", () => {
    expect(
      buildProtectedRedirectUrl({
        redirectReason: "session-expired",
        redirectTo: "/login?source=oauth",
      }),
    ).toBe("/login?source=oauth&reason=session-expired");
  });
});

describe("ProtectedRoute", () => {
  beforeEach(() => {
    replaceMock.mockReset();
    usePathnameMock.mockReturnValue("/dashboard");
    useSearchParamsMock.mockReturnValue(new URLSearchParams("tab=members"));
  });

  afterEach(() => {
    cleanup();
  });

  it("renders the loading state while auth is restoring", () => {
    vi.mocked(useAuth).mockReturnValue({
      accessToken: null,
      isAuthenticated: false,
      isInitialized: false,
      login: vi.fn(),
      logout: vi.fn(),
      refreshSession: vi.fn(),
      status: "loading",
      user: null,
    });

    render(
      <ProtectedRoute>
        <div>Secret dashboard</div>
      </ProtectedRoute>,
    );

    expect(screen.getByText("Restoring session...")).toBeInTheDocument();
    expect(screen.queryByText("Secret dashboard")).not.toBeInTheDocument();
  });

  it("redirects guests to login with the current path", async () => {
    vi.mocked(useAuth).mockReturnValue({
      accessToken: null,
      isAuthenticated: false,
      isInitialized: true,
      login: vi.fn(),
      logout: vi.fn(),
      refreshSession: vi.fn(),
      status: "guest",
      user: null,
    });

    render(
      <ProtectedRoute>
        <div>Secret dashboard</div>
      </ProtectedRoute>,
    );

    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith(
        "/login?reason=protected&next=%2Fdashboard%3Ftab%3Dmembers",
      );
    });
  });

  it("renders children for authenticated users", () => {
    vi.mocked(useAuth).mockReturnValue({
      accessToken: "access-token",
      isAuthenticated: true,
      isInitialized: true,
      login: vi.fn(),
      logout: vi.fn(),
      refreshSession: vi.fn(),
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
      <ProtectedRoute>
        <div>Secret dashboard</div>
      </ProtectedRoute>,
    );

    expect(screen.getByText("Secret dashboard")).toBeInTheDocument();
    expect(replaceMock).not.toHaveBeenCalled();
  });
});
