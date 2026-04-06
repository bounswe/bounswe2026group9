"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Map, { Marker, Popup, type MapRef } from "react-map-gl/maplibre";
import { Bookmark, BookmarkCheck, Check, Clock, Lock, Minus, Pencil, Plus, Users, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { requestAccess, type EventListItem } from "@/lib/events-api";
import { useEventInteraction } from "@/hooks/use-event-interaction";
import { getEditEventPagePath } from "@/lib/event-routes";
import {
  clearAccessRequestPending,
  isAccessRequestPending,
  markAccessRequestPending,
} from "@/lib/access-request-store";
import { cn } from "@/lib/utils";

import "maplibre-gl/dist/maplibre-gl.css";

const MAPTILER_STYLE = "https://tiles.openfreemap.org/styles/liberty";
const DEFAULT_CENTER = { longitude: 28.9784, latitude: 41.0082, zoom: 11 };

interface MapViewProps {
  currentUserId: string | null;
  events: EventListItem[];
  isAuthenticated: boolean;
}

function formatDateShort(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
}

function formatTime(dateStr: string): string {
  return new Date(dateStr).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false });
}

function CategoryIcon({ name }: { name: string }) {
  return <span className="text-[10px] font-extrabold text-white uppercase">{name.slice(0, 1)}</span>;
}

// ── Popup body — separate component so it can use the shared hook ────────────

function PopupBody({
  event,
  isAuthenticated,
  currentUserId,
  onClose,
}: {
  event: EventListItem;
  isAuthenticated: boolean;
  currentUserId: string | null;
  onClose: () => void;
}) {
  const router = useRouter();
  const { bookmarked, bookmarkCount, going, goingCount, toggleBookmark, toggleGoing } =
    useEventInteraction({
      eventId: event.id,
      initialBookmarked: event.is_bookmarked === true,
      initialBookmarkCount: event.bookmark_count ?? 0,
      initialGoing: event.attendance_status === "going",
      initialGoingCount: event.going_count ?? 0,
    });
  const isPrivate = event.visibility === "private";
  const hasPrivateAccess = event.has_access === true || event.attendance_status === "going";
  const [requestState, setRequestState] = useState<"idle" | "loading" | "error">("idle");
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

  const full =
    event.is_full === true ||
    (event.attendee_limit != null && goingCount >= event.attendee_limit);

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

  async function handleRequestAccess() {
    setRequestState("loading");
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
        router.push(`/event/${event.id}`);
      } else if (message.includes("already exists")) {
        markAccessRequestPending(event.id, currentUserId);
        setRequestState("idle");
      } else {
        setRequestState("error");
      }
    }
  }

  return (
    <div
      className="relative overflow-hidden rounded-xl border border-brand-mid-alpha bg-white shadow-brand-panel"
      style={{ width: "min(280px, calc(100vw - 2rem))" }}
    >
      <button
        onClick={onClose}
        className="absolute right-2 top-2 z-10 flex size-6 items-center justify-center rounded-full bg-black/20 text-white transition-colors hover:bg-black/40 cursor-pointer"
      >
        <X className="size-3.5" />
      </button>

      <div className="bg-brand-mid relative h-20 w-full">
        {event.primary_image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={event.primary_image_url} alt={event.title} className="h-full w-full object-cover" />
        ) : (
          <div className="flex h-full w-full items-center justify-center">
            <span className="text-[10px] font-bold uppercase tracking-widest text-white/40">Event Photo</span>
          </div>
        )}
      </div>

      <div className="p-4">
        <h3 className="font-heading text-brand-dark mb-1 text-[15px] font-bold leading-tight">{event.title}</h3>
        <p className="text-brand-mid mb-2 text-xs font-semibold">
          {formatDateShort(event.start_datetime)} · {formatTime(event.start_datetime)}
        </p>

        {event.categories[0] && (
          <span className="bg-brand-mid-alpha text-brand-dark mb-3 inline-block rounded-full px-3 py-0.5 text-[11px] font-bold">
            {event.categories[0].name}
          </span>
        )}

        <div className="text-brand-dark mb-3 flex items-center gap-3 text-xs">
          <span className="flex items-center gap-1">
            <Users className="text-brand-mid size-3.5" />
            {goingCount}{event.attendee_limit ? `/${event.attendee_limit}` : ""} going
          </span>
          <span className="flex items-center gap-1">
            <Bookmark className="text-brand-mid size-3.5" />
            {bookmarkCount} saved
          </span>
        </div>

        <Link href={`/event/${event.id}`} className="text-brand-mid text-sm font-bold transition-colors hover:text-brand-dark cursor-pointer">
          View Details →
        </Link>

        {isAuthenticated && (
          <div className="border-brand-mid-alpha mt-3 flex gap-2 border-t pt-3">
            {currentUserId === event.host_id ? (
              <Link
                href={getEditEventPagePath(event.id)}
                className="bg-brand-dark flex flex-1 items-center justify-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold text-white transition-all duration-150 hover:bg-brand-dark/85 hover:shadow-md cursor-pointer"
              >
                <Pencil className="size-3.5" /> Edit
              </Link>
            ) : (
              <>
                <button
                  onClick={() => { void toggleBookmark(); }}
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
                {isPrivate && !going && !hasPrivateAccess ? (
                  accessStatus === "pending" ? (
                    <div className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-brand-mid-alpha px-3 py-1.5 text-xs font-bold text-brand-dark/60">
                      <Clock className="size-3.5" />
                      Pending
                    </div>
                  ) : (
                    <button
                      onClick={() => { void handleRequestAccess(); }}
                      disabled={accessStatus === "loading"}
                      className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-brand-dark px-3 py-1.5 text-xs font-bold text-white transition-all duration-150 hover:bg-brand-dark/85 hover:shadow-md active:scale-[0.96] disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      <Lock className="size-3.5" />
                      {accessStatus === "loading" ? "Sending…" : accessStatus === "error" ? "Try Again" : "Request Access"}
                    </button>
                  )
                ) : (
                  <button
                    onClick={() => { void toggleGoing(); }}
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
    </div>
  );
}

// ── Main MapView ─────────────────────────────────────────────────────────────

interface ActivePopup {
  event: EventListItem;
  longitude: number;
  latitude: number;
}

export function MapView({ currentUserId, events, isAuthenticated }: MapViewProps) {
  const [popup, setPopup] = useState<ActivePopup | null>(null);
  const mapRef = useRef<MapRef>(null);
  const mappableEvents = events.filter((e) => e.primary_location !== null);

  const handleMarkerClick = useCallback((event: EventListItem) => {
    const loc = event.primary_location!;
    setPopup({ event, longitude: loc.longitude, latitude: loc.latitude });
  }, []);

  return (
    <div className="relative flex-1">
      <div className="absolute right-3 top-3 z-10 flex flex-col gap-1 sm:right-4 sm:top-4">
        <button onClick={() => mapRef.current?.zoomIn()} className="flex size-8 items-center justify-center rounded-lg border border-brand-mid-alpha bg-white/90 text-brand-dark shadow-brand-card backdrop-blur-sm transition-colors hover:bg-white sm:size-9 cursor-pointer" aria-label="Zoom in">
          <Plus className="size-4" />
        </button>
        <button onClick={() => mapRef.current?.zoomOut()} className="flex size-8 items-center justify-center rounded-lg border border-brand-mid-alpha bg-white/90 text-brand-dark shadow-brand-card backdrop-blur-sm transition-colors hover:bg-white sm:size-9 cursor-pointer" aria-label="Zoom out">
          <Minus className="size-4" />
        </button>
      </div>

      <Map ref={mapRef} initialViewState={DEFAULT_CENTER} style={{ width: "100%", height: "100%" }} mapStyle={MAPTILER_STYLE} attributionControl={false}>
        {mappableEvents.map((event) => {
          const loc = event.primary_location!;
          const isActive = popup?.event.id === event.id;
          const primaryCategory = event.categories[0];
          return (
            <Marker key={event.id} longitude={loc.longitude} latitude={loc.latitude} anchor="bottom" onClick={(e) => { e.originalEvent.stopPropagation(); handleMarkerClick(event); }}>
              <div className={cn("flex cursor-pointer flex-col items-center transition-transform hover:scale-110", isActive && "scale-110")}>
                <div className={cn("relative flex size-9 items-center justify-center rounded-full shadow-brand-card", isActive ? "bg-brand-mid ring-4 ring-brand-mid/30" : "bg-brand-dark")}>
                  {primaryCategory ? <CategoryIcon name={primaryCategory.name} /> : <span className="text-[10px] font-extrabold text-white">E</span>}
                  <span className={cn("absolute -bottom-1.5 left-1/2 -translate-x-1/2 border-x-[6px] border-t-[8px] border-x-transparent", isActive ? "border-t-brand-mid" : "border-t-brand-dark")} />
                </div>
              </div>
            </Marker>
          );
        })}

        {popup && (
          <Popup longitude={popup.longitude} latitude={popup.latitude} anchor="top" closeOnClick={false} onClose={() => setPopup(null)} className="!p-0 !bg-transparent !border-0 !shadow-none" maxWidth="280px">
            <PopupBody event={popup.event} isAuthenticated={isAuthenticated} currentUserId={currentUserId} onClose={() => setPopup(null)} />
          </Popup>
        )}
      </Map>

      <div className="absolute bottom-3 left-3 rounded bg-white/80 px-2 py-0.5 text-[9px] text-gray-500 sm:bottom-2 sm:left-auto sm:right-2 sm:text-[10px]">
        © <a href="https://openfreemap.org" target="_blank" rel="noreferrer">OpenFreeMap</a> · © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a>
      </div>
    </div>
  );
}
