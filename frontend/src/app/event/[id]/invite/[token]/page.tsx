"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { CheckCircle, Loader2, XCircle } from "lucide-react";

import { useAuth } from "@/hooks/use-auth";
import { Navbar } from "@/components/layout/navbar";
import { acceptInvite } from "@/lib/events-api";

type InviteStatus = "loading" | "success" | "error" | "login-required";

export default function InviteAcceptPage() {
  const { id, token } = useParams<{ id: string; token: string }>();
  const { isAuthenticated, isInitialized } = useAuth();
  const router = useRouter();

  const [requestStatus, setRequestStatus] = useState<"loading" | "success" | "error">("loading");
  const [errorMessage, setErrorMessage] = useState("Something went wrong. The invite may be invalid or expired.");
  const status: InviteStatus =
    !isInitialized || requestStatus === "loading"
      ? "loading"
      : !isAuthenticated
      ? "login-required"
      : requestStatus;

  useEffect(() => {
    if (!isInitialized || !id || !token || !isAuthenticated) {
      return;
    }

    let cancelled = false;

    acceptInvite(id, token)
      .then(() => {
        if (!cancelled) {
          setRequestStatus("success");
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err && typeof err === "object" && "message" in err) {
          setErrorMessage((err as { message: string }).message);
        }
        setRequestStatus("error");
      });

    return () => {
      cancelled = true;
    };
  }, [id, token, isAuthenticated, isInitialized]);

  return (
    <div className="bg-brand-bg min-h-screen">
      <Navbar />

      <div className="flex flex-col items-center justify-center px-6 py-32 text-center max-w-lg mx-auto">
        {status === "loading" && (
          <>
            <Loader2 className="size-12 text-brand-mid animate-spin mb-6" />
            <h1 className="font-heading text-2xl font-bold text-brand-dark mb-2">
              Accepting Invite
            </h1>
            <p className="text-brand-mid text-sm">Please wait while we process your invitation...</p>
          </>
        )}

        {status === "success" && (
          <>
            <div className="flex size-16 items-center justify-center rounded-full bg-green-100 mb-6">
              <CheckCircle className="size-8 text-green-600" />
            </div>
            <h1 className="font-heading text-2xl font-bold text-brand-dark mb-2">
              Invite Accepted!
            </h1>
            <p className="text-brand-mid text-sm mb-6">
              You now have access to this event. You can view the full event details.
            </p>
            <button
              onClick={() => router.push(`/event/${id}`)}
              className="rounded-xl bg-brand-dark px-7 py-3.5 text-[15px] font-bold text-white transition-all hover:bg-brand-dark/85 hover:-translate-y-0.5 hover:shadow-lg"
            >
              View Event
            </button>
          </>
        )}

        {status === "error" && (
          <>
            <div className="flex size-16 items-center justify-center rounded-full bg-red-100 mb-6">
              <XCircle className="size-8 text-red-500" />
            </div>
            <h1 className="font-heading text-2xl font-bold text-brand-dark mb-2">
              Invite Failed
            </h1>
            <p className="text-brand-mid text-sm mb-6">{errorMessage}</p>
            <div className="flex gap-4">
              <Link
                href={`/event/${id}`}
                className="rounded-xl bg-brand-dark px-7 py-3.5 text-[15px] font-bold text-white transition-all hover:bg-brand-dark/85"
              >
                Go to Event
              </Link>
              <Link
                href="/"
                className="rounded-xl border-2 border-brand-dark px-7 py-3.5 text-[15px] font-bold text-brand-dark transition-all hover:bg-brand-dark hover:text-white"
              >
                Browse Events
              </Link>
            </div>
          </>
        )}

        {status === "login-required" && (
          <>
            <div className="flex size-16 items-center justify-center rounded-full bg-brand-mid-alpha mb-6">
              <Loader2 className="size-8 text-brand-mid" />
            </div>
            <h1 className="font-heading text-2xl font-bold text-brand-dark mb-2">
              Sign In Required
            </h1>
            <p className="text-brand-mid text-sm mb-6">
              You need to sign in to accept this invite. After signing in, you&apos;ll be redirected back.
            </p>
            <Link
              href={`/login?next=/event/${id}/invite/${token}`}
              className="rounded-xl bg-brand-dark px-7 py-3.5 text-[15px] font-bold text-white transition-all hover:bg-brand-dark/85 hover:-translate-y-0.5 hover:shadow-lg"
            >
              Sign In
            </Link>
          </>
        )}
      </div>
    </div>
  );
}
