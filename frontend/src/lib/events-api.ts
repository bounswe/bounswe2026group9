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
  host_id: string;
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
  attendance_status: string | null;
  access_request_status: "pending" | "approved" | "rejected" | null;
  has_access: boolean | null;
  going_count: number;
  bookmark_count: number;
  is_full: boolean | null;
  categories: Category[];
  primary_location: EventLocation | null;
  primary_image_url: string | null;
}

export type AttendanceStatus = "going" | null;
export type PersonalFilter = "bookmarked" | "going";

export interface EventListResponse {
  items: EventListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  /**
   * Set by the backend when ?suggested=true was requested but the user has no
   * past attendance history to bias on. UI should render an "attend events to
   * get personalised suggestions" hint and fall back to the default listing.
   */
  suggested_fallback?: boolean;
}

export type TemporalFilter = "today" | "this_week" | "weekend";

export interface DiscoveryParams {
  search?: string;
  category_id?: string;
  temporal_filter?: "today" | "this_week";
  /**
   * Bias the listing toward categories the authenticated user attended on past
   * ended events. Silently ignored for guests by the backend. When the user
   * has no attendance history the response sets `suggested_fallback=true`.
   */
  suggested?: boolean;
  page?: number;
  page_size?: number;
}

export interface AllEventsResult {
  items: EventListItem[];
  suggested_fallback: boolean;
}

// ─── API Functions ─────────────────────────────────────────────────────────────

export async function fetchEvents(params: DiscoveryParams = {}): Promise<EventListResponse> {
  const query = new URLSearchParams();

  if (params.search?.trim()) query.set("search", params.search.trim());
  if (params.category_id) query.set("category_id", params.category_id);
  if (params.temporal_filter) query.set("temporal_filter", params.temporal_filter);
  if (params.suggested) query.set("suggested", "true");
  if (params.page && params.page > 1) query.set("page", String(params.page));
  if (params.page_size) query.set("page_size", String(params.page_size));

  const qs = query.toString();
  return apiRequest<EventListResponse>(`/events${qs ? `?${qs}` : ""}`, { auth: "optional" });
}

export async function fetchAllEvents(params: DiscoveryParams = {}): Promise<AllEventsResult> {
  const pageSize = 100;
  const firstPage = await fetchEvents({ ...params, page: 1, page_size: pageSize });
  const suggested_fallback = firstPage.suggested_fallback ?? false;

  if (firstPage.total_pages <= 1) {
    return { items: firstPage.items, suggested_fallback };
  }

  const remainingPages = await Promise.all(
    Array.from({ length: firstPage.total_pages - 1 }, (_, index) =>
      fetchEvents({ ...params, page: index + 2, page_size: pageSize }),
    ),
  );

  const items = [firstPage, ...remainingPages].flatMap((page) => page.items);
  return { items, suggested_fallback };
}

export async function fetchCategories(): Promise<Category[]> {
  return apiRequest<Category[]>("/categories");
}

// ─── GeoJSON Types ─────────────────────────────────────────────────────────────

export interface GeoJSONPoint {
  type: "Point";
  coordinates: [number, number];
}

export interface EventGeoJSONProperties {
  id: string;
  host_id: string;
  title: string;
  start_datetime: string;
  status: string;
  visibility: string;
  primary_category: string | null;
  attendee_count: number;
  attendee_limit: number | null;
  is_bookmarked: boolean | null;
  attendance_status: string | null;
  going_count: number;
  bookmark_count: number;
  primary_image_url: string | null;
}

export interface GeoJSONFeature {
  type: "Feature";
  geometry: GeoJSONPoint;
  properties: EventGeoJSONProperties;
}

export interface GeoJSONFeatureCollection {
  type: "FeatureCollection";
  features: GeoJSONFeature[];
}

export async function fetchGeoJsonEvents(params: DiscoveryParams = {}): Promise<GeoJSONFeatureCollection> {
  const query = new URLSearchParams();

  if (params.search?.trim()) query.set("search", params.search.trim());
  if (params.category_id) query.set("category_id", params.category_id);
  if (params.temporal_filter) query.set("temporal_filter", params.temporal_filter);
  if (params.suggested) query.set("suggested", "true");

  const qs = query.toString();
  return apiRequest<GeoJSONFeatureCollection>(`/events/geojson${qs ? `?${qs}` : ""}`, { auth: "optional" });
}

// ─── Event Detail Types ────────────────────────────────────────────────────────

export interface EventImage {
  id: string;
  image_url: string;
  upload_date: string;
}

export interface VenueMetadata {
  id: string;
  price: string | null;
  language: string | null;
  health_requirements: string | null;
  wheelchair_access: boolean;
  accessible_restroom: boolean;
  elevator_available: boolean;
  seating_available: boolean;
  captions_support: boolean;
  quiet_friendly: boolean;
}

export interface EquipmentRequirement {
  id: string;
  item_name: string;
  is_required: boolean;
}

/** Full event detail — returned for authenticated users with access */
export interface EventDetail {
  id: string;
  host_id: string;
  title: string;
  description: string;
  start_datetime: string;
  end_datetime: string;
  visibility: "public" | "private";
  is_age_restricted: boolean;
  attendee_limit: number | null;
  attendee_count: number;
  status: "draft" | "published" | "updated" | "cancelled" | "ended";
  created_at: string;
  updated_at: string;
  is_bookmarked: boolean | null;
  attendance_status: string | null;
  access_request_status: "pending" | "approved" | "rejected" | null;
  going_count: number;
  bookmark_count: number;
  is_full: boolean | null;
  locations: EventLocation[];
  categories: Category[];
  images: EventImage[];
  venue_metadata: VenueMetadata | null;
  equipment_requirements: EquipmentRequirement[];
  attendees: { id: string; username: string }[];
  /** Discriminant — always present on full response */
  _type: "full";
}

/** Limited preview — returned for guests and non-host on private events */
export interface EventDetailLimited {
  id: string;
  title: string;
  start_datetime: string;
  end_datetime: string;
  visibility: "public" | "private";
  is_age_restricted: boolean;
  status: "draft" | "published" | "updated" | "cancelled" | "ended";
  is_bookmarked: boolean | null;
  access_request_status: "pending" | "approved" | "rejected" | null;
  categories: Category[];
  _type: "limited";
}

export type AnyEventDetail = EventDetail | EventDetailLimited;

export interface CommentAuthor {
  id: string;
  username: string;
}

export interface Comment {
  id: string;
  event_id: string;
  user: CommentAuthor;
  text: string;
  created_at: string;
  parent_id: string | null;
  replies: Comment[];
}

export interface CommentListResponse {
  items: Comment[];
  total: number;
}

export interface HostProfile {
  id: string;
  username: string;
  email: string | null;
  phone_number: string | null;
  average_rating: number | null;
  hosted_events_count: number;
  hosted_events: EventListItem[];
  can_rate: boolean;
}

// ─── Event Detail API Functions ────────────────────────────────────────────────

export async function fetchEventDetail(id: string): Promise<AnyEventDetail> {
  // auth: "optional" — sends token when available so authenticated users get full details
  const raw = await apiRequest<Record<string, unknown>>(`/events/${id}`, { auth: "optional" });
  // Full response has host_id; limited response (private event for non-host/guest) does not
  const isFullResponse = "host_id" in raw && typeof raw.host_id === "string";
  if (isFullResponse) {
    return { ...(raw as unknown as Omit<EventDetail, "_type">), _type: "full" };
  }
  return { ...(raw as unknown as Omit<EventDetailLimited, "_type">), _type: "limited" };
}

export async function setAttendance(
  eventId: string,
  status: "going",
): Promise<void> {
  await apiRequest(`/events/${eventId}/attendance`, {
    method: "POST",
    auth: "required",
    body: { status },
  });
}

export async function removeAttendance(eventId: string): Promise<void> {
  await apiRequest(`/events/${eventId}/attendance`, { 
    method: "DELETE",
    auth: "required",
  });
}

export async function addBookmark(eventId: string): Promise<void> {
  await apiRequest(`/events/${eventId}/bookmark`, { 
    method: "POST",
    auth: "required",
  });
}

export async function removeBookmark(eventId: string): Promise<void> {
  await apiRequest(`/events/${eventId}/bookmark`, { 
    method: "DELETE",
    auth: "required",
  });
}

export async function changeEventStatus(
  eventId: string,
  status: "published" | "cancelled" | "ended",
): Promise<void> {
  await apiRequest(`/events/${eventId}/status`, {
    method: "PATCH",
    auth: "required",
    body: { status },
  });
}

export async function deleteEvent(eventId: string): Promise<void> {
  await apiRequest(`/events/${eventId}`, { 
    method: "DELETE",
    auth: "required",
  });
}

export async function fetchComments(eventId: string): Promise<CommentListResponse> {
  return apiRequest<CommentListResponse>(`/events/${eventId}/comments`);
}

export async function postComment(
  eventId: string,
  content: string,
  parentId?: string,
): Promise<Comment> {
  const body: Record<string, string> = { text: content };
  if (parentId) body.parent_id = parentId;
  return apiRequest<Comment>(`/events/${eventId}/comments`, {
    method: "POST",
    auth: "required",
    body,
  });
}

export async function deleteComment(eventId: string, commentId: string): Promise<void> {
  await apiRequest(`/events/${eventId}/comments/${commentId}`, { 
    method: "DELETE",
    auth: "required",
  });
}

export async function fetchHostProfile(userId: string): Promise<HostProfile> {
  return apiRequest<HostProfile>(`/users/${userId}/profile`, { auth: "optional" });
}

export async function rateHost(userId: string, score: number): Promise<void> {
  await apiRequest<void>(`/users/${userId}/ratings`, {
    method: "POST",
    auth: "required",
    body: { score },
    parseAs: "void",
  });
}

// ─── Notification Types ──────────────────────────────────────────────────────

export interface Notification {
  id: string;
  user_id: string;
  event_id: string | null;
  type: string;
  message: string;
  is_read: boolean;
  created_at: string;
}

export interface NotificationListResponse {
  items: Notification[];
  total: number;
  unread_count: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface NotificationReadResponse {
  id: string;
  is_read: boolean;
}

export interface NotificationReadAllResponse {
  updated_count: number;
}

// ─── Notification API Functions ──────────────────────────────────────────────

export async function fetchNotifications(
  page = 1,
  pageSize = 20,
): Promise<NotificationListResponse> {
  return apiRequest<NotificationListResponse>(
    `/notifications?page=${page}&page_size=${pageSize}`,
    { auth: "required" },
  );
}

export async function markNotificationRead(
  notificationId: string,
): Promise<NotificationReadResponse> {
  return apiRequest<NotificationReadResponse>(
    `/notifications/${notificationId}/read`,
    { method: "PATCH", auth: "required" },
  );
}

export async function markAllNotificationsRead(): Promise<NotificationReadAllResponse> {
  return apiRequest<NotificationReadAllResponse>(
    `/notifications/read-all`,
    { method: "PATCH", auth: "required" },
  );
}

export async function fetchUnreadNotificationCount(): Promise<number> {
  // Fetch first page; use server-provided unread_count if available,
  // otherwise count from the items array (works with older backends).
  const res = await fetchNotifications(1, 50);
  return res.unread_count ?? res.items.filter((n) => !n.is_read).length;
}

// ─── Access Request Types & API ─────────────────────────────────────────────

export interface AccessRequest {
  id: string;
  user_id: string;
  username: string;
  status: "pending" | "approved" | "rejected";
  created_at: string;
}

export interface AccessRequestListResponse {
  items: AccessRequest[];
}

export async function requestAccess(eventId: string): Promise<void> {
  await apiRequest(`/events/${eventId}/access-requests`, {
    method: "POST",
    auth: "required",
  });
}

export async function fetchAccessRequests(eventId: string): Promise<AccessRequest[]> {
  const res = await apiRequest<AccessRequestListResponse>(
    `/events/${eventId}/access-requests`,
    { auth: "required" },
  );
  return res.items ?? res as unknown as AccessRequest[];
}

export async function updateAccessRequest(
  eventId: string,
  requestId: string,
  action: "approved" | "rejected",
): Promise<void> {
  await apiRequest(`/events/${eventId}/access-requests/${requestId}`, {
    method: "PATCH",
    auth: "required",
    body: { status: action },
  });
}

// ─── Invite Types & API ─────────────────────────────────────────────────────

export interface Invite {
  id: string;
  event_id: string;
  token: string;
  invite_url: string;
  expires_at: string | null;
  max_uses: number | null;
  use_count: number;
  created_at: string;
}

export interface InviteListResponse {
  items: Invite[];
}

export async function createInvite(eventId: string): Promise<Invite> {
  return apiRequest<Invite>(`/events/${eventId}/invites`, {
    method: "POST",
    auth: "required",
    body: {},
  });
}

export async function fetchInvites(eventId: string): Promise<Invite[]> {
  const res = await apiRequest<InviteListResponse>(
    `/events/${eventId}/invites`,
    { auth: "required" },
  );
  return res.items ?? res as unknown as Invite[];
}

export async function acceptInvite(eventId: string, token: string): Promise<void> {
  await apiRequest(`/events/${eventId}/invites/${token}/accept`, {
    method: "POST",
    auth: "required",
  });
}
