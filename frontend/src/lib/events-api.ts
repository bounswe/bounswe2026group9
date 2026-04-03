import { apiRequest } from "@/lib/api";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface Category {
  id: string;
  name: string;
  is_predefined: boolean;
  is_approved: boolean;
}

export interface EventLocation {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  is_primary: boolean;
  order_index: number;
}

export interface EventListItem {
  id: string;
  title: string;
  description: string | null;
  start_datetime: string;
  end_datetime: string;
  visibility: "public" | "private";
  is_age_restricted: boolean;
  attendee_limit: number | null;
  attendee_count: number;
  status: string;
  is_bookmarked: boolean | null;
  going_count: number;
  interested_count: number;
  is_full: boolean | null;
  categories: Category[];
  primary_location: EventLocation | null;
  primary_image_url: string | null;
}

export interface EventListResponse {
  items: EventListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export type TemporalFilter = "upcoming" | "today" | "this_week";

export interface DiscoveryParams {
  search?: string;
  category_id?: string;
  temporal_filter?: TemporalFilter;
  page?: number;
  page_size?: number;
}

// ─── API Functions ─────────────────────────────────────────────────────────────

export async function fetchEvents(params: DiscoveryParams = {}): Promise<EventListResponse> {
  const query = new URLSearchParams();

  if (params.search?.trim()) query.set("search", params.search.trim());
  if (params.category_id) query.set("category_id", params.category_id);
  if (params.temporal_filter) query.set("temporal_filter", params.temporal_filter);
  if (params.page && params.page > 1) query.set("page", String(params.page));
  if (params.page_size) query.set("page_size", String(params.page_size));

  const qs = query.toString();
  return apiRequest<EventListResponse>(`/events${qs ? `?${qs}` : ""}`);
}

export async function fetchCategories(): Promise<Category[]> {
  return apiRequest<Category[]>("/categories");
}
