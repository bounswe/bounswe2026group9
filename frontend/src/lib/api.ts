import {
  type AuthResponse,
  type AuthUser,
  getSessionState,
  setAuthenticatedSession,
  setGuestSession,
} from "@/lib/session";

const DEFAULT_API_BASE_URL = "http://localhost:8888";
const JSON_CONTENT_TYPE = "application/json";

type ApiAuthMode = "none" | "optional" | "required";
type ApiParseMode = "json" | "text" | "void";

type JsonBody = object;

interface ApiRequestOptions extends Omit<RequestInit, "body"> {
  auth?: ApiAuthMode;
  body?: BodyInit | JsonBody | null;
  parseAs?: ApiParseMode;
  redirectOnAuthFailure?: boolean;
  retryOnAuthFailure?: boolean;
}

export interface HealthResponse {
  database: string;
  status: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  date_of_birth: string;
  email: string;
  password: string;
  username: string;
}

export interface CategoryOption {
  id: string;
  is_approved: boolean;
  is_predefined: boolean;
  name: string;
}

export type ProfileVisibility = "private" | "public";

export interface EventLocationPayload {
  is_primary: boolean;
  latitude: number;
  longitude: number;
  name: string;
  order_index: number;
  /** Optional human-readable address (issue #295 — populated by mobile via Nominatim). */
  location_address?: string | null;
}

/**
 * Itinerary segment (issue #149 / #157).
 *
 * `location_index` references a position in the request's `locations[]` array
 * because at create-time the client doesn't yet know the server-assigned UUID.
 * The backend resolves it positionally inside the atomic create RPC.
 */
export interface SegmentPayload {
  location_index: number;
  order_index: number;
  start_datetime: string;
  end_datetime: string;
  description?: string | null;
}

export interface SegmentResponse {
  id: string;
  location_id: string;
  order_index: number;
  start_datetime: string;
  end_datetime: string;
  description: string | null;
}

export interface VenueMetadataPayload {
  accessible_restroom: boolean;
  captions_support: boolean;
  elevator_available: boolean;
  health_requirements: string | null;
  language: string | null;
  price: string | null;
  quiet_friendly: boolean;
  seating_available: boolean;
  wheelchair_access: boolean;
}

export interface EquipmentRequirementPayload {
  is_required: boolean;
  item_name: string;
}

export interface EventImage {
  id: string;
  image_url: string;
  upload_date: string;
}

export interface BookmarkEventLocation {
  id: string;
  is_primary: boolean;
  latitude: number;
  longitude: number;
  name: string;
  order_index: number;
}

export interface BookmarkedEventSummary {
  id: string;
  title: string;
  start_datetime: string;
  end_datetime: string;
  visibility: "public" | "private";
  is_age_restricted: boolean;
  status: "cancelled" | "draft" | "ended" | "published" | "updated";
  categories: CategoryOption[];
  primary_location: BookmarkEventLocation | null;
  primary_image_url: string | null;
  bookmarked_at: string;
}

export interface BookmarkListResponse {
  items: BookmarkedEventSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface HostedEventSummary {
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
  status: "cancelled" | "draft" | "ended" | "published" | "updated";
  categories: CategoryOption[];
  primary_location: BookmarkEventLocation | null;
  primary_image_url: string | null;
}

export interface HostProfileSummaryResponse {
  id: string;
  username: string;
  email: string | null;
  phone_number: string | null;
  average_rating: number | null;
  hosted_events_count: number;
  hosted_events: HostedEventSummary[];
}

export interface ProfileUpdatePayload {
  date_of_birth?: string;
  email_visibility?: ProfileVisibility;
  phone_number?: string;
  phone_visibility?: ProfileVisibility;
}

export interface EventCreatePayload {
  category_ids: string[];
  description: string;
  end_datetime: string;
  equipment_requirements?: EquipmentRequirementPayload[] | null;
  attendee_limit?: number | null;
  is_age_restricted?: boolean;
  locations: EventLocationPayload[];
  segments?: SegmentPayload[] | null;
  start_datetime: string;
  status: "draft" | "published";
  title: string;
  venue_metadata?: VenueMetadataPayload | null;
  visibility: "public" | "private";
}

export interface EventUpdatePayload {
  attendee_limit?: number | null;
  category_ids?: string[];
  clear_attendee_limit?: boolean;
  description?: string;
  end_datetime?: string;
  equipment_requirements?: EquipmentRequirementPayload[] | null;
  is_age_restricted?: boolean;
  locations?: EventLocationPayload[];
  segments?: SegmentPayload[] | null;
  start_datetime?: string;
  title?: string;
  venue_metadata?: VenueMetadataPayload | null;
  visibility?: "public" | "private";
}

export interface EventStatusChangePayload {
  status: "cancelled" | "ended" | "published";
}

export interface EventDetailResponse {
  attendee_count: number;
  attendee_limit: number | null;
  attendance_status: string | null;
  categories: CategoryOption[];
  created_at: string;
  description: string;
  end_datetime: string;
  equipment_requirements: Array<
    EquipmentRequirementPayload & {
      id: string;
    }
  >;
  going_count: number;
  host_id: string;
  id: string;
  images: EventImage[];
  bookmark_count: number;
  is_age_restricted: boolean;
  is_bookmarked: boolean | null;
  is_full: boolean | null;
  locations: Array<
    EventLocationPayload & {
      id: string;
    }
  >;
  segments?: SegmentResponse[];
  start_datetime: string;
  status: "cancelled" | "draft" | "ended" | "published" | "updated";
  title: string;
  updated_at: string;
  venue_metadata: (VenueMetadataPayload & { id: string }) | null;
  visibility: "public" | "private";
}

export interface EventLimitedResponse {
  categories: CategoryOption[];
  end_datetime: string;
  id: string;
  is_age_restricted: boolean;
  is_bookmarked: boolean | null;
  start_datetime: string;
  status: "cancelled" | "draft" | "ended" | "published" | "updated";
  title: string;
  visibility: "public" | "private";
}

export class ApiError extends Error {
  body: unknown;
  status: number;

  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.name = "ApiError";
    this.body = body;
    this.status = status;
  }
}

let refreshRequest: Promise<AuthResponse> | null = null;
let authRedirectSuppressed = false;

function getApiBaseUrl() {
  if (typeof window !== "undefined" && process.env.NEXT_PUBLIC_API_BASE_URL) {
    // In the browser, use the Next.js rewrite proxy to avoid CORS issues
    return "/api/proxy";
  }
  return process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/+$/, "") ?? DEFAULT_API_BASE_URL;
}

function buildApiUrl(path: string) {
  return `${getApiBaseUrl()}${path.startsWith("/") ? path : `/${path}`}`;
}

function isJsonBody(value: BodyInit | JsonBody | null): value is JsonBody {
  if (!value || typeof value !== "object") {
    return false;
  }

  return (
    !(value instanceof FormData) &&
    !(value instanceof URLSearchParams) &&
    !(value instanceof Blob) &&
    !(value instanceof ArrayBuffer) &&
    !(value instanceof ReadableStream)
  );
}

function prepareRequestBody(headers: Headers, body: BodyInit | JsonBody | null | undefined) {
  if (body == null) {
    return undefined;
  }

  if (!isJsonBody(body)) {
    return body;
  }

  headers.set("Content-Type", JSON_CONTENT_TYPE);
  return JSON.stringify(body);
}

async function parseResponseBody(response: Response) {
  if (response.status === 204 || response.status === 205) {
    return null;
  }

  const contentType = response.headers.get("content-type") ?? "";

  if (contentType.includes(JSON_CONTENT_TYPE)) {
    return (await response.json()) as unknown;
  }

  const text = await response.text();
  return text || null;
}

function getApiErrorMessage(status: number, body: unknown, fallbackMessage: string) {
  if (typeof body === "string" && body.trim()) {
    return body;
  }

  if (body && typeof body === "object") {
    if ("detail" in body && typeof body.detail === "string" && body.detail.trim()) {
      return body.detail;
    }

    if ("message" in body && typeof body.message === "string" && body.message.trim()) {
      return body.message;
    }
  }

  return fallbackMessage || `Request failed with status ${status}`;
}

function buildLoginUrl(reason: string) {
  if (typeof window === "undefined") {
    return "/login";
  }

  const nextPath = `${window.location.pathname}${window.location.search}`;
  const url = new URL("/login", window.location.origin);
  url.searchParams.set("reason", reason);

  if (nextPath !== "/login" && nextPath !== "/auth/callback") {
    url.searchParams.set("next", nextPath);
  }

  return url.toString();
}

function redirectToLogin(reason: string) {
  if (authRedirectSuppressed) {
    return;
  }

  if (typeof window === "undefined") {
    return;
  }

  if (window.location.pathname === "/login" || window.location.pathname === "/auth/callback") {
    return;
  }

  window.location.assign(buildLoginUrl(reason));
}

export function setAuthRedirectSuppressed(suppressed: boolean) {
  authRedirectSuppressed = suppressed;
}

async function sendRequest(
  path: string,
  { auth = "none", body, headers: providedHeaders, ...init }: ApiRequestOptions = {},
) {
  const headers = new Headers(providedHeaders);
  headers.set("Accept", JSON_CONTENT_TYPE);

  const accessToken = getSessionState().accessToken;
  if ((auth === "required" || auth === "optional") && accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  return fetch(buildApiUrl(path), {
    ...init,
    body: prepareRequestBody(headers, body),
    cache: "no-store",
    credentials: "include",
    headers,
  });
}

async function parseApiResponse<T>(response: Response, parseAs: ApiParseMode = "json") {
  const body = await parseResponseBody(response);

  if (!response.ok) {
    throw new ApiError(
      getApiErrorMessage(response.status, body, response.statusText),
      response.status,
      body,
    );
  }

  if (parseAs === "void") {
    return undefined as T;
  }

  if (parseAs === "text") {
    return (typeof body === "string" ? body : JSON.stringify(body)) as T;
  }

  return body as T;
}

async function performRefresh() {
  const response = await sendRequest("/auth/refresh", {
    method: "POST",
  });
  return parseApiResponse<AuthResponse>(response);
}

export async function refreshSession({
  redirectOnFailure = false,
}: {
  redirectOnFailure?: boolean;
} = {}) {
  refreshRequest ??= performRefresh().finally(() => {
    refreshRequest = null;
  });

  try {
    const auth = await refreshRequest;
    setAuthenticatedSession(auth);
    return auth;
  } catch (error) {
    setGuestSession();

    if (redirectOnFailure) {
      redirectToLogin("session-expired");
    }

    throw error;
  }
}

export async function apiRequest<T>(
  path: string,
  {
    auth = "none",
    parseAs = "json",
    redirectOnAuthFailure = auth === "required",
    retryOnAuthFailure = auth === "required",
    ...options
  }: ApiRequestOptions = {},
) {
  const response = await sendRequest(path, {
    ...options,
    auth,
  });

  // Required auth: try refresh then retry
  if (response.status === 401 && auth === "required" && retryOnAuthFailure) {
    await refreshSession({ redirectOnFailure: redirectOnAuthFailure });
    const retriedResponse = await sendRequest(path, { ...options, auth });
    return parseApiResponse<T>(retriedResponse, parseAs);
  }

  // Optional auth: token may be stale → try refresh first, then fall back to guest
  if (response.status === 401 && auth === "optional") {
    try {
      await refreshSession();
      const retriedResponse = await sendRequest(path, { ...options, auth });
      return parseApiResponse<T>(retriedResponse, parseAs);
    } catch {
      // Refresh failed (e.g. localhost cookie issue) — fall back to guest
      const guestResponse = await sendRequest(path, { ...options, auth: "none" });
      return parseApiResponse<T>(guestResponse, parseAs);
    }
  }

  return parseApiResponse<T>(response, parseAs);
}

export async function login(payload: LoginPayload) {
  const response = await apiRequest<AuthResponse>("/auth/login", {
    auth: "none",
    body: payload,
    method: "POST",
  });

  setAuthenticatedSession(response);
  return response;
}

export async function register(payload: RegisterPayload) {
  const response = await apiRequest<AuthResponse>("/auth/register", {
    auth: "none",
    body: payload,
    method: "POST",
  });

  setAuthenticatedSession(response);
  return response;
}

export async function logout() {
  try {
    await apiRequest("/auth/logout", {
      auth: "none",
      method: "POST",
      parseAs: "void",
      retryOnAuthFailure: false,
    });
  } finally {
    setGuestSession();
  }
}

export function getGoogleLoginUrl(mode: "login" | "signup" = "login") {
  // Google OAuth requires a full URL redirect to the backend, not the proxy
  const backendBase =
    process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/+$/, "") ?? DEFAULT_API_BASE_URL;
  return `${backendBase}/auth/google?mode=${mode}`;
}

export function getLoginRedirectUrl(reason: string) {
  return buildLoginUrl(reason);
}

export function getBackendBaseUrl() {
  return getApiBaseUrl();
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

export function getErrorMessage(error: unknown, fallbackMessage: string) {
  if (error instanceof ApiError) {
    return error.message;
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallbackMessage;
}

export async function getBackendHealth() {
  return apiRequest<HealthResponse>("/health");
}

export async function getCurrentUser() {
  return apiRequest<AuthUser>("/auth/me", {
    auth: "required",
  });
}

export async function updateMyProfile(payload: ProfileUpdatePayload) {
  return apiRequest<AuthUser>("/users/me", {
    auth: "required",
    body: payload,
    method: "PUT",
  });
}

export async function getHostProfileSummary(userId: string) {
  return apiRequest<HostProfileSummaryResponse>(`/users/${userId}/profile`, {
    auth: "required",
  });
}

export async function getMyBookmarks({
  page = 1,
  pageSize = 6,
}: {
  page?: number;
  pageSize?: number;
} = {}) {
  const query = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });

  return apiRequest<BookmarkListResponse>(`/users/me/bookmarks?${query.toString()}`, {
    auth: "required",
  });
}

export async function getCategories(search?: string) {
  const query = search ? `?search=${encodeURIComponent(search)}` : "";
  return apiRequest<CategoryOption[]>(`/categories${query}`);
}

export async function createEvent(payload: EventCreatePayload) {
  return apiRequest<EventDetailResponse>("/events", {
    auth: "required",
    body: payload,
    method: "POST",
  });
}

export async function getEvent(eventId: string) {
  return apiRequest<EventDetailResponse | EventLimitedResponse>(`/events/${eventId}`, {
    auth: "required",
  });
}

export async function updateEvent(eventId: string, payload: EventUpdatePayload) {
  return apiRequest<EventDetailResponse>(`/events/${eventId}`, {
    auth: "required",
    body: payload,
    method: "PUT",
  });
}

export async function changeEventStatus(eventId: string, payload: EventStatusChangePayload) {
  return apiRequest<EventDetailResponse>(`/events/${eventId}/status`, {
    auth: "required",
    body: payload,
    method: "PATCH",
  });
}

export async function uploadEventImage(eventId: string, file: File) {
  const formData = new FormData();
  formData.append("file", file);

  return apiRequest<EventImage>(`/events/${eventId}/images`, {
    auth: "required",
    body: formData,
    method: "POST",
  });
}

export async function deleteEventImage(eventId: string, imageId: string) {
  return apiRequest<void>(`/events/${eventId}/images/${imageId}`, {
    auth: "required",
    method: "DELETE",
    parseAs: "void",
  });
}
