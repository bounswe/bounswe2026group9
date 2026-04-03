"use client";

/**
 * Discovery Page — Issue #124
 *
 * URL is single source of truth: view, q, temporal, category (comma-separated), page.
 *
 * Category logic:
 *   - Multi-select, OR/union between selected categories
 *   - Temporal (quick filter) is AND on top of the category union
 *   - Category counts are computed from a separate "counts fetch" that has NO
 *     category filter, so counts stay stable regardless of which categories are selected
 *
 * useSearchParams() requires a Suspense boundary → DiscoveryShell wraps DiscoveryPage.
 */

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { useRouter, useSearchParams } from "next/navigation";

import { useAuth } from "@/hooks/use-auth";
import { Navbar, ActionBar } from "@/components/layout/navbar";
import { FilterSidebar, type FilterState } from "@/components/discovery/filter-sidebar";
import { ListView } from "@/components/discovery/list-view";
import {
  fetchEvents,
  fetchCategories,
  type Category,
  type EventListItem,
  type EventListResponse,
  type TemporalFilter,
} from "@/lib/events-api";

// SSR-safe — MapLibre uses WebGL/window APIs
const MapView = dynamic(
  () => import("@/components/discovery/map-view").then((m) => ({ default: m.MapView })),
  { ssr: false },
);

// ─── URL helpers ────────────────────────────────────────────────────────────────

type ViewMode = "map" | "list";

interface PageParams {
  view: ViewMode;
  search: string;
  temporal: TemporalFilter | null;
  /** comma-separated in URL, array in JS */
  categoryIds: string[];
  page: number;
}

function readParams(sp: ReturnType<typeof useSearchParams>): PageParams {
  const raw = sp.get("category") ?? "";
  return {
    view: sp.get("view") === "list" ? "list" : "map",
    search: sp.get("q") ?? "",
    temporal: (sp.get("temporal") as TemporalFilter | null) ?? null,
    categoryIds: raw ? raw.split(",").filter(Boolean) : [],
    page: Math.max(1, parseInt(sp.get("page") ?? "1", 10)),
  };
}

function buildQS(p: PageParams & { resetPage?: boolean }): string {
  const sp = new URLSearchParams();
  if (p.view !== "map") sp.set("view", p.view);
  if (p.search) sp.set("q", p.search);
  if (p.temporal) sp.set("temporal", p.temporal);
  if (p.categoryIds.length > 0) sp.set("category", p.categoryIds.join(","));
  if (!p.resetPage && p.page > 1) sp.set("page", String(p.page));
  const qs = sp.toString();
  return qs ? `?${qs}` : "?";
}

// ─── Union fetch — OR across multiple category IDs ──────────────────────────────

async function fetchEventsUnion(
  categoryIds: string[],
  opts: { search?: string; temporal?: TemporalFilter; page: number; pageSize: number },
): Promise<EventListResponse> {
  const base = {
    search: opts.search,
    temporal_filter: opts.temporal,
    page: opts.page,
    page_size: opts.pageSize,
  };

  if (categoryIds.length === 0) {
    return fetchEvents(base);
  }
  if (categoryIds.length === 1) {
    return fetchEvents({ ...base, category_id: categoryIds[0] });
  }

  // Multiple categories: parallel fetch + deduplicate (union)
  // Use larger page_size per category so we capture enough items
  const results = await Promise.all(
    categoryIds.map((id) => fetchEvents({ ...base, category_id: id, page_size: 50, page: 1 })),
  );

  const seen = new Set<string>();
  const items: EventListItem[] = [];
  for (const res of results) {
    for (const item of res.items) {
      if (!seen.has(item.id)) {
        seen.add(item.id);
        items.push(item);
      }
    }
  }

  // Client-side page slice
  const start = (opts.page - 1) * opts.pageSize;
  const pageItems = items.slice(start, start + opts.pageSize);
  const totalPages = Math.max(1, Math.ceil(items.length / opts.pageSize));

  return { items: pageItems, total: items.length, page: opts.page, page_size: opts.pageSize, total_pages: totalPages };
}

// ─── Loading skeleton ───────────────────────────────────────────────────────────

function ListSkeleton() {
  return (
    <div className="grid flex-1 grid-cols-1 gap-6 px-8 py-6 sm:grid-cols-2 xl:grid-cols-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <div
          key={i}
          className="bg-brand-surface border-brand-mid-alpha animate-pulse overflow-hidden rounded-xl border"
        >
          <div className="bg-brand-mid aspect-[16/10] w-full opacity-40" />
          <div className="space-y-3 p-4">
            <div className="bg-brand-mid h-4 w-3/4 rounded opacity-30" />
            <div className="bg-brand-mid h-3 w-1/2 rounded opacity-20" />
            <div className="bg-brand-mid h-3 w-1/4 rounded-full opacity-20" />
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Page ───────────────────────────────────────────────────────────────────────

function DiscoveryPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isAuthenticated } = useAuth();

  const params = readParams(searchParams);

  const [categories, setCategories] = useState<Category[]>([]);
  const [events, setEvents] = useState<EventListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);

  // categoryCounts come from a separate fetch WITHOUT category filter
  const [categoryCounts, setCategoryCounts] = useState<Record<string, number>>({});

  // Draft filters (not yet pushed to URL)
  const [draftFilters, setDraftFilters] = useState<FilterState>({
    temporal: params.temporal,
    categoryIds: params.categoryIds,
  });

  // Sync draft on back/forward
  const prevRef = useRef({ temporal: params.temporal, categoryIds: params.categoryIds });
  useEffect(() => {
    const prev = prevRef.current;
    const sameIds =
      prev.categoryIds.length === params.categoryIds.length &&
      prev.categoryIds.every((id, i) => id === params.categoryIds[i]);
    if (prev.temporal !== params.temporal || !sameIds) {
      setDraftFilters({ temporal: params.temporal, categoryIds: params.categoryIds });
      prevRef.current = { temporal: params.temporal, categoryIds: params.categoryIds };
    }
  }, [params.temporal, params.categoryIds]);

  // ── URL push / replace ─────────────────────────────────────────────────────────

  const replaceParams = useCallback(
    (updates: Partial<PageParams> & { resetPage?: boolean }) => {
      const next = { ...readParams(searchParams), ...updates };
      router.replace(buildQS({ ...next, resetPage: updates.resetPage }), { scroll: false });
    },
    [router, searchParams],
  );

  const pushParams = useCallback(
    (updates: Partial<PageParams> & { resetPage?: boolean }) => {
      const next = { ...readParams(searchParams), ...updates };
      router.push(buildQS({ ...next, resetPage: updates.resetPage }), { scroll: false });
    },
    [router, searchParams],
  );

  // ── Fetch categories (once) ────────────────────────────────────────────────────
  useEffect(() => {
    fetchCategories().then(setCategories).catch(() => setCategories([]));
  }, []);

  // ── Fetch events (on params change) ───────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    fetchEventsUnion(params.categoryIds, {
      search: params.search || undefined,
      temporal: params.temporal ?? undefined,
      page: params.page,
      pageSize: 12,
    })
      .then((res) => {
        if (cancelled) return;
        setEvents(res.items);
        setTotal(res.total);
        setTotalPages(res.total_pages);
      })
      .catch(() => {
        if (cancelled) return;
        setEvents([]);
        setTotal(0);
        setTotalPages(1);
      })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.search, params.temporal, params.page, params.categoryIds.join(",")]);

  // ── Fetch counts WITHOUT category filter (stable across category selection) ────
  useEffect(() => {
    let cancelled = false;

    fetchEvents({
      search: params.search || undefined,
      temporal_filter: params.temporal ?? undefined,
      page: 1,
      page_size: 100,
    })
      .then((res) => {
        if (cancelled) return;
        const counts: Record<string, number> = {};
        for (const event of res.items) {
          for (const cat of event.categories) {
            counts[cat.id] = (counts[cat.id] ?? 0) + 1;
          }
        }
        setCategoryCounts(counts);
      })
      .catch(() => { if (!cancelled) setCategoryCounts({}); });

    return () => { cancelled = true; };
  }, [params.search, params.temporal]);

  // Re-fetch on tab visibility restore
  const fetchNow = useCallback(() => {
    const sp = new URLSearchParams(window.location.search);
    const p = readParams(sp as unknown as ReturnType<typeof useSearchParams>);
    setLoading(true);
    fetchEventsUnion(p.categoryIds, {
      search: p.search || undefined,
      temporal: p.temporal ?? undefined,
      page: p.page,
      pageSize: 12,
    })
      .then((res) => { setEvents(res.items); setTotal(res.total); setTotalPages(res.total_pages); })
      .catch(() => { setEvents([]); setTotal(0); setTotalPages(1); })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const onVisible = () => { if (document.visibilityState === "visible") fetchNow(); };
    document.addEventListener("visibilitychange", onVisible);
    return () => document.removeEventListener("visibilitychange", onVisible);
  }, [fetchNow]);

  // ── Active filter count ────────────────────────────────────────────────────────
  const activeFilterCount = (draftFilters.temporal ? 1 : 0) + draftFilters.categoryIds.length;

  // ── Handlers ───────────────────────────────────────────────────────────────────

  function handleViewChange(view: ViewMode) { pushParams({ view }); }
  function handleSearchSubmit(v: string) { pushParams({ search: v, resetPage: true }); }
  function handleSearchChange(v: string) { replaceParams({ search: v, resetPage: true }); }
  function handleFiltersChange(f: FilterState) { setDraftFilters(f); }

  function handleApplyFilters() {
    pushParams({ temporal: draftFilters.temporal, categoryIds: draftFilters.categoryIds, resetPage: true });
  }

  function handleClearFilters() {
    setDraftFilters({ temporal: null, categoryIds: [] });
    pushParams({ temporal: null, categoryIds: [], resetPage: true });
  }

  function handlePageChange(page: number) {
    pushParams({ page });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  // ── Render ─────────────────────────────────────────────────────────────────────

  return (
    <div className="bg-brand-bg flex h-dvh flex-col overflow-hidden">
      <Navbar
        searchValue={params.search}
        onSearchChange={handleSearchChange}
        onSearchSubmit={handleSearchSubmit}
      />

      <ActionBar view={params.view} onViewChange={handleViewChange} />

      <div className="flex flex-1 overflow-hidden">
        <FilterSidebar
          filters={draftFilters}
          categories={categories}
          categoryCounts={categoryCounts}
          onFiltersChange={handleFiltersChange}
          onApply={handleApplyFilters}
          onClear={handleClearFilters}
          activeCount={activeFilterCount}
        />

        <main className="flex min-h-0 flex-1 flex-col overflow-y-auto">
          {params.view === "map" ? (
            <div className="flex flex-1" style={{ minHeight: "calc(100vh - 8rem)" }}>
              <MapView events={events} isAuthenticated={isAuthenticated} />
            </div>
          ) : loading ? (
            <ListSkeleton />
          ) : (
            <ListView
              events={events}
              isAuthenticated={isAuthenticated}
              total={total}
              page={params.page}
              totalPages={totalPages}
              onPageChange={handlePageChange}
            />
          )}
        </main>
      </div>
    </div>
  );
}

export default function DiscoveryShell() {
  return (
    <Suspense>
      <DiscoveryPage />
    </Suspense>
  );
}
