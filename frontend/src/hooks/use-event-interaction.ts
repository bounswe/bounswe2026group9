import { useEffect, useState } from "react";
import {
  type EventInteraction,
  getInteraction,
  initInteraction,
  refreshInteraction,
  setBookmarked as storeSetBookmarked,
  setGoing as storeSetGoing,
  subscribe,
} from "@/lib/event-interaction-store";
import {
  addBookmark,
  removeBookmark,
  setAttendance,
  removeAttendance,
} from "@/lib/events-api";

interface UseEventInteractionArgs {
  eventId: string;
  initialBookmarked: boolean;
  initialBookmarkCount: number;
  initialGoing: boolean;
  initialGoingCount: number;
  /** When true, overwrite any existing store data with these values (use for detail page with fresh server data). */
  fresh?: boolean;
}

export function useEventInteraction({
  eventId,
  initialBookmarked,
  initialBookmarkCount,
  initialGoing,
  initialGoingCount,
  fresh = false,
}: UseEventInteractionArgs) {
  const data = {
    bookmarked: initialBookmarked,
    bookmarkCount: Math.max(initialBookmarkCount, initialBookmarked ? 1 : 0),
    going: initialGoing,
    goingCount: Math.max(initialGoingCount, initialGoing ? 1 : 0),
  };
  // Always init during render (safe — initInteraction never calls notify)
  initInteraction(eventId, data);

  const [, tick] = useState(0);
  useEffect(() => subscribe(() => tick((n) => n + 1)), []);

  // refreshInteraction calls notify() which triggers state updates — must be in useEffect
  useEffect(() => {
    if (fresh) {
      refreshInteraction(eventId, data);
    }
    // data is intentionally excluded from deps: we only want to refresh on eventId change
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eventId, fresh]);

  const state = getInteraction(eventId)!;

  async function toggleBookmark() {
    const prev = state.bookmarked;
    // Optimistic update
    storeSetBookmarked(eventId, !prev);
    try {
      if (prev) {
        await removeBookmark(eventId);
      } else {
        await addBookmark(eventId);
      }
    } catch {
      // Rollback on failure — restore previous state
      storeSetBookmarked(eventId, prev);
    }
  }

  async function toggleGoing() {
    const prev = state.going;
    // Optimistic update
    storeSetGoing(eventId, !prev);
    try {
      if (prev) {
        await removeAttendance(eventId);
      } else {
        await setAttendance(eventId, "going");
      }
    } catch {
      // Rollback on failure — restore previous state
      storeSetGoing(eventId, prev);
    }
  }

  return {
    bookmarked: state.bookmarked,
    bookmarkCount: state.bookmarkCount,
    going: state.going,
    goingCount: state.goingCount,
    toggleBookmark,
    toggleGoing,
  } as const;
}
