import { Lock, XCircle, Clock, Users } from "lucide-react";
import { cn } from "@/lib/utils";

type StatusVariant = "cancelled" | "ended" | "full" | "private" | "published" | "draft";

interface StatusBadgeProps {
  variant: StatusVariant;
  className?: string;
}

const VARIANTS: Record<
  StatusVariant,
  { label: string; icon?: React.ReactNode; className: string }
> = {
  published: {
    label: "Published",
    className: "bg-brand-mid text-white",
  },
  draft: {
    label: "Draft",
    className: "bg-brand-mid-alpha text-brand-dark",
  },
  cancelled: {
    label: "Cancelled",
    icon: <XCircle className="size-3" />,
    className: "bg-danger text-white",
  },
  ended: {
    label: "Ended",
    icon: <Clock className="size-3" />,
    className: "bg-brand-mid text-white",
  },
  full: {
    label: "Full",
    icon: <Users className="size-3" />,
    className: "bg-warning text-white",
  },
  private: {
    label: "Private",
    icon: <Lock className="size-3" />,
    className: "bg-brand-dark text-white",
  },
};

export function StatusBadge({ variant, className }: StatusBadgeProps) {
  const { label, icon, className: variantClass } = VARIANTS[variant];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-3 py-1 text-[11px] font-extrabold tracking-wide uppercase",
        variantClass,
        className,
      )}
    >
      {icon}
      {label}
    </span>
  );
}

export function eventStatusVariant(status: string, isFull: boolean | null): StatusVariant {
  if (status === "cancelled") return "cancelled";
  if (status === "ended") return "ended";
  if (isFull) return "full";
  if (status === "draft") return "draft";
  return "published";
}
