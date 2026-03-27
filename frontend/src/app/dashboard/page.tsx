"use client";

import Link from "next/link";
import { startTransition, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/use-auth";
import { getCurrentUser, getErrorMessage } from "@/lib/api";
import type { AuthUser } from "@/lib/session";

export default function DashboardPage() {
  const router = useRouter();
  const { isInitialized, logout, refreshSession, status, user } = useAuth();
  const [profile, setProfile] = useState<AuthUser | null>(user);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [isLoadingProfile, setIsLoadingProfile] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  useEffect(() => {
    setProfile(user);
  }, [user]);

  useEffect(() => {
    if (!isInitialized || status !== "guest") {
      return;
    }

    startTransition(() => {
      router.replace("/login?reason=protected&next=/dashboard");
    });
  }, [isInitialized, router, status]);

  async function handleLoadProfile() {
    setFeedback(null);
    setIsLoadingProfile(true);

    try {
      const me = await getCurrentUser();
      setProfile(me);
      setFeedback("Profile synced from /auth/me.");
    } catch (error) {
      setFeedback(getErrorMessage(error, "Unable to load your profile."));
    } finally {
      setIsLoadingProfile(false);
    }
  }

  async function handleRefresh() {
    setFeedback(null);
    setIsRefreshing(true);

    try {
      await refreshSession({ redirectOnFailure: true });
      setFeedback("Refresh token exchanged successfully.");
    } catch (error) {
      setFeedback(getErrorMessage(error, "Unable to refresh the current session."));
    } finally {
      setIsRefreshing(false);
    }
  }

  async function handleLogout() {
    setIsLoggingOut(true);
    await logout();
    setIsLoggingOut(false);
  }

  if (!isInitialized || status === "loading") {
    return (
      <main className="flex flex-1 items-center justify-center px-6 py-16">
        <div className="border-border/70 bg-card/90 shadow-brand-panel w-full max-w-xl rounded-[2rem] border p-10 text-center">
          <p className="text-accent text-sm font-semibold tracking-[0.24em] uppercase">
            Protected Route
          </p>
          <h1 className="text-foreground mt-4 text-4xl">Restoring session...</h1>
          <p className="text-muted-foreground mt-4 text-base leading-7">
            The auth provider is checking the refresh cookie before rendering authenticated content.
          </p>
        </div>
      </main>
    );
  }

  if (status === "guest" || !user) {
    return null;
  }

  return (
    <main className="flex flex-1 justify-center px-6 py-16">
      <section className="w-full max-w-5xl space-y-6">
        <div className="border-border/70 bg-card/90 shadow-brand-panel flex flex-col gap-4 rounded-[2rem] border p-8 sm:flex-row sm:items-end sm:justify-between">
          <div className="space-y-3">
            <p className="text-accent text-sm font-semibold tracking-[0.24em] uppercase">
              Authenticated Session
            </p>
            <h1 className="text-foreground text-4xl text-balance sm:text-5xl">
              Dashboard access is protected by the shared API client.
            </h1>
            <p className="text-muted-foreground max-w-3xl text-base leading-7 sm:text-lg">
              This page uses the access token for `/auth/me`, refreshes through the backend cookie
              when necessary, and bounces back to login if the refresh flow can no longer recover
              the session.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <Button asChild size="lg" variant="outline">
              <Link href="/">Home</Link>
            </Button>
            <Button
              onClick={() => {
                void handleRefresh();
              }}
              size="lg"
              variant="secondary"
            >
              {isRefreshing ? "Refreshing..." : "Rotate session"}
            </Button>
            <Button
              onClick={() => {
                void handleLogout();
              }}
              size="lg"
            >
              {isLoggingOut ? "Signing out..." : "Logout"}
            </Button>
          </div>
        </div>

        {feedback ? (
          <div className="border-border/70 bg-background/80 text-foreground shadow-brand-card rounded-2xl border px-5 py-4 text-sm">
            {feedback}
          </div>
        ) : null}

        <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
          <article className="border-border/70 bg-card/92 shadow-brand-card space-y-4 rounded-[2rem] border p-7">
            <div className="space-y-1">
              <h2 className="text-foreground text-2xl">Session summary</h2>
              <p className="text-muted-foreground text-sm leading-6">
                Auth state is available globally through the provider and hook.
              </p>
            </div>

            <dl className="grid gap-4 text-sm">
              <div className="border-border/70 bg-background/70 rounded-2xl border px-4 py-3">
                <dt className="text-muted-foreground">Username</dt>
                <dd className="text-foreground mt-1 font-medium">{user.username}</dd>
              </div>
              <div className="border-border/70 bg-background/70 rounded-2xl border px-4 py-3">
                <dt className="text-muted-foreground">Email</dt>
                <dd className="text-foreground mt-1 font-medium">{user.email}</dd>
              </div>
              <div className="border-border/70 bg-background/70 rounded-2xl border px-4 py-3">
                <dt className="text-muted-foreground">Role</dt>
                <dd className="text-foreground mt-1 font-medium capitalize">{user.role}</dd>
              </div>
              <div className="border-border/70 bg-background/70 rounded-2xl border px-4 py-3">
                <dt className="text-muted-foreground">Provider</dt>
                <dd className="text-foreground mt-1 font-medium capitalize">
                  {user.auth_provider}
                </dd>
              </div>
            </dl>

            <Button
              className="h-11 w-full rounded-2xl"
              onClick={() => {
                void handleLoadProfile();
              }}
              variant="outline"
            >
              {isLoadingProfile ? "Syncing profile..." : "Fetch /auth/me again"}
            </Button>
          </article>

          <article className="border-border/70 bg-card/92 shadow-brand-card rounded-[2rem] border p-7">
            <div className="space-y-1">
              <h2 className="text-foreground text-2xl">User payload</h2>
              <p className="text-muted-foreground text-sm leading-6">
                Useful for validating that the frontend schema matches the backend response model.
              </p>
            </div>

            <pre className="border-border/70 bg-background/80 text-foreground mt-5 overflow-x-auto rounded-[1.5rem] border p-5 text-sm leading-7">
              {JSON.stringify(profile, null, 2)}
            </pre>
          </article>
        </div>
      </section>
    </main>
  );
}
