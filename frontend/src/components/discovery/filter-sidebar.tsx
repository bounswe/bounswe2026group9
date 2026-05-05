"use client";

import { Accessibility, Check, Clock, Sparkles, SlidersHorizontal, X } from "lucide-react";

import type {
  AccessibilityFilters,
  Category,
  PersonalFilter,
  QuickFilter,
  SortOption,
  TemporalFilter,
} from "@/lib/events-api";
import { cn } from "@/lib/utils";

export interface FilterState {
  /** Backend `quick_filter` (now/today/this_week/weekend/upcoming). "past" is reached via the `showPast` toggle, never via this list. */
  temporal: TemporalFilter | null;
  /** Client-side personal filter (bookmarked / going). */
  personal: PersonalFilter | null;
  /** Multi-select category IDs (OR/union). */
  categoryIds: string[];
  /** Toggle: include past events in the result set. Maps to `quick_filter=past` when no other temporal is set. */
  showPast: boolean;
  /** Sort selection. "distance" is location-aware and prompts the browser for geolocation when chosen. */
  sort: SortOption;
  /** Accessibility venue filters. */
  accessibility: AccessibilityFilters;
}

interface FilterSidebarProps {
  filters: FilterState;
  categories: Category[];
  /** Counts computed WITHOUT the category filter so they stay stable. */
  categoryCounts: Record<string, number>;
  onFiltersChange: (filters: FilterState) => void;
  onApply: () => void;
  onClear: () => void;
  activeCount: number;
  isAuthenticated: boolean;
  mobileOpen: boolean;
  onMobileClose: () => void;
}

const QUICK_FILTERS: { value: QuickFilter; label: string }[] = [
  { value: "now", label: "Now" },
  { value: "today", label: "Today" },
  { value: "weekend", label: "Weekend" },
  { value: "this_week", label: "This Week" },
  { value: "upcoming", label: "Upcoming" },
];

const PERSONAL_OPTIONS: { value: PersonalFilter; label: string }[] = [
  { value: "bookmarked", label: "Bookmarked" },
  { value: "going", label: "Going" },
];

const SORT_OPTIONS: { value: SortOption; label: string; helper: string }[] = [
  { value: "start_time", label: "Start time", helper: "Nearest in time first" },
  { value: "distance", label: "Distance (uses your location)", helper: "Closest to you first" },
  { value: "category", label: "Category", helper: "Group by category, A → Z" },
];

const ACCESSIBILITY_OPTIONS: { key: keyof AccessibilityFilters; label: string }[] = [
  { key: "wheelchair", label: "Wheelchair access" },
  { key: "accessible_restroom", label: "Accessible restroom" },
  { key: "elevator", label: "Elevator available" },
  { key: "seating", label: "Seating available" },
  { key: "captions", label: "Captions / interpreter support" },
  { key: "quiet_friendly", label: "Quiet-friendly" },
];

export function countActiveFilters(state: FilterState): number {
  const accessibility = ACCESSIBILITY_OPTIONS.reduce(
    (acc, opt) => acc + (state.accessibility[opt.key] ? 1 : 0),
    0,
  );
  return (
    (state.temporal ? 1 : 0)
    + (state.personal ? 1 : 0)
    + state.categoryIds.length
    + (state.showPast ? 1 : 0)
    + (state.sort !== "start_time" ? 1 : 0)
    + accessibility
  );
}

export const DEFAULT_FILTER_STATE: FilterState = {
  temporal: null,
  personal: null,
  categoryIds: [],
  showPast: false,
  sort: "start_time",
  accessibility: {},
};

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
  const sortedCategories = [...categories].sort((a, b) => {
    const ca = categoryCounts[a.id] ?? 0;
    const cb = categoryCounts[b.id] ?? 0;
    if (ca !== cb) return cb - ca;
    return a.name.localeCompare(b.name);
  });

  function toggleTemporal(value: QuickFilter) {
    onFiltersChange({
      ...filters,
      temporal: filters.temporal === value ? null : value,
    });
  }

  function togglePersonal(value: PersonalFilter) {
    onFiltersChange({
      ...filters,
      personal: filters.personal === value ? null : value,
    });
  }

  function toggleCategory(id: string) {
    const next = filters.categoryIds.includes(id)
      ? filters.categoryIds.filter((c) => c !== id)
      : [...filters.categoryIds, id];
    onFiltersChange({ ...filters, categoryIds: next });
  }

  function setSort(value: SortOption) {
    onFiltersChange({ ...filters, sort: value });
  }

  function toggleShowPast() {
    onFiltersChange({ ...filters, showPast: !filters.showPast });
  }

  function toggleAccessibility(key: keyof AccessibilityFilters) {
    onFiltersChange({
      ...filters,
      accessibility: {
        ...filters.accessibility,
        [key]: !filters.accessibility[key],
      },
    });
  }

  function renderSidebarContent(isMobile: boolean) {
    return (
      <>
        <div className={cn("border-brand-mid-alpha flex items-center gap-2 border-b", isMobile ? "px-4 py-4" : "px-5 py-4")}>
          <SlidersHorizontal className="text-brand-mid size-5" aria-hidden />
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

        <div className={cn("flex-1 overflow-y-auto space-y-6", isMobile ? "px-4 py-4" : "px-5 py-4")}>
          <section aria-labelledby="filter-quick-heading">
            <p
              id="filter-quick-heading"
              className="text-brand-mid mb-3 text-xs font-bold uppercase tracking-widest"
            >
              Quick Filters
            </p>
            <div className="flex flex-wrap gap-2" role="group" aria-label="Time window">
              {QUICK_FILTERS.map((opt) => {
                const active = filters.temporal === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => toggleTemporal(opt.value)}
                    aria-pressed={active}
                    className={cn(
                      "rounded-full border px-4 py-1.5 text-xs font-bold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-dark focus-visible:ring-offset-1",
                      active
                        ? "bg-brand-dark border-brand-dark text-white"
                        : "border-brand-mid-alpha text-brand-dark hover:bg-brand-mid-alpha",
                    )}
                  >
                    {opt.label}
                  </button>
                );
              })}
            </div>
          </section>

          {isAuthenticated && (
            <section aria-labelledby="filter-personal-heading">
              <p
                id="filter-personal-heading"
                className="text-brand-mid mb-3 text-xs font-bold uppercase tracking-widest"
              >
                My Events
              </p>
              <div className="flex flex-wrap gap-2" role="group" aria-label="My events">
                {PERSONAL_OPTIONS.map((opt) => {
                  const active = filters.personal === opt.value;
                  return (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => togglePersonal(opt.value)}
                      aria-pressed={active}
                      className={cn(
                        "rounded-full border px-4 py-1.5 text-xs font-bold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-dark focus-visible:ring-offset-1",
                        active
                          ? "bg-brand-dark border-brand-dark text-white"
                          : "border-brand-mid-alpha text-brand-dark hover:bg-brand-mid-alpha",
                      )}
                    >
                      {opt.label}
                    </button>
                  );
                })}
              </div>
            </section>
          )}

          <section aria-labelledby="filter-toggles-heading">
            <p
              id="filter-toggles-heading"
              className="text-brand-mid mb-3 text-xs font-bold uppercase tracking-widest"
            >
              Display
            </p>
            <ToggleRow
              icon={<Clock className="size-4 text-brand-mid" aria-hidden />}
              label="Show past events"
              helper="Include events whose end time has already passed."
              checked={filters.showPast}
              onChange={toggleShowPast}
            />
          </section>

          <section aria-labelledby="filter-sort-heading">
            <p
              id="filter-sort-heading"
              className="text-brand-mid mb-3 text-xs font-bold uppercase tracking-widest"
            >
              Sort by
            </p>
            <div role="radiogroup" aria-labelledby="filter-sort-heading" className="space-y-1">
              {SORT_OPTIONS.map((opt) => {
                const active = filters.sort === opt.value;
                const id = `sort-${opt.value}`;
                return (
                  <label
                    key={opt.value}
                    htmlFor={id}
                    className={cn(
                      "flex cursor-pointer items-start gap-3 rounded-lg px-2 py-1.5 transition-colors hover:bg-brand-mid-alpha",
                      active && "bg-brand-mid-alpha/60",
                    )}
                  >
                    <input
                      id={id}
                      type="radio"
                      name="discovery-sort"
                      value={opt.value}
                      checked={active}
                      onChange={() => setSort(opt.value)}
                      className="mt-1 size-4 cursor-pointer accent-brand-dark"
                    />
                    <span className="flex-1">
                      <span className="block text-sm font-semibold text-brand-dark">
                        {opt.label}
                      </span>
                      <span className="block text-[11px] text-brand-mid">{opt.helper}</span>
                    </span>
                  </label>
                );
              })}
            </div>
          </section>

          <section aria-labelledby="filter-accessibility-heading">
            <p
              id="filter-accessibility-heading"
              className="mb-3 flex items-center gap-1.5 text-xs font-bold uppercase tracking-widest text-brand-mid"
            >
              <Accessibility className="size-3.5" aria-hidden />
              Accessibility
            </p>
            <div className="space-y-1">
              {ACCESSIBILITY_OPTIONS.map((opt) => {
                const id = `a11y-${opt.key}`;
                const checked = filters.accessibility[opt.key] === true;
                return (
                  <label
                    key={opt.key}
                    htmlFor={id}
                    className="flex cursor-pointer items-center gap-3 rounded-lg px-2 py-1.5 transition-colors hover:bg-brand-mid-alpha"
                  >
                    <input
                      id={id}
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleAccessibility(opt.key)}
                      className="size-[18px] cursor-pointer accent-brand-dark"
                    />
                    <span className="text-sm text-brand-dark flex-1">{opt.label}</span>
                  </label>
                );
              })}
            </div>
          </section>

          <section aria-labelledby="filter-category-heading">
            <p
              id="filter-category-heading"
              className="text-brand-mid mb-3 text-xs font-bold uppercase tracking-widest"
            >
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
                      type="button"
                      onClick={() => toggleCategory(cat.id)}
                      aria-pressed={isSelected}
                      className="flex w-full items-center gap-3 rounded-lg px-2 py-1.5 text-left text-sm transition-colors hover:bg-brand-mid-alpha focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-dark focus-visible:ring-offset-1"
                    >
                      <span
                        className={cn(
                          "flex size-[18px] shrink-0 items-center justify-center rounded border-2 transition-colors",
                          isSelected
                            ? "bg-brand-dark border-brand-dark"
                            : "border-brand-mid-alpha",
                        )}
                      >
                        {isSelected && <Check className="size-3 text-white" strokeWidth={3} aria-hidden />}
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

        <div className={cn("border-brand-mid-alpha space-y-2 border-t", isMobile ? "px-4 py-4 pb-5" : "px-5 py-4")}>
          <button
            type="button"
            onClick={onApply}
            className="bg-brand-dark w-full rounded-lg py-2.5 text-sm font-bold text-white transition-colors hover:bg-brand-dark/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-dark focus-visible:ring-offset-1"
          >
            <Sparkles className="mr-1 inline size-4 -translate-y-px" aria-hidden />
            Apply Filters
          </button>
          <button
            type="button"
            onClick={onClear}
            className="text-brand-mid w-full rounded-lg py-2 text-sm font-semibold transition-colors hover:text-brand-dark focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-dark focus-visible:ring-offset-1"
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
            "absolute inset-0 bg-brand-dark/35 transition-opacity",
            mobileOpen ? "opacity-100" : "opacity-0",
          )}
          aria-label="Close filters"
        />
        <aside
          className={cn(
            "bg-card border-brand-mid-alpha absolute left-0 top-0 flex h-full w-[min(22rem,88vw)] flex-col border-r shadow-brand-panel transition-transform duration-200",
            mobileOpen ? "translate-x-0" : "-translate-x-full",
          )}
        >
          {renderSidebarContent(true)}
        </aside>
      </div>
    </>
  );
}

interface ToggleRowProps {
  icon: React.ReactNode;
  label: string;
  helper: string;
  checked: boolean;
  onChange: () => void;
}

function ToggleRow({ icon, label, helper, checked, onChange }: ToggleRowProps) {
  const labelId = `toggle-${label.replace(/\s+/g, "-").toLowerCase()}`;
  return (
    <div className="flex items-start gap-3 rounded-lg px-1 py-1">
      <span className="mt-1">{icon}</span>
      <div className="flex-1 min-w-0">
        <span id={labelId} className="block text-sm font-semibold text-brand-dark">
          {label}
        </span>
        <span className="block text-[11px] text-brand-mid">{helper}</span>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-labelledby={labelId}
        onClick={onChange}
        className={cn(
          "relative mt-1 inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-dark focus-visible:ring-offset-1",
          checked ? "bg-brand-dark" : "bg-brand-mid-alpha",
        )}
      >
        <span
          className={cn(
            "inline-block size-4 transform rounded-full bg-white shadow transition-transform",
            checked ? "translate-x-[18px]" : "translate-x-[2px]",
          )}
        />
      </button>
    </div>
  );
}
