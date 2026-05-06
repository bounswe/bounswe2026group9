"use client";

import { useEffect, useId, useRef } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  description: string;
  confirmLabel: string;
  confirmVariant?: "danger" | "primary";
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel,
  confirmVariant = "danger",
  loading = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const titleId = useId();
  const descriptionId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);

  // Move focus into the dialog on open and close on Escape (WCAG 2.1.1, 2.1.2).
  useEffect(() => {
    if (!open) return;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    dialogRef.current?.focus();

    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        onCancel();
      }
    }
    window.addEventListener("keydown", handleKey);
    return () => {
      window.removeEventListener("keydown", handleKey);
      previouslyFocused?.focus?.();
    };
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop — clicking dismisses, but is not a focusable button so screen
          readers don't announce a confusing extra control. */}
      <div
        className="absolute inset-0 bg-brand-dark/50 backdrop-blur-sm"
        onClick={onCancel}
        aria-hidden="true"
      />

      {/* Dialog */}
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        tabIndex={-1}
        className="relative w-full max-w-md rounded-2xl border border-brand-mid-alpha bg-white p-6 shadow-brand-panel mx-4 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-mid/60 focus-visible:ring-offset-2"
      >
        {/* Close */}
        <button
          type="button"
          onClick={onCancel}
          aria-label="Close dialog"
          className="absolute right-4 top-4 flex size-7 items-center justify-center rounded-full text-brand-mid hover:bg-brand-mid-alpha transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-mid/60"
        >
          <X className="size-4" aria-hidden="true" />
        </button>

        <h2 id={titleId} className="font-heading text-brand-dark text-xl font-bold mb-2">{title}</h2>
        <p id={descriptionId} className="text-muted-foreground text-sm mb-6">{description}</p>

        <div className="flex gap-3 justify-end">
          <button
            type="button"
            onClick={onCancel}
            disabled={loading}
            className="rounded-lg border border-brand-mid-alpha px-5 py-2.5 text-sm font-semibold text-brand-dark transition-colors hover:bg-brand-mid-alpha disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-mid/60 focus-visible:ring-offset-2"
          >
            Keep Event
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={loading}
            className={cn(
              "rounded-lg px-5 py-2.5 text-sm font-bold text-white transition-colors disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2",
              confirmVariant === "danger"
                ? "bg-danger hover:bg-danger/85 focus-visible:ring-danger/60"
                : "bg-brand-dark hover:bg-brand-dark/85 focus-visible:ring-brand-dark/60",
            )}
          >
            {loading ? "Processing…" : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
