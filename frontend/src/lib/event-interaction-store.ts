/**
 * Shared in-memory store for per-event bookmark & going state.
 * Both EventCard and EventDetailPage read/write from the same store,
 * so toggling "Going" on the card is immediately reflected on the detail page.
 */

type Listener = () => void;

export interface EventInteraction {
  bookmarked: boolean;
  bookmarkCount: number;
  going: boolean;
  goingCount: number;
}

const store = new Map<string, EventInteraction>();
const listeners = new Set<Listener>();

function notify() {
  listeners.forEach((fn) => fn());
}

export function getInteraction(eventId: string): EventInteraction | undefined {
  return store.get(eventId);
}

/** Initialize only if not already in the store (first mount wins). */
export function initInteraction(eventId: string, data: EventInteraction) {
  if (!store.has(eventId)) {
    store.set(eventId, data);
  }
}

/** Overwrite with fresh server data (e.g. after enrichEventsWithAttendance). */
export function refreshInteraction(eventId: string, data: EventInteraction) {
  store.set(eventId, data);
  notify();
}

export function setBookmarked(eventId: string, value: boolean) {
  const cur = store.get(eventId);
  if (!cur) return;
  const delta = value && !cur.bookmarked ? 1 : !value && cur.bookmarked ? -1 : 0;
  store.set(eventId, {
    ...cur,
    bookmarked: value,
    bookmarkCount: Math.max(0, cur.bookmarkCount + delta),
  });
  notify();
}

export function setGoing(eventId: string, value: boolean) {
  const cur = store.get(eventId);
  if (!cur) return;
  const delta = value && !cur.going ? 1 : !value && cur.going ? -1 : 0;
  store.set(eventId, {
    ...cur,
    going: value,
    goingCount: Math.max(0, cur.goingCount + delta),
  });
  notify();
}

export function subscribe(listener: Listener): () => void {
  listeners.add(listener);
  return () => { listeners.delete(listener); };
}
