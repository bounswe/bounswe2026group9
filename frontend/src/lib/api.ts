import {
  type AuthResponse,
  type AuthUser,
  getSessionState,
  setAuthenticatedSession,
  setGuestSession,
} from "@/lib/session";

const DEFAULT_API_BASE_URL = "http://localhost:8888";
const JSON_CONTENT_TYPE = "application/json";

type ApiAuthMode = "none" | "required";
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

function getApiBaseUrl() {
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
  if (typeof window === "undefined") {
    return;
  }

  if (window.location.pathname === "/login" || window.location.pathname === "/auth/callback") {
    return;
  }

  window.location.assign(buildLoginUrl(reason));
}

async function sendRequest(
  path: string,
  { auth = "none", body, headers: providedHeaders, ...init }: ApiRequestOptions = {},
) {
  const headers = new Headers(providedHeaders);
  headers.set("Accept", JSON_CONTENT_TYPE);

  const accessToken = getSessionState().accessToken;
  if (auth === "required" && accessToken) {
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

  if (response.status !== 401 || auth !== "required" || !retryOnAuthFailure) {
    return parseApiResponse<T>(response, parseAs);
  }

  await refreshSession({ redirectOnFailure: redirectOnAuthFailure });

  const retriedResponse = await sendRequest(path, {
    ...options,
    auth,
  });

  return parseApiResponse<T>(retriedResponse, parseAs);
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
  const url = new URL(buildApiUrl("/auth/google"));
  url.searchParams.set("mode", mode);
  return url.toString();
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
