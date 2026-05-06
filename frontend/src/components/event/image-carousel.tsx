"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import type { EventImage } from "@/lib/events-api";

interface ImageCarouselProps {
  images: EventImage[];
  title: string;
}

export function ImageCarousel({ images, title }: ImageCarouselProps) {
  const [index, setIndex] = useState(0);

  if (images.length === 0) {
    return (
      <div className="bg-brand-surface flex aspect-[16/9] w-full items-center justify-center rounded-xl">
        <span className="text-xs font-bold uppercase tracking-widest text-white/40">
          No Photos
        </span>
      </div>
    );
  }

  const prev = () => setIndex((i) => (i - 1 + images.length) % images.length);
  const next = () => setIndex((i) => (i + 1) % images.length);

  return (
    <div
      role="region"
      aria-roledescription="carousel"
      aria-label={`${title} photos`}
      className="group relative aspect-[16/9] w-full overflow-hidden rounded-xl"
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={images[index].image_url}
        alt={`${title} — photo ${index + 1} of ${images.length}`}
        className="h-full w-full object-cover transition-opacity duration-300"
      />

      {images.length > 1 && (
        <>
          {/* Arrows — visible on hover and on keyboard focus so keyboard users
              can see them when tabbed into. */}
          <button
            type="button"
            onClick={prev}
            className="absolute left-3 top-1/2 -translate-y-1/2 flex size-9 items-center justify-center rounded-full bg-black/30 text-white backdrop-blur-sm transition-colors hover:bg-black/50 opacity-0 group-hover:opacity-100 focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/80"
            aria-label="Previous image"
          >
            <ChevronLeft className="size-5" aria-hidden="true" />
          </button>
          <button
            type="button"
            onClick={next}
            className="absolute right-3 top-1/2 -translate-y-1/2 flex size-9 items-center justify-center rounded-full bg-black/30 text-white backdrop-blur-sm transition-colors hover:bg-black/50 opacity-0 group-hover:opacity-100 focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/80"
            aria-label="Next image"
          >
            <ChevronRight className="size-5" aria-hidden="true" />
          </button>

          {/* Dots — toggle pattern (button + aria-pressed) rather than the
              tab/tablist/tabpanel pattern, because there is only one
              always-visible <img> rather than separate tab panels. The
              previous role="tab" + aria-controls="carousel-photo-${i}"
              referenced ids that did not exist (orphan reference); each
              dot now describes "press to jump to photo N" with state. */}
          <div
            role="group"
            aria-label="Photo selector"
            className="absolute bottom-3 left-1/2 flex -translate-x-1/2 gap-1.5"
          >
            {images.map((_, i) => (
              <button
                key={i}
                type="button"
                aria-pressed={i === index}
                onClick={() => setIndex(i)}
                className={cn(
                  "size-2 rounded-full transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/80",
                  i === index ? "bg-white scale-125" : "bg-white/50 hover:bg-white/75",
                )}
                aria-label={`Go to photo ${i + 1}`}
              />
            ))}
          </div>

          {/* Counter — announced live so screen readers report which photo is on. */}
          <span
            aria-live="polite"
            className="absolute right-3 top-3 rounded-full bg-black/40 px-2.5 py-0.5 text-[11px] font-bold text-white backdrop-blur-sm"
          >
            {index + 1} / {images.length}
          </span>
        </>
      )}
    </div>
  );
}
