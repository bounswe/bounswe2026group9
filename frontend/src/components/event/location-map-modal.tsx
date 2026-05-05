"use client";

import { useEffect, useId, useRef } from "react";
import { X } from "lucide-react";

interface LocationMapModalProps {
  open: boolean;
  onClose: () => void;
  latitude: number;
  longitude: number;
  locationName: string;
}

export function LocationMapModal({
  open,
  onClose,
  latitude,
  longitude,
  locationName,
}: LocationMapModalProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<unknown>(null);
  const titleId = useId();

  useEffect(() => {
    if (!open || !mapContainerRef.current || mapRef.current) return;

    let cancelled = false;

    void import("maplibre-gl").then((maplibregl) => {
      if (cancelled || !mapContainerRef.current) return;

      void import("maplibre-gl/dist/maplibre-gl.css");

      const map = new maplibregl.Map({
        container: mapContainerRef.current,
        style: "https://tiles.openfreemap.org/styles/liberty",
        center: [longitude, latitude],
        zoom: 15,
      });

      new maplibregl.Marker({ color: "#493628" })
        .setLngLat([longitude, latitude])
        .setPopup(new maplibregl.Popup().setText(locationName))
        .addTo(map)
        .togglePopup();

      mapRef.current = map;
    });

    return () => {
      cancelled = true;
    };
  }, [open, latitude, longitude, locationName]);

  useEffect(() => {
    if (!open) {
      if (mapRef.current) {
        (mapRef.current as { remove: () => void }).remove();
        mapRef.current = null;
      }
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    function handleEsc(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleEsc);
    return () => window.removeEventListener("keydown", handleEsc);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="relative w-full max-w-2xl mx-4 rounded-xl overflow-hidden bg-white shadow-2xl focus:outline-none"
      >
        <div className="flex items-center justify-between px-5 py-3 border-b border-brand-mid-alpha">
          <h3 id={titleId} className="font-heading text-brand-dark font-bold text-[16px]">{locationName}</h3>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close map"
            className="flex size-8 items-center justify-center rounded-full hover:bg-brand-mid-alpha transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-mid/60"
          >
            <X className="size-4 text-brand-dark" aria-hidden="true" />
          </button>
        </div>
        <div
          ref={mapContainerRef}
          // role="img" rather than role="application": application is only
          // appropriate when the widget owns its own complete keyboard
          // interaction model. MapLibre's default keyboard handlers cover
          // basic pan/zoom but not full marker-level navigation, and
          // role="application" forces screen readers to surrender all of
          // their navigation shortcuts to the widget. role="img" with a
          // descriptive label is the safer WAI-ARIA recommendation for
          // static map renders that don't yet have dedicated keyboard UX.
          role="img"
          aria-label={`Map showing ${locationName}`}
          className="h-[400px] w-full"
        />
      </div>
    </div>
  );
}
