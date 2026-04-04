"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { Users, Bookmark, BookmarkCheck, Check, Lock, Pencil } from "lucide-react";

import type { EventListItem } from "@/lib/events-api";
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

  const full =
    event.is_full === true ||
    (event.attendee_limit != null && goingCount >= event.attendee_limit);

  return (
    <Link
      href={`/event/${event.id}`}
      className="bg-brand-surface border-brand-mid-alpha group flex flex-col overflow-hidden rounded-xl border transition-all hover:-translate-y-0.5 hover:shadow-brand-card"
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
        <h3 className="font-heading text-brand-dark mb-1 truncate text-[15px] font-bold">{event.title}</h3>
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
              </>
            )}
          </div>
        )}
      </div>
    </Link>
  );
}
