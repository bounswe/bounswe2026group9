"use client";

import { startTransition, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { getErrorMessage } from "@/lib/api";
import { useAuth } from "@/hooks/use-auth";

export default function AuthCallbackPage() {
  const router = useRouter();
  const { refreshSession } = useAuth();
  const [message, setMessage] = useState("Finalizing your sign-in session...");

  useEffect(() => {
    void (async () => {
      try {
        await refreshSession();
        setMessage("Session established. Redirecting to the dashboard...");
        startTransition(() => {
          router.replace("/dashboard");
        });
      } catch (error) {
        setMessage(getErrorMessage(error, "Unable to complete Google sign-in."));
        startTransition(() => {
          router.replace("/login?reason=oauth-failed");
        });
      }
    })();
  }, [refreshSession, router]);

  return (
    <main className="flex flex-1 items-center justify-center px-6 py-16">
      <section className="border-border/70 bg-card/92 shadow-brand-panel w-full max-w-xl rounded-[2rem] border p-10 text-center">
        <p className="text-accent text-sm font-semibold tracking-[0.24em] uppercase">
          OAuth Callback
        </p>
        <h1 className="text-foreground mt-4 text-4xl">Connecting your account</h1>
        <p className="text-muted-foreground mt-4 text-base leading-7">{message}</p>
      </section>
    </main>
  );
}
