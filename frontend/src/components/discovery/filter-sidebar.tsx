"use client";

import { SlidersHorizontal, Check } from "lucide-react";

import type { Category, TemporalFilter } from "@/lib/events-api";
import { cn } from "@/lib/utils";

export interface FilterState {
  temporal: TemporalFilter | null;
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
}

const TEMPORAL_OPTIONS: { value: TemporalFilter; label: string }[] = [
  { value: "upcoming", label: "Upcoming" },
  { value: "today", label: "Today" },
  { value: "this_week", label: "This Week" },
];

export function FilterSidebar({
  filters,
  categories,
  categoryCounts,
  onFiltersChange,
  onApply,
  onClear,
  activeCount,
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
    });
  }

  function toggleCategory(id: string) {
    const next = filters.categoryIds.includes(id)
      ? filters.categoryIds.filter((c) => c !== id)
      : [...filters.categoryIds, id];
    onFiltersChange({ ...filters, categoryIds: next });
  }

  return (
    <aside className="bg-card border-brand-mid-alpha flex h-full w-72 shrink-0 flex-col border-r">
      {/* Header */}
      <div className="border-brand-mid-alpha flex items-center gap-2 border-b px-5 py-4">
        <SlidersHorizontal className="text-brand-mid size-5" />
        <h2 className="font-heading text-brand-dark text-lg font-bold">Filters</h2>
        {activeCount > 0 && (
          <span className="bg-brand-mid ml-auto rounded-full px-2 py-0.5 text-xs font-bold text-white">
            {activeCount}
          </span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-6">
        {/* Quick Filters — intersect (AND) with category */}
        <section>
          <p className="text-brand-mid mb-3 text-xs font-bold uppercase tracking-widest">
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
          </div>
        </section>

        {/* Category — union (OR) between selections */}
        <section>
          <p className="text-brand-mid mb-3 text-xs font-bold uppercase tracking-widest">
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
                    className="flex w-full items-center gap-3 rounded-lg px-2 py-1.5 text-left text-sm transition-colors hover:bg-brand-mid-alpha"
                  >
                    <span
                      className={cn(
                        "flex size-[18px] shrink-0 items-center justify-center rounded border-2 transition-colors",
                        isSelected
                          ? "bg-brand-dark border-brand-dark"
                          : "border-brand-mid-alpha",
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

      {/* Footer actions */}
      <div className="border-brand-mid-alpha border-t px-5 py-4 space-y-2">
        <button
          onClick={onApply}
          className="bg-brand-dark w-full rounded-lg py-2.5 text-sm font-bold text-white transition-colors hover:bg-brand-dark/80"
        >
          Apply Filters
        </button>
        <button
          onClick={onClear}
          className="text-brand-mid w-full rounded-lg py-2 text-sm font-semibold transition-colors hover:text-brand-dark"
        >
          Clear All
        </button>
      </div>
    </aside>
  );
}
