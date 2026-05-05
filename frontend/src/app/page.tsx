"use client";

/**
 * Discovery Page — Issues #124 + #156
 *
 * URL is the single source of truth. The discovery state is reflected in the
 * query string so any view can be deep-linked or shared:
 *
 *   /?view=list&q=jazz&temporal=this_week&showPast=1&sort=distance
 *      &category=<id1>,<id2>&page=2&a11y=wheelchair,quiet_friendly
 *
 * Behaviour:
 *   - Backend `quick_filter` and accessibility flags are sent verbatim.
 *   - `sort=distance` is location-aware: the browser's geolocation is requested
 *     when the option is selected. If it is denied or unavailable, we fall back
 *     to `use_default_area=true` for authenticated users; otherwise the sort
 *     resets to `start_time` and a visible banner explains why.
 *   - The free-text search input is debounced (250 ms) so each keystroke does
 *     not hammer the API.
 */

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, X as XIcon } from "lucide-react";
import dynamic from "next/dynamic";
import { useRouter, useSearchParams } from "next/navigation";

import { useAuth } from "@/hooks/use-auth";
import { Navbar, ActionBar } from "@/components/layout/navbar";
import {
  DEFAULT_FILTER_STATE,
  FilterSidebar,
  countActiveFilters,
  type FilterState,
} from "@/components/discovery/filter-sidebar";
import { ListView } from "@/components/discovery/list-view";
import {
  fetchAllEvents,
  fetchEvents,
  fetchCategories,
  type AccessibilityFilters,
  type Category,
  type DiscoveryParams,
  type EventListItem,
  type PersonalFilter,
  type QuickFilter,
  type SortOption,
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
  /** comma-separated in URL, array in JS */
  categoryIds: string[];
  showPast: boolean;
  sort: SortOption;
  accessibility: AccessibilityFilters;
  page: number;
}

const QUICK_FILTER_VALUES: readonly QuickFilter[] = [
  "now",
  "today",
  "this_week",
  "weekend",
  "upcoming",
];
const SORT_VALUES: readonly SortOption[] = ["start_time", "distance", "category"];
const A11Y_KEYS: readonly (keyof AccessibilityFilters)[] = [
  "wheelchair",
  "accessible_restroom",
  "elevator",
  "seating",
  "captions",
  "quiet_friendly",
];

function isQuickFilter(value: string | null): value is QuickFilter {
  return value !== null && (QUICK_FILTER_VALUES as readonly string[]).includes(value);
}

function isPersonalFilter(value: string | null): value is PersonalFilter {
  return value === "bookmarked" || value === "going";
}

function isSortOption(value: string | null): value is SortOption {
  return value !== null && (SORT_VALUES as readonly string[]).includes(value);
}

function readAccessibilityFromUrl(raw: string | null): AccessibilityFilters {
  if (!raw) return {};
  const set = new Set(raw.split(",").filter(Boolean));
  const out: AccessibilityFilters = {};
  for (const key of A11Y_KEYS) {
    if (set.has(key)) {
      out[key] = true;
    }
  }
  return out;
}

function readParams(sp: ReturnType<typeof useSearchParams>): PageParams {
  const raw = sp.get("category") ?? "";
  const temporal = sp.get("temporal");
  const personal = sp.get("personal");
  const sort = sp.get("sort");
  return {
    view: sp.get("view") === "list" ? "list" : "map",
    search: sp.get("q") ?? "",
    temporal: isQuickFilter(temporal) ? temporal : null,
    personal: isPersonalFilter(personal) ? personal : null,
    categoryIds: raw ? raw.split(",").filter(Boolean) : [],
    showPast: sp.get("showPast") === "1",
    sort: isSortOption(sort) ? sort : "start_time",
    accessibility: readAccessibilityFromUrl(sp.get("a11y")),
    page: Math.max(1, parseInt(sp.get("page") ?? "1", 10)),
  };
}

function activeAccessibilityKeys(a11y: AccessibilityFilters): string[] {
  return A11Y_KEYS.filter((k) => a11y[k] === true);
}

function buildQS(p: PageParams & { resetPage?: boolean }): string {
  const sp = new URLSearchParams();
  if (p.view !== "map") sp.set("view", p.view);
  if (p.search) sp.set("q", p.search);
  if (p.temporal) sp.set("temporal", p.temporal);
  if (p.personal) sp.set("personal", p.personal);
  if (p.categoryIds.length > 0) sp.set("category", p.categoryIds.join(","));
  if (p.showPast) sp.set("showPast", "1");
  if (p.sort !== "start_time") sp.set("sort", p.sort);
  const a11yKeys = activeAccessibilityKeys(p.accessibility);
  if (a11yKeys.length > 0) sp.set("a11y", a11yKeys.join(","));
  if (!p.resetPage && p.page > 1) sp.set("page", String(p.page));
  const qs = sp.toString();
  return qs ? `?${qs}` : "?";
}

const LIST_PAGE_SIZE = 12;
const SEARCH_DEBOUNCE_MS = 250;

interface DiscoveryPageResult {
  items: EventListItem[];
  total: number;
  totalPages: number;
}

interface DiscoveryQueryShape {
  search: string;
  temporal: TemporalFilter | null;
  showPast: boolean;
  sort: SortOption;
  accessibilityKeys: string[];
  categoryIds: string[];
}

function buildQueryShape(p: PageParams): DiscoveryQueryShape {
  return {
    search: p.search.trim(),
    temporal: p.temporal,
    showPast: p.showPast,
    sort: p.sort,
    accessibilityKeys: activeAccessibilityKeys(p.accessibility),
    categoryIds: [...p.categoryIds].sort(),
  };
}

function buildDiscoveryCacheKey(
  shape: DiscoveryQueryShape,
  personal: PersonalFilter | null,
  userKey: string,
  geoKey: string,
): string {
  return JSON.stringify({ ...shape, personal, userKey, geoKey });
}

function paginateDiscoveryEvents(items: EventListItem[], page: number): DiscoveryPageResult {
  const startIndex = (page - 1) * LIST_PAGE_SIZE;
  return {
    items: items.slice(startIndex, startIndex + LIST_PAGE_SIZE),
    total: items.length,
    totalPages: items.length > 0 ? Math.ceil(items.length / LIST_PAGE_SIZE) : 0,
  };
}

function buildDiscoveryQuery(params: PageParams, geo: GeoState): DiscoveryParams {
  const out: DiscoveryParams = {
    search: params.search.trim() || undefined,
  };

  if (params.temporal) {
    out.quick_filter = params.temporal;
  } else if (params.showPast) {
    out.quick_filter = "past";
  }

  if (params.sort !== "start_time") {
    out.sort = params.sort;
  }

  const a11y = params.accessibility;
  const a11yKeys = activeAccessibilityKeys(a11y);
  if (a11yKeys.length > 0) {
    out.accessibility = { ...a11y };
  }

  // Distance sort needs a location; pass coords (or default-area fallback) when ready.
  if (params.sort === "distance") {
    if (geo.coords) {
      out.near_lat = geo.coords.lat;
      out.near_lng = geo.coords.lng;
    } else if (geo.useDefaultArea) {
      out.use_default_area = true;
    }
  }

  return out;
}

function applyShowPastFilter(events: EventListItem[], showPast: boolean): EventListItem[] {
  if (showPast) return events;
  return events.filter((event) => event.status !== "ended");
}

function applyPersonalFilter(
  events: EventListItem[],
  personal: PersonalFilter | null,
): EventListItem[] {
  if (personal === "bookmarked") {
    return events.filter((event) => event.is_bookmarked);
  }
  if (personal === "going") {
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

async function fetchUnionEvents(
  categoryIds: string[],
  query: DiscoveryParams,
  showPast: boolean,
  personal: PersonalFilter | null,
): Promise<EventListItem[]> {
  const applyFilters = (items: EventListItem[]) =>
    applyPersonalFilter(applyShowPastFilter(items, showPast), personal);

  if (categoryIds.length === 0) {
    return applyFilters(await fetchAllEvents(query));
  }

  if (categoryIds.length === 1) {
    return applyFilters(await fetchAllEvents({ ...query, category_id: categoryIds[0] }));
  }

  const results = await Promise.all(
    categoryIds.map((categoryId) => fetchAllEvents({ ...query, category_id: categoryId })),
  );

  const eventsById = new Map<string, EventListItem>();
  for (const items of results) {
    for (const item of items) {
      eventsById.set(item.id, item);
    }
  }

  return applyFilters(Array.from(eventsById.values()).sort(sortDiscoveryEvents));
}

// ─── Geolocation helper ────────────────────────────────────────────────────────

interface GeoState {
  status: "idle" | "pending" | "ready" | "denied" | "fallback";
  coords: { lat: number; lng: number } | null;
  useDefaultArea: boolean;
}

const IDLE_GEO_STATE: GeoState = { status: "idle", coords: null, useDefaultArea: false };

function hasGeolocation(): boolean {
  return typeof navigator !== "undefined" && typeof navigator.geolocation !== "undefined";
}

function useDistanceGeo(enabled: boolean, isAuthenticated: boolean): GeoState {
  const [resolved, setResolved] = useState<GeoState | null>(null);

  useEffect(() => {
    if (!enabled || !hasGeolocation()) return;

    let cancelled = false;
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        if (cancelled) return;
        setResolved({
          status: "ready",
          coords: { lat: pos.coords.latitude, lng: pos.coords.longitude },
          useDefaultArea: false,
        });
      },
      () => {
        if (cancelled) return;
        if (isAuthenticated) {
          setResolved({ status: "fallback", coords: null, useDefaultArea: true });
        } else {
          setResolved({ status: "denied", coords: null, useDefaultArea: false });
        }
      },
      { enableHighAccuracy: false, maximumAge: 60_000, timeout: 8_000 },
    );

    return () => {
      cancelled = true;
    };
  }, [enabled, isAuthenticated]);

  if (!enabled) return IDLE_GEO_STATE;
  if (!hasGeolocation()) {
    return isAuthenticated
      ? { status: "fallback", coords: null, useDefaultArea: true }
      : { status: "denied", coords: null, useDefaultArea: false };
  }
  return resolved ?? { status: "pending", coords: null, useDefaultArea: false };
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
    <div
      className="bg-brand-bg-alpha absolute inset-0 z-20 flex items-center justify-center px-6 backdrop-blur-sm"
      role="status"
      aria-live="polite"
      aria-label="Loading discovery results"
    >
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
  const a11yKey = activeAccessibilityKeys(params.accessibility).join(",");

  const [categories, setCategories] = useState<Category[]>([]);
  const [events, setEvents] = useState<EventListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [refreshTick, setRefreshTick] = useState(0);
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [bannerDismissed, setBannerDismissed] = useState(false);
  const fullResultsCacheRef = useRef(new Map<string, EventListItem[]>());
  const pendingFullResultsRef = useRef(new Map<string, Promise<EventListItem[]>>());
  const pagedResultsCacheRef = useRef(new Map<string, DiscoveryPageResult>());

  const distanceMode = params.sort === "distance";
  const geoState = useDistanceGeo(distanceMode, isAuthenticated);
  const geoKey = useMemo(() => {
    if (!distanceMode) return "off";
    if (geoState.status === "ready" && geoState.coords) {
      return `geo:${geoState.coords.lat.toFixed(2)},${geoState.coords.lng.toFixed(2)}`;
    }
    if (geoState.status === "fallback") return "default-area";
    if (geoState.status === "denied") return "denied";
    return "pending";
  }, [distanceMode, geoState]);

  // Reset banner dismissal when geo status moves out of "denied"
  useEffect(() => {
    if (geoState.status !== "denied") {
      setBannerDismissed(false);
    }
  }, [geoState.status]);

  // categoryCounts come from a separate fetch WITHOUT category filter
  const [categoryCounts, setCategoryCounts] = useState<Record<string, number>>({});

  // Draft filters (not yet pushed to URL)
  const [draftFilters, setDraftFilters] = useState<FilterState>({
    temporal: params.temporal,
    personal: activePersonalFilter,
    categoryIds: params.categoryIds,
    showPast: params.showPast,
    sort: params.sort,
    accessibility: { ...params.accessibility },
  });

  // Sync draft on back/forward
  const prevRef = useRef({
    temporal: params.temporal,
    personal: activePersonalFilter,
    categoryIds: params.categoryIds,
    showPast: params.showPast,
    sort: params.sort,
    accessibility: params.accessibility,
  });
  useEffect(() => {
    const prev = prevRef.current;
    const sameIds =
      prev.categoryIds.length === params.categoryIds.length &&
      prev.categoryIds.every((id, i) => id === params.categoryIds[i]);
    const sameA11y =
      activeAccessibilityKeys(prev.accessibility).join(",")
        === activeAccessibilityKeys(params.accessibility).join(",");
    const changed =
      prev.temporal !== params.temporal ||
      prev.personal !== activePersonalFilter ||
      prev.showPast !== params.showPast ||
      prev.sort !== params.sort ||
      !sameIds ||
      !sameA11y;
    if (changed) {
      setDraftFilters({
        temporal: params.temporal,
        personal: activePersonalFilter,
        categoryIds: params.categoryIds,
        showPast: params.showPast,
        sort: params.sort,
        accessibility: { ...params.accessibility },
      });
      prevRef.current = {
        temporal: params.temporal,
        personal: activePersonalFilter,
        categoryIds: params.categoryIds,
        showPast: params.showPast,
        sort: params.sort,
        accessibility: params.accessibility,
      };
    }
  }, [
    params.temporal,
    activePersonalFilter,
    params.categoryIds,
    params.showPast,
    params.sort,
    params.accessibility,
    categoryIdsKey,
    a11yKey,
  ]);

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

  // Auto-revert sort to start_time if geolocation was rejected and we have no fallback
  useEffect(() => {
    if (params.sort === "distance" && geoState.status === "denied") {
      replaceParams({ sort: "start_time" });
    }
  }, [params.sort, geoState.status, replaceParams]);

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
      showPast: boolean,
      personal: PersonalFilter | null,
    ) => {
      const cachedItems = fullResultsCacheRef.current.get(cacheKey);
      if (cachedItems) {
        return Promise.resolve(cachedItems);
      }

      const pendingRequest = pendingFullResultsRef.current.get(cacheKey);
      if (pendingRequest) {
        return pendingRequest;
      }

      const request = fetchUnionEvents(categoryIds, query, showPast, personal)
        .then((items) => {
          fullResultsCacheRef.current.set(cacheKey, items);
          return items;
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

    // While waiting for geolocation we hold off fetching with sort=distance to
    // avoid issuing a request without coords (which would cause a backend 422).
    if (distanceMode && geoState.status === "pending") {
      return;
    }

    const query = buildDiscoveryQuery(params, geoState);
    const shape = buildQueryShape(params);
    const resultCacheKey = buildDiscoveryCacheKey(
      shape,
      activePersonalFilter,
      discoveryUserKey,
      geoKey,
    );
    const pageCacheKey = `${resultCacheKey}|page:${params.page}`;
    const canUseSimpleListFetch =
      !activePersonalFilter && params.categoryIds.length <= 1;

    async function loadEvents() {
      setLoading(true);
      setErrorMessage(null);

      try {
        let nextResult: DiscoveryPageResult;

        if (params.view === "map") {
          const items = await getFullDiscoveryEvents(
            resultCacheKey,
            query,
            params.categoryIds,
            params.showPast,
            activePersonalFilter,
          );

          nextResult = {
            items,
            total: items.length,
            totalPages: items.length > 0 ? Math.ceil(items.length / LIST_PAGE_SIZE) : 0,
          };
        } else {
          const cachedFullItems = fullResultsCacheRef.current.get(resultCacheKey);
          if (cachedFullItems) {
            nextResult = paginateDiscoveryEvents(cachedFullItems, params.page);
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
                items: applyShowPastFilter(res.items, params.showPast),
                total: res.total,
                totalPages: res.total_pages,
              };
              pagedResultsCacheRef.current.set(pageCacheKey, nextResult);

              void getFullDiscoveryEvents(
                resultCacheKey,
                query,
                params.categoryIds,
                params.showPast,
                activePersonalFilter,
              ).catch(() => undefined);
            } else {
              const items = await getFullDiscoveryEvents(
                resultCacheKey,
                query,
                params.categoryIds,
                params.showPast,
                activePersonalFilter,
              );
              nextResult = paginateDiscoveryEvents(items, params.page);
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
      } catch (err: unknown) {
        if (cancelled) return;
        setEvents([]);
        setTotal(0);
        setTotalPages(1);
        setErrorMessage(
          err instanceof Error
            ? err.message
            : "Couldn't load events. Please try again.",
        );
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
    params.search,
    params.temporal,
    activePersonalFilter,
    params.page,
    params.view,
    params.showPast,
    params.sort,
    categoryIdsKey,
    a11yKey,
    geoKey,
    distanceMode,
    refreshTick,
  ]);

  // ── Fetch counts WITHOUT category filter (stable across category selection) ────
  useEffect(() => {
    let cancelled = false;

    if (distanceMode && geoState.status === "pending") {
      return;
    }

    const baseQuery = buildDiscoveryQuery(params, geoState);
    delete baseQuery.sort;
    fetchAllEvents(baseQuery)
      .then((items) => {
        if (cancelled) return;
        const counts: Record<string, number> = {};
        const filteredItems = applyPersonalFilter(
          applyShowPastFilter(items, params.showPast),
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
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    params.search,
    params.temporal,
    activePersonalFilter,
    params.showPast,
    a11yKey,
    geoKey,
    distanceMode,
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
  const activeFilterCount = countActiveFilters(draftFilters);

  // ── Search debounce ────────────────────────────────────────────────────────────

  const [searchDraft, setSearchDraft] = useState(params.search);
  const lastSyncedSearchRef = useRef(params.search);
  useEffect(() => {
    if (params.search !== lastSyncedSearchRef.current && params.search !== searchDraft) {
      setSearchDraft(params.search);
    }
    lastSyncedSearchRef.current = params.search;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.search]);

  useEffect(() => {
    if (searchDraft === params.search) return;
    const t = setTimeout(() => {
      replaceParams({ search: searchDraft, resetPage: true });
    }, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(t);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchDraft]);

  // ── Handlers ───────────────────────────────────────────────────────────────────

  function handleViewChange(view: ViewMode) {
    setMobileFiltersOpen(false);
    pushParams({ view });
  }
  function handleSearchSubmit(v: string) {
    setSearchDraft(v);
    pushParams({ search: v, resetPage: true });
  }
  function handleSearchChange(v: string) {
    setSearchDraft(v);
  }
  function handleFiltersChange(f: FilterState) { setDraftFilters(f); }

  function applyDraftFilters(draft: FilterState) {
    pushParams({
      temporal: draft.temporal,
      personal: isAuthenticated ? draft.personal : null,
      categoryIds: draft.categoryIds,
      showPast: draft.showPast,
      sort: draft.sort,
      accessibility: draft.accessibility,
      resetPage: true,
    });
  }

  function handleApplyFilters() {
    setMobileFiltersOpen(false);
    applyDraftFilters(draftFilters);
  }

  function handleMobileClose() {
    setMobileFiltersOpen(false);
    // Issue #156: closing the bottom sheet must update results immediately.
    applyDraftFilters(draftFilters);
  }

  function handleClearFilters() {
    setDraftFilters({ ...DEFAULT_FILTER_STATE });
    setMobileFiltersOpen(false);
    pushParams({
      temporal: null,
      personal: null,
      categoryIds: [],
      showPast: false,
      sort: "start_time",
      accessibility: {},
      resetPage: true,
    });
  }

  function handlePageChange(page: number) {
    pushParams({ page });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function handleRetry() {
    fullResultsCacheRef.current.clear();
    pendingFullResultsRef.current.clear();
    pagedResultsCacheRef.current.clear();
    setRefreshTick((tick) => tick + 1);
  }

  // ── Banners ────────────────────────────────────────────────────────────────────

  const showGeoFallbackBanner = distanceMode && geoState.status === "fallback";
  const showGeoDeniedBanner =
    distanceMode && geoState.status === "denied" && !bannerDismissed;

  // ── Render ─────────────────────────────────────────────────────────────────────

  return (
    <div className="bg-brand-bg flex h-dvh flex-col overflow-hidden">
      <Navbar
        searchValue={searchDraft}
        onSearchChange={handleSearchChange}
        onSearchSubmit={handleSearchSubmit}
      />

      <ActionBar
        view={params.view}
        onViewChange={handleViewChange}
        activeFilterCount={activeFilterCount}
        onToggleFilters={() => setMobileFiltersOpen(true)}
      />

      {(showGeoDeniedBanner || showGeoFallbackBanner || errorMessage) && (
        <div className="border-brand-mid-alpha flex flex-col gap-2 border-b bg-amber-50/70 px-4 py-2 sm:px-6 lg:px-8">
          {showGeoDeniedBanner && (
            <div
              role="alert"
              className="flex items-start gap-2 text-sm text-amber-800"
            >
              <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden />
              <span className="flex-1">
                We couldn&apos;t access your location, so distance sorting was reset.
                Allow location access in your browser, or sign in and set a default
                area in your profile.
              </span>
              <button
                type="button"
                onClick={() => setBannerDismissed(true)}
                aria-label="Dismiss notice"
                className="text-amber-800/70 hover:text-amber-900"
              >
                <XIcon className="size-4" />
              </button>
            </div>
          )}
          {showGeoFallbackBanner && (
            <div
              role="status"
              className="flex items-center gap-2 text-sm text-brand-dark"
            >
              <AlertTriangle className="size-4 shrink-0" aria-hidden />
              Using your saved default area for distance sorting.
            </div>
          )}
          {errorMessage && (
            <div role="alert" className="flex items-center gap-2 text-sm text-red-700">
              <AlertTriangle className="size-4 shrink-0" aria-hidden />
              <span className="flex-1">Couldn&apos;t load events. {errorMessage}</span>
              <button
                type="button"
                onClick={handleRetry}
                className="rounded-md border border-red-300 bg-white px-2 py-1 text-xs font-bold text-red-700 hover:bg-red-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-400 focus-visible:ring-offset-1"
              >
                Retry
              </button>
            </div>
          )}
        </div>
      )}

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
          onMobileClose={handleMobileClose}
        />

        <main
          className={cn(
            "flex min-h-0 flex-1 flex-col",
            loading && params.view === "list" ? "overflow-hidden" : "overflow-y-auto",
          )}
        >
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
