"use client";

import dynamic from "next/dynamic";
import { Clock, MapPin } from "lucide-react";

import type { EventLocation, EventSegment } from "@/lib/events-api";
import { cn } from "@/lib/utils";

const RouteMap = dynamic(
  () => import("@/components/events/route-map").then((mod) => mod.RouteMap),
  {
    loading: () => (
      <div className="border-border/80 bg-brand-surface/35 h-[220px] animate-pulse rounded-[12px] border sm:h-[260px]" />
    ),
    ssr: false,
  },
);

interface ItineraryTimelineProps {
  locations: EventLocation[];
  segments: EventSegment[];
  /** Hide the route map preview — useful when the caller already shows one. */
  hideMap?: boolean;
  className?: string;
}

interface TimelineRow {
  location: EventLocation;
  segment: EventSegment | null;
}

function formatRange(start: string, end: string): string {
  const s = new Date(start);
  const e = new Date(end);
  const sameDay =
    s.getFullYear() === e.getFullYear() &&
    s.getMonth() === e.getMonth() &&
    s.getDate() === e.getDate();
  const dateFmt = new Intl.DateTimeFormat("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
  const timeFmt = new Intl.DateTimeFormat("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  if (sameDay) {
    return `${dateFmt.format(s)} · ${timeFmt.format(s)}–${timeFmt.format(e)}`;
  }
  return `${dateFmt.format(s)} ${timeFmt.format(s)} → ${dateFmt.format(e)} ${timeFmt.format(e)}`;
}

/**
 * Vertical itinerary timeline for the event detail page (issue #157).
 *
 * Renders one row per location, in `order_index` order, with a numbered marker
 * connected by a dashed vertical guide. When the corresponding segment timing
 * exists, the row also shows the start/end window and the host's notes.
 *
 * If the event has 2+ stops the component also renders a read-only RouteMap
 * preview above the timeline so attendees can see the polyline route at a glance.
 */
export function ItineraryTimeline({
  locations,
  segments,
  hideMap = false,
  className,
}: ItineraryTimelineProps) {
  if (locations.length === 0) {
    return null;
  }

  const sortedLocations = [...locations].sort((a, b) => a.order_index - b.order_index);
  const segmentByLocation = new Map<string, EventSegment>();
  for (const segment of segments) {
    segmentByLocation.set(segment.location_id, segment);
  }

  const rows: TimelineRow[] = sortedLocations.map((location) => ({
    location,
    segment: segmentByLocation.get(location.id) ?? null,
  }));

  const mapStops = sortedLocations.map((location) => ({
    id: location.id,
    latitude: location.latitude,
    longitude: location.longitude,
    label: location.name,
  }));

  return (
    <section className={cn("space-y-4", className)} aria-label="Event itinerary">
      {!hideMap && sortedLocations.length >= 1 && <RouteMap stops={mapStops} className="w-full" />}

      <ol className="space-y-0">
        {rows.map(({ location, segment }, index) => {
          const isLast = index === rows.length - 1;
          return (
            <li key={location.id} className="relative">
              <div className="flex gap-4">
                <div className="relative flex flex-col items-center">
                  <div
                    aria-label={`Stop ${index + 1}`}
                    className="bg-brand-dark shadow-brand-card relative z-10 flex size-9 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white"
                  >
                    {index + 1}
                  </div>
                  {!isLast && (
                    <span
                      aria-hidden="true"
                      className="border-brand-mid/60 mt-1 flex-1 border-l-2 border-dashed"
                    />
                  )}
                </div>
                <div className={cn("min-w-0 flex-1 pb-6", isLast && "pb-0")}>
                  <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                    <p className="font-heading text-brand-dark text-base font-semibold">
                      {location.name || `Stop ${index + 1}`}
                    </p>
                    {location.is_primary && (
                      <span className="border-brand-mid bg-brand-mid-alpha text-brand-dark rounded-full border px-2 py-0.5 text-[10px] font-bold tracking-wider uppercase">
                        Primary
                      </span>
                    )}
                  </div>
                  {location.location_address && (
                    <p className="text-brand-mid mt-0.5 flex items-start gap-1.5 text-xs leading-5">
                      <MapPin className="mt-[2px] size-3.5 shrink-0" />
                      <span className="break-words">{location.location_address}</span>
                    </p>
                  )}
                  {segment && (
                    <p className="text-brand-dark mt-1 flex items-center gap-1.5 text-[13px] font-semibold">
                      <Clock className="text-brand-mid size-3.5 shrink-0" />
                      {formatRange(segment.start_datetime, segment.end_datetime)}
                    </p>
                  )}
                  {segment?.description && (
                    <p className="text-brand-dark/85 mt-1 text-[13px] leading-6 break-words whitespace-pre-wrap">
                      {segment.description}
                    </p>
                  )}
                </div>
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
