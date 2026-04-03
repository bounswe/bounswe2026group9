"use client";

import { startTransition, useEffect, useMemo } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { useAuth } from "@/hooks/use-auth";

interface BuildProtectedRedirectOptions {
  nextPath?: string;
  redirectReason?: string;
  redirectTo?: string;
}

interface ProtectedRouteProps extends BuildProtectedRedirectOptions {
  children: React.ReactNode;
  loadingMessage?: string;
  loadingTitle?: string;
}

export function buildProtectedRedirectUrl({
  nextPath,
  redirectReason = "protected",
  redirectTo = "/login",
}: BuildProtectedRedirectOptions = {}) {
  const url = new URL(redirectTo, "http://localhost");
  url.searchParams.set("reason", redirectReason);

  if (nextPath) {
    url.searchParams.set("next", nextPath);
  }

  return `${url.pathname}${url.search}`;
}

function resolveNextPath(
  pathname: string | null,
  searchParams: Pick<URLSearchParams, "toString"> | null,
) {
  if (!pathname) {
    return "/";
  }

  const search = searchParams?.toString();
  return search ? `${pathname}?${search}` : pathname;
}

export function ProtectedRoute({
  children,
  loadingMessage = "The auth provider is checking the refresh cookie before rendering authenticated content.",
  loadingTitle = "Restoring session...",
  nextPath,
  redirectReason = "protected",
  redirectTo = "/login",
}: ProtectedRouteProps) {
  const { isInitialized, isLoggingOut, status } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();

  const requestedPath = useMemo(
    () => nextPath ?? resolveNextPath(pathname, searchParams),
    [nextPath, pathname, searchParams],
  );

  useEffect(() => {
    if (!isInitialized || isLoggingOut || status !== "guest") {
      return;
    }

    startTransition(() => {
      router.replace(
        buildProtectedRedirectUrl({
          nextPath: requestedPath,
          redirectReason,
          redirectTo,
        }),
      );
    });
  }, [isInitialized, isLoggingOut, redirectReason, redirectTo, requestedPath, router, status]);

  if (!isInitialized || status === "loading") {
    return (
      <main className="flex flex-1 items-center justify-center px-6 py-16">
        <div className="border-border/70 bg-card/90 shadow-brand-panel w-full max-w-xl rounded-[2rem] border p-10 text-center">
          <p className="text-accent text-sm font-semibold tracking-[0.24em] uppercase">
            Protected Route
          </p>
          <h1 className="text-foreground mt-4 text-4xl">{loadingTitle}</h1>
          <p className="text-muted-foreground mt-4 text-base leading-7">{loadingMessage}</p>
        </div>
      </main>
    );
  }

  if (status === "guest") {
    return null;
  }

  return children;
}
