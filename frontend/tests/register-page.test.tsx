import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import RegisterPage from "@/app/register/page";
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

describe("RegisterPage", () => {
  const registerMock = vi.fn();

  beforeEach(() => {
    registerMock.mockReset();
    replaceMock.mockReset();
    useSearchParamsMock.mockReturnValue(new URLSearchParams());
    vi.mocked(useAuth).mockReturnValue({
      accessToken: null,
      isAuthenticated: false,
      isInitialized: true,
      login: vi.fn(),
      logout: vi.fn(),
      refreshSession: vi.fn(),
      register: registerMock,
      status: "guest",
      user: null,
    });
  });

  afterEach(cleanup);

  it("validates required fields before submitting", async () => {
    const user = userEvent.setup();

    render(<RegisterPage />);

    await user.click(screen.getByRole("button", { name: "Create Account" }));

    expect(screen.getByText("Username is required.")).toBeInTheDocument();
    expect(screen.getByText("Email is required.")).toBeInTheDocument();
    expect(screen.getByText("Password is required.")).toBeInTheDocument();
    expect(screen.getByText("Please confirm your password.")).toBeInTheDocument();
    expect(screen.getByText("Date of birth is required.")).toBeInTheDocument();
    expect(
      screen.getByText("You must accept the Terms of Service and Privacy Policy."),
    ).toBeInTheDocument();
    expect(registerMock).not.toHaveBeenCalled();
  });

  it("submits valid registration details", async () => {
    const user = userEvent.setup();
    registerMock.mockResolvedValue({
      email: "alice@example.com",
      username: "alice",
    });

    render(<RegisterPage />);

    await user.type(screen.getByLabelText("Email"), "alice@example.com");
    await user.type(screen.getByLabelText("Username"), "alice");
    await user.type(screen.getByLabelText("Password"), "StrongPass1!");
    await user.type(screen.getByLabelText("Confirm Password"), "StrongPass1!");
    await user.type(screen.getByLabelText("Date of Birth"), "2000-04-03");
    await user.click(screen.getByLabelText("Accept terms"));
    await user.click(screen.getByRole("button", { name: "Create Account" }));

    await waitFor(() => {
      expect(registerMock).toHaveBeenCalledWith({
        date_of_birth: "2000-04-03",
        email: "alice@example.com",
        password: "StrongPass1!",
        username: "alice",
      });
    });

    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith("/dashboard");
    });
  });
});
