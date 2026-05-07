"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Check, CheckCircle, Loader2, Lock, Users, XCircle } from "lucide-react";

import { useAuth } from "@/hooks/use-auth";
import { Navbar } from "@/components/layout/navbar";
import { getProfileHref } from "@/lib/profile-route";
import {
  fetchEventDetail,
  fetchAccessRequests,
  updateAccessRequest,
  type EventDetail,
  type AccessRequest,
} from "@/lib/events-api";

export default function ManageAttendeesPage() {
  const { id } = useParams<{ id: string }>();
  const { user, isAuthenticated, isInitialized } = useAuth();
  const router = useRouter();

  const [event, setEvent] = useState<EventDetail | null>(null);
  const [accessRequests, setAccessRequests] = useState<AccessRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  useEffect(() => {
    if (!isInitialized) return;
    if (!isAuthenticated) {
      router.replace(`/login?next=/event/${id}/attendees`);
      return;
    }

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const detail = await fetchEventDetail(id);
        if (detail._type !== "full") {
          setError("You don't have access to manage this event.");
          return;
        }
        if (detail.host_id !== user?.id) {
          setError("Only the host can manage attendees.");
          return;
        }
        setEvent(detail);

        if (detail.visibility === "private") {
          const requests = await fetchAccessRequests(id);
          setAccessRequests(requests);
        }
      } catch {
        setError("Failed to load event. Please try again.");
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, [id, isInitialized, isAuthenticated, user?.id, router]);

  async function handleAction(requestId: string, action: "approved" | "rejected") {
    setActionLoading(requestId);
    try {
      await updateAccessRequest(id, requestId, action);
      setAccessRequests((prev) => prev.filter((r) => r.id !== requestId));
    } finally {
      setActionLoading(null);
    }
  }

  return (
    <div className="bg-brand-bg min-h-screen">
      <Navbar />

      <div className="mx-auto max-w-2xl px-6 py-10">
        <Link
          href={`/event/${id}`}
          className="text-brand-mid hover:text-brand-dark mb-8 inline-flex items-center gap-1.5 text-[15px] font-bold transition-colors"
        >
          <ArrowLeft className="size-4" />
          Back to Event
        </Link>

        {loading && (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="text-brand-mid size-8 animate-spin" />
          </div>
        )}

        {error && (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <XCircle className="mb-4 size-10 text-red-400" />
            <p className="text-brand-dark mb-2 text-lg font-bold">Access Denied</p>
            <p className="text-brand-mid text-sm">{error}</p>
          </div>
        )}

        {event && !loading && !error && (
          <div className="space-y-6">
            {/* Header */}
            <div>
              <p className="text-brand-mid mb-1 text-[11px] font-bold tracking-widest uppercase">
                Manage Attendees
              </p>
              <h1 className="font-heading text-brand-dark text-2xl font-bold">{event.title}</h1>
            </div>

            {/* Capacity card */}
            <div className="border-brand-mid-alpha rounded-xl border bg-white p-5">
              <div className="mb-4 flex items-center gap-2">
                <Users className="text-brand-mid size-4" />
                <p className="text-brand-mid text-[13px] font-bold tracking-widest uppercase">
                  Attendance
                </p>
              </div>

              <div className="mb-3 flex items-end gap-2">
                <span className="font-heading text-brand-dark text-4xl font-bold">
                  {event.going_count}
                </span>
                {event.attendee_limit && (
                  <span className="text-brand-mid mb-1 text-lg">/ {event.attendee_limit}</span>
                )}
                <span className="text-brand-mid mb-1 ml-1 text-sm">going</span>
              </div>

              {event.attendee_limit && (
                <div className="bg-brand-mid-alpha h-2 w-full overflow-hidden rounded-full">
                  <div
                    className="bg-brand-dark h-full rounded-full transition-all duration-300"
                    style={{
                      width: `${Math.min(100, (event.going_count / event.attendee_limit) * 100)}%`,
                    }}
                  />
                </div>
              )}

              {event.is_full && (
                <div className="mt-3 flex items-center gap-2 rounded-lg border border-orange-200 bg-orange-50 px-3 py-2">
                  <Users className="size-3.5 shrink-0 text-orange-500" />
                  <p className="text-[12px] font-bold text-orange-600">Event is at full capacity</p>
                </div>
              )}
            </div>

            {/* Attendees list */}
            {event.attendees && event.attendees.length > 0 ? (
              <div className="border-brand-mid-alpha rounded-xl border bg-white p-5">
                <p className="text-brand-mid mb-4 text-[11px] font-bold tracking-widest uppercase">
                  Going ({event.attendees.length})
                </p>
                <div className="space-y-2">
                  {event.attendees.map((attendee) => (
                    <Link
                      key={attendee.id}
                      href={getProfileHref(attendee.id, user?.id ?? null)}
                      aria-label={`View ${attendee.username}'s profile`}
                      className="bg-brand-bg hover:bg-brand-mid-alpha focus-visible:ring-brand-dark flex items-center gap-3 rounded-lg px-3 py-2.5 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-1"
                    >
                      <div className="bg-brand-mid flex size-8 shrink-0 items-center justify-center rounded-full text-[12px] font-bold text-white">
                        {attendee.username.slice(0, 2).toUpperCase()}
                      </div>
                      <span className="text-brand-dark text-[14px] font-bold">
                        {attendee.username}
                      </span>
                      <Check className="ml-auto size-3.5 text-green-600" />
                    </Link>
                  ))}
                </div>
              </div>
            ) : (
              <div className="border-brand-mid-alpha rounded-xl border bg-white p-5">
                <p className="text-brand-mid mb-3 text-[11px] font-bold tracking-widest uppercase">
                  Going
                </p>
                {event.going_count === 0 ? (
                  <p className="text-brand-mid text-sm">No attendees yet.</p>
                ) : (
                  <p className="text-brand-mid text-sm">
                    {event.going_count} {event.going_count === 1 ? "person is" : "people are"}{" "}
                    going.
                  </p>
                )}
              </div>
            )}

            {/* Access requests — private events only */}
            {event.visibility === "private" && (
              <div className="border-brand-mid-alpha rounded-xl border bg-white p-5">
                <div className="mb-4 flex items-center gap-2">
                  <Lock className="text-brand-mid size-4" />
                  <p className="text-brand-mid text-[11px] font-bold tracking-widest uppercase">
                    Access Requests
                  </p>
                </div>

                {accessRequests.length === 0 ? (
                  <p className="text-brand-mid text-sm">No pending access requests.</p>
                ) : (
                  <div className="space-y-2">
                    {accessRequests.map((req) => (
                      <div
                        key={req.id}
                        className="bg-brand-bg flex items-center justify-between gap-3 rounded-lg px-3 py-2.5"
                      >
                        <Link
                          href={getProfileHref(req.user_id, user?.id ?? null)}
                          aria-label={`View ${req.username}'s profile`}
                          className="focus-visible:ring-brand-dark flex min-w-0 items-center gap-3 rounded-md transition-colors hover:opacity-80 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-1"
                        >
                          <div className="bg-brand-surface text-brand-dark flex size-8 shrink-0 items-center justify-center rounded-full text-[12px] font-bold">
                            {req.username.slice(0, 2).toUpperCase()}
                          </div>
                          <span className="text-brand-dark truncate text-[14px] font-bold hover:underline">
                            {req.username}
                          </span>
                        </Link>
                        <div className="flex shrink-0 gap-2">
                          <button
                            onClick={() => {
                              void handleAction(req.id, "approved");
                            }}
                            disabled={actionLoading === req.id}
                            className="flex items-center gap-1.5 rounded-lg bg-green-600 px-3 py-1.5 text-[12px] font-bold text-white transition-colors hover:bg-green-700 disabled:opacity-50"
                          >
                            {actionLoading === req.id ? (
                              <Loader2 className="size-3.5 animate-spin" />
                            ) : (
                              <CheckCircle className="size-3.5" />
                            )}
                            Approve
                          </button>
                          <button
                            onClick={() => {
                              void handleAction(req.id, "rejected");
                            }}
                            disabled={actionLoading === req.id}
                            className="flex items-center gap-1.5 rounded-lg bg-red-500 px-3 py-1.5 text-[12px] font-bold text-white transition-colors hover:bg-red-600 disabled:opacity-50"
                          >
                            <XCircle className="size-3.5" />
                            Reject
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
