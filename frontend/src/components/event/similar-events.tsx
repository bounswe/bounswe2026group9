"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Loader2 } from "lucide-react";

import { fetchSimilarEvents, type EventListItem } from "@/lib/events-api";
import { cn } from "@/lib/utils";

interface SimilarEventsSectionProps {
  eventId: string;
}

function formatShortDate(dateStr: string): string {
  const d = new Date(dateStr);
  const date = d.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
  const time = d.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  return `${date} · ${time}`;
}

export function SimilarEventsSection({ eventId }: SimilarEventsSectionProps) {
  const [events, setEvents] = useState<EventListItem[] | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    fetchSimilarEvents(eventId)
      .then((items) => {
        if (!cancelled) setEvents(items);
      })
      .catch(() => {
        if (!cancelled) setEvents([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [eventId]);

  if (!loading && (!events || events.length === 0)) return null;

  return (
    <section className="mt-8" aria-labelledby="similar-events-heading">
      <h3
        id="similar-events-heading"
        className="font-heading text-brand-dark mb-3 text-lg font-semibold"
      >
        Similar events
      </h3>

      {loading ? (
        <div
          className="border-brand-mid-alpha flex h-32 items-center justify-center rounded-xl border bg-white"
          role="status"
          aria-label="Loading similar events"
        >
          <Loader2 className="text-brand-mid size-5 animate-spin" />
        </div>
      ) : (
        <ul
          className="-mx-1 flex snap-x gap-3 overflow-x-auto px-1 pb-2 [scrollbar-width:thin]"
          role="list"
        >
          {events!.map((event) => (
            <li key={event.id} className="snap-start">
              <SimilarEventCard event={event} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

interface SimilarEventCardProps {
  event: EventListItem;
}

function SimilarEventCard({ event }: SimilarEventCardProps) {
  const primaryCategory = event.categories[0]?.name;
  const locationName = event.primary_location?.name;
  const [imageBroken, setImageBroken] = useState(false);
  const showImage = !!event.primary_image_url && !imageBroken;

  return (
    <Link
      href={`/event/${event.id}`}
      className={cn(
        "border-brand-mid-alpha hover:border-brand-mid focus-visible:ring-brand-dark group relative block w-[200px] shrink-0 overflow-hidden rounded-xl border bg-white transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2",
      )}
      aria-label={`Similar event: ${event.title}`}
    >
      <div className="bg-brand-mid/20 relative h-24 w-full overflow-hidden">
        {showImage ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={event.primary_image_url!}
            alt=""
            className="size-full object-cover transition-transform duration-300 group-hover:scale-105"
            loading="lazy"
            onError={() => setImageBroken(true)}
          />
        ) : (
          <div className="bg-brand-surface flex size-full items-center justify-center">
            <span className="text-brand-mid font-serif text-xs tracking-wider uppercase">
              No image
            </span>
          </div>
        )}
      </div>
      <div className="space-y-1 p-3">
        <p className="text-brand-dark line-clamp-2 text-sm leading-tight font-semibold">
          {event.title}
        </p>
        <p className="text-brand-mid text-xs">{formatShortDate(event.start_datetime)}</p>
        {primaryCategory ? (
          <p className="text-brand-mid truncate text-xs">{primaryCategory}</p>
        ) : locationName ? (
          <p className="text-brand-mid truncate text-xs">{locationName}</p>
        ) : null}
      </div>
    </Link>
  );
}
