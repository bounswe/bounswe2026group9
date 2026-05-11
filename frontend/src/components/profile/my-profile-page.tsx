"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  Bookmark,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  Eye,
  Lock,
  Mail,
  PenSquare,
  Phone,
  Plus,
  Shield,
  Users,
  XCircle,
} from "lucide-react";

import { ProtectedRoute } from "@/components/auth/protected-route";
import { Navbar } from "@/components/layout/navbar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/hooks/use-auth";
import {
  getHostProfileSummary,
  changeEventStatus,
  getCurrentUser,
  getErrorMessage,
  getMyBookmarks,
  updateMyProfile,
  type BookmarkListResponse,
  type BookmarkedEventSummary,
  type HostedEventSummary,
  type HostProfileSummaryResponse,
  type ProfileUpdatePayload,
  type ProfileVisibility,
} from "@/lib/api";
import { fetchMyGoingEvents, type EventListItem } from "@/lib/events-api";
import {
  CREATE_EVENT_PAGE_PATH,
  getEditEventPagePath,
  getEventDetailPagePath,
} from "@/lib/event-routes";
import type { AuthUser } from "@/lib/session";
import { cn } from "@/lib/utils";

const BOOKMARKS_PAGE_SIZE = 6;
type MyEventsTab = "draft" | "past" | "upcoming";
type GoingTab = "upcoming" | "past";
type ProfileSection = "going-events" | "my-events" | "saved-events" | "settings";

interface ProfileFormState {
  dateOfBirth: string;
  emailVisibility: ProfileVisibility;
  phoneNumber: string;
  phoneVisibility: ProfileVisibility;
}

function toVisibility(value: boolean): ProfileVisibility {
  return value ? "public" : "private";
}

function toFormState(user: AuthUser): ProfileFormState {
  return {
    dateOfBirth: user.date_of_birth ?? "",
    emailVisibility: toVisibility(user.email_visibility),
    phoneNumber: user.phone_number ?? "",
    phoneVisibility: toVisibility(user.phone_visibility ?? false),
  };
}

function initials(username: string) {
  return (
    username
      .split(/[\s._-]+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() ?? "")
      .join("") || username.slice(0, 2).toUpperCase()
  );
}

function formatDateTime(value: string) {
  return new Date(value).toLocaleString("en-US", {
    day: "numeric",
    hour: "2-digit",
    hour12: false,
    minute: "2-digit",
    month: "short",
  });
}

function statusLabel(status: BookmarkedEventSummary["status"]) {
  if (status === "published" || status === "updated") {
    return "Saved";
  }

  return status.charAt(0).toUpperCase() + status.slice(1);
}

function isPublicVisibility(value: ProfileVisibility) {
  return value === "public";
}

function PrivacyToggle({
  label,
  onChange,
  value,
}: {
  label: string;
  onChange: (value: ProfileVisibility) => void;
  value: ProfileVisibility;
}) {
  const isEnabled = isPublicVisibility(value);

  return (
    <div className="border-brand-mid/12 flex items-center justify-between gap-4 rounded-[20px] border bg-white px-4 py-4">
      <div>
        <p className="text-brand-dark text-sm font-semibold">{label}</p>
        <p className="text-brand-mid mt-1 text-xs">
          {isEnabled
            ? "Visible on your public host profile."
            : "Hidden from your public host profile."}
        </p>
      </div>

      <button
        type="button"
        role="switch"
        aria-checked={isEnabled}
        onClick={() => onChange(isEnabled ? "private" : "public")}
        className={cn(
          "relative inline-flex h-8 w-[58px] shrink-0 cursor-pointer rounded-full border transition-colors",
          isEnabled ? "border-brand-mid bg-brand-mid" : "border-brand-mid/20 bg-brand-bg",
        )}
      >
        <span
          className={cn(
            "text-brand-dark absolute top-1 flex h-6 w-6 items-center justify-center rounded-full bg-white text-[10px] font-bold shadow-sm transition-transform",
            isEnabled ? "translate-x-[28px]" : "translate-x-1",
          )}
        >
          {isEnabled ? "On" : "Off"}
        </span>
      </button>
    </div>
  );
}

function isPastHostedEvent(event: HostedEventSummary) {
  if (event.status === "cancelled" || event.status === "ended") {
    return true;
  }

  return new Date(event.end_datetime).getTime() < Date.now();
}

function myEventStatusChip(event: HostedEventSummary) {
  if (event.status === "draft") {
    return {
      className: "border border-brand-mid/15 bg-brand-bg text-brand-dark",
      label: "Draft",
    };
  }

  if (event.status === "cancelled") {
    return {
      className: "border border-red-200 bg-red-100 text-red-700",
      label: "Cancelled",
    };
  }

  if (event.status === "ended" || isPastHostedEvent(event)) {
    return {
      className: "border border-brand-mid/15 bg-brand-bg text-brand-mid",
      label: "Ended",
    };
  }

  return {
    className: "border border-emerald-200 bg-emerald-100 text-emerald-700",
    label: "Live",
  };
}

function GoingEventCard({ event, isPast }: { event: EventListItem; isPast: boolean }) {
  return (
    <Link
      href={`/event/${event.id}`}
      className="group border-brand-mid/12 overflow-hidden rounded-[24px] border bg-white shadow-[0_20px_54px_-42px_rgba(73,54,40,0.55)] transition-all duration-200 hover:-translate-y-1 hover:shadow-[0_26px_66px_-40px_rgba(73,54,40,0.6)]"
    >
      <div className="bg-brand-mid/20 relative h-44 overflow-hidden">
        {event.primary_image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={event.primary_image_url}
            alt={event.title}
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.03]"
          />
        ) : (
          <div className="flex h-full items-center justify-center bg-[linear-gradient(135deg,rgba(73,54,40,0.9),rgba(171,136,109,0.7))]">
            <CalendarDays className="size-10 text-white/45" />
          </div>
        )}
        <div className="absolute inset-x-0 top-0 flex items-start justify-between gap-2 p-4">
          <span
            className={cn(
              "rounded-full px-3 py-1 text-[11px] font-bold tracking-[0.14em] uppercase",
              isPast
                ? "border-brand-mid/15 bg-brand-bg text-brand-mid border"
                : "border border-emerald-200 bg-emerald-100 text-emerald-700",
            )}
          >
            {isPast ? "Attended" : "Going"}
          </span>
        </div>
      </div>

      <div className="space-y-3 p-5">
        <div className="flex flex-wrap gap-2">
          {event.categories.slice(0, 3).map((category) => (
            <span
              key={category.id}
              className="bg-brand-bg text-brand-mid rounded-full px-3 py-1 text-[11px] font-semibold"
            >
              {category.name}
            </span>
          ))}
        </div>
        <div>
          <h3 className="font-heading text-brand-dark text-xl font-semibold">{event.title}</h3>
          <p className="text-brand-mid mt-1 text-sm font-medium">
            {formatDateTime(event.start_datetime)}
          </p>
        </div>
        <p className="text-brand-mid text-xs">
          {event.primary_location ? event.primary_location.name : "Location not set"}
        </p>
      </div>
    </Link>
  );
}

function BookmarkedEventCard({ event }: { event: BookmarkedEventSummary }) {
  return (
    <Link
      href={`/event/${event.id}`}
      className="group border-brand-mid/12 overflow-hidden rounded-[24px] border bg-white shadow-[0_20px_54px_-42px_rgba(73,54,40,0.55)] transition-all duration-200 hover:-translate-y-1 hover:shadow-[0_26px_66px_-40px_rgba(73,54,40,0.6)]"
    >
      <div className="bg-brand-mid/20 relative h-44 overflow-hidden">
        {event.primary_image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={event.primary_image_url}
            alt={event.title}
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.03]"
          />
        ) : (
          <div className="flex h-full items-center justify-center bg-[linear-gradient(135deg,rgba(73,54,40,0.9),rgba(171,136,109,0.7))]">
            {event.visibility === "private" ? (
              <Lock className="size-10 text-white/55" />
            ) : (
              <Bookmark className="size-10 text-white/45" />
            )}
          </div>
        )}

        <div className="absolute inset-x-0 top-0 flex items-start justify-between gap-2 p-4">
          <Badge
            variant={
              event.status === "published" || event.status === "updated" ? "success" : "outline"
            }
            className="text-brand-dark border-0 bg-white/85"
          >
            {statusLabel(event.status)}
          </Badge>
          {event.visibility === "private" ? (
            <span className="bg-brand-dark/85 inline-flex items-center gap-1 rounded-full px-3 py-1 text-[11px] font-bold tracking-[0.14em] text-white uppercase">
              <Lock className="size-3" />
              Private
            </span>
          ) : null}
        </div>
      </div>

      <div className="space-y-4 p-5">
        <div className="flex flex-wrap gap-2">
          {event.categories.slice(0, 3).map((category) => (
            <span
              key={category.id}
              className="bg-brand-bg text-brand-mid rounded-full px-3 py-1 text-[11px] font-semibold"
            >
              {category.name}
            </span>
          ))}
        </div>

        <div>
          <h3 className="font-heading text-brand-dark text-xl font-semibold">{event.title}</h3>
          <p className="text-brand-mid mt-1 text-sm font-medium">
            {formatDateTime(event.start_datetime)}
          </p>
        </div>

        <div className="text-brand-dark/80 space-y-1 text-sm">
          <p>
            Bookmarked on{" "}
            <span className="text-brand-dark font-semibold">
              {formatDateTime(event.bookmarked_at)}
            </span>
          </p>
          <p className="text-brand-mid">
            {event.primary_location
              ? event.primary_location.name
              : event.visibility === "private"
                ? "Location hidden for private event"
                : "Location not set"}
          </p>
        </div>
      </div>
    </Link>
  );
}

function HostedEventCard({
  event,
  isCancelling,
  onQuickCancel,
}: {
  event: HostedEventSummary;
  isCancelling: boolean;
  onQuickCancel: (eventId: string) => void;
}) {
  const status = myEventStatusChip(event);
  const attendeeFill = event.attendee_limit
    ? Math.min(100, Math.round((event.attendee_count / event.attendee_limit) * 100))
    : null;
  const canQuickCancel =
    event.status !== "draft" &&
    event.status !== "cancelled" &&
    event.status !== "ended" &&
    !isPastHostedEvent(event);

  return (
    <div className="border-brand-mid/12 overflow-hidden rounded-[24px] border bg-white shadow-[0_20px_54px_-42px_rgba(73,54,40,0.55)]">
      <div className="bg-brand-mid/20 relative h-44 overflow-hidden">
        {event.primary_image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={event.primary_image_url}
            alt={event.title}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full items-center justify-center bg-[linear-gradient(135deg,rgba(73,54,40,0.9),rgba(171,136,109,0.72))]">
            <CalendarDays className="size-10 text-white/45" />
          </div>
        )}

        <div className="absolute inset-x-0 top-0 flex items-start justify-between gap-2 p-4">
          <span
            className={cn(
              "rounded-full px-3 py-1 text-[11px] font-bold tracking-[0.14em] uppercase",
              status.className,
            )}
          >
            {status.label}
          </span>
          {event.visibility === "private" ? (
            <span className="bg-brand-dark/85 inline-flex items-center gap-1 rounded-full px-3 py-1 text-[11px] font-bold tracking-[0.14em] text-white uppercase">
              <Lock className="size-3" />
              Private
            </span>
          ) : null}
        </div>
      </div>

      <div className="space-y-4 p-5">
        <div className="flex flex-wrap gap-2">
          {event.categories.slice(0, 3).map((category) => (
            <span
              key={category.id}
              className="bg-brand-bg text-brand-mid rounded-full px-3 py-1 text-[11px] font-semibold"
            >
              {category.name}
            </span>
          ))}
        </div>

        <div>
          <h3 className="font-heading text-brand-dark text-xl font-semibold">{event.title}</h3>
          <p className="text-brand-mid mt-1 text-sm font-medium">
            {formatDateTime(event.start_datetime)}
          </p>
        </div>

        <div className="space-y-2">
          <div className="text-brand-dark flex items-center justify-between text-xs font-semibold">
            <span>
              {event.attendee_count}
              {event.attendee_limit ? `/${event.attendee_limit}` : ""} going
            </span>
            <span className="text-brand-mid max-w-[56%] truncate text-right">
              {event.primary_location
                ? event.primary_location.name
                : event.visibility === "private"
                  ? "Location hidden"
                  : "Location not set"}
            </span>
          </div>

          {attendeeFill !== null ? (
            <div className="bg-brand-bg h-2 rounded-full">
              <div
                className="bg-brand-mid h-full rounded-full"
                style={{ width: `${attendeeFill}%` }}
              />
            </div>
          ) : null}
        </div>

        <div className="flex items-center gap-2 pt-1">
          <Button
            asChild
            variant="outline"
            className="border-brand-mid/20 text-brand-dark hover:bg-brand-bg flex-1 bg-white"
          >
            <Link href={getEditEventPagePath(event.id)}>
              <PenSquare className="size-4" />
              Edit
            </Link>
          </Button>
          <Button
            asChild
            className="bg-brand-dark hover:bg-brand-dark/85 flex-1 border-0 text-white"
          >
            <Link href={getEventDetailPagePath(event.id)}>
              <Eye className="size-4" />
              View
            </Link>
          </Button>
          {canQuickCancel ? (
            <Button
              type="button"
              variant="outline"
              disabled={isCancelling}
              onClick={() => onQuickCancel(event.id)}
              className="flex-1 border-red-200 bg-white text-red-700 hover:bg-red-50 hover:text-red-800"
            >
              <XCircle className="size-4" />
              {isCancelling ? "Cancelling..." : "Cancel"}
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export function MyProfilePage() {
  const { isInitialized, status, user } = useAuth();

  const [profile, setProfile] = useState<AuthUser | null>(user);
  const [form, setForm] = useState<ProfileFormState | null>(user ? toFormState(user) : null);
  const [profileLoading, setProfileLoading] = useState(true);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [bookmarks, setBookmarks] = useState<BookmarkListResponse | null>(null);
  const [hostProfile, setHostProfile] = useState<HostProfileSummaryResponse | null>(null);
  const [goingEvents, setGoingEvents] = useState<EventListItem[]>([]);
  const [bookmarksLoading, setBookmarksLoading] = useState(true);
  const [bookmarksError, setBookmarksError] = useState<string | null>(null);
  const [hostProfileLoading, setHostProfileLoading] = useState(true);
  const [hostProfileError, setHostProfileError] = useState<string | null>(null);
  const [goingEventsLoading, setGoingEventsLoading] = useState(true);
  const [goingEventsError, setGoingEventsError] = useState<string | null>(null);
  const [bookmarkPage, setBookmarkPage] = useState(1);
  const [activeSection, setActiveSection] = useState<ProfileSection>("settings");
  const [eventsTab, setEventsTab] = useState<MyEventsTab>("upcoming");
  const [goingTab, setGoingTab] = useState<GoingTab>("upcoming");
  const [cancellingEventId, setCancellingEventId] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (!isInitialized || status !== "authenticated") {
      return;
    }

    let active = true;

    void getCurrentUser()
      .then((currentUser) => {
        if (!active) {
          return;
        }

        setProfile(currentUser);
        setForm(toFormState(currentUser));
        setProfileError(null);
        setProfileLoading(false);
      })
      .catch((error: unknown) => {
        if (!active) {
          return;
        }

        setProfileError(getErrorMessage(error, "We could not load your profile settings."));
        setProfileLoading(false);
      });

    return () => {
      active = false;
    };
  }, [isInitialized, status]);

  useEffect(() => {
    if (!isInitialized || status !== "authenticated" || !user?.id) {
      return;
    }

    let active = true;

    void getHostProfileSummary(user.id)
      .then((response) => {
        if (!active) {
          return;
        }

        setHostProfile(response);
        setHostProfileError(null);
        setHostProfileLoading(false);
      })
      .catch((error: unknown) => {
        if (!active) {
          return;
        }

        setHostProfileError(getErrorMessage(error, "We could not load the events you created."));
        setHostProfileLoading(false);
      });

    return () => {
      active = false;
    };
  }, [isInitialized, status, user?.id]);

  useEffect(() => {
    if (!isInitialized || status !== "authenticated") {
      return;
    }

    let active = true;

    void getMyBookmarks({ page: bookmarkPage, pageSize: BOOKMARKS_PAGE_SIZE })
      .then((response) => {
        if (!active) {
          return;
        }

        setBookmarks(response);
        setBookmarksError(null);
        setBookmarksLoading(false);
      })
      .catch((error: unknown) => {
        if (!active) {
          return;
        }

        setBookmarksError(getErrorMessage(error, "We could not load your bookmarked events."));
        setBookmarksLoading(false);
      });

    return () => {
      active = false;
    };
  }, [bookmarkPage, isInitialized, status]);

  useEffect(() => {
    if (!isInitialized || status !== "authenticated") {
      return;
    }

    let active = true;

    void fetchMyGoingEvents()
      .then((events) => {
        if (!active) {
          return;
        }

        setGoingEvents(events);
        setGoingEventsError(null);
        setGoingEventsLoading(false);
      })
      .catch((error: unknown) => {
        if (!active) {
          return;
        }

        setGoingEventsError(getErrorMessage(error, "We could not load your going events."));
        setGoingEventsLoading(false);
      });

    return () => {
      active = false;
    };
  }, [isInitialized, status]);

  function updateForm<K extends keyof ProfileFormState>(key: K, value: ProfileFormState[K]) {
    setForm((current) => (current ? { ...current, [key]: value } : current));
    setSaveError(null);
    setSaveSuccess(null);
  }

  function handleBookmarkPageChange(nextPage: number) {
    if (
      !bookmarks ||
      nextPage < 1 ||
      nextPage > bookmarks.total_pages ||
      nextPage === bookmarkPage
    ) {
      return;
    }

    setBookmarksLoading(true);
    setBookmarkPage(nextPage);
  }

  async function handleSave() {
    if (!profile || !form) {
      return;
    }

    if (!form.dateOfBirth && profile.date_of_birth) {
      setSaveError("Removing date of birth is not supported with the current profile endpoint.");
      setSaveSuccess(null);
      return;
    }

    const payload: ProfileUpdatePayload = {};

    if (form.phoneNumber.trim() !== (profile.phone_number ?? "")) {
      payload.phone_number = form.phoneNumber.trim();
    }

    if (form.dateOfBirth !== (profile.date_of_birth ?? "")) {
      payload.date_of_birth = form.dateOfBirth;
    }

    if (form.emailVisibility !== toVisibility(profile.email_visibility)) {
      payload.email_visibility = form.emailVisibility;
    }

    if (form.phoneVisibility !== toVisibility(profile.phone_visibility ?? false)) {
      payload.phone_visibility = form.phoneVisibility;
    }

    if (Object.keys(payload).length === 0) {
      setSaveSuccess("No changes to save.");
      setSaveError(null);
      return;
    }

    setIsSaving(true);
    setSaveError(null);
    setSaveSuccess(null);

    try {
      const updated = await updateMyProfile(payload);
      setProfile(updated);
      setForm(toFormState(updated));
      setSaveSuccess("Your profile settings have been updated.");
    } catch (error: unknown) {
      setSaveError(getErrorMessage(error, "We could not save your profile settings."));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleQuickCancel(eventId: string) {
    setCancellingEventId(eventId);
    setHostProfileError(null);

    try {
      await changeEventStatus(eventId, { status: "cancelled" });
      setHostProfile((current) =>
        current
          ? {
              ...current,
              hosted_events: current.hosted_events.map((event) =>
                event.id === eventId ? { ...event, status: "cancelled" } : event,
              ),
            }
          : current,
      );
    } catch (error: unknown) {
      setHostProfileError(getErrorMessage(error, "We could not cancel this event."));
    } finally {
      setCancellingEventId(null);
    }
  }

  const upcomingGoingEvents = goingEvents.filter(
    (event) =>
      event.status !== "cancelled" &&
      event.status !== "ended" &&
      new Date(event.end_datetime).getTime() >= Date.now(),
  );
  const pastGoingEvents = goingEvents.filter(
    (event) =>
      event.status === "cancelled" ||
      event.status === "ended" ||
      new Date(event.end_datetime).getTime() < Date.now(),
  );
  const visibleGoingEvents = goingTab === "upcoming" ? upcomingGoingEvents : pastGoingEvents;

  const hostedEvents = hostProfile?.hosted_events ?? [];
  const draftHostedEvents = hostedEvents.filter((event) => event.status === "draft");
  const upcomingHostedEvents = hostedEvents.filter(
    (event) => event.status !== "draft" && !isPastHostedEvent(event),
  );
  const pastHostedEvents = hostedEvents.filter(
    (event) => event.status !== "draft" && isPastHostedEvent(event),
  );
  const visibleHostedEvents =
    eventsTab === "upcoming"
      ? upcomingHostedEvents
      : eventsTab === "past"
        ? pastHostedEvents
        : draftHostedEvents;
  const liveEventCount = hostedEvents.filter(
    (event) =>
      event.status !== "draft" && event.status !== "cancelled" && !isPastHostedEvent(event),
  ).length;
  const totalHostedAttendees = hostedEvents.reduce((sum, event) => sum + event.attendee_count, 0);

  return (
    <ProtectedRoute
      loadingTitle="Opening your settings..."
      loadingMessage="We’re verifying your session before showing your private profile settings."
    >
      <div className="bg-brand-bg min-h-screen">
        <Navbar />

        <section className="relative overflow-hidden bg-[linear-gradient(135deg,#493628_0%,#5e4434_48%,#AB886D_100%)]">
          <div className="mx-auto h-56 max-w-[1280px]" />
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.18),transparent_45%)]" />
        </section>

        <main className="relative mx-auto -mt-14 max-w-[1240px] px-4 pb-8 sm:px-6 lg:px-8 lg:pb-10">
          <div className="space-y-8">
            <section className="mx-auto max-w-4xl">
              <div className="flex flex-col items-center text-center">
                <div className="bg-brand-mid flex size-28 items-center justify-center rounded-full border-4 border-white text-3xl font-bold text-white shadow-[0_12px_28px_-18px_rgba(73,54,40,0.55)]">
                  {initials(profile?.username ?? user?.username ?? "U")}
                </div>

                <h1 className="font-heading text-brand-dark mt-5 text-4xl font-bold">
                  {profile?.username ?? user?.username ?? "My Profile"}
                </h1>
                <p className="text-brand-mid mt-1 text-sm">
                  @{profile?.username ?? user?.username ?? "user"}
                </p>

                <p className="text-brand-dark/80 mt-4 max-w-2xl text-sm leading-7">
                  Manage your account settings, created events, and saved events from the same home
                  base where other users can discover you as a host.
                </p>

                <div className="mt-6 grid w-full max-w-2xl grid-cols-1 gap-3 sm:grid-cols-3">
                  <div className="border-brand-mid/12 rounded-[20px] border bg-white/85 px-5 py-4">
                    <p className="text-brand-dark text-2xl font-bold">{hostedEvents.length}</p>
                    <p className="text-brand-mid mt-1 text-xs font-semibold tracking-[0.18em] uppercase">
                      Events
                    </p>
                  </div>
                  <div className="border-brand-mid/12 rounded-[20px] border bg-white/85 px-5 py-4">
                    <p className="text-brand-dark text-2xl font-bold">
                      {hostProfile?.average_rating !== null &&
                      hostProfile?.average_rating !== undefined
                        ? hostProfile.average_rating.toFixed(1)
                        : "New"}
                    </p>
                    <p className="text-brand-mid mt-1 text-xs font-semibold tracking-[0.18em] uppercase">
                      Average Rating
                    </p>
                  </div>
                  <div className="border-brand-mid/12 rounded-[20px] border bg-white/85 px-5 py-4">
                    <p className="text-brand-dark text-2xl font-bold">
                      {upcomingHostedEvents.length}
                    </p>
                    <p className="text-brand-mid mt-1 text-xs font-semibold tracking-[0.18em] uppercase">
                      Upcoming
                    </p>
                  </div>
                </div>

                <div className="mt-5 flex flex-wrap items-center justify-center gap-3">
                  <div className="border-brand-mid/18 text-brand-dark inline-flex items-center gap-2 rounded-full border bg-white/85 px-4 py-2 text-sm font-medium">
                    <Mail className="text-brand-mid size-4" />
                    {profile?.email ?? user?.email ?? "No email available"}
                  </div>

                  {profile?.phone_number ? (
                    <div className="border-brand-mid/18 text-brand-dark inline-flex items-center gap-2 rounded-full border bg-white/85 px-4 py-2 text-sm font-medium">
                      <Phone className="text-brand-mid size-4" />
                      {profile.phone_number}
                    </div>
                  ) : null}

                  <div className="border-brand-mid/18 text-brand-dark inline-flex items-center gap-2 rounded-full border bg-white/85 px-4 py-2 text-sm font-medium">
                    <Shield className="text-brand-mid size-4" />
                    {profile?.email_verified ? "Email verified" : "Verification pending"}
                  </div>
                </div>
              </div>
            </section>

            <div className="flex overflow-x-auto sm:justify-center">
              <div className="border-brand-mid/12 inline-flex min-w-max gap-2 rounded-[26px] border bg-white p-2 shadow-[0_18px_48px_-40px_rgba(73,54,40,0.55)]">
                {(
                  [
                    {
                      description: "Account and privacy",
                      icon: Shield,
                      key: "settings",
                      label: "Settings",
                    },
                    {
                      description: "Created events",
                      icon: CalendarDays,
                      key: "my-events",
                      label: "My Events",
                    },
                    {
                      description: "Going & attended",
                      icon: Users,
                      key: "going-events",
                      label: "Going Events",
                    },
                    {
                      description: "Bookmarked events",
                      icon: Bookmark,
                      key: "saved-events",
                      label: "Saved Events",
                    },
                  ] as const
                ).map((section) => {
                  const Icon = section.icon;
                  const isActive = activeSection === section.key;

                  return (
                    <button
                      key={section.key}
                      type="button"
                      onClick={() => setActiveSection(section.key)}
                      className={cn(
                        "flex min-w-[190px] cursor-pointer items-center gap-3 rounded-[20px] px-4 py-3 text-left transition-colors",
                        isActive
                          ? "bg-brand-dark text-white shadow-[0_14px_26px_-20px_rgba(73,54,40,0.8)]"
                          : "text-brand-dark hover:bg-brand-bg",
                      )}
                    >
                      <span
                        className={cn(
                          "flex size-10 shrink-0 items-center justify-center rounded-full",
                          isActive ? "bg-white/14 text-white" : "bg-brand-bg text-brand-mid",
                        )}
                      >
                        <Icon className="size-4" />
                      </span>
                      <span className="min-w-0">
                        <span className="block text-sm font-semibold whitespace-nowrap">
                          {section.label}
                        </span>
                        <span
                          className={cn(
                            "block text-xs",
                            isActive ? "text-white/72" : "text-brand-mid",
                          )}
                        >
                          {section.description}
                        </span>
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            {activeSection === "settings" ? (
              <div className="mx-auto max-w-[920px]">
                <section>
                  <Card className="border-brand-mid/10 rounded-[32px] shadow-[0_28px_72px_-48px_rgba(73,54,40,0.55)]">
                    <CardHeader className="px-6 pt-6 sm:px-8">
                      <CardTitle className="font-heading text-brand-dark text-3xl">
                        Profile Settings
                      </CardTitle>
                      <CardDescription className="text-brand-mid">
                        Update the fields supported by the current profile endpoint and control what
                        appears on your public host profile.
                      </CardDescription>
                    </CardHeader>

                    <CardContent className="space-y-6 px-6 pb-8 sm:px-8">
                      {profileError ? (
                        <div className="rounded-[20px] border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                          {profileError}
                        </div>
                      ) : null}

                      {profileLoading || !profile || !form ? (
                        <div className="space-y-4">
                          <div className="bg-brand-mid/12 h-12 animate-pulse rounded-xl" />
                          <div className="bg-brand-mid/10 h-12 animate-pulse rounded-xl" />
                          <div className="bg-brand-mid/8 h-24 animate-pulse rounded-[20px]" />
                        </div>
                      ) : (
                        <>
                          <div className="grid gap-5 md:grid-cols-2">
                            <div className="space-y-2">
                              <Label htmlFor="profile-username">Username</Label>
                              <Input
                                id="profile-username"
                                value={profile.username}
                                readOnly
                                className="border-brand-mid/15 bg-brand-bg/60 text-brand-dark/70"
                              />
                            </div>

                            <div className="space-y-2">
                              <Label htmlFor="profile-email">Email</Label>
                              <Input
                                id="profile-email"
                                value={profile.email}
                                readOnly
                                className="border-brand-mid/15 bg-brand-bg/60 text-brand-dark/70"
                              />
                            </div>

                            <div className="space-y-2">
                              <Label htmlFor="profile-phone">Phone Number</Label>
                              <Input
                                id="profile-phone"
                                type="tel"
                                placeholder="Optional phone number"
                                value={form.phoneNumber}
                                onChange={(event) => updateForm("phoneNumber", event.target.value)}
                                className="border-brand-mid/15 bg-white"
                              />
                            </div>

                            <div className="space-y-2">
                              <Label htmlFor="profile-dob">Date of Birth</Label>
                              <Input
                                id="profile-dob"
                                type="date"
                                value={form.dateOfBirth}
                                onChange={(event) => updateForm("dateOfBirth", event.target.value)}
                                className="border-brand-mid/15 bg-white"
                              />
                            </div>
                          </div>

                          <div className="space-y-4">
                            <PrivacyToggle
                              label="Email visibility"
                              value={form.emailVisibility}
                              onChange={(value) => updateForm("emailVisibility", value)}
                            />
                            <PrivacyToggle
                              label="Phone visibility"
                              value={form.phoneVisibility}
                              onChange={(value) => updateForm("phoneVisibility", value)}
                            />
                          </div>

                          {saveError ? (
                            <div className="rounded-[20px] border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                              {saveError}
                            </div>
                          ) : null}

                          {saveSuccess ? (
                            <div className="rounded-[20px] border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                              {saveSuccess}
                            </div>
                          ) : null}

                          <div className="flex justify-end">
                            <Button
                              type="button"
                              onClick={() => {
                                void handleSave();
                              }}
                              disabled={isSaving}
                              className="bg-brand-dark hover:bg-brand-dark/85 border-0 px-6 text-white"
                            >
                              {isSaving ? "Saving..." : "Save Changes"}
                            </Button>
                          </div>
                        </>
                      )}
                    </CardContent>
                  </Card>
                </section>
              </div>
            ) : null}

            {activeSection === "going-events" ? (
              <section className="space-y-6">
                <div>
                  <h2 className="font-heading text-brand-dark text-3xl font-bold">Going Events</h2>
                  <p className="text-brand-mid mt-1 text-sm">
                    Events you&apos;ve marked as going or already attended.
                  </p>
                </div>

                <div className="border-brand-mid/15 overflow-x-auto border-b">
                  <div className="flex min-w-max gap-0">
                    {(
                      [
                        { key: "upcoming", label: "Upcoming", count: upcomingGoingEvents.length },
                        { key: "past", label: "Past / Attended", count: pastGoingEvents.length },
                      ] as const
                    ).map((tab) => (
                      <button
                        key={tab.key}
                        type="button"
                        onClick={() => setGoingTab(tab.key)}
                        className={cn(
                          "inline-flex cursor-pointer items-center gap-2 border-b-[3px] px-6 py-3 text-sm transition-colors",
                          goingTab === tab.key
                            ? "border-brand-dark text-brand-dark font-bold"
                            : "text-brand-mid hover:text-brand-dark border-transparent font-medium",
                        )}
                      >
                        {tab.label}
                        <span
                          className={cn(
                            "rounded-full px-1.5 py-0.5 text-[10px] font-semibold",
                            goingTab === tab.key
                              ? "bg-brand-dark text-white"
                              : "bg-brand-surface text-brand-mid",
                          )}
                        >
                          {tab.count}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>

                {goingEventsError ? (
                  <div className="rounded-[20px] border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                    {goingEventsError}
                  </div>
                ) : goingEventsLoading ? (
                  <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                    {Array.from({ length: 3 }).map((_, index) => (
                      <div
                        key={index}
                        className="border-brand-mid/12 overflow-hidden rounded-[24px] border bg-white"
                      >
                        <div className="bg-brand-mid/15 h-44 animate-pulse" />
                        <div className="space-y-3 p-5">
                          <div className="bg-brand-mid/12 h-4 animate-pulse rounded-full" />
                          <div className="bg-brand-mid/10 h-4 w-2/3 animate-pulse rounded-full" />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : visibleGoingEvents.length > 0 ? (
                  <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                    {visibleGoingEvents.map((event) => (
                      <GoingEventCard key={event.id} event={event} isPast={goingTab === "past"} />
                    ))}
                  </div>
                ) : (
                  <div className="border-brand-mid/12 bg-brand-bg/75 rounded-[24px] border px-6 py-12 text-center">
                    <div className="bg-brand-mid/12 text-brand-mid mx-auto flex size-16 items-center justify-center rounded-full">
                      <Users className="size-7" />
                    </div>
                    <p className="font-heading text-brand-dark mt-4 text-2xl">
                      {goingTab === "upcoming" ? "No upcoming events" : "No attended events yet"}
                    </p>
                    <p className="text-brand-mid mt-2 text-sm">
                      {goingTab === "upcoming"
                        ? "Mark events as going from the discovery page to see them here."
                        : "Events you attended will appear here after they end."}
                    </p>
                    <Button
                      asChild
                      className="bg-brand-dark hover:bg-brand-dark/85 mt-5 border-0 text-white"
                    >
                      <Link href="/">Explore Events</Link>
                    </Button>
                  </div>
                )}
              </section>
            ) : null}

            {activeSection === "saved-events" ? (
              <section>
                <Card className="border-brand-mid/10 rounded-[32px] shadow-[0_28px_72px_-48px_rgba(73,54,40,0.55)]">
                  <CardHeader className="px-6 pt-6 sm:px-8">
                    <CardTitle className="font-heading text-brand-dark text-3xl">
                      Saved Events
                    </CardTitle>
                    <CardDescription className="text-brand-mid">
                      Browse the events you bookmarked and jump back into their detail pages.
                    </CardDescription>
                  </CardHeader>

                  <CardContent className="px-6 pb-8 sm:px-8">
                    {bookmarksError ? (
                      <div className="rounded-[20px] border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                        {bookmarksError}
                      </div>
                    ) : bookmarksLoading ? (
                      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                        {Array.from({ length: 3 }).map((_, index) => (
                          <div
                            key={index}
                            className="border-brand-mid/12 overflow-hidden rounded-[24px] border bg-white"
                          >
                            <div className="bg-brand-mid/15 h-44 animate-pulse" />
                            <div className="space-y-3 p-5">
                              <div className="bg-brand-mid/12 h-4 animate-pulse rounded-full" />
                              <div className="bg-brand-mid/10 h-4 w-2/3 animate-pulse rounded-full" />
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : bookmarks && bookmarks.items.length > 0 ? (
                      <>
                        <div className="mb-4 flex items-center justify-between gap-3">
                          <p className="text-brand-mid text-sm">
                            Showing{" "}
                            <span className="text-brand-dark font-semibold">
                              {bookmarks.items.length}
                            </span>{" "}
                            of{" "}
                            <span className="text-brand-dark font-semibold">{bookmarks.total}</span>{" "}
                            bookmarked events
                          </p>
                        </div>

                        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                          {bookmarks.items.map((event) => (
                            <BookmarkedEventCard key={event.id} event={event} />
                          ))}
                        </div>

                        {bookmarks.total_pages > 1 ? (
                          <div className="mt-5 flex items-center justify-center gap-3">
                            <button
                              type="button"
                              onClick={() => handleBookmarkPageChange(bookmarkPage - 1)}
                              disabled={bookmarkPage <= 1}
                              className={cn(
                                "flex size-9 items-center justify-center rounded-full border transition-colors",
                                bookmarkPage <= 1
                                  ? "border-brand-mid/10 text-brand-mid/40 cursor-not-allowed"
                                  : "border-brand-mid/20 text-brand-dark hover:bg-brand-mid-alpha/70",
                              )}
                            >
                              <ChevronLeft className="size-4" />
                            </button>

                            <p className="text-brand-dark text-sm font-semibold">
                              Page {bookmarkPage} / {bookmarks.total_pages}
                            </p>

                            <button
                              type="button"
                              onClick={() => handleBookmarkPageChange(bookmarkPage + 1)}
                              disabled={bookmarkPage >= bookmarks.total_pages}
                              className={cn(
                                "flex size-9 items-center justify-center rounded-full border transition-colors",
                                bookmarkPage >= bookmarks.total_pages
                                  ? "border-brand-mid/10 text-brand-mid/40 cursor-not-allowed"
                                  : "border-brand-mid/20 text-brand-dark hover:bg-brand-mid-alpha/70",
                              )}
                            >
                              <ChevronRight className="size-4" />
                            </button>
                          </div>
                        ) : null}
                      </>
                    ) : (
                      <div className="border-brand-mid/12 bg-brand-bg/75 rounded-[24px] border px-6 py-12 text-center">
                        <div className="bg-brand-mid/12 text-brand-mid mx-auto flex size-16 items-center justify-center rounded-full">
                          <Bookmark className="size-7" />
                        </div>
                        <p className="font-heading text-brand-dark mt-4 text-2xl">
                          No bookmarked events yet
                        </p>
                        <p className="text-brand-mid mt-2 text-sm">
                          Save interesting events from discovery to keep them handy here.
                        </p>
                        <Button
                          asChild
                          className="bg-brand-dark hover:bg-brand-dark/85 mt-5 border-0 text-white"
                        >
                          <Link href="/">Explore Events</Link>
                        </Button>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </section>
            ) : null}

            {activeSection === "my-events" ? (
              <section className="space-y-6">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
                  <div>
                    <h2 className="font-heading text-brand-dark text-3xl font-bold">My Events</h2>
                    <p className="text-brand-mid mt-1 text-sm">
                      Manage events you&apos;ve created.
                    </p>
                  </div>

                  <Button
                    asChild
                    className="bg-brand-dark hover:bg-brand-dark/85 border-0 text-white"
                  >
                    <Link href={CREATE_EVENT_PAGE_PATH}>
                      <Plus className="size-4" />
                      Create New Event
                    </Link>
                  </Button>
                </div>

                <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                  <div className="bg-brand-surface flex items-center gap-3 rounded-[22px] px-5 py-4">
                    <CalendarDays className="text-brand-dark size-6" />
                    <div>
                      <p className="text-brand-dark text-xl font-bold">{hostedEvents.length}</p>
                      <p className="text-brand-mid text-xs">Total Events</p>
                    </div>
                  </div>
                  <div className="bg-brand-surface flex items-center gap-3 rounded-[22px] px-5 py-4">
                    <div className="size-3 rounded-full bg-emerald-500" />
                    <div>
                      <p className="text-brand-dark text-xl font-bold">{liveEventCount}</p>
                      <p className="text-brand-mid text-xs">Live</p>
                    </div>
                  </div>
                  <div className="bg-brand-surface flex items-center gap-3 rounded-[22px] px-5 py-4">
                    <Users className="text-brand-dark size-6" />
                    <div>
                      <p className="text-brand-dark text-xl font-bold">{totalHostedAttendees}</p>
                      <p className="text-brand-mid text-xs">Total Attendees</p>
                    </div>
                  </div>
                  <div className="bg-brand-surface flex items-center gap-3 rounded-[22px] px-5 py-4">
                    <Shield className="text-brand-dark size-6" />
                    <div>
                      <p className="text-brand-dark text-xl font-bold">
                        {hostProfile?.average_rating !== null &&
                        hostProfile?.average_rating !== undefined
                          ? `${hostProfile.average_rating.toFixed(1)} ★`
                          : "New"}
                      </p>
                      <p className="text-brand-mid text-xs">Avg Rating</p>
                    </div>
                  </div>
                </div>

                <div className="border-brand-mid/15 overflow-x-auto border-b">
                  <div className="flex min-w-max gap-0">
                    {(
                      [
                        { key: "upcoming", label: "Upcoming", count: upcomingHostedEvents.length },
                        { key: "past", label: "Past", count: pastHostedEvents.length },
                        { key: "draft", label: "Draft", count: draftHostedEvents.length },
                      ] as const
                    ).map((tab) => (
                      <button
                        key={tab.key}
                        type="button"
                        onClick={() => setEventsTab(tab.key)}
                        className={cn(
                          "inline-flex cursor-pointer items-center gap-2 border-b-[3px] px-6 py-3 text-sm transition-colors",
                          eventsTab === tab.key
                            ? "border-brand-dark text-brand-dark font-bold"
                            : "text-brand-mid hover:text-brand-dark border-transparent font-medium",
                        )}
                      >
                        {tab.label}
                        <span
                          className={cn(
                            "rounded-full px-1.5 py-0.5 text-[10px] font-semibold",
                            eventsTab === tab.key
                              ? "bg-brand-dark text-white"
                              : "bg-brand-surface text-brand-mid",
                          )}
                        >
                          {tab.count}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>

                {hostProfileError ? (
                  <div className="rounded-[20px] border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                    {hostProfileError}
                  </div>
                ) : hostProfileLoading ? (
                  <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                    {Array.from({ length: 3 }).map((_, index) => (
                      <div
                        key={index}
                        className="border-brand-mid/12 overflow-hidden rounded-[24px] border bg-white"
                      >
                        <div className="bg-brand-mid/15 h-44 animate-pulse" />
                        <div className="space-y-3 p-5">
                          <div className="bg-brand-mid/12 h-4 animate-pulse rounded-full" />
                          <div className="bg-brand-mid/10 h-4 w-2/3 animate-pulse rounded-full" />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : visibleHostedEvents.length > 0 ? (
                  <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                    {visibleHostedEvents.map((event) => (
                      <HostedEventCard
                        key={event.id}
                        event={event}
                        isCancelling={cancellingEventId === event.id}
                        onQuickCancel={(eventId) => {
                          void handleQuickCancel(eventId);
                        }}
                      />
                    ))}
                  </div>
                ) : (
                  <div className="border-brand-mid/12 rounded-[24px] border bg-white px-6 py-12 text-center">
                    <p className="font-heading text-brand-dark text-2xl">No {eventsTab} events</p>
                    <p className="text-brand-mid mt-2 text-sm">
                      {eventsTab === "upcoming"
                        ? "Create a new event or publish an existing draft to see it here."
                        : eventsTab === "past"
                          ? "Past, ended, and cancelled events will appear here once they exist."
                          : "Draft events you are still working on will appear here."}
                    </p>
                  </div>
                )}
              </section>
            ) : null}
          </div>
        </main>
      </div>
    </ProtectedRoute>
  );
}
