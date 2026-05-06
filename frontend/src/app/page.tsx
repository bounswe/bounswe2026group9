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
  fetchAllEvents,
  fetchEvents,
  fetchCategories,
  type Category,
  type DiscoveryParams,
  type EventListItem,
  type PersonalFilter,
  type TemporalFilter,
} from "@/lib/events-api";
import { cn } from "@/lib/utils";

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
  personal: PersonalFilter | null;
  /** "Suggested for you" — issue #285. Auth-only on the wire (silently ignored
   *  for guests by the backend, but we also gate the chip in the UI). */
  suggested: boolean;
  /** comma-separated in URL, array in JS */
  categoryIds: string[];
  page: number;
}

function isTemporalFilter(value: string | null): value is TemporalFilter {
  return value === "today" || value === "this_week" || value === "weekend";
}

function isPersonalFilter(value: string | null): value is PersonalFilter {
  return value === "bookmarked" || value === "going";
}

function readParams(sp: ReturnType<typeof useSearchParams>): PageParams {
  const raw = sp.get("category") ?? "";
  const temporal = sp.get("temporal");
  const personal = sp.get("personal");
  return {
    view: sp.get("view") === "list" ? "list" : "map",
    search: sp.get("q") ?? "",
    temporal: isTemporalFilter(temporal) ? temporal : null,
    personal: isPersonalFilter(personal) ? personal : null,
    suggested: sp.get("suggested") === "1",
    categoryIds: raw ? raw.split(",").filter(Boolean) : [],
    page: Math.max(1, parseInt(sp.get("page") ?? "1", 10)),
  };
}

function buildQS(p: PageParams & { resetPage?: boolean }): string {
  const sp = new URLSearchParams();
  if (p.view !== "map") sp.set("view", p.view);
  if (p.search) sp.set("q", p.search);
  if (p.temporal) sp.set("temporal", p.temporal);
  if (p.personal) sp.set("personal", p.personal);
  if (p.suggested) sp.set("suggested", "1");
  if (p.categoryIds.length > 0) sp.set("category", p.categoryIds.join(","));
  if (!p.resetPage && p.page > 1) sp.set("page", String(p.page));
  const qs = sp.toString();
  return qs ? `?${qs}` : "?";
}

const LIST_PAGE_SIZE = 12;

interface DiscoveryPageResult {
  items: EventListItem[];
  total: number;
  totalPages: number;
  suggested_fallback: boolean;
}

function buildDiscoveryCacheKey(
  params: Pick<PageParams, "search" | "temporal" | "categoryIds" | "suggested">,
  personal: PersonalFilter | null,
  userKey: string,
): string {
  return JSON.stringify({
    search: params.search.trim(),
    temporal: params.temporal,
    personal,
    suggested: params.suggested,
    categoryIds: [...params.categoryIds].sort(),
    userKey,
  });
}

function paginateDiscoveryEvents(
  items: EventListItem[],
  page: number,
  suggested_fallback: boolean,
): DiscoveryPageResult {
  const startIndex = (page - 1) * LIST_PAGE_SIZE;
  return {
    items: items.slice(startIndex, startIndex + LIST_PAGE_SIZE),
    total: items.length,
    totalPages: items.length > 0 ? Math.ceil(items.length / LIST_PAGE_SIZE) : 0,
    suggested_fallback,
  };
}

function buildDiscoveryQuery(
  params: PageParams,
  isAuthenticated: boolean,
): DiscoveryParams {
  return {
    search: params.search || undefined,
    temporal_filter:
      params.temporal === "today" || params.temporal === "this_week"
        ? params.temporal
        : undefined,
    suggested: params.suggested && isAuthenticated ? true : undefined,
  };
}

function isWeekendEvent(dateStr: string): boolean {
  const dayOfWeek = new Date(dateStr).getDay();
  return dayOfWeek === 0 || dayOfWeek === 6;
}

function applyTemporalFilter(
  events: EventListItem[],
  temporal: TemporalFilter | null,
): EventListItem[] {
  if (temporal !== "weekend") {
    return events;
  }

  return events.filter((event) => isWeekendEvent(event.start_datetime));
}

function applyPersonalFilter(
  events: EventListItem[],
  personal: PersonalFilter | null,
): EventListItem[] {
  if (personal === "bookmarked") {
    return events.filter((event) => event.is_bookmarked);
  }

  if (personal === "going") {
    // attendance_status is now returned directly by the list endpoint for authenticated users
    return events.filter((event) => event.attendance_status === "going");
  }

  return events;
}

function sortDiscoveryEvents(a: EventListItem, b: EventListItem): number {
  const startDifference = Date.parse(a.start_datetime) - Date.parse(b.start_datetime);
  if (startDifference !== 0) {
    return startDifference;
  }
  return a.id.localeCompare(b.id);
}

interface UnionEventsResult {
  items: EventListItem[];
  suggested_fallback: boolean;
}

async function fetchUnionEvents(
  categoryIds: string[],
  query: DiscoveryParams,
  temporal: TemporalFilter | null,
  personal: PersonalFilter | null,
): Promise<UnionEventsResult> {
  const applyFilters = (items: EventListItem[]) =>
    applyPersonalFilter(
      applyTemporalFilter(items, temporal),
      personal,
    );

  if (categoryIds.length === 0) {
    const res = await fetchAllEvents(query);
    return { items: applyFilters(res.items), suggested_fallback: res.suggested_fallback };
  }

  if (categoryIds.length === 1) {
    const res = await fetchAllEvents({ ...query, category_id: categoryIds[0] });
    return { items: applyFilters(res.items), suggested_fallback: res.suggested_fallback };
  }

  const results = await Promise.all(
    categoryIds.map((categoryId) => fetchAllEvents({ ...query, category_id: categoryId })),
  );

  const eventsById = new Map<string, EventListItem>();
  for (const res of results) {
    for (const item of res.items) {
      eventsById.set(item.id, item);
    }
  }

  // Treat fallback as union: any per-category call that fell back means the
  // user has no history matching that category — surface the hint.
  const suggested_fallback = results.some((res) => res.suggested_fallback);
  return {
    items: applyFilters(Array.from(eventsById.values()).sort(sortDiscoveryEvents)),
    suggested_fallback,
  };
}

// ─── Loading UI ─────────────────────────────────────────────────────────────────

function LoadingPulseCard() {
  return (
    <div className="bg-card/90 border-brand-mid-alpha shadow-brand-panel w-full max-w-[22rem] rounded-[1.75rem] border p-5 backdrop-blur-md sm:max-w-md sm:p-6">
      <div className="flex items-center gap-3 sm:gap-4">
        <div className="bg-brand-mid-alpha relative flex size-10 shrink-0 items-center justify-center rounded-full sm:size-12">
          <span className="bg-brand-mid absolute size-5 animate-ping rounded-full opacity-60" />
          <span className="bg-brand-dark relative size-5 rounded-full" />
        </div>
        <div className="min-w-0">
          <p className="font-heading text-brand-dark text-base font-bold sm:text-lg">
            Updating discovery results
          </p>
          <p className="text-muted-foreground text-xs sm:text-sm">
            Applying your latest search and filters.
          </p>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-3 gap-2 sm:mt-6 sm:gap-3">
        {Array.from({ length: 3 }).map((_, index) => (
          <div
            key={index}
            className="bg-brand-surface/70 border-brand-mid-alpha animate-pulse rounded-2xl border p-2.5 sm:p-3"
          >
            <div className="bg-brand-mid h-14 rounded-lg opacity-25 sm:h-20 sm:rounded-xl" />
            <div className="mt-2 space-y-1.5 sm:mt-3 sm:space-y-2">
              <div className="bg-brand-mid h-2.5 rounded opacity-25 sm:h-3" />
              <div className="bg-brand-mid h-2.5 w-3/4 rounded opacity-20 sm:h-3" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function DiscoveryLoadingOverlay() {
  return (
    <div className="bg-brand-bg-alpha absolute inset-0 z-20 flex items-center justify-center px-6 backdrop-blur-sm">
      <LoadingPulseCard />
    </div>
  );
}

// ─── Page ───────────────────────────────────────────────────────────────────────

function DiscoveryPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isAuthenticated, user } = useAuth();
  const params = readParams(searchParams);
  const activePersonalFilter = isAuthenticated ? params.personal : null;
  const discoveryUserKey = isAuthenticated ? (user?.id ?? "authenticated") : "guest";
  const categoryIdsKey = params.categoryIds.join(",");

  const [categories, setCategories] = useState<Category[]>([]);
  const [events, setEvents] = useState<EventListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [suggestedFallback, setSuggestedFallback] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshTick, setRefreshTick] = useState(0);
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);
  const fullResultsCacheRef = useRef(new Map<string, UnionEventsResult>());
  const pendingFullResultsRef = useRef(new Map<string, Promise<UnionEventsResult>>());
  const pagedResultsCacheRef = useRef(new Map<string, DiscoveryPageResult>());

  // categoryCounts come from a separate fetch WITHOUT category filter
  const [categoryCounts, setCategoryCounts] = useState<Record<string, number>>({});

  // Suggested is auth-only — strip it from the URL state for guests so the
  // chip never gets a phantom "on" reading and the wire never receives it.
  const activeSuggested = isAuthenticated && params.suggested;

  // Draft filters (not yet pushed to URL)
  const [draftFilters, setDraftFilters] = useState<FilterState>({
    temporal: params.temporal,
    personal: activePersonalFilter,
    suggested: activeSuggested,
    categoryIds: params.categoryIds,
  });

  // Sync draft on back/forward
  const prevRef = useRef({
    temporal: params.temporal,
    personal: activePersonalFilter,
    suggested: activeSuggested,
    categoryIds: params.categoryIds,
  });
  useEffect(() => {
    const prev = prevRef.current;
    const sameIds =
      prev.categoryIds.length === params.categoryIds.length &&
      prev.categoryIds.every((id, i) => id === params.categoryIds[i]);
    if (
      prev.temporal !== params.temporal ||
      prev.personal !== activePersonalFilter ||
      prev.suggested !== activeSuggested ||
      !sameIds
    ) {
      setDraftFilters({
        temporal: params.temporal,
        personal: activePersonalFilter,
        suggested: activeSuggested,
        categoryIds: params.categoryIds,
      });
      prevRef.current = {
        temporal: params.temporal,
        personal: activePersonalFilter,
        suggested: activeSuggested,
        categoryIds: params.categoryIds,
      };
    }
  }, [params.temporal, activePersonalFilter, activeSuggested, params.categoryIds]);

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

  useEffect(() => {
    void import("@/components/discovery/map-view");
  }, []);

  const getFullDiscoveryEvents = useCallback(
    (
      cacheKey: string,
      query: DiscoveryParams,
      categoryIds: string[],
      temporal: TemporalFilter | null,
      personal: PersonalFilter | null,
    ) => {
      const cachedResult = fullResultsCacheRef.current.get(cacheKey);
      if (cachedResult) {
        return Promise.resolve(cachedResult);
      }

      const pendingRequest = pendingFullResultsRef.current.get(cacheKey);
      if (pendingRequest) {
        return pendingRequest;
      }

      const request = fetchUnionEvents(
        categoryIds,
        query,
        temporal,
        personal,
      )
        .then((result) => {
          fullResultsCacheRef.current.set(cacheKey, result);
          return result;
        })
        .finally(() => {
          pendingFullResultsRef.current.delete(cacheKey);
        });

      pendingFullResultsRef.current.set(cacheKey, request);
      return request;
    },
    [],
  );

  // ── Fetch events (on params change) ───────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;

    const query = buildDiscoveryQuery(params, isAuthenticated);
    const resultCacheKey = buildDiscoveryCacheKey(params, activePersonalFilter, discoveryUserKey);
    const pageCacheKey = `${resultCacheKey}|page:${params.page}`;
    const canUseSimpleListFetch =
      !activePersonalFilter &&
      params.temporal !== "weekend" &&
      params.categoryIds.length <= 1;

    async function loadEvents() {
      setLoading(true);

      try {
        let nextResult: DiscoveryPageResult;

        if (params.view === "map") {
          const res = await getFullDiscoveryEvents(
            resultCacheKey,
            query,
            params.categoryIds,
            params.temporal,
            activePersonalFilter,
          );

          nextResult = {
            items: res.items,
            total: res.items.length,
            totalPages: res.items.length > 0 ? Math.ceil(res.items.length / LIST_PAGE_SIZE) : 0,
            suggested_fallback: res.suggested_fallback,
          };
        } else {
          const cachedFull = fullResultsCacheRef.current.get(resultCacheKey);
          if (cachedFull) {
            nextResult = paginateDiscoveryEvents(
              cachedFull.items,
              params.page,
              cachedFull.suggested_fallback,
            );
          } else {
            const cachedPage = pagedResultsCacheRef.current.get(pageCacheKey);
            if (cachedPage) {
              nextResult = cachedPage;
            } else if (canUseSimpleListFetch) {
              const res = await fetchEvents({
                ...query,
                category_id: params.categoryIds[0],
                page: params.page,
                page_size: LIST_PAGE_SIZE,
              });

              nextResult = {
                items: res.items,
                total: res.total,
                totalPages: res.total_pages,
                suggested_fallback: res.suggested_fallback ?? false,
              };
              pagedResultsCacheRef.current.set(pageCacheKey, nextResult);

              void getFullDiscoveryEvents(
                resultCacheKey,
                query,
                params.categoryIds,
                params.temporal,
                activePersonalFilter,
              ).catch(() => undefined);
            } else {
              const res = await getFullDiscoveryEvents(
                resultCacheKey,
                query,
                params.categoryIds,
                params.temporal,
                activePersonalFilter,
              );
              nextResult = paginateDiscoveryEvents(res.items, params.page, res.suggested_fallback);
            }
          }
        }

        if (cancelled) return;

        const safePage = Math.max(1, nextResult.totalPages);
        if (params.view === "list" && nextResult.totalPages !== 0 && params.page > safePage) {
          replaceParams({ page: safePage });
          return;
        }
        if (params.view === "list" && nextResult.totalPages === 0 && params.page > 1) {
          replaceParams({ page: 1 });
          return;
        }

        setEvents(nextResult.items);
        setTotal(nextResult.total);
        setTotalPages(nextResult.totalPages);
        setSuggestedFallback(nextResult.suggested_fallback);

        // attendance_status and is_bookmarked are now returned directly by the list endpoint
        // when authenticated — no separate enrichment needed.
      } catch {
        if (cancelled) return;
        setEvents([]);
        setTotal(0);
        setTotalPages(1);
        setSuggestedFallback(false);
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadEvents();

    return () => { cancelled = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    discoveryUserKey,
    getFullDiscoveryEvents,
    replaceParams,
    isAuthenticated,
    params.search,
    params.temporal,
    activePersonalFilter,
    activeSuggested,
    params.page,
    params.view,
    categoryIdsKey,
    refreshTick,
  ]);

  // ── Fetch counts WITHOUT category filter (stable across category selection) ────
  useEffect(() => {
    let cancelled = false;

    fetchAllEvents({
      search: params.search || undefined,
      temporal_filter:
        params.temporal === "today" || params.temporal === "this_week"
          ? params.temporal
          : undefined,
      // Counts must reflect the same suggested-narrowed set the listing uses,
      // otherwise the badge totals stop matching what the user actually sees.
      suggested: activeSuggested ? true : undefined,
    })
      .then((res) => {
        if (cancelled) return;
        const counts: Record<string, number> = {};
        const filteredItems = applyPersonalFilter(
          applyTemporalFilter(res.items, params.temporal),
          activePersonalFilter,
        );
        if (cancelled) return;
        for (const event of filteredItems) {
          for (const cat of event.categories) {
            counts[cat.id] = (counts[cat.id] ?? 0) + 1;
          }
        }
        setCategoryCounts(counts);
      })
      .catch(() => { if (!cancelled) setCategoryCounts({}); });

    return () => { cancelled = true; };
  }, [
    params.search,
    params.temporal,
    activePersonalFilter,
    activeSuggested,
    refreshTick,
  ]);

  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState === "visible") {
        fullResultsCacheRef.current.clear();
        pendingFullResultsRef.current.clear();
        pagedResultsCacheRef.current.clear();
        setRefreshTick((tick) => tick + 1);
      }
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => document.removeEventListener("visibilitychange", onVisible);
  }, []);

  // ── Active filter count ────────────────────────────────────────────────────────
  const activeFilterCount =
    ((draftFilters.temporal || draftFilters.personal) ? 1 : 0) +
    (draftFilters.suggested ? 1 : 0) +
    draftFilters.categoryIds.length;

  // ── Handlers ───────────────────────────────────────────────────────────────────

  function handleViewChange(view: ViewMode) {
    setMobileFiltersOpen(false);
    pushParams({ view });
  }
  function handleSearchSubmit(v: string) { pushParams({ search: v, resetPage: true }); }
  function handleSearchChange(v: string) { replaceParams({ search: v, resetPage: true }); }
  function handleFiltersChange(f: FilterState) { setDraftFilters(f); }

  function handleApplyFilters() {
    setMobileFiltersOpen(false);
    pushParams({
      temporal: draftFilters.temporal,
      personal: isAuthenticated ? draftFilters.personal : null,
      suggested: isAuthenticated ? draftFilters.suggested : false,
      categoryIds: draftFilters.categoryIds,
      resetPage: true,
    });
  }

  function handleClearFilters() {
    setDraftFilters({ temporal: null, personal: null, suggested: false, categoryIds: [] });
    setMobileFiltersOpen(false);
    pushParams({
      temporal: null,
      personal: null,
      suggested: false,
      categoryIds: [],
      resetPage: true,
    });
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

      <ActionBar
        view={params.view}
        onViewChange={handleViewChange}
        activeFilterCount={activeFilterCount}
        onToggleFilters={() => setMobileFiltersOpen(true)}
      />

      <div className="flex flex-1 overflow-hidden">
        <FilterSidebar
          filters={draftFilters}
          categories={categories}
          categoryCounts={categoryCounts}
          onFiltersChange={handleFiltersChange}
          onApply={handleApplyFilters}
          onClear={handleClearFilters}
          activeCount={activeFilterCount}
          isAuthenticated={isAuthenticated}
          mobileOpen={mobileFiltersOpen}
          onMobileClose={() => setMobileFiltersOpen(false)}
        />

        <main
          className={cn(
            "flex min-h-0 flex-1 flex-col",
            loading && params.view === "list" ? "overflow-hidden" : "overflow-y-auto",
          )}
        >
          {activeSuggested && suggestedFallback && !loading && (
            <div
              role="status"
              className="border-brand-mid-alpha bg-brand-surface/60 text-brand-dark mx-4 mt-3 rounded-lg border px-4 py-2.5 text-xs sm:mx-6"
            >
              Attend events to get personalised suggestions. Showing default
              results in the meantime.
            </div>
          )}
          <div className="relative flex min-h-0 flex-1">
            <div
              className={cn(
                "flex min-h-0 flex-1 flex-col transition duration-200",
                loading && "pointer-events-none select-none blur-[3px]",
              )}
            >
              {params.view === "map" ? (
                <div className="flex min-h-[22rem] flex-1 sm:min-h-[28rem] lg:min-h-0">
                  <MapView
                    currentUserId={user?.id ?? null}
                    events={events}
                    isAuthenticated={isAuthenticated}
                  />
                </div>
              ) : (
                <ListView
                  currentUserId={user?.id ?? null}
                  events={events}
                  isAuthenticated={isAuthenticated}
                  total={total}
                  page={params.page}
                  totalPages={totalPages}
                  onPageChange={handlePageChange}
                />
              )}
            </div>

            {loading && <DiscoveryLoadingOverlay />}
          </div>
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
