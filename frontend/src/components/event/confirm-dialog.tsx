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
        className="bg-brand-dark/50 absolute inset-0 backdrop-blur-sm"
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
        className="border-brand-mid-alpha shadow-brand-panel focus-visible:ring-brand-mid/60 relative mx-4 w-full max-w-md rounded-2xl border bg-white p-6 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2"
      >
        {/* Close */}
        <button
          type="button"
          onClick={onCancel}
          aria-label="Close dialog"
          className="text-brand-mid hover:bg-brand-mid-alpha focus-visible:ring-brand-mid/60 absolute top-4 right-4 flex size-7 items-center justify-center rounded-full transition-colors focus-visible:ring-2 focus-visible:outline-none"
        >
          <X className="size-4" aria-hidden="true" />
        </button>

        <h2 id={titleId} className="font-heading text-brand-dark mb-2 text-xl font-bold">
          {title}
        </h2>
        <p id={descriptionId} className="text-muted-foreground mb-6 text-sm">
          {description}
        </p>

        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            disabled={loading}
            className="border-brand-mid-alpha text-brand-dark hover:bg-brand-mid-alpha focus-visible:ring-brand-mid/60 rounded-lg border px-5 py-2.5 text-sm font-semibold transition-colors focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none disabled:opacity-50"
          >
            Keep Event
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={loading}
            className={cn(
              "rounded-lg px-5 py-2.5 text-sm font-bold text-white transition-colors focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none disabled:opacity-50",
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
