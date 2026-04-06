export type AuthStatus = "loading" | "authenticated" | "guest";

export interface AuthUser {
  id: string;
  username: string;
  email: string;
  phone_number: string | null;
  date_of_birth: string | null;
  email_visibility: boolean;
  phone_visibility?: boolean;
  role: string;
  auth_provider: string;
  email_verified: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

export interface SessionState {
  accessToken: string | null;
  isInitialized: boolean;
  status: AuthStatus;
  user: AuthUser | null;
}

type SessionListener = (state: SessionState) => void;

const initialSessionState: SessionState = {
  accessToken: null,
  isInitialized: false,
  status: "loading",
  user: null,
};

let sessionState: SessionState = initialSessionState;
const listeners = new Set<SessionListener>();

function notifyListeners() {
  for (const listener of listeners) {
    listener(sessionState);
  }
}

function updateSessionState(nextState: SessionState) {
  sessionState = nextState;
  notifyListeners();
}

export function getSessionState() {
  return sessionState;
}

export function subscribeToSession(listener: SessionListener) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function markSessionLoading() {
  updateSessionState({
    ...sessionState,
    status: "loading",
  });
}

export function setAuthenticatedSession(auth: AuthResponse) {
  updateSessionState({
    accessToken: auth.access_token,
    isInitialized: true,
    status: "authenticated",
    user: auth.user,
  });
}

export function setGuestSession() {
  updateSessionState({
    accessToken: null,
    isInitialized: true,
    status: "guest",
    user: null,
  });
}

export function resetSessionState() {
  updateSessionState(initialSessionState);
}
