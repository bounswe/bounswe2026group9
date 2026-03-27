"use client";

import Link from "next/link";
import { startTransition, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/use-auth";
import { getBackendBaseUrl, getErrorMessage, getGoogleLoginUrl } from "@/lib/api";

const reasonMessages: Record<string, string> = {
  "oauth-failed": "Google sign-in could not be completed. Please try again.",
  protected: "Please sign in to access the dashboard.",
  "session-expired": "Your session expired. Please sign in again.",
};

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isAuthenticated, login, status } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const nextPath = useMemo(() => searchParams.get("next") ?? "/dashboard", [searchParams]);
  const reason = searchParams.get("reason");
  const bannerMessage = reason ? reasonMessages[reason] : null;

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }

    startTransition(() => {
      router.replace(nextPath);
    });
  }, [isAuthenticated, nextPath, router]);

  async function submitLogin() {
    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      await login({ email, password });
      startTransition(() => {
        router.replace(nextPath);
      });
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Unable to sign in."));
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitLogin();
  }

  return (
    <main className="flex flex-1 items-center justify-center px-6 py-16">
      <section className="grid w-full max-w-5xl gap-10 lg:grid-cols-[1.15fr_0.85fr]">
        <div className="border-border/70 bg-card/85 shadow-brand-panel space-y-6 rounded-[2rem] border p-8 backdrop-blur sm:p-10">
          <div className="space-y-3">
            <p className="text-accent text-sm font-semibold tracking-[0.24em] uppercase">
              Social Event Mapper
            </p>
            <h1 className="text-foreground text-4xl text-balance sm:text-5xl">
              Frontend session management is now the entry point.
            </h1>
            <p className="text-muted-foreground max-w-2xl text-base leading-7 sm:text-lg">
              Sign in with your backend credentials to exercise the shared API client, automatic
              access-token injection, refresh rotation, and protected-route handling required by
              issue #122.
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <article className="border-border/70 bg-background/75 shadow-brand-card rounded-2xl border p-5">
              <p className="text-foreground text-sm font-semibold">Backend origin</p>
              <p className="text-muted-foreground mt-2 text-sm leading-6 break-all">
                {getBackendBaseUrl()}
              </p>
            </article>
            <article className="border-border/70 bg-background/75 shadow-brand-card rounded-2xl border p-5">
              <p className="text-foreground text-sm font-semibold">Session state</p>
              <p className="text-muted-foreground mt-2 text-sm leading-6">
                {status === "loading"
                  ? "Checking whether a refresh cookie already exists."
                  : "Login keeps the access token in the client session while the backend owns refresh-token persistence."}
              </p>
            </article>
            <article className="border-border/70 bg-background/75 shadow-brand-card rounded-2xl border p-5">
              <p className="text-foreground text-sm font-semibold">Protected route</p>
              <p className="text-muted-foreground mt-2 text-sm leading-6">
                The dashboard calls authenticated endpoints and redirects back here when refresh can
                no longer recover the session.
              </p>
            </article>
          </div>
        </div>

        <div className="border-border/70 bg-card/92 shadow-brand-panel rounded-[2rem] border p-8 backdrop-blur sm:p-10">
          <div className="space-y-2">
            <h2 className="text-foreground text-3xl">Sign in</h2>
            <p className="text-muted-foreground text-sm leading-6">
              Use a local account from the backend or continue with Google.
            </p>
          </div>

          {bannerMessage ? (
            <div className="border-accent/25 bg-accent/10 text-foreground mt-6 rounded-2xl border px-4 py-3 text-sm">
              {bannerMessage}
            </div>
          ) : null}

          {errorMessage ? (
            <div className="border-destructive/30 bg-destructive/10 text-destructive mt-4 rounded-2xl border px-4 py-3 text-sm">
              {errorMessage}
            </div>
          ) : null}

          <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
            <label className="block space-y-2">
              <span className="text-foreground text-sm font-medium">Email</span>
              <input
                autoComplete="email"
                className="border-border bg-background/75 text-foreground focus:border-ring focus:ring-ring/20 h-12 w-full rounded-2xl border px-4 text-sm transition outline-none focus:ring-3"
                name="email"
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@example.com"
                type="email"
                value={email}
              />
            </label>

            <label className="block space-y-2">
              <span className="text-foreground text-sm font-medium">Password</span>
              <input
                autoComplete="current-password"
                className="border-border bg-background/75 text-foreground focus:border-ring focus:ring-ring/20 h-12 w-full rounded-2xl border px-4 text-sm transition outline-none focus:ring-3"
                name="password"
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Enter your password"
                type="password"
                value={password}
              />
            </label>

            <Button className="h-12 w-full rounded-2xl text-sm" disabled={isSubmitting}>
              {isSubmitting ? "Signing in..." : "Sign in with email"}
            </Button>
          </form>

          <div className="mt-4">
            <Button asChild className="h-12 w-full rounded-2xl" variant="secondary">
              <a href={getGoogleLoginUrl()} rel="noreferrer">
                Continue with Google
              </a>
            </Button>
          </div>

          <div className="text-muted-foreground mt-6 flex flex-wrap items-center gap-3 text-sm">
            <Button asChild size="sm" variant="outline">
              <Link href="/">Back home</Link>
            </Button>
            <span>Refresh handling will redirect protected flows back here.</span>
          </div>
        </div>
      </section>
    </main>
  );
}
