"use client";

import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/use-auth";
import { getBackendBaseUrl, getBackendHealth, getErrorMessage } from "@/lib/api";
import type { HealthResponse } from "@/lib/api";

export default function HomePage() {
  const { isAuthenticated, logout, status, user } = useAuth();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [isCheckingHealth, setIsCheckingHealth] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  async function handleCheckHealth() {
    setHealth(null);
    setHealthError(null);
    setIsCheckingHealth(true);

    try {
      const result = await getBackendHealth();
      setHealth(result);
    } catch (error) {
      setHealthError(getErrorMessage(error, "Unable to reach the backend health endpoint."));
    } finally {
      setIsCheckingHealth(false);
    }
  }

  async function handleLogout() {
    setIsLoggingOut(true);
    await logout();
    setIsLoggingOut(false);
  }

  return (
    <main className="flex flex-1 justify-center px-6 py-16">
      <section className="w-full max-w-6xl space-y-6">
        <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
          <article className="border-border/70 bg-card/90 shadow-brand-panel rounded-[2rem] border p-8 sm:p-10">
            <div className="space-y-3">
              <p className="text-accent text-sm font-semibold tracking-[0.24em] uppercase">
                Issue #122
              </p>
              <h1 className="text-foreground text-4xl text-balance sm:text-5xl">
                Centralized API access and session management for the web app.
              </h1>
              <p className="text-muted-foreground max-w-3xl text-base leading-7 sm:text-lg">
                The frontend now has a shared API client, auth context, refresh handling through the
                backend cookie, and a protected dashboard that depends on that session layer.
              </p>
            </div>

            <div className="mt-8 flex flex-wrap gap-3">
              {isAuthenticated ? (
                <>
                  <Button asChild size="lg">
                    <Link href="/dashboard">Open dashboard</Link>
                  </Button>
                  <Button
                    onClick={() => {
                      void handleLogout();
                    }}
                    size="lg"
                    variant="outline"
                  >
                    {isLoggingOut ? "Signing out..." : "Logout"}
                  </Button>
                </>
              ) : (
                <Button asChild size="lg">
                  <Link href="/login">Go to login</Link>
                </Button>
              )}
              <Button
                onClick={() => {
                  void handleCheckHealth();
                }}
                size="lg"
                variant="secondary"
              >
                {isCheckingHealth ? "Checking backend..." : "Check backend health"}
              </Button>
            </div>
          </article>

          <article className="border-border/70 bg-card/92 shadow-brand-panel rounded-[2rem] border p-8 sm:p-10">
            <div className="space-y-1">
              <h2 className="text-foreground text-2xl">Current client state</h2>
              <p className="text-muted-foreground text-sm leading-6">
                This is the global auth snapshot exposed via context.
              </p>
            </div>

            <dl className="mt-6 grid gap-4 text-sm">
              <div className="border-border/70 bg-background/70 rounded-2xl border px-4 py-3">
                <dt className="text-muted-foreground">Status</dt>
                <dd className="text-foreground mt-1 font-medium capitalize">{status}</dd>
              </div>
              <div className="border-border/70 bg-background/70 rounded-2xl border px-4 py-3">
                <dt className="text-muted-foreground">Backend URL</dt>
                <dd className="text-foreground mt-1 font-medium break-all">
                  {getBackendBaseUrl()}
                </dd>
              </div>
              <div className="border-border/70 bg-background/70 rounded-2xl border px-4 py-3">
                <dt className="text-muted-foreground">Active user</dt>
                <dd className="text-foreground mt-1 font-medium">
                  {user ? `${user.username} (${user.email})` : "Guest"}
                </dd>
              </div>
            </dl>
          </article>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <article className="border-border/70 bg-card/92 shadow-brand-card rounded-[2rem] border p-8">
            <div className="space-y-1">
              <h2 className="text-foreground text-2xl">What this branch covers</h2>
              <p className="text-muted-foreground text-sm leading-6">
                The implementation is aligned with the backend auth contract that already exists in
                the FastAPI service.
              </p>
            </div>

            <ul className="text-muted-foreground mt-5 space-y-3 text-sm leading-7">
              <li>Shared fetch wrapper with base URL config and auth header injection.</li>
              <li>Automatic refresh on `401` using the HTTP-only refresh cookie.</li>
              <li>Global auth provider and hook for session access in any component.</li>
              <li>Protected dashboard with login redirect on unrecoverable refresh failure.</li>
            </ul>
          </article>

          <article className="border-border/70 bg-card/92 shadow-brand-card rounded-[2rem] border p-8">
            <div className="space-y-1">
              <h2 className="text-foreground text-2xl">Backend health</h2>
              <p className="text-muted-foreground text-sm leading-6">
                Public endpoint check through the same centralized client.
              </p>
            </div>

            <div className="border-border/70 bg-background/80 text-foreground mt-5 rounded-[1.5rem] border p-5 text-sm leading-7">
              {health ? (
                <pre className="overflow-x-auto whitespace-pre-wrap">
                  {JSON.stringify(health, null, 2)}
                </pre>
              ) : healthError ? (
                <p className="text-destructive">{healthError}</p>
              ) : (
                <p className="text-muted-foreground">
                  Run the backend locally and use the button above to verify the configured API
                  origin.
                </p>
              )}
            </div>
          </article>
        </div>
      </section>
    </main>
  );
}
