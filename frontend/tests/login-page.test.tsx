import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import LoginPage from "@/app/login/page";
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

describe("LoginPage", () => {
  const loginMock = vi.fn();

  beforeEach(() => {
    loginMock.mockReset();
    replaceMock.mockReset();
    useSearchParamsMock.mockReturnValue(new URLSearchParams());
    vi.mocked(useAuth).mockReturnValue({
      accessToken: null,
      isAuthenticated: false,
      isInitialized: true,
      isLoggingOut: false,
      login: loginMock,
      logout: vi.fn(),
      refreshSession: vi.fn(),
      register: vi.fn(),
      status: "guest",
      user: null,
    });
  });

  afterEach(cleanup);

  it("shows the protected-route banner when redirected to login", () => {
    useSearchParamsMock.mockReturnValue(new URLSearchParams("reason=protected"));

    render(<LoginPage />);

    expect(screen.getByText("Please sign in to continue.")).toBeInTheDocument();
  });

  it("submits valid login credentials and redirects to the requested path", async () => {
    const user = userEvent.setup();
    loginMock.mockResolvedValue({
      email: "alice@example.com",
      username: "alice",
    });
    useSearchParamsMock.mockReturnValue(new URLSearchParams("next=/events/create"));

    render(<LoginPage />);

    await user.type(screen.getByLabelText("Email"), "alice@example.com");
    await user.type(screen.getByLabelText("Password"), "StrongPass1!");
    await user.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      expect(loginMock).toHaveBeenCalledWith({
        email: "alice@example.com",
        password: "StrongPass1!",
      });
    });

    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith("/events/create");
    });
  });

  it("renders backend login errors", async () => {
    const user = userEvent.setup();
    loginMock.mockRejectedValue(new Error("Invalid email or password"));

    render(<LoginPage />);

    await user.type(screen.getByLabelText("Email"), "alice@example.com");
    await user.type(screen.getByLabelText("Password"), "wrong-password");
    await user.click(screen.getByRole("button", { name: "Sign In" }));

    expect(await screen.findByText("Invalid email or password")).toBeInTheDocument();
  });

  it("does not render placeholder remember-me or password-reset actions", () => {
    render(<LoginPage />);

    expect(screen.queryByText("Remember me")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Forgot password?" })).not.toBeInTheDocument();
  });
});
