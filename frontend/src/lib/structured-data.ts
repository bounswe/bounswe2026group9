// JSON-LD 1.1 / Schema.org structured-data builders for public pages.
// Issue #243.
//
// Two builders are exported:
//   - buildEventStructuredData: Schema.org Event for /event/[id]
//   - buildHostStructuredData : Schema.org Person (+ AggregateRating) for /profile/[id]
//
// Both produce a plain object suitable for rendering inside
// <script type="application/ld+json">. Pass the result through JSON.stringify
// in the consumer.
//
// Privacy contract for Event:
//   - Public events emit the full payload (description, location, image, etc.).
//   - Private events emit ONLY visibility-safe fields (name, dates, status, url,
//     categories) — same surface a guest already sees in the limited preview.
//   - Cancelled / ended status is reflected via eventStatus so search engines
//     don't show stale events as bookable.

import type {
  AnyEventDetail,
  EventDetail,
  EventLocation,
  HostProfile,
} from "@/lib/events-api";

const EVENT_STATUS_MAP: Record<EventDetail["status"], string> = {
  draft: "https://schema.org/EventScheduled",
  published: "https://schema.org/EventScheduled",
  updated: "https://schema.org/EventRescheduled",
  cancelled: "https://schema.org/EventCancelled",
  ended: "https://schema.org/EventScheduled",
};

function eventUrl(baseUrl: string, eventId: string): string {
  return `${baseUrl.replace(/\/$/, "")}/event/${eventId}`;
}

function profileUrl(baseUrl: string, userId: string): string {
  return `${baseUrl.replace(/\/$/, "")}/profile/${userId}`;
}

function pickPrimaryLocation(locations: EventLocation[] | undefined): EventLocation | null {
  if (!locations || locations.length === 0) return null;
  return locations.find((l) => l.is_primary) ?? locations[0];
}

/**
 * Build a Schema.org Event object for the given event payload.
 *
 * `host` is optional; when provided, organizer is filled with the host's
 * username and profile URL.
 *
 * For private events (or limited responses) only the visibility-safe subset
 * is emitted — never description, location coordinates, attendees, or images.
 */
export function buildEventStructuredData(
  event: AnyEventDetail,
  host: HostProfile | null,
  baseUrl: string,
): Record<string, unknown> {
  const base: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "Event",
    name: event.title,
    startDate: event.start_datetime,
    endDate: event.end_datetime,
    eventStatus: EVENT_STATUS_MAP[event.status],
    eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
    url: eventUrl(baseUrl, event.id),
  };

  // Categories are visible in both limited and full views, safe to expose.
  const categoryNames = event.categories.map((c) => c.name).filter(Boolean);
  if (categoryNames.length > 0) {
    base.keywords = categoryNames.join(", ");
  }

  // Private events stop here — never leak description, location, attendees.
  // Type-narrowing is done inline so TS sees `fullEvent` as EventDetail.
  if (event._type !== "full" || event.visibility !== "public") {
    return base;
  }
  const fullEvent: EventDetail = event;

  if (fullEvent.description) {
    base.description = fullEvent.description;
  }

  if (fullEvent.images && fullEvent.images.length > 0) {
    base.image = fullEvent.images.map((img) => img.image_url);
  }

  const primary = pickPrimaryLocation(fullEvent.locations);
  if (primary) {
    base.location = {
      "@type": "Place",
      name: primary.name,
      geo: {
        "@type": "GeoCoordinates",
        latitude: primary.latitude,
        longitude: primary.longitude,
      },
    };
  }

  if (host && fullEvent.host_id) {
    base.organizer = {
      "@type": "Person",
      name: host.username,
      url: profileUrl(baseUrl, fullEvent.host_id),
    };
  }

  // Capacity, when explicitly set by the host, is public on the detail page.
  if (fullEvent.attendee_limit != null) {
    base.maximumAttendeeCapacity = fullEvent.attendee_limit;
  }

  // Free-of-charge hint via venue metadata. We only set isAccessibleForFree
  // when the host explicitly typed something starting with "free" — guessing
  // would mislead crawlers, so the conservative default is to omit.
  const price = fullEvent.venue_metadata?.price?.toLowerCase() ?? "";
  if (price.startsWith("free")) {
    base.isAccessibleForFree = true;
  }

  return base;
}

/**
 * Build a Schema.org Person object for a host profile.
 *
 * `email` and `telephone` are only included when the backend has already
 * gated them through the user's privacy settings (the API returns them as
 * null when the host opted out, so we just forward what we got).
 *
 * AggregateRating is included when `average_rating` is available.
 * `ratingCount` is intentionally omitted — the profile endpoint doesn't
 * expose it today, and emitting a fake count would be worse than leaving
 * it off. Schema.org allows AggregateRating with `ratingValue`,
 * `bestRating`, and `worstRating` alone.
 */
export function buildHostStructuredData(
  host: HostProfile,
  baseUrl: string,
): Record<string, unknown> {
  type WithSameAs = string | undefined;

  const data: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "Person",
    identifier: host.id,
    name: host.username,
    url: profileUrl(baseUrl, host.id),
  };

  if (host.email) {
    data.email = host.email;
  }
  if (host.phone_number) {
    data.telephone = host.phone_number;
  }

  if (host.average_rating !== null && host.average_rating !== undefined) {
    data.aggregateRating = {
      "@type": "AggregateRating",
      ratingValue: Number(host.average_rating.toFixed(2)),
      bestRating: 5,
      worstRating: 1,
    };
  }

  // sameAs is left empty — kept on the type to make adding social links
  // trivial later without changing the consumer signature.
  void (undefined as WithSameAs);

  return data;
}
