"use client";

import Link from "next/link";

import { getProfileHref } from "@/lib/profile-route";
import { cn } from "@/lib/utils";

interface Attendee {
  id: string;
  username: string;
}

interface AttendeeAvatarStackProps {
  attendees?: Attendee[];
  maxShow?: number;
  className?: string;
  currentUserId?: string | null;
}

function getAvatarColor(userId: string): string {
  const colors = ["bg-brand-dark", "bg-brand-mid", "bg-[#7a5d45]", "bg-[#c4a882]", "bg-[#8b7355]"];
  let hash = 0;
  for (const ch of userId) hash = (hash * 31 + ch.charCodeAt(0)) & 0xffff;
  return colors[hash % colors.length];
}

function initials(username: string): string {
  return username.slice(0, 2).toUpperCase();
}

export function AttendeeAvatarStack({
  attendees = [],
  maxShow = 5,
  className,
  currentUserId = null,
}: AttendeeAvatarStackProps) {
  if (attendees.length === 0) {
    return null;
  }

  const shown = attendees.slice(0, maxShow);
  const remaining = attendees.length - maxShow;

  return (
    <div className={cn("flex items-center", className)}>
      {shown.map((attendee, index) => (
        <Link
          key={attendee.id}
          href={getProfileHref(attendee.id, currentUserId)}
          aria-label={`View ${attendee.username}'s profile`}
          title={attendee.username}
          className={cn(
            "flex size-9 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white border-2 border-white transition-transform hover:-translate-y-0.5 hover:shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-dark focus-visible:ring-offset-1",
            getAvatarColor(attendee.id),
            index > 0 && "-ml-2",
          )}
        >
          {initials(attendee.username)}
        </Link>
      ))}
      {remaining > 0 && (
        <div className="ml-2 text-sm font-bold text-brand-mid">
          +{remaining} more
        </div>
      )}
    </div>
  );
}
