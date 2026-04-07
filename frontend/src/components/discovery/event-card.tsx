"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Users, Bookmark, BookmarkCheck, Check, Clock, Lock, Pencil } from "lucide-react";

import type { EventListItem } from "@/lib/events-api";
import { requestAccess } from "@/lib/events-api";
import {
  clearAccessRequestPending,
  isAccessRequestPending,
  markAccessRequestPending,
} from "@/lib/access-request-store";
import { useEventInteraction } from "@/hooks/use-event-interaction";
import { getEditEventPagePath } from "@/lib/event-routes";
import { cn } from "@/lib/utils";

interface EventCardProps {
  currentUserId: string | null;
  event: EventListItem;
  isAuthenticated: boolean;
}

function formatDateShort(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
}

function formatTime(dateStr: string): string {
  return new Date(dateStr).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false });
}

export function EventCard({ currentUserId, event, isAuthenticated }: EventCardProps) {
  const router = useRouter();
  const isOwner = currentUserId === event.host_id;
  const isPrivate = event.visibility === "private";
  const hasPrivateAccess = event.has_access === true || event.attendance_status === "going";
  const visibleCategories = event.categories.slice(0, 3);
  const hiddenCategoryCount = Math.max(event.categories.length - visibleCategories.length, 0);

  const { bookmarked, bookmarkCount, going, goingCount, toggleBookmark, toggleGoing } =
    useEventInteraction({
      eventId: event.id,
      initialBookmarked: event.is_bookmarked === true,
      initialBookmarkCount: event.bookmark_count ?? 0,
      initialGoing: event.attendance_status === "going",
      initialGoingCount: event.going_count ?? 0,
    });

  // Access request state for private events — initialised from backend status or user-scoped localStorage
  const [requestState, setRequestState] = useState<"idle" | "loading" | "error">("idle");
  const [accessError, setAccessError] = useState<string | null>(null);
  const isPendingRequest =
    isPrivate &&
    !hasPrivateAccess &&
    (
      event.access_request_status === "pending" ||
      isAccessRequestPending(event.id, currentUserId)
    );
  const accessStatus: "idle" | "loading" | "pending" | "error" =
    requestState === "loading" || requestState === "error"
      ? requestState
      : isPendingRequest
      ? "pending"
      : "idle";

  useEffect(() => {
    if (!isPrivate || !currentUserId) {
      return;
    }

    if (hasPrivateAccess || event.access_request_status === "approved") {
      clearAccessRequestPending(event.id, currentUserId);
      return;
    }

    if (event.access_request_status === "pending") {
      markAccessRequestPending(event.id, currentUserId);
      return;
    }

    if (event.access_request_status === "rejected") {
      clearAccessRequestPending(event.id, currentUserId);
    }
  }, [
    currentUserId,
    event.access_request_status,
    event.id,
    hasPrivateAccess,
    isPrivate,
  ]);

  const full =
    event.is_full === true ||
    (event.attendee_limit != null && goingCount >= event.attendee_limit);

  async function handleRequestAccess(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    setRequestState("loading");
    setAccessError(null);
    try {
      await requestAccess(event.id);
      markAccessRequestPending(event.id, currentUserId);
      setRequestState("idle");
    } catch (err: unknown) {
      const message = (
        err && typeof err === "object" && "message" in err
          ? (err as { message: string }).message
          : ""
      ).toLowerCase();

      if (message.includes("already granted")) {
        clearAccessRequestPending(event.id, currentUserId);
        setRequestState("idle");
        // User already has access — go to event detail
        router.push(`/event/${event.id}`);
      } else if (message.includes("already exists")) {
        // Request already sent — persist and show pending
        markAccessRequestPending(event.id, currentUserId);
        setRequestState("idle");
      } else {
        setRequestState("error");
        setAccessError("Could not send request.");
      }
    }
  }

  return (
    <Link
      href={`/event/${event.id}`}
      className="bg-brand-surface border-brand-mid-alpha group flex h-full flex-col overflow-hidden rounded-xl border transition-all hover:-translate-y-0.5 hover:shadow-brand-card"
    >
      {/* Image */}
      <div className="bg-brand-mid relative aspect-[16/10] w-full">
        {event.primary_image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={event.primary_image_url} alt={event.title} className="h-full w-full object-cover" />
        ) : (
          <div className="flex h-full w-full items-center justify-center">
            <span className="text-xs font-bold uppercase tracking-widest text-white/40">Event Photo</span>
          </div>
        )}
        <div className="absolute top-2 right-2 flex gap-1.5">
          {full && (
            <span className="rounded-full bg-red-600 px-2.5 py-0.5 text-[10px] font-extrabold uppercase tracking-wide text-white">Full</span>
          )}
          {event.is_age_restricted && (
            <span className="rounded-full bg-black/60 px-2.5 py-0.5 text-[10px] font-extrabold uppercase tracking-wide text-white">18+</span>
          )}
          {event.visibility === "private" && (
            <span className="flex items-center gap-1 rounded-full bg-black/60 px-2.5 py-0.5 text-[10px] font-extrabold uppercase tracking-wide text-white">
              <Lock className="size-2.5" /> Private
            </span>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="flex flex-1 flex-col p-4">
        <h3 className="font-heading text-brand-dark mb-1 line-clamp-2 text-[15px] font-bold">{event.title}</h3>
        <p className="text-brand-mid mb-2 text-xs font-semibold">
          {formatDateShort(event.start_datetime)} · {formatTime(event.start_datetime)}
        </p>

        {visibleCategories.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-1.5">
            {visibleCategories.map((c) => (
              <span key={c.id} className="bg-brand-mid-alpha text-brand-dark rounded-full px-3 py-0.5 text-[11px] font-bold">{c.name}</span>
            ))}
            {hiddenCategoryCount > 0 && (
              <span className="bg-background text-brand-dark rounded-full border border-brand-mid-alpha px-3 py-0.5 text-[11px] font-bold">+{hiddenCategoryCount}</span>
            )}
          </div>
        )}

        {/* Counts — always visible */}
        <div className="text-brand-dark mb-4 flex items-center gap-3 text-xs">
          <span className="flex items-center gap-1">
            <Users className="text-brand-mid size-3.5" />
            {goingCount}{event.attendee_limit ? `/${event.attendee_limit}` : ""} going
          </span>
          <span className="flex items-center gap-1">
            <Bookmark className="text-brand-mid size-3.5" />
            {bookmarkCount} saved
          </span>
        </div>

        {/* Actions */}
        {isAuthenticated && (
          <div className="border-brand-mid-alpha mt-auto flex gap-2 border-t pt-3">
            {isOwner ? (
              <button
                onClick={(e) => { e.preventDefault(); router.push(getEditEventPagePath(event.id)); }}
                className="bg-brand-dark flex flex-1 items-center justify-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold text-white transition-all duration-150 hover:bg-brand-dark/85 hover:shadow-md active:scale-[0.96] cursor-pointer"
              >
                <Pencil className="size-3.5" /> Edit
              </button>
            ) : (
              <>
                {/* Bookmark — always visible */}
                <button
                  onClick={(e) => { e.preventDefault(); e.stopPropagation(); void toggleBookmark(); }}
                  className={cn(
                    "flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-bold transition-all duration-150 cursor-pointer active:scale-[0.96]",
                    bookmarked
                      ? "bg-brand-dark border-brand-dark text-white hover:bg-brand-dark/80"
                      : "border-brand-mid text-brand-dark hover:bg-brand-mid-alpha",
                  )}
                >
                  {bookmarked ? <BookmarkCheck className="size-3.5" /> : <Bookmark className="size-3.5" />}
                  {bookmarked ? "Saved" : "Bookmark"}
                </button>

                {/* Private event without access → Request Access */}
                {isPrivate && !going && !hasPrivateAccess ? (
                  accessStatus === "pending" ? (
                    <div className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-brand-mid-alpha px-3 py-1.5 text-xs font-bold text-brand-dark/60 cursor-default">
                      <Clock className="size-3.5" />
                      Pending
                    </div>
                  ) : (
                    <button
                      onClick={(e) => { void handleRequestAccess(e); }}
                      disabled={accessStatus === "loading"}
                      title={accessError ?? undefined}
                      className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-brand-dark px-3 py-1.5 text-xs font-bold text-white transition-all duration-150 hover:bg-brand-dark/85 hover:shadow-md active:scale-[0.96] cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
                    >
                      <Lock className="size-3.5" />
                      {accessStatus === "loading" ? "Sending…" : accessStatus === "error" ? "Try Again" : "Request Access"}
                    </button>
                  )
                ) : (
                  /* Public event or private event with access → Going */
                  <button
                    onClick={(e) => { e.preventDefault(); e.stopPropagation(); void toggleGoing(); }}
                    disabled={full && !going}
                    className={cn(
                      "flex flex-1 items-center justify-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold transition-all duration-150",
                      full && !going
                        ? "cursor-not-allowed bg-brand-mid-alpha text-brand-dark/40"
                        : going
                        ? "bg-brand-dark text-white hover:bg-brand-dark/80 cursor-pointer active:scale-[0.96]"
                        : "bg-brand-mid text-white hover:bg-brand-mid/80 cursor-pointer active:scale-[0.96]",
                    )}
                  >
                    <Check className="size-3.5" />
                    {full && !going ? "Full" : going ? "Attended ✓" : "Going"}
                  </button>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </Link>
  );
}
