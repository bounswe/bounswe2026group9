"use client";

import { createContext, startTransition, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

import {
  login as loginRequest,
  register as registerRequest,
  logout as logoutRequest,
  refreshSession as refreshSessionRequest,
  setAuthRedirectSuppressed,
} from "@/lib/api";
import {
  type AuthUser,
  getSessionState,
  markSessionLoading,
  setGuestSession,
  subscribeToSession,
  type SessionState,
} from "@/lib/session";

interface LoginCredentials {
  email: string;
  password: string;
}

interface RegisterCredentials extends LoginCredentials {
  date_of_birth: string;
  username: string;
}

interface AuthContextValue extends SessionState {
  isAuthenticated: boolean;
  isLoggingOut: boolean;
  login: (credentials: LoginCredentials) => Promise<AuthUser>;
  register: (credentials: RegisterCredentials) => Promise<AuthUser>;
  logout: () => Promise<void>;
  refreshSession: (options?: { redirectOnFailure?: boolean }) => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [session, setSession] = useState(getSessionState);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  useEffect(() => subscribeToSession(setSession), []);

  useEffect(() => {
    if (!isLoggingOut) {
      return;
    }

    if (pathname === "/" || session.status === "authenticated") {
      const frameId = window.requestAnimationFrame(() => {
        setIsLoggingOut(false);
      });

      return () => window.cancelAnimationFrame(frameId);
    }
  }, [isLoggingOut, pathname, session.status]);

  useEffect(() => {
    if (session.status === "authenticated") {
      setAuthRedirectSuppressed(false);
    }
  }, [session.status]);

  useEffect(() => {
    if (getSessionState().isInitialized) {
      return;
    }

    markSessionLoading();

    void refreshSessionRequest().catch(() => {
      setGuestSession();
    });
  }, []);

  async function refreshSession(options?: { redirectOnFailure?: boolean }) {
    await refreshSessionRequest(options);
  }

  async function login(credentials: LoginCredentials) {
    const auth = await loginRequest(credentials);
    return auth.user;
  }

  async function register(credentials: RegisterCredentials) {
    const auth = await registerRequest(credentials);
    return auth.user;
  }

  async function logout() {
    setIsLoggingOut(true);
    setAuthRedirectSuppressed(true);

    try {
      await logoutRequest();
      startTransition(() => {
        router.replace("/");
      });
    } catch (error) {
      setAuthRedirectSuppressed(false);
      setIsLoggingOut(false);
      throw error;
    }
  }

  return (
    <AuthContext.Provider
      value={{
        ...session,
        isAuthenticated: session.status === "authenticated",
        isLoggingOut,
        login,
        logout,
        refreshSession,
        register,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
