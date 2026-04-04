"use client";

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
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-brand-dark/50 backdrop-blur-sm"
        onClick={onCancel}
      />

      {/* Dialog */}
      <div className="relative w-full max-w-md rounded-2xl border border-brand-mid-alpha bg-white p-6 shadow-brand-panel mx-4">
        {/* Close */}
        <button
          onClick={onCancel}
          className="absolute right-4 top-4 flex size-7 items-center justify-center rounded-full text-brand-mid hover:bg-brand-mid-alpha transition-colors"
        >
          <X className="size-4" />
        </button>

        <h2 className="font-heading text-brand-dark text-xl font-bold mb-2">{title}</h2>
        <p className="text-muted-foreground text-sm mb-6">{description}</p>

        <div className="flex gap-3 justify-end">
          <button
            onClick={onCancel}
            disabled={loading}
            className="rounded-lg border border-brand-mid-alpha px-5 py-2.5 text-sm font-semibold text-brand-dark transition-colors hover:bg-brand-mid-alpha disabled:opacity-50"
          >
            Keep Event
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className={cn(
              "rounded-lg px-5 py-2.5 text-sm font-bold text-white transition-colors disabled:opacity-50",
              confirmVariant === "danger"
                ? "bg-danger hover:bg-danger/85"
                : "bg-brand-dark hover:bg-brand-dark/85",
            )}
          >
            {loading ? "Processing…" : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
