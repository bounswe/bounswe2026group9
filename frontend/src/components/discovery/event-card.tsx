import { useRouter } from "next/navigation";
import Link from "next/link";
import { Users, Bookmark, Check, Lock, Pencil } from "lucide-react";

import type { EventListItem } from "@/lib/events-api";
import { cn } from "@/lib/utils";

interface EventCardProps {
  currentUserId: string | null;
  event: EventListItem;
  isAuthenticated: boolean;
}

function formatDateShort(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

function formatTime(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export function EventCard({ currentUserId, event, isAuthenticated }: EventCardProps) {
  const router = useRouter();
  const isFull = event.is_full ?? event.going_count >= (event.attendee_limit ?? Infinity);
  const isPrivate = event.visibility === "private";
  const isOwner = currentUserId === event.host_id;
  const visibleCategories = event.categories.slice(0, 3);
  const hiddenCategoryCount = Math.max(event.categories.length - visibleCategories.length, 0);

  return (
    <Link
      href={`/events/${event.id}`}
      className="bg-brand-surface border-brand-mid-alpha group flex flex-col overflow-hidden rounded-xl border transition-all hover:-translate-y-0.5 hover:shadow-brand-card"
    >
      {/* Image area */}
      <div className="bg-brand-mid relative aspect-[16/10] w-full">
        {event.primary_image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={event.primary_image_url}
            alt={event.title}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center">
            <span className="text-xs font-bold uppercase tracking-widest text-white/40">
              Event Photo
            </span>
          </div>
        )}

        {/* Badges */}
        <div className="absolute top-2 right-2 flex gap-1.5">
          {isFull && (
            <span className="rounded-full bg-red-600 px-2.5 py-0.5 text-[10px] font-extrabold uppercase tracking-wide text-white">
              Full
            </span>
          )}
          {event.is_age_restricted && (
            <span className="rounded-full bg-black/60 px-2.5 py-0.5 text-[10px] font-extrabold uppercase tracking-wide text-white">
              18+
            </span>
          )}
          {isPrivate && (
            <span className="flex items-center gap-1 rounded-full bg-black/60 px-2.5 py-0.5 text-[10px] font-extrabold uppercase tracking-wide text-white">
              <Lock className="size-2.5" />
              Private
            </span>
          )}
        </div>
      </div>

      {/* Card body */}
      <div className="flex flex-1 flex-col p-4">
        {/* Title */}
        <h3 className="font-heading text-brand-dark mb-1 truncate text-[15px] font-bold">
          {event.title}
        </h3>

        {/* Date */}
        <p className="text-brand-mid mb-2 text-xs font-semibold">
          {formatDateShort(event.start_datetime)} · {formatTime(event.start_datetime)}
        </p>

        {/* Category tags */}
        {visibleCategories.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-1.5">
            {visibleCategories.map((category) => (
              <span
                className="bg-brand-mid-alpha text-brand-dark rounded-full px-3 py-0.5 text-[11px] font-bold"
                key={category.id}
              >
                {category.name}
              </span>
            ))}
            {hiddenCategoryCount > 0 ? (
              <span className="bg-background text-brand-dark rounded-full border border-brand-mid-alpha px-3 py-0.5 text-[11px] font-bold">
                +{hiddenCategoryCount}
              </span>
            ) : null}
          </div>
        )}

        {/* Attendee count */}
        <div className="text-brand-dark mb-4 flex items-center gap-1.5 text-xs">
          <Users className="text-brand-mid size-3.5" />
          <span>
            {event.going_count}
            {event.attendee_limit ? `/${event.attendee_limit}` : ""} going
          </span>
        </div>

        {/* Actions — only for registered users, pushed to bottom */}
        {isAuthenticated && (
          <div className="border-brand-mid-alpha mt-auto flex gap-2 border-t pt-3">
            {isOwner ? (
              <button
                onClick={(e) => {
                  e.preventDefault();
                  router.push(`/events/${event.id}/edit`);
                }}
                className="bg-brand-dark flex flex-1 items-center justify-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold text-white transition-colors hover:bg-brand-dark/85"
              >
                <Pencil className="size-3.5" />
                Edit
              </button>
            ) : (
              <>
                <button
                  onClick={(e) => {
                    e.preventDefault(); // Don't navigate to detail
                    // Bookmark action will be wired in Task 7
                  }}
                  className={cn(
                    "border-brand-mid flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-bold transition-colors",
                    event.is_bookmarked
                      ? "bg-brand-mid text-white"
                      : "text-brand-dark hover:bg-brand-mid-alpha",
                  )}
                >
                  <Bookmark className="size-3.5" />
                  {event.is_bookmarked ? "Saved" : "Bookmark"}
                </button>

                <button
                  onClick={(e) => {
                    e.preventDefault(); // Don't navigate to detail
                    // Going action will be wired in Task 7
                  }}
                  disabled={isFull}
                  className={cn(
                    "flex flex-1 items-center justify-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold transition-colors",
                    isFull
                      ? "cursor-not-allowed bg-brand-mid-alpha text-brand-dark/40"
                      : "bg-brand-mid text-white hover:bg-brand-mid/80",
                  )}
                >
                  <Check className="size-3.5" />
                  {isFull ? "Full" : "Going"}
                </button>
              </>
            )}
          </div>
        )}
      </div>
    </Link>
  );
}
