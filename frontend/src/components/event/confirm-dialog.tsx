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
      <div className="bg-brand-dark/50 absolute inset-0 backdrop-blur-sm" onClick={onCancel} />

      {/* Dialog */}
      <div className="border-brand-mid-alpha shadow-brand-panel relative mx-4 w-full max-w-md rounded-2xl border bg-white p-6">
        {/* Close */}
        <button
          onClick={onCancel}
          className="text-brand-mid hover:bg-brand-mid-alpha absolute top-4 right-4 flex size-7 items-center justify-center rounded-full transition-colors"
        >
          <X className="size-4" />
        </button>

        <h2 className="font-heading text-brand-dark mb-2 text-xl font-bold">{title}</h2>
        <p className="text-muted-foreground mb-6 text-sm">{description}</p>

        <div className="flex justify-end gap-3">
          <button
            onClick={onCancel}
            disabled={loading}
            className="border-brand-mid-alpha text-brand-dark hover:bg-brand-mid-alpha rounded-lg border px-5 py-2.5 text-sm font-semibold transition-colors disabled:opacity-50"
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
