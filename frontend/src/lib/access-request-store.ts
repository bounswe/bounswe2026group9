/**
 * Persists access request "pending" state in localStorage so it survives
 * page navigation and refreshes, and is shared between the event card and
 * the private event detail page.
 */

const KEY = "pending_access_requests";

function getSet(): Set<string> {
  if (typeof window === "undefined") return new Set();
  try {
    const raw = localStorage.getItem(KEY);
    return new Set(raw ? (JSON.parse(raw) as string[]) : []);
  } catch {
    return new Set();
  }
}

function saveSet(s: Set<string>) {
  try {
    localStorage.setItem(KEY, JSON.stringify([...s]));
  } catch {
    // ignore quota errors
  }
}

export function markAccessRequestPending(eventId: string) {
  const s = getSet();
  s.add(eventId);
  saveSet(s);
}

export function isAccessRequestPending(eventId: string): boolean {
  return getSet().has(eventId);
}

export function clearAccessRequestPending(eventId: string) {
  const s = getSet();
  s.delete(eventId);
  saveSet(s);
}
