"use client";

import { useEffect, useId, useRef, useState } from "react";
import { Loader2, MapPin } from "lucide-react";

import { Input } from "@/components/ui/input";
import { suggestPlaces, type NominatimResult } from "@/lib/nominatim";
import { cn } from "@/lib/utils";

const SUGGEST_DEBOUNCE_MS = 400;
const SUGGEST_MIN_QUERY_LENGTH = 2;

interface LocationSearchInputProps {
  value: string;
  onChange: (name: string) => void;
  onPick: (result: NominatimResult) => void;
  onFocus?: () => void;
  placeholder?: string;
  className?: string;
  ariaInvalid?: boolean;
}

/**
 * Mirrors mobile's per-stop autocomplete pattern:
 * — 400ms debounce
 * — fetches Nominatim suggestions
 * — selecting a suggestion calls `onPick(result)` so the parent can update name + lat/lng + address atomically
 * — abort controllers prevent stale results from overwriting newer ones
 */
export function LocationSearchInput({
  value,
  onChange,
  onPick,
  onFocus,
  placeholder = "Search a place…",
  className,
  ariaInvalid,
}: LocationSearchInputProps) {
  const [suggestions, setSuggestions] = useState<NominatimResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const lastQueryRef = useRef<string>("");
  const justPickedRef = useRef(false);
  const listboxId = useId();

  // Debounced suggest fetch.
  useEffect(() => {
    if (justPickedRef.current) {
      justPickedRef.current = false;
      lastQueryRef.current = value;
      return;
    }
    const trimmed = value.trim();
    if (trimmed.length < SUGGEST_MIN_QUERY_LENGTH) {
      abortRef.current?.abort();
      // Defer the reset to the next microtask so the rule treats it as a
      // response to user input rather than an in-effect state assignment.
      const cleanupHandle = window.setTimeout(() => {
        setSuggestions([]);
        setLoading(false);
      }, 0);
      return () => window.clearTimeout(cleanupHandle);
    }
    if (trimmed === lastQueryRef.current) return;

    const handle = window.setTimeout(() => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      lastQueryRef.current = trimmed;
      setLoading(true);
      void suggestPlaces(trimmed, 5, controller.signal)
        .then((results) => {
          if (controller.signal.aborted) return;
          setSuggestions(results);
          setOpen(true);
        })
        .finally(() => {
          if (!controller.signal.aborted) setLoading(false);
        });
    }, SUGGEST_DEBOUNCE_MS);

    return () => {
      window.clearTimeout(handle);
    };
  }, [value]);

  // Close the dropdown when the user clicks outside.
  useEffect(() => {
    if (!open) return;
    function handlePointerDown(event: MouseEvent) {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handlePointerDown);
    return () => document.removeEventListener("mousedown", handlePointerDown);
  }, [open]);

  // Cancel any in-flight request on unmount.
  useEffect(() => () => abortRef.current?.abort(), []);

  function handlePick(result: NominatimResult) {
    justPickedRef.current = true;
    setOpen(false);
    setSuggestions([]);
    onPick(result);
  }

  return (
    <div className={cn("relative min-w-0 flex-1", className)} ref={containerRef}>
      <Input
        aria-autocomplete="list"
        aria-controls={open ? listboxId : undefined}
        aria-expanded={open}
        aria-invalid={ariaInvalid}
        autoComplete="off"
        className="h-9 min-w-0 flex-1"
        onChange={(event) => {
          onChange(event.target.value);
          if (!open && event.target.value.trim().length >= SUGGEST_MIN_QUERY_LENGTH) {
            setOpen(true);
          }
        }}
        onClick={(event) => event.stopPropagation()}
        onFocus={() => {
          onFocus?.();
          if (suggestions.length > 0) setOpen(true);
        }}
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            setOpen(false);
          }
        }}
        placeholder={placeholder}
        role="combobox"
        value={value}
      />
      {loading ? (
        <Loader2 className="text-brand-mid pointer-events-none absolute top-1/2 right-2 size-3.5 -translate-y-1/2 animate-spin" />
      ) : null}
      {open && suggestions.length > 0 ? (
        <ul
          className="border-brand-mid-alpha absolute top-full right-0 left-0 z-20 mt-1 max-h-64 overflow-y-auto rounded-md border bg-white shadow-lg"
          id={listboxId}
          role="listbox"
        >
          {suggestions.map((result, index) => (
            <li key={`${result.lat},${result.lng},${index}`} role="option" aria-selected={false}>
              <button
                className="text-brand-dark hover:bg-brand-surface focus:bg-brand-surface flex w-full items-start gap-2 px-3 py-2 text-left text-sm transition-colors focus:outline-none"
                onClick={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  handlePick(result);
                }}
                onMouseDown={(event) => event.preventDefault()}
                type="button"
              >
                <MapPin className="text-brand-mid mt-0.5 size-4 shrink-0" />
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-semibold">{result.shortName}</span>
                  <span className="text-brand-mid block truncate text-xs">
                    {result.displayName}
                  </span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
