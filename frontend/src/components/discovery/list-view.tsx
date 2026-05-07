import { ChevronLeft, ChevronRight, SearchX } from "lucide-react";

import type { EventListItem } from "@/lib/events-api";
import { EventCard } from "@/components/discovery/event-card";
import { cn } from "@/lib/utils";

interface ListViewProps {
  events: EventListItem[];
  currentUserId: string | null;
  isAuthenticated: boolean;
  total: number;
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export function ListView({
  events,
  currentUserId,
  isAuthenticated,
  total,
  page,
  totalPages,
  onPageChange,
}: ListViewProps) {
  if (events.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 px-4 py-20 text-center sm:px-6 sm:py-24">
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
      <div className="px-4 pt-4 pb-2 sm:px-6 sm:pt-5 lg:px-8 lg:pt-6">
        <p className="text-muted-foreground text-sm">
          Showing <span className="text-brand-dark font-semibold">{events.length}</span> of{" "}
          <span className="text-brand-dark font-semibold">{total}</span> events
        </p>
      </div>

      {/* Grid */}
      <div className="grid flex-1 grid-cols-1 content-start items-stretch gap-4 px-4 pb-4 sm:grid-cols-2 sm:gap-5 sm:px-6 sm:pb-6 xl:grid-cols-3 xl:gap-6 xl:px-8">
        {events.map((event) => (
          <EventCard
            key={event.id}
            event={event}
            currentUserId={currentUserId}
            isAuthenticated={isAuthenticated}
          />
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <nav
          aria-label="Pagination"
          className="border-brand-mid-alpha flex items-center justify-center gap-2 border-t px-4 py-4 sm:px-6 lg:px-8"
        >
          <button
            type="button"
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
            aria-label="Previous page"
            className={cn(
              "focus-visible:ring-brand-mid/60 flex size-8 items-center justify-center rounded-lg border transition-colors focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none",
              page <= 1
                ? "border-brand-mid-alpha text-brand-dark/30 cursor-not-allowed"
                : "border-brand-mid-alpha text-brand-dark hover:bg-brand-mid-alpha",
            )}
          >
            <ChevronLeft className="size-4" aria-hidden="true" />
          </button>

          {/* Page numbers */}
          {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => {
            const isCurrentPage = p === page;
            const isNearby = Math.abs(p - page) <= 1 || p === 1 || p === totalPages;

            if (!isNearby) {
              if (p === 2 || p === totalPages - 1) {
                return (
                  <span key={p} aria-hidden="true" className="text-brand-mid text-sm">
                    ...
                  </span>
                );
              }
              return null;
            }

            return (
              <button
                key={p}
                type="button"
                onClick={() => onPageChange(p)}
                aria-label={`Go to page ${p}`}
                aria-current={isCurrentPage ? "page" : undefined}
                className={cn(
                  "focus-visible:ring-brand-mid/60 flex size-8 items-center justify-center rounded-lg border text-sm font-semibold transition-colors focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none",
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
            type="button"
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages}
            aria-label="Next page"
            className={cn(
              "focus-visible:ring-brand-mid/60 flex size-8 items-center justify-center rounded-lg border transition-colors focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none",
              page >= totalPages
                ? "border-brand-mid-alpha text-brand-dark/30 cursor-not-allowed"
                : "border-brand-mid-alpha text-brand-dark hover:bg-brand-mid-alpha",
            )}
          >
            <ChevronRight className="size-4" aria-hidden="true" />
          </button>
        </nav>
      )}
    </div>
  );
}
