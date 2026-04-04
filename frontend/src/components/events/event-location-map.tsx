"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Map, { Marker, type MapRef } from "react-map-gl/maplibre";
import { Minus, Plus } from "lucide-react";

import { cn } from "@/lib/utils";

import "maplibre-gl/dist/maplibre-gl.css";

interface EventLocationMapLocation {
  id: string;
  isPrimary: boolean;
  latitude: string;
  longitude: string;
  name: string;
}

interface EventLocationMapProps {
  activeLocationId: string;
  className?: string;
  locations: EventLocationMapLocation[];
  onActiveLocationChange: (locationId: string) => void;
  onSelectCoordinates: (locationId: string, latitude: number, longitude: number) => void;
}

interface MappableLocation {
  id: string;
  isActive: boolean;
  isPrimary: boolean;
  label: string;
  latitude: number;
  longitude: number;
}

const MAP_STYLE = "https://tiles.openfreemap.org/styles/liberty";
const DEFAULT_CENTER = { longitude: 28.9784, latitude: 41.0082, zoom: 11 };

function isCoordinateValid(value: string, min: number, max: number) {
  const parsed = Number(value);
  return value.trim() !== "" && !Number.isNaN(parsed) && parsed >= min && parsed <= max;
}

function getLocationLabel(location: EventLocationMapLocation, index: number) {
  const name = location.name.trim();
  return name !== "" ? name : `Location ${index + 1}`;
}

export function EventLocationMap({
  activeLocationId,
  className,
  locations,
  onActiveLocationChange,
  onSelectCoordinates,
}: EventLocationMapProps) {
  const mapRef = useRef<MapRef>(null);
  const [isMapReady, setIsMapReady] = useState(false);

  const activeLocation = useMemo(
    () => locations.find((location) => location.id === activeLocationId) ?? locations[0] ?? null,
    [activeLocationId, locations],
  );

  const mappableLocations = useMemo<MappableLocation[]>(
    () =>
      locations.flatMap((location, index) => {
        if (!isCoordinateValid(location.latitude, -90, 90)) {
          return [];
        }

        if (!isCoordinateValid(location.longitude, -180, 180)) {
          return [];
        }

        return [{
          id: location.id,
          isActive: location.id === activeLocation?.id,
          isPrimary: location.isPrimary,
          label: getLocationLabel(location, index),
          latitude: Number(location.latitude),
          longitude: Number(location.longitude),
        }];
      }),
    [activeLocation?.id, locations],
  );

  const activeMappableLocation = useMemo(
    () => mappableLocations.find((location) => location.id === activeLocation?.id) ?? null,
    [activeLocation?.id, mappableLocations],
  );

  useEffect(() => {
    if (!isMapReady || !mapRef.current) {
      return;
    }

    const map = mapRef.current.getMap();

    if (activeMappableLocation) {
      map.flyTo({
        center: [activeMappableLocation.longitude, activeMappableLocation.latitude],
        duration: 700,
        zoom: Math.max(map.getZoom(), 13),
      });
      return;
    }

    if (mappableLocations.length > 1) {
      const bounds = mappableLocations.reduce<[[number, number], [number, number]]>(
        (currentBounds, location) => [
          [
            Math.min(currentBounds[0][0], location.longitude),
            Math.min(currentBounds[0][1], location.latitude),
          ],
          [
            Math.max(currentBounds[1][0], location.longitude),
            Math.max(currentBounds[1][1], location.latitude),
          ],
        ],
        [
          [mappableLocations[0].longitude, mappableLocations[0].latitude],
          [mappableLocations[0].longitude, mappableLocations[0].latitude],
        ],
      );

      map.fitBounds(bounds, { animate: true, padding: 48 });
      return;
    }

    if (mappableLocations.length === 1) {
      map.flyTo({
        center: [mappableLocations[0].longitude, mappableLocations[0].latitude],
        duration: 700,
        zoom: 13,
      });
      return;
    }

    map.flyTo({
      center: [DEFAULT_CENTER.longitude, DEFAULT_CENTER.latitude],
      duration: 700,
      zoom: DEFAULT_CENTER.zoom,
    });
  }, [activeMappableLocation, isMapReady, mappableLocations]);

  return (
    <div className={cn("space-y-4", className)}>
      <div className="border-border/80 bg-brand-surface/35 relative overflow-hidden rounded-[12px] border">
        <div className="h-[420px] w-full sm:h-[480px] xl:h-[540px]">
          <Map
            ref={mapRef}
            attributionControl={false}
            initialViewState={DEFAULT_CENTER}
            mapStyle={MAP_STYLE}
            onClick={(event) => {
              if (!activeLocation) {
                return;
              }

              onSelectCoordinates(activeLocation.id, event.lngLat.lat, event.lngLat.lng);
            }}
            onLoad={() => setIsMapReady(true)}
            style={{ width: "100%", height: "100%" }}
          >
            {mappableLocations.map((location, index) => (
              <Marker
                key={location.id}
                anchor="bottom"
                latitude={location.latitude}
                longitude={location.longitude}
                onClick={(event) => {
                  event.originalEvent.stopPropagation();
                  onActiveLocationChange(location.id);
                }}
              >
                <button
                  aria-label={`Focus ${location.label}`}
                  className={cn(
                    "flex cursor-pointer flex-col items-center transition-transform hover:scale-110",
                    location.isActive && "scale-110",
                  )}
                  title={location.label}
                  type="button"
                >
                  <div
                    className={cn(
                      "relative flex size-9 items-center justify-center rounded-full text-xs font-bold text-white shadow-brand-card",
                      location.isActive
                        ? "bg-brand-dark ring-4 ring-brand-dark/20"
                        : location.isPrimary
                          ? "bg-brand-mid"
                          : "bg-brand-mid/75",
                    )}
                  >
                    {index + 1}
                    <span
                      className={cn(
                        "absolute -bottom-1.5 left-1/2 -translate-x-1/2 border-x-[6px] border-t-[8px] border-x-transparent",
                        location.isActive
                          ? "border-t-brand-dark"
                          : location.isPrimary
                            ? "border-t-brand-mid"
                            : "border-t-brand-mid/75",
                      )}
                    />
                  </div>
                </button>
              </Marker>
            ))}
          </Map>
        </div>

        <div className="absolute right-3 top-3 z-10 flex flex-col gap-1 sm:right-4 sm:top-4">
          <button
            className="flex size-8 items-center justify-center rounded-lg border border-brand-mid-alpha bg-white/90 text-brand-dark shadow-brand-card backdrop-blur-sm transition-colors hover:bg-white sm:size-9"
            onClick={() => mapRef.current?.zoomIn()}
            type="button"
          >
            <Plus className="size-4" />
          </button>
          <button
            className="flex size-8 items-center justify-center rounded-lg border border-brand-mid-alpha bg-white/90 text-brand-dark shadow-brand-card backdrop-blur-sm transition-colors hover:bg-white sm:size-9"
            onClick={() => mapRef.current?.zoomOut()}
            type="button"
          >
            <Minus className="size-4" />
          </button>
        </div>

        <div className="absolute bottom-3 left-3 rounded bg-white/80 px-2 py-0.5 text-[9px] text-gray-500 sm:bottom-2 sm:left-auto sm:right-2 sm:text-[10px]">
          © <a href="https://openfreemap.org" rel="noreferrer" target="_blank">OpenFreeMap</a> · ©{" "}
          <a href="https://www.openstreetmap.org/copyright" rel="noreferrer" target="_blank">OpenStreetMap</a>
        </div>
      </div>

      <div className="text-muted-foreground flex flex-wrap items-center gap-3 text-sm leading-6">
        <span>Click anywhere on the map to update the active location.</span>
        {activeLocation ? (
          <button
            className="bg-brand-dark rounded-full px-3 py-1 text-xs font-semibold text-white"
            onClick={() => {
              onActiveLocationChange(activeLocation.id);
            }}
            type="button"
          >
            Editing: {getLocationLabel(activeLocation, locations.indexOf(activeLocation))}
          </button>
        ) : null}
      </div>
    </div>
  );
}
