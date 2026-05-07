"use client";

import { Check, SlidersHorizontal, X } from "lucide-react";

import type { Category, PersonalFilter, TemporalFilter } from "@/lib/events-api";
import { cn } from "@/lib/utils";

export interface FilterState {
  temporal: TemporalFilter | null;
  personal: PersonalFilter | null;
  /** Multiple categories = union (OR) logic */
  categoryIds: string[];
}

interface FilterSidebarProps {
  filters: FilterState;
  categories: Category[];
  /** Counts computed WITHOUT the category filter so they stay stable */
  categoryCounts: Record<string, number>;
  onFiltersChange: (filters: FilterState) => void;
  onApply: () => void;
  onClear: () => void;
  activeCount: number;
  isAuthenticated: boolean;
  mobileOpen: boolean;
  onMobileClose: () => void;
}

const TEMPORAL_OPTIONS: { value: TemporalFilter; label: string }[] = [
  { value: "today", label: "Today" },
  { value: "this_week", label: "This Week" },
  { value: "weekend", label: "Weekend" },
];

const PERSONAL_OPTIONS: { value: PersonalFilter; label: string }[] = [
  { value: "bookmarked", label: "Bookmarked" },
  { value: "going", label: "Going" },
];

export function FilterSidebar({
  filters,
  categories,
  categoryCounts,
  onFiltersChange,
  onApply,
  onClear,
  activeCount,
  isAuthenticated,
  mobileOpen,
  onMobileClose,
}: FilterSidebarProps) {
  // Sort: higher count first, then alphabetical within same count
  const sortedCategories = [...categories].sort((a, b) => {
    const ca = categoryCounts[a.id] ?? 0;
    const cb = categoryCounts[b.id] ?? 0;
    if (ca !== cb) return cb - ca;
    return a.name.localeCompare(b.name);
  });

  function toggleTemporal(value: TemporalFilter) {
    onFiltersChange({
      ...filters,
      temporal: filters.temporal === value ? null : value,
      personal: null,
    });
  }

  function togglePersonal(value: PersonalFilter) {
    onFiltersChange({
      ...filters,
      temporal: null,
      personal: filters.personal === value ? null : value,
    });
  }

  function toggleCategory(id: string) {
    const next = filters.categoryIds.includes(id)
      ? filters.categoryIds.filter((c) => c !== id)
      : [...filters.categoryIds, id];
    onFiltersChange({ ...filters, categoryIds: next });
  }

  function renderSidebarContent(isMobile: boolean) {
    return (
      <>
        <div
          className={cn(
            "border-brand-mid-alpha flex items-center gap-2 border-b",
            isMobile ? "px-4 py-4" : "px-5 py-4",
          )}
        >
          <SlidersHorizontal className="text-brand-mid size-5" />
          <h2 className="font-heading text-brand-dark text-lg font-bold">Filters</h2>
          <div className="ml-auto flex items-center gap-2">
            {activeCount > 0 && (
              <span className="bg-brand-mid rounded-full px-2 py-0.5 text-xs font-bold text-white">
                {activeCount}
              </span>
            )}
            {isMobile && (
              <button
                onClick={onMobileClose}
                className="border-brand-mid-alpha text-brand-dark hover:bg-brand-mid-alpha flex size-8 items-center justify-center rounded-lg border transition-colors"
                aria-label="Close filters"
              >
                <X className="size-4" />
              </button>
            )}
          </div>
        </div>

        <div
          className={cn("flex-1 space-y-6 overflow-y-auto", isMobile ? "px-4 py-4" : "px-5 py-4")}
        >
          <section>
            <p className="text-brand-mid mb-3 text-xs font-bold tracking-widest uppercase">
              Quick Filters
            </p>
            <div className="flex flex-wrap gap-2">
              {TEMPORAL_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => toggleTemporal(opt.value)}
                  className={cn(
                    "rounded-full border px-4 py-1.5 text-xs font-bold transition-colors",
                    filters.temporal === opt.value
                      ? "bg-brand-dark border-brand-dark text-white"
                      : "border-brand-mid-alpha text-brand-dark hover:bg-brand-mid-alpha",
                  )}
                >
                  {opt.label}
                </button>
              ))}
              {isAuthenticated &&
                PERSONAL_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => togglePersonal(opt.value)}
                    className={cn(
                      "rounded-full border px-4 py-1.5 text-xs font-bold transition-colors",
                      filters.personal === opt.value
                        ? "bg-brand-dark border-brand-dark text-white"
                        : "border-brand-mid-alpha text-brand-dark hover:bg-brand-mid-alpha",
                    )}
                  >
                    {opt.label}
                  </button>
                ))}
            </div>
          </section>

          <section>
            <p className="text-brand-mid mb-3 text-xs font-bold tracking-widest uppercase">
              Category
            </p>
            <div className="space-y-1">
              {categories.length === 0 ? (
                <p className="text-muted-foreground text-sm">Loading categories…</p>
              ) : (
                sortedCategories.map((cat) => {
                  const isSelected = filters.categoryIds.includes(cat.id);
                  return (
                    <button
                      key={cat.id}
                      onClick={() => toggleCategory(cat.id)}
                      className="hover:bg-brand-mid-alpha flex w-full items-center gap-3 rounded-lg px-2 py-1.5 text-left text-sm transition-colors"
                    >
                      <span
                        className={cn(
                          "flex size-[18px] shrink-0 items-center justify-center rounded border-2 transition-colors",
                          isSelected ? "bg-brand-dark border-brand-dark" : "border-brand-mid-alpha",
                        )}
                      >
                        {isSelected && <Check className="size-3 text-white" strokeWidth={3} />}
                      </span>
                      <span className="text-brand-dark flex-1">{cat.name}</span>
                      <span className="bg-brand-mid-alpha text-brand-mid rounded-full px-2 py-0.5 text-[11px] font-bold tabular-nums">
                        {categoryCounts[cat.id] ?? 0}
                      </span>
                    </button>
                  );
                })
              )}
            </div>
          </section>
        </div>

        <div
          className={cn(
            "border-brand-mid-alpha space-y-2 border-t",
            isMobile ? "px-4 py-4 pb-5" : "px-5 py-4",
          )}
        >
          <button
            onClick={onApply}
            className="bg-brand-dark hover:bg-brand-dark/80 w-full rounded-lg py-2.5 text-sm font-bold text-white transition-colors"
          >
            Apply Filters
          </button>
          <button
            onClick={onClear}
            className="text-brand-mid hover:text-brand-dark w-full rounded-lg py-2 text-sm font-semibold transition-colors"
          >
            Clear All
          </button>
        </div>
      </>
    );
  }

  return (
    <>
      <aside className="bg-card border-brand-mid-alpha hidden h-full w-72 shrink-0 flex-col border-r lg:flex">
        {renderSidebarContent(false)}
      </aside>

      <div
        className={cn("fixed inset-0 z-[60] lg:hidden", mobileOpen ? "" : "pointer-events-none")}
        aria-hidden={!mobileOpen}
      >
        <button
          onClick={onMobileClose}
          className={cn(
            "bg-brand-dark/35 absolute inset-0 transition-opacity",
            mobileOpen ? "opacity-100" : "opacity-0",
          )}
          aria-label="Close filters"
        />
        <aside
          className={cn(
            "bg-card border-brand-mid-alpha shadow-brand-panel absolute top-0 left-0 flex h-full w-[min(22rem,88vw)] flex-col border-r transition-transform duration-200",
            mobileOpen ? "translate-x-0" : "-translate-x-full",
          )}
        >
          {renderSidebarContent(true)}
        </aside>
      </div>
    </>
  );
}
