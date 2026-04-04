import { useEffect, useState } from "react";
import {
  type EventInteraction,
  getInteraction,
  initInteraction,
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
}

export function useEventInteraction({
  eventId,
  initialBookmarked,
  initialBookmarkCount,
  initialGoing,
  initialGoingCount,
}: UseEventInteractionArgs) {
  // Seed store on first mount
  initInteraction(eventId, {
    bookmarked: initialBookmarked,
    bookmarkCount: Math.max(initialBookmarkCount, initialBookmarked ? 1 : 0),
    going: initialGoing,
    goingCount: Math.max(initialGoingCount, initialGoing ? 1 : 0),
  });

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
