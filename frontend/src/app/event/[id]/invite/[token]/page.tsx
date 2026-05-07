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
  const [errorMessage, setErrorMessage] = useState(
    "Something went wrong. The invite may be invalid or expired.",
  );
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

      <div className="mx-auto flex max-w-lg flex-col items-center justify-center px-6 py-32 text-center">
        {status === "loading" && (
          <>
            <Loader2 className="text-brand-mid mb-6 size-12 animate-spin" />
            <h1 className="font-heading text-brand-dark mb-2 text-2xl font-bold">
              Accepting Invite
            </h1>
            <p className="text-brand-mid text-sm">
              Please wait while we process your invitation...
            </p>
          </>
        )}

        {status === "success" && (
          <>
            <div className="mb-6 flex size-16 items-center justify-center rounded-full bg-green-100">
              <CheckCircle className="size-8 text-green-600" />
            </div>
            <h1 className="font-heading text-brand-dark mb-2 text-2xl font-bold">
              Invite Accepted!
            </h1>
            <p className="text-brand-mid mb-6 text-sm">
              You now have access to this event. You can view the full event details.
            </p>
            <button
              onClick={() => router.push(`/event/${id}`)}
              className="bg-brand-dark hover:bg-brand-dark/85 rounded-xl px-7 py-3.5 text-[15px] font-bold text-white transition-all hover:-translate-y-0.5 hover:shadow-lg"
            >
              View Event
            </button>
          </>
        )}

        {status === "error" && (
          <>
            <div className="mb-6 flex size-16 items-center justify-center rounded-full bg-red-100">
              <XCircle className="size-8 text-red-500" />
            </div>
            <h1 className="font-heading text-brand-dark mb-2 text-2xl font-bold">Invite Failed</h1>
            <p className="text-brand-mid mb-6 text-sm">{errorMessage}</p>
            <div className="flex gap-4">
              <Link
                href={`/event/${id}`}
                className="bg-brand-dark hover:bg-brand-dark/85 rounded-xl px-7 py-3.5 text-[15px] font-bold text-white transition-all"
              >
                Go to Event
              </Link>
              <Link
                href="/"
                className="border-brand-dark text-brand-dark hover:bg-brand-dark rounded-xl border-2 px-7 py-3.5 text-[15px] font-bold transition-all hover:text-white"
              >
                Browse Events
              </Link>
            </div>
          </>
        )}

        {status === "login-required" && (
          <>
            <div className="bg-brand-mid-alpha mb-6 flex size-16 items-center justify-center rounded-full">
              <Loader2 className="text-brand-mid size-8" />
            </div>
            <h1 className="font-heading text-brand-dark mb-2 text-2xl font-bold">
              Sign In Required
            </h1>
            <p className="text-brand-mid mb-6 text-sm">
              You need to sign in to accept this invite. After signing in, you&apos;ll be redirected
              back.
            </p>
            <Link
              href={`/login?next=/event/${id}/invite/${token}`}
              className="bg-brand-dark hover:bg-brand-dark/85 rounded-xl px-7 py-3.5 text-[15px] font-bold text-white transition-all hover:-translate-y-0.5 hover:shadow-lg"
            >
              Sign In
            </Link>
          </>
        )}
      </div>
    </div>
  );
}
