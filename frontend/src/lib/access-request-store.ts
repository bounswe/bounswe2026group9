/**
 * Persists access request "pending" state in localStorage so it survives
 * page navigation and refreshes, and is shared between the event card and
 * the private event detail page.
 */

const KEY = "pending_access_requests_by_user";

function getStore(): Record<string, string[]> {
  if (typeof window === "undefined") return {};
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as Record<string, string[]>) : {};
  } catch {
    return {};
  }
}

function saveStore(store: Record<string, string[]>) {
  try {
    localStorage.setItem(KEY, JSON.stringify(store));
  } catch {
    // ignore quota errors
  }
}

function getSetForUser(userId: string | null): Set<string> {
  if (!userId) return new Set();
  return new Set(getStore()[userId] ?? []);
}

function saveSetForUser(userId: string | null, set: Set<string>) {
  if (!userId) return;

  const store = getStore();
  if (set.size === 0) {
    delete store[userId];
  } else {
    store[userId] = [...set];
  }
  saveStore(store);
}

export function markAccessRequestPending(eventId: string, userId: string | null) {
  const set = getSetForUser(userId);
  set.add(eventId);
  saveSetForUser(userId, set);
}

export function isAccessRequestPending(eventId: string, userId: string | null): boolean {
  return getSetForUser(userId).has(eventId);
}

export function clearAccessRequestPending(eventId: string, userId: string | null) {
  const set = getSetForUser(userId);
  set.delete(eventId);
  saveSetForUser(userId, set);
}
