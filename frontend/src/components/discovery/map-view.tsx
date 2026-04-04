"use client";

import { useCallback, useRef, useState } from "react";
import Map, { Marker, Popup, type MapRef } from "react-map-gl/maplibre";
import { Minus, Pencil, Plus, Users, X } from "lucide-react";
import Link from "next/link";

import type { EventListItem } from "@/lib/events-api";
import { getEditEventPagePath } from "@/lib/event-routes";
import { cn } from "@/lib/utils";

import "maplibre-gl/dist/maplibre-gl.css";

// OpenFreeMap — free, no API key, Mapbox-quality vector tiles
const MAPTILER_STYLE = "https://tiles.openfreemap.org/styles/liberty";

// Default center: Istanbul
const DEFAULT_CENTER = { longitude: 28.9784, latitude: 41.0082, zoom: 11 };

interface MapPopupData {
  event: EventListItem;
  longitude: number;
  latitude: number;
}

interface MapViewProps {
  currentUserId: string | null;
  events: EventListItem[];
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

/** Category icon — simple letter-based fallback */
function CategoryIcon({ name }: { name: string }) {
  return (
    <span className="text-[10px] font-extrabold text-white uppercase">
      {name.slice(0, 1)}
    </span>
  );
}

export function MapView({ currentUserId, events, isAuthenticated }: MapViewProps) {
  const [popup, setPopup] = useState<MapPopupData | null>(null);
  const mapRef = useRef<MapRef>(null);

  // Only events with a primary location can appear on map
  const mappableEvents = events.filter((e) => e.primary_location !== null);

  const handleMarkerClick = useCallback(
    (event: EventListItem) => {
      const loc = event.primary_location!;
      setPopup({ event, longitude: loc.longitude, latitude: loc.latitude });
    },
    [],
  );

  return (
    <div className="relative flex-1">
      {/* Zoom controls — top right, elegant */}
      <div className="absolute right-3 top-3 z-10 flex flex-col gap-1 sm:right-4 sm:top-4">
        <button
          onClick={() => mapRef.current?.zoomIn()}
          className="flex size-8 items-center justify-center rounded-lg border border-brand-mid-alpha bg-white/90 text-brand-dark shadow-brand-card backdrop-blur-sm transition-colors hover:bg-white sm:size-9"
          aria-label="Zoom in"
        >
          <Plus className="size-4" />
        </button>
        <button
          onClick={() => mapRef.current?.zoomOut()}
          className="flex size-8 items-center justify-center rounded-lg border border-brand-mid-alpha bg-white/90 text-brand-dark shadow-brand-card backdrop-blur-sm transition-colors hover:bg-white sm:size-9"
          aria-label="Zoom out"
        >
          <Minus className="size-4" />
        </button>
      </div>

      <Map
        ref={mapRef}
        initialViewState={DEFAULT_CENTER}
        style={{ width: "100%", height: "100%" }}
        mapStyle={MAPTILER_STYLE}
        attributionControl={false}
      >
        {/* Event pins */}
        {mappableEvents.map((event) => {
          const loc = event.primary_location!;
          const isActive = popup?.event.id === event.id;
          const primaryCategory = event.categories[0];

          return (
            <Marker
              key={event.id}
              longitude={loc.longitude}
              latitude={loc.latitude}
              anchor="bottom"
              onClick={(e) => {
                e.originalEvent.stopPropagation();
                handleMarkerClick(event);
              }}
            >
              <div
                className={cn(
                  "flex cursor-pointer flex-col items-center transition-transform hover:scale-110",
                  isActive && "scale-110",
                )}
              >
                {/* Pin circle */}
                <div
                  className={cn(
                    "relative flex size-9 items-center justify-center rounded-full shadow-brand-card",
                    isActive
                      ? "bg-brand-mid ring-4 ring-brand-mid/30"
                      : "bg-brand-dark",
                  )}
                >
                  {primaryCategory ? (
                    <CategoryIcon name={primaryCategory.name} />
                  ) : (
                    <span className="text-[10px] font-extrabold text-white">E</span>
                  )}
                  {/* Pin tail */}
                  <span
                    className={cn(
                      "absolute -bottom-1.5 left-1/2 -translate-x-1/2 border-x-[6px] border-t-[8px] border-x-transparent",
                      isActive ? "border-t-brand-mid" : "border-t-brand-dark",
                    )}
                  />
                </div>
              </div>
            </Marker>
          );
        })}

        {/* Popup card */}
        {popup && (
          <Popup
            longitude={popup.longitude}
            latitude={popup.latitude}
            anchor="top"
            closeOnClick={false}
            onClose={() => setPopup(null)}
            className="!p-0 !bg-transparent !border-0 !shadow-none"
            maxWidth="280px"
          >
            <div
              className="relative overflow-hidden rounded-xl border border-brand-mid-alpha bg-white shadow-brand-panel"
              style={{ width: "min(280px, calc(100vw - 2rem))" }}
            >
              {/* Close button */}
              <button
                onClick={() => setPopup(null)}
                className="absolute right-2 top-2 z-10 flex size-6 items-center justify-center rounded-full bg-black/20 text-white transition-colors hover:bg-black/40"
              >
                <X className="size-3.5" />
              </button>

              {/* Image */}
              <div className="bg-brand-mid relative h-20 w-full">
                {popup.event.primary_image_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={popup.event.primary_image_url}
                    alt={popup.event.title}
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <div className="flex h-full w-full items-center justify-center">
                    <span className="text-[10px] font-bold uppercase tracking-widest text-white/40">
                      Event Photo
                    </span>
                  </div>
                )}
              </div>

              {/* Body */}
              <div className="p-4">
                <h3 className="font-heading text-brand-dark mb-1 text-[15px] font-bold leading-tight">
                  {popup.event.title}
                </h3>
                <p className="text-brand-mid mb-2 text-xs font-semibold">
                  {formatDateShort(popup.event.start_datetime)} ·{" "}
                  {formatTime(popup.event.start_datetime)}
                </p>

                {popup.event.categories[0] && (
                  <span className="bg-brand-mid-alpha text-brand-dark mb-3 inline-block rounded-full px-3 py-0.5 text-[11px] font-bold">
                    {popup.event.categories[0].name}
                  </span>
                )}

                <div className="text-brand-dark mb-3 flex items-center gap-1.5 text-xs">
                  <Users className="text-brand-mid size-3.5" />
                  <span>
                    {popup.event.going_count}
                    {popup.event.attendee_limit ? `/${popup.event.attendee_limit}` : ""} going
                  </span>
                </div>

                <Link
                  href={`/events/${popup.event.id}`}
                  className="text-brand-mid text-sm font-bold transition-colors hover:text-brand-dark"
                >
                  View Details →
                </Link>

                {/* Owner / attendee actions */}
                {isAuthenticated && (
                  <div className="border-brand-mid-alpha mt-3 flex gap-2 border-t pt-3">
                    {currentUserId === popup.event.host_id ? (
                      <Link
                        href={getEditEventPagePath(popup.event.id)}
                        className="bg-brand-dark flex flex-1 items-center justify-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold text-white transition-colors hover:bg-brand-dark/85"
                      >
                        <Pencil className="size-3.5" />
                        Edit
                      </Link>
                    ) : (
                      <>
                        <button
                          onClick={(e) => {
                            e.preventDefault();
                            // Will be wired in Task 7
                          }}
                          className={cn(
                            "border-brand-mid flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-bold transition-colors",
                            popup.event.is_bookmarked
                              ? "bg-brand-mid text-white"
                              : "text-brand-dark hover:bg-brand-mid-alpha",
                          )}
                        >
                          Bookmark
                        </button>
                        <button
                          disabled={popup.event.is_full ?? false}
                          className={cn(
                            "flex flex-1 items-center justify-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold transition-colors",
                            popup.event.is_full
                              ? "cursor-not-allowed bg-brand-mid-alpha text-brand-dark/40"
                              : "bg-brand-mid text-white hover:bg-brand-mid/80",
                          )}
                        >
                          {popup.event.is_full ? "Full" : "Going"}
                        </button>
                      </>
                    )}
                  </div>
                )}
              </div>
            </div>
          </Popup>
        )}
      </Map>

      {/* Attribution */}
      <div className="absolute bottom-3 left-3 rounded bg-white/80 px-2 py-0.5 text-[9px] text-gray-500 sm:bottom-2 sm:left-auto sm:right-2 sm:text-[10px]">
        © <a href="https://openfreemap.org" target="_blank" rel="noreferrer">OpenFreeMap</a> · © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a>
      </div>
    </div>
  );
}
