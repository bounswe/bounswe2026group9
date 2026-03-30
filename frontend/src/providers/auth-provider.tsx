"use client";

import { createContext, startTransition, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import {
  login as loginRequest,
  logout as logoutRequest,
  refreshSession as refreshSessionRequest,
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

interface AuthContextValue extends SessionState {
  isAuthenticated: boolean;
  login: (credentials: LoginCredentials) => Promise<AuthUser>;
  logout: () => Promise<void>;
  refreshSession: (options?: { redirectOnFailure?: boolean }) => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [session, setSession] = useState(getSessionState);

  useEffect(() => subscribeToSession(setSession), []);

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

  async function logout() {
    await logoutRequest();
    startTransition(() => {
      router.replace("/login");
    });
  }

  return (
    <AuthContext.Provider
      value={{
        ...session,
        isAuthenticated: session.status === "authenticated",
        login,
        logout,
        refreshSession,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
