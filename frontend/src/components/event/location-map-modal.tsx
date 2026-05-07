"use client";

import { useEffect, useRef } from "react";
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
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="relative mx-4 w-full max-w-2xl overflow-hidden rounded-xl bg-white shadow-2xl">
        <div className="border-brand-mid-alpha flex items-center justify-between border-b px-5 py-3">
          <h3 className="font-heading text-brand-dark text-[16px] font-bold">{locationName}</h3>
          <button
            onClick={onClose}
            className="hover:bg-brand-mid-alpha flex size-8 items-center justify-center rounded-full transition-colors"
          >
            <X className="text-brand-dark size-4" />
          </button>
        </div>
        <div ref={mapContainerRef} className="h-[400px] w-full" />
      </div>
    </div>
  );
}
