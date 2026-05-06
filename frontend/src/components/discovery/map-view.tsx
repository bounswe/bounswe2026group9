"use client";

import { useRef, useState, useEffect } from "react";
import Map, { Popup, Source, Layer, type MapRef } from "react-map-gl/maplibre";
import { Bookmark, BookmarkCheck, Minus, Pencil, Plus, Users, X } from "lucide-react";
import Link from "next/link";

import { type EventListItem, type EventGeoJSONProperties, type GeoJSONFeatureCollection, fetchGeoJsonEvents, type TemporalFilter } from "@/lib/events-api";
import { useEventInteraction } from "@/hooks/use-event-interaction";
import { getEditEventPagePath } from "@/lib/event-routes";
import { cn } from "@/lib/utils";
import { useSearchParams } from "next/navigation";

import "maplibre-gl/dist/maplibre-gl.css";

const MAPTILER_STYLE = "https://tiles.openfreemap.org/styles/liberty";
const DEFAULT_CENTER = { longitude: 28.9784, latitude: 41.0082, zoom: 11 };

interface MapViewProps {
  currentUserId: string | null;
  // Kept for backward compatibility with page.tsx, but ignored in favor of GeoJSON fetch
  events?: EventListItem[]; 
  isAuthenticated: boolean;
}

function formatDateShort(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
}

function formatTime(dateStr: string): string {
  return new Date(dateStr).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false });
}



// ── Popup body — separate component so it can use the shared hook ────────────

function PopupBody({
  event,
  isAuthenticated,
  currentUserId,
  onClose,
}: {
  event: EventGeoJSONProperties;
  isAuthenticated: boolean;
  currentUserId: string | null;
  onClose: () => void;
}) {
  const { bookmarked, bookmarkCount, goingCount, toggleBookmark } =
    useEventInteraction({
      eventId: event.id,
      initialBookmarked: event.is_bookmarked === true,
      initialBookmarkCount: event.bookmark_count ?? 0,
      initialGoing: event.attendance_status === "going",
      initialGoingCount: event.going_count ?? 0,
    });

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

        {event.primary_category && (
          <span className="bg-brand-mid-alpha text-brand-dark mb-3 inline-block rounded-full px-3 py-0.5 text-[11px] font-bold">
            {event.primary_category}
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
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main MapView ─────────────────────────────────────────────────────────────

interface ActivePopup {
  event: EventGeoJSONProperties;
  longitude: number;
  latitude: number;
}

export function MapView({ currentUserId, isAuthenticated }: MapViewProps) {
  const [popup, setPopup] = useState<ActivePopup | null>(null);
  const mapRef = useRef<MapRef>(null);
  const searchParams = useSearchParams();
  
  const [geoJson, setGeoJson] = useState<GeoJSONFeatureCollection | null>(null);

  // Fetch GeoJSON whenever URL filters change
  useEffect(() => {
    let cancelled = false;
    const fetchGeo = async () => {
      try {
        const res = await fetchGeoJsonEvents({
          search: searchParams.get("q") ?? undefined,
          category_id: searchParams.get("category")?.split(",")[0] ?? undefined,
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          temporal_filter: (searchParams.get("temporal") as any) ?? undefined,
          suggested: searchParams.get("suggested") === "1" ? true : undefined,
        });
        if (!cancelled) setGeoJson(res);
      } catch (err) {
        console.error("Failed to fetch map GeoJSON", err);
      }
    };
    void fetchGeo();
    return () => { cancelled = true; };
  }, [searchParams]);

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

      <Map 
        ref={mapRef} 
        initialViewState={DEFAULT_CENTER} 
        style={{ width: "100%", height: "100%" }} 
        mapStyle={MAPTILER_STYLE} 
        attributionControl={false}
        interactiveLayerIds={["events-points"]}
        onClick={(e) => {
          if (e.features && e.features.length > 0) {
            const feature = e.features[0];
            const properties = feature.properties as unknown as EventGeoJSONProperties;
            
            // MapLibre parses stringified booleans/nulls back, but sometimes we need to be careful
            setPopup({
              event: {
                ...properties,
                is_bookmarked: String(properties.is_bookmarked) === "true",
              },
              longitude: e.lngLat.lng,
              latitude: e.lngLat.lat,
            });
          } else {
            setPopup(null);
          }
        }}
        onMouseEnter={() => {
          if (mapRef.current) mapRef.current.getCanvas().style.cursor = 'pointer';
        }}
        onMouseLeave={() => {
          if (mapRef.current) mapRef.current.getCanvas().style.cursor = '';
        }}
      >
        {geoJson && (
          <Source id="events-source" type="geojson" data={geoJson as unknown as string}>
            <Layer
              id="events-points"
              type="circle"
              paint={{
                "circle-radius": 12,
                "circle-color": "#2A2A2A", // brand-dark
                "circle-stroke-width": 3,
                "circle-stroke-color": "#FFFFFF",
              }}
            />
          </Source>
        )}

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
