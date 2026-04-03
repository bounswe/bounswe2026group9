import { ChevronLeft, ChevronRight, SearchX } from "lucide-react";

import type { EventListItem } from "@/lib/events-api";
import { EventCard } from "@/components/discovery/event-card";
import { cn } from "@/lib/utils";

interface ListViewProps {
  events: EventListItem[];
  isAuthenticated: boolean;
  total: number;
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export function ListView({
  events,
  isAuthenticated,
  total,
  page,
  totalPages,
  onPageChange,
}: ListViewProps) {
  if (events.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 py-24 text-center">
        <SearchX className="text-brand-mid size-12 opacity-50" />
        <div>
          <p className="font-heading text-brand-dark text-xl font-bold">No events found</p>
          <p className="text-muted-foreground mt-1 text-sm">
            Try adjusting your filters or search query.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col">
      {/* Result count */}
      <div className="px-8 pb-2 pt-6">
        <p className="text-muted-foreground text-sm">
          Showing <span className="text-brand-dark font-semibold">{events.length}</span> of{" "}
          <span className="text-brand-dark font-semibold">{total}</span> events
        </p>
      </div>

      {/* Grid */}
      <div className="grid flex-1 grid-cols-1 gap-6 px-8 pb-6 sm:grid-cols-2 xl:grid-cols-3">
        {events.map((event) => (
          <EventCard key={event.id} event={event} isAuthenticated={isAuthenticated} />
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="border-brand-mid-alpha flex items-center justify-center gap-2 border-t px-8 py-4">
          <button
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
            className={cn(
              "flex size-8 items-center justify-center rounded-lg border transition-colors",
              page <= 1
                ? "border-brand-mid-alpha text-brand-dark/30 cursor-not-allowed"
                : "border-brand-mid-alpha text-brand-dark hover:bg-brand-mid-alpha",
            )}
          >
            <ChevronLeft className="size-4" />
          </button>

          {/* Page numbers */}
          {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => {
            const isCurrentPage = p === page;
            const isNearby = Math.abs(p - page) <= 1 || p === 1 || p === totalPages;

            if (!isNearby) {
              if (p === 2 || p === totalPages - 1) {
                return (
                  <span key={p} className="text-brand-mid text-sm">
                    ...
                  </span>
                );
              }
              return null;
            }

            return (
              <button
                key={p}
                onClick={() => onPageChange(p)}
                className={cn(
                  "flex size-8 items-center justify-center rounded-lg border text-sm font-semibold transition-colors",
                  isCurrentPage
                    ? "bg-brand-dark border-brand-dark text-white"
                    : "border-brand-mid-alpha text-brand-dark hover:bg-brand-mid-alpha",
                )}
              >
                {p}
              </button>
            );
          })}

          <button
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages}
            className={cn(
              "flex size-8 items-center justify-center rounded-lg border transition-colors",
              page >= totalPages
                ? "border-brand-mid-alpha text-brand-dark/30 cursor-not-allowed"
                : "border-brand-mid-alpha text-brand-dark hover:bg-brand-mid-alpha",
            )}
          >
            <ChevronRight className="size-4" />
          </button>
        </div>
      )}
    </div>
  );
}
