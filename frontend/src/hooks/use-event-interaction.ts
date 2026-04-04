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
  // Detail page passes fresh=true to overwrite stale card data with server truth
  if (fresh) {
    refreshInteraction(eventId, data);
  } else {
    initInteraction(eventId, data);
  }

  const [, tick] = useState(0);
  useEffect(() => subscribe(() => tick((n) => n + 1)), []);

  const state = getInteraction(eventId)!;

  async function toggleBookmark() {
    try {
      if (state.bookmarked) {
        await removeBookmark(eventId);
        storeSetBookmarked(eventId, false);
      } else {
        await addBookmark(eventId);
        storeSetBookmarked(eventId, true);
      }
    } catch {
      // 409/404 — flip to sync
      storeSetBookmarked(eventId, !state.bookmarked);
    }
  }

  async function toggleGoing() {
    try {
      if (state.going) {
        await removeAttendance(eventId);
        storeSetGoing(eventId, false);
      } else {
        await setAttendance(eventId, "going");
        storeSetGoing(eventId, true);
      }
    } catch {
      storeSetGoing(eventId, !state.going);
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
