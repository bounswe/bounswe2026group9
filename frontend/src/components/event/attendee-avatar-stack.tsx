"use client";

import { cn } from "@/lib/utils";

interface Attendee {
  id: string;
  username: string;
}

interface AttendeeAvatarStackProps {
  attendees?: Attendee[];
  maxShow?: number;
  className?: string;
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
}: AttendeeAvatarStackProps) {
  if (attendees.length === 0) {
    return null;
  }

  const shown = attendees.slice(0, maxShow);
  const remaining = attendees.length - maxShow;

  return (
    <div className={cn("flex items-center", className)}>
      {shown.map((attendee, index) => (
        <div
          key={attendee.id}
          className={cn(
            "flex size-9 shrink-0 items-center justify-center rounded-full border-2 border-white text-xs font-bold text-white",
            getAvatarColor(attendee.id),
            index > 0 && "-ml-2",
          )}
          title={attendee.username}
        >
          {initials(attendee.username)}
        </div>
      ))}
      {remaining > 0 && (
        <div className="text-brand-mid ml-2 text-sm font-bold">+{remaining} more</div>
      )}
    </div>
  );
}
