"use client";

import Link from "next/link";
import { Check, Loader2 } from "lucide-react";

import type { AttendeeStatus } from "@/lib/events-api";
import { getProfileHref } from "@/lib/profile-route";

export interface AttendeeRosterProps {
  attendees: AttendeeStatus[];
  currentUserId: string | null;
  markError: string | null;
  markingId: string | null;
  onMarkIn: (userId: string) => void;
}

function formatCheckInTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

/**
 * Host-facing roster of Going attendees with per-row check-in status.
 * Mirrors mobile's HostAttendeeListScreen (#234): shows "Pending" or
 * "Checked in · {time}" and surfaces a manual "Mark in" button as a
 * fallback when the camera scanner can't be used.
 */
export function AttendeeRoster({
  attendees,
  currentUserId,
  markError,
  markingId,
  onMarkIn,
}: AttendeeRosterProps) {
  const total = attendees.length;
  const checkedIn = attendees.filter((a) => a.checked_in_at !== null).length;

  return (
    <div className="border-brand-mid-alpha rounded-xl border bg-white p-5">
      <div className="mb-4 flex items-center justify-between">
        <p className="text-brand-mid text-[11px] font-bold tracking-widest uppercase">
          Going ({total})
        </p>
        {total > 0 && (
          <p className="text-brand-mid text-[12px] font-semibold">
            <Check className="mr-1 inline size-3.5 text-green-600" />
            {checkedIn} / {total} checked in
          </p>
        )}
      </div>

      {markError && (
        <div
          className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-[12px] font-semibold text-red-600"
          role="alert"
        >
          {markError}
        </div>
      )}

      {total === 0 ? (
        <p className="text-brand-mid text-sm">No attendees yet.</p>
      ) : (
        <ul className="space-y-2">
          {attendees.map((attendee) => {
            const isCheckedIn = attendee.checked_in_at !== null;
            const isMarking = markingId === attendee.user_id;
            return (
              <li
                key={attendee.user_id}
                className="bg-brand-bg flex items-center gap-3 rounded-lg px-3 py-2.5"
              >
                <Link
                  aria-label={`View ${attendee.username}'s profile`}
                  className="focus-visible:ring-brand-dark flex min-w-0 flex-1 items-center gap-3 rounded-md transition-opacity hover:opacity-80 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-1"
                  href={getProfileHref(attendee.user_id, currentUserId)}
                >
                  <div className="bg-brand-mid flex size-8 shrink-0 items-center justify-center rounded-full text-[12px] font-bold text-white">
                    {attendee.username.slice(0, 2).toUpperCase()}
                  </div>
                  <div className="min-w-0">
                    <p className="text-brand-dark truncate text-[14px] font-bold">
                      @{attendee.username}
                    </p>
                    <p className="text-brand-mid truncate text-[11px]">
                      {isCheckedIn
                        ? `Checked in · ${formatCheckInTime(attendee.checked_in_at!)}`
                        : "Pending"}
                    </p>
                  </div>
                </Link>
                {isCheckedIn ? (
                  <span className="inline-flex items-center gap-1 rounded-md bg-green-600/15 px-2 py-1 text-[11px] font-bold text-green-700">
                    <Check className="size-3" />
                    In
                  </span>
                ) : (
                  <button
                    aria-label={`Manually mark ${attendee.username} as checked in`}
                    className="border-brand-dark text-brand-dark hover:bg-brand-mid-alpha inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-[11px] font-bold transition-colors disabled:opacity-50"
                    disabled={isMarking}
                    onClick={() => onMarkIn(attendee.user_id)}
                    type="button"
                  >
                    {isMarking ? (
                      <Loader2 className="size-3 animate-spin" />
                    ) : (
                      <Check className="size-3" />
                    )}
                    Mark in
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
