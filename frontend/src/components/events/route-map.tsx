"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Map, { Layer, Marker, Source, type MapRef } from "react-map-gl/maplibre";
import { Minus, Plus } from "lucide-react";

import { cn } from "@/lib/utils";

import "maplibre-gl/dist/maplibre-gl.css";

const MAP_STYLE = "https://tiles.openfreemap.org/styles/liberty";
const DEFAULT_CENTER = { longitude: 28.9784, latitude: 41.0082, zoom: 11 };

const POLYLINE_LAYER_ID = "route-polyline";
const POLYLINE_SOURCE_ID = "route-polyline-source";

export interface RouteMapStop {
  /** Stable id for React keys; not surfaced in the UI. */
  id: string;
  latitude: number;
  longitude: number;
  /** Optional label rendered as a tooltip on the numbered pin. */
  label?: string | null;
}

interface RouteMapProps {
  stops: RouteMapStop[];
  className?: string;
  /** Total height of the map container. Defaults to a compact 220px. */
  heightClassName?: string;
  /** Hides the +/- zoom buttons (e.g. when embedded inside a card). */
  hideControls?: boolean;
  /** Optional CSS color override for the polyline. Defaults to brand-dark. */
  polylineColor?: string;
}

interface PolylineFeature {
  type: "Feature";
  geometry: { type: "LineString"; coordinates: [number, number][] };
  properties: Record<string, never>;
}

function buildPolylineFeature(stops: RouteMapStop[]): PolylineFeature | null {
  if (stops.length < 2) {
    return null;
  }
  return {
    type: "Feature",
    geometry: {
      type: "LineString",
      coordinates: stops.map((stop) => [stop.longitude, stop.latitude]),
    },
    properties: {},
  };
}

/**
 * Read-only map that renders a numbered pin per stop and connects them with a
 * polyline in stop order. Used by the Create Event Location step (live preview)
 * and the Event Detail itinerary section.
 *
 * Coordinates are intentionally taken straight from the props — the map
 * recomputes its bounds whenever the stop list changes (add / remove / reorder),
 * which satisfies issue #157's acceptance criteria.
 */
export function RouteMap({
  stops,
  className,
  heightClassName = "h-[220px] sm:h-[260px]",
  hideControls = false,
  polylineColor,
}: RouteMapProps) {
  const mapRef = useRef<MapRef>(null);
  const [isMapReady, setIsMapReady] = useState(false);

  const polyline = useMemo(() => buildPolylineFeature(stops), [stops]);

  useEffect(() => {
    if (!isMapReady || !mapRef.current) {
      return;
    }
    const map = mapRef.current.getMap();

    if (stops.length === 0) {
      map.flyTo({
        center: [DEFAULT_CENTER.longitude, DEFAULT_CENTER.latitude],
        zoom: DEFAULT_CENTER.zoom,
        duration: 400,
      });
      return;
    }

    if (stops.length === 1) {
      map.flyTo({
        center: [stops[0].longitude, stops[0].latitude],
        zoom: 13,
        duration: 400,
      });
      return;
    }

    const bounds = stops.reduce<[[number, number], [number, number]]>(
      (acc, stop) => [
        [Math.min(acc[0][0], stop.longitude), Math.min(acc[0][1], stop.latitude)],
        [Math.max(acc[1][0], stop.longitude), Math.max(acc[1][1], stop.latitude)],
      ],
      [
        [stops[0].longitude, stops[0].latitude],
        [stops[0].longitude, stops[0].latitude],
      ],
    );
    map.fitBounds(bounds, { animate: true, padding: 48, maxZoom: 14 });
  }, [isMapReady, stops]);

  return (
    <div
      className={cn(
        "border-border/80 bg-brand-surface/35 relative overflow-hidden rounded-[12px] border",
        className,
      )}
    >
      <div className={cn("w-full", heightClassName)}>
        <Map
          ref={mapRef}
          attributionControl={false}
          initialViewState={DEFAULT_CENTER}
          mapStyle={MAP_STYLE}
          onLoad={() => setIsMapReady(true)}
          style={{ width: "100%", height: "100%" }}
        >
          {polyline && (
            <Source id={POLYLINE_SOURCE_ID} type="geojson" data={polyline}>
              <Layer
                id={POLYLINE_LAYER_ID}
                type="line"
                layout={{ "line-cap": "round", "line-join": "round" }}
                paint={{
                  "line-color": polylineColor ?? "#493628",
                  "line-width": 3,
                  "line-opacity": 0.85,
                }}
              />
            </Source>
          )}
          {stops.map((stop, index) => (
            <Marker
              key={stop.id}
              anchor="bottom"
              latitude={stop.latitude}
              longitude={stop.longitude}
            >
              <div
                aria-label={stop.label ?? `Stop ${index + 1}`}
                className="flex flex-col items-center"
                title={stop.label ?? undefined}
              >
                <div className="bg-brand-dark shadow-brand-card relative flex size-9 items-center justify-center rounded-full text-xs font-bold text-white">
                  {index + 1}
                  <span className="border-t-brand-dark absolute -bottom-1.5 left-1/2 -translate-x-1/2 border-x-[6px] border-t-[8px] border-x-transparent" />
                </div>
              </div>
            </Marker>
          ))}
        </Map>
      </div>

      {!hideControls && (
        <div className="absolute top-3 right-3 z-10 flex flex-col gap-1">
          <button
            aria-label="Zoom in"
            className="border-brand-mid-alpha text-brand-dark shadow-brand-card flex size-8 items-center justify-center rounded-lg border bg-white/90 backdrop-blur-sm transition-colors hover:bg-white"
            onClick={() => mapRef.current?.zoomIn()}
            type="button"
          >
            <Plus className="size-4" />
          </button>
          <button
            aria-label="Zoom out"
            className="border-brand-mid-alpha text-brand-dark shadow-brand-card flex size-8 items-center justify-center rounded-lg border bg-white/90 backdrop-blur-sm transition-colors hover:bg-white"
            onClick={() => mapRef.current?.zoomOut()}
            type="button"
          >
            <Minus className="size-4" />
          </button>
        </div>
      )}

      <div className="absolute right-2 bottom-2 rounded bg-white/80 px-2 py-0.5 text-[10px] text-gray-500">
        ©{" "}
        <a href="https://openfreemap.org" rel="noreferrer" target="_blank">
          OpenFreeMap
        </a>{" "}
        · ©{" "}
        <a href="https://www.openstreetmap.org/copyright" rel="noreferrer" target="_blank">
          OpenStreetMap
        </a>
      </div>
    </div>
  );
}
