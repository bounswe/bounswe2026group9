"use client";

import { startTransition, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { useAuth } from "@/hooks/use-auth";

interface GuestOnlyRouteProps {
  children: React.ReactNode;
  fallbackPath?: string;
}

function resolveRedirectPath(
  searchParams: ReturnType<typeof useSearchParams>,
  fallbackPath: string,
) {
  const nextPath = searchParams.get("next");

  if (nextPath?.startsWith("/")) {
    return nextPath;
  }

  return fallbackPath;
}

export function GuestOnlyRoute({ children, fallbackPath = "/dashboard" }: GuestOnlyRouteProps) {
  const { isInitialized, status } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    if (!isInitialized || status !== "authenticated") {
      return;
    }

    startTransition(() => {
      router.replace(resolveRedirectPath(searchParams, fallbackPath));
    });
  }, [fallbackPath, isInitialized, router, searchParams, status]);

  if (!isInitialized || status === "loading" || status === "authenticated") {
    return null;
  }

  return children;
}
