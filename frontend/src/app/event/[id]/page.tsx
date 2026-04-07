"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowLeft,
  Bookmark,
  BookmarkCheck,
  Calendar,
  Car,
  Check,
  CheckCircle,
  Clock,
  Copy,
  Edit,
  Globe,
  Info,
  Link2,
  Loader2,
  Lock,
  MapPin,
  MessageSquareOff,
  Shield,
  Users,
  Accessibility,
  XCircle,
} from "lucide-react";

import { useAuth } from "@/hooks/use-auth";
import { useEventInteraction } from "@/hooks/use-event-interaction";
import { Navbar } from "@/components/layout/navbar";
import { StatusBadge, eventStatusVariant } from "@/components/event/status-badge";
import { ImageCarousel } from "@/components/event/image-carousel";
import { CommentSection } from "@/components/event/comment-section";
import { ConfirmDialog } from "@/components/event/confirm-dialog";
import { AttendeeAvatarStack } from "@/components/event/attendee-avatar-stack";
import { LocationMapModal } from "@/components/event/location-map-modal";
import { cn } from "@/lib/utils";
import {
  clearAccessRequestPending,
  isAccessRequestPending,
  markAccessRequestPending,
} from "@/lib/access-request-store";
import {
  fetchEventDetail,
  fetchHostProfile,
  changeEventStatus,
  requestAccess,
  fetchAccessRequests,
  updateAccessRequest,
  createInvite,
  fetchInvites,
  type EventDetail,
  type EventDetailLimited,
  type AnyEventDetail,
  type HostProfile,
  type AccessRequest,
  type Invite,
} from "@/lib/events-api";

// ─── Helpers ───────────────────────────────────────────────────────────────────

function formatDate(dt: string) {
  return new Date(dt).toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function formatTime(dt: string) {
  return new Date(dt).toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function starRating(rating: number) {
  return Array.from({ length: 5 }, (_, i) => (
    <svg
      key={i}
      className={cn("size-3.5", i < Math.round(rating) ? "text-brand-mid" : "text-brand-mid/30")}
      fill="currentColor"
      viewBox="0 0 20 20"
    >
      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
    </svg>
  ));
}

function buildGoogleCalendarUrl(event: EventDetail, locationName?: string) {
  const fmt = (dt: string) => new Date(dt).toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, "");
  const params = new URLSearchParams({
    action: "TEMPLATE",
    text: event.title,
    dates: `${fmt(event.start_datetime)}/${fmt(event.end_datetime)}`,
    details: event.description || "",
  });
  if (locationName) params.set("location", locationName);
  return `https://calendar.google.com/calendar/render?${params.toString()}`;
}

async function copyTextWithFallback(value: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(value);
    return true;
  } catch {
    if (typeof document === "undefined") {
      return false;
    }

    const textarea = document.createElement("textarea");
    textarea.value = value;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    textarea.style.pointerEvents = "none";
    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();

    try {
      return document.execCommand("copy");
    } catch {
      return false;
    } finally {
      document.body.removeChild(textarea);
    }
  }
}

// ─── Age gate (18+ events) ────────────────────────────────────────────────────

function isAtLeast18(dob: string): boolean {
  const birth = new Date(dob);
  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  const m = today.getMonth() - birth.getMonth();
  if (m < 0 || (m === 0 && today.getDate() < birth.getDate())) age--;
  return age >= 18;
}

function AgeGate({
  eventId,
  isAuthenticated,
  userDob,
}: {
  eventId: string;
  isAuthenticated: boolean;
  userDob: string | null;
}) {

  // If user has dob and is underage — show block screen
  if (userDob && !isAtLeast18(userDob)) {
    return (
      <div className="min-h-[80vh] relative overflow-hidden flex flex-col items-center justify-center px-6 py-20 text-center">
        <span className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 font-heading text-[200px] font-bold text-brand-dark/[0.06] select-none pointer-events-none leading-none max-sm:text-[120px]">
          18+
        </span>
        <div className="relative z-[1]">
          <div className="mb-6">
            <AlertTriangle className="size-20 text-red-400 mx-auto" strokeWidth={1.5} />
          </div>
          <h1 className="font-heading text-4xl font-bold text-brand-dark mb-4">Age Restricted Event</h1>
          <p className="text-[17px] leading-[1.7] text-brand-dark/75 max-w-[440px] mb-2">
            This event is restricted to attendees aged 18 and above.
          </p>
          <p className="text-[15px] text-brand-mid max-w-[400px] mb-8">
            Your account indicates you do not meet the age requirement for this event.
          </p>
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-[15px] font-bold text-brand-mid hover:text-brand-dark transition-colors"
          >
            <ArrowLeft className="size-4" />
            Back to Discovery
          </Link>
        </div>
      </div>
    );
  }

  // Guests and users without a stored DOB cannot access 18+ events by default.
  return (
    <div className="min-h-[80vh] relative overflow-hidden flex flex-col items-center justify-center px-6 py-20 text-center">
      <span className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 font-heading text-[200px] font-bold text-brand-dark/[0.06] select-none pointer-events-none leading-none max-sm:text-[120px]">
        18+
      </span>
      <div className="relative z-[1] flex flex-col items-center max-w-[600px]">
        <div className="mb-6">
          <AlertTriangle className="size-20 text-red-400 mx-auto" strokeWidth={1.5} />
        </div>
        <h1 className="font-heading text-4xl font-bold text-brand-dark mb-4">Age Restricted Event</h1>
        <p className="text-[17px] leading-[1.7] text-brand-dark/75 max-w-[440px]">
          This event is restricted to attendees aged 18 and above.
        </p>

        <div className="bg-brand-surface rounded-xl p-8 max-w-[420px] w-full mt-8 text-center">
          {isAuthenticated ? (
            <>
              <h3 className="font-heading text-xl font-semibold text-brand-dark mb-3">
                Date of birth required
              </h3>
              <p className="text-[15px] leading-[1.7] text-brand-dark/75 mb-6">
                Add your date of birth in your profile settings to access 18+ events.
              </p>
              <Link
                href="/profile/me"
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-brand-dark border-2 border-brand-dark px-7 py-3.5 text-[15px] font-bold text-white transition-all hover:bg-[#5e4535] hover:border-[#5e4535] hover:-translate-y-0.5 hover:shadow-lg"
              >
                Go to Profile
              </Link>
            </>
          ) : (
            <>
              <h3 className="font-heading text-xl font-semibold text-brand-dark mb-3">
                Sign in to continue
              </h3>
              <p className="text-[15px] leading-[1.7] text-brand-dark/75 mb-6">
                Sign in with an account that has a verified date of birth to access this 18+ event.
              </p>
              <Link
                href={`/login?next=/event/${eventId}`}
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-brand-dark border-2 border-brand-dark px-7 py-3.5 text-[15px] font-bold text-white transition-all hover:bg-[#5e4535] hover:border-[#5e4535] hover:-translate-y-0.5 hover:shadow-lg"
              >
                Sign In
              </Link>
            </>
          )}
        </div>

        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-[15px] font-bold text-brand-mid hover:text-brand-dark transition-colors mt-6"
        >
          <ArrowLeft className="size-4" />
          Back to Discovery
        </Link>
      </div>
    </div>
  );
}

// ─── Limited view (guest / private non-host) ──────────────────────────────────

function LimitedView({
  event,
  isGuest,
  currentUserId,
}: {
  event: EventDetailLimited;
  isGuest: boolean;
  currentUserId: string | null;
}) {
  const [requestState, setRequestState] = useState<"idle" | "loading" | "error">("idle");
  const isPendingRequest =
    !isGuest &&
    (
      event.access_request_status === "pending" ||
      isAccessRequestPending(event.id, currentUserId)
    );
  const accessStatus: "idle" | "loading" | "pending" | "error" =
    requestState === "loading" || requestState === "error"
      ? requestState
      : isPendingRequest
      ? "pending"
      : "idle";

  useEffect(() => {
    if (isGuest || !currentUserId) {
      return;
    }

    if (event.access_request_status === "pending") {
      markAccessRequestPending(event.id, currentUserId);
      return;
    }

    if (event.access_request_status === "approved") {
      clearAccessRequestPending(event.id, currentUserId);
      return;
    }

    if (event.access_request_status === "rejected") {
      clearAccessRequestPending(event.id, currentUserId);
    }
  }, [currentUserId, event.access_request_status, event.id, isGuest]);

  async function handleRequestAccess() {
    setRequestState("loading");
    try {
      await requestAccess(event.id);
      markAccessRequestPending(event.id, currentUserId);
      setRequestState("idle");
    } catch (err: unknown) {
      const message = (
        err && typeof err === "object" && "message" in err
          ? (err as { message: string }).message
          : ""
      ).toLowerCase();
      if (message.includes("already granted")) {
        clearAccessRequestPending(event.id, currentUserId);
        setRequestState("idle");
        window.location.href = `/event/${event.id}`;
      } else if (message.includes("already exists")) {
        markAccessRequestPending(event.id, currentUserId);
        setRequestState("idle");
      } else {
        setRequestState("error");
      }
    }
  }

  return (
    <div className="max-w-screen-xl mx-auto px-10 py-16 flex flex-col items-center gap-6 text-center">
      {/* Faint background code */}
      <span className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 font-heading text-[200px] font-bold text-brand-dark/[0.06] select-none pointer-events-none leading-none z-0 max-sm:text-[120px]">
        403
      </span>

      <div className="relative z-[1] flex size-16 items-center justify-center rounded-full bg-brand-mid-alpha">
        {isGuest ? (
          <Users className="size-8 text-brand-mid" />
        ) : (
          <Lock className="size-8 text-brand-mid" />
        )}
      </div>

      <div className="relative z-[1]">
        <div className="flex flex-wrap gap-2 justify-center mb-3">
          {event.categories.map((cat) => (
            <span
              key={cat.id}
              className="bg-brand-dark/10 text-brand-dark rounded-full px-3 py-0.5 text-[12px] font-bold"
            >
              {cat.name}
            </span>
          ))}
        </div>
        <h1 className="font-heading text-brand-dark text-2xl font-bold mb-2">{event.title}</h1>
        <p className="text-brand-mid text-sm font-semibold">
          {formatDate(event.start_datetime)} · {formatTime(event.start_datetime)}
        </p>
      </div>

      <div className="relative z-[1] bg-brand-surface rounded-xl border border-brand-mid-alpha px-6 py-8 w-full max-w-lg">
        {isGuest ? (
          <>
            <p className="text-brand-dark font-semibold mb-1">Sign in for the full experience</p>
            <p className="text-brand-mid text-sm mb-5">
              View the description, location, attendees, and interact with this event.
            </p>
            <div className="flex gap-3 justify-center">
              <Link
                href={`/login?next=/event/${event.id}`}
                className="rounded-lg bg-brand-dark px-5 py-2.5 text-sm font-bold text-white transition-colors hover:bg-brand-dark/85"
              >
                Sign In
              </Link>
              <Link
                href={`/register?next=/event/${event.id}`}
                className="rounded-lg border border-brand-mid-alpha px-5 py-2.5 text-sm font-bold text-brand-dark transition-colors hover:bg-brand-mid-alpha"
              >
                Sign Up
              </Link>
            </div>
          </>
        ) : event.status === "cancelled" ? (
          <>
            <XCircle className="size-6 text-red-500 mx-auto mb-3 opacity-70" />
            <p className="text-brand-dark font-semibold mb-1">This event has been cancelled</p>
            <p className="text-brand-mid text-sm">
              The host cancelled this event. It is no longer taking place.
            </p>
          </>
        ) : (
          <>
            <Lock className="size-6 text-brand-mid mx-auto mb-3 opacity-50" />
            <p className="text-brand-dark font-semibold mb-1">This is a private event</p>
            <p className="text-brand-mid text-sm mb-5">
              Only the host and invited attendees can view the full details.
            </p>

            {accessStatus === "pending" ? (
              <div className="flex items-center justify-center gap-2 rounded-lg bg-brand-dark/10 px-5 py-3 text-sm font-bold text-brand-dark">
                <Clock className="size-4" />
                Access Requested — Pending
              </div>
            ) : (
              <button
                onClick={() => { void handleRequestAccess(); }}
                disabled={accessStatus === "loading"}
                className="w-full flex items-center justify-center gap-2 rounded-lg bg-brand-dark px-5 py-3 text-sm font-bold text-white transition-all hover:bg-brand-dark/85 hover:-translate-y-0.5 hover:shadow-lg cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {accessStatus === "loading" ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <Lock className="size-4" />
                )}
                {accessStatus === "loading" ? "Sending Request…" : "Request Access"}
              </button>
            )}
            {accessStatus === "error" && (
              <p className="text-red-500 text-xs mt-2">Failed to send request. Please try again.</p>
            )}
          </>
        )}
      </div>

      {/* Back to discovery */}
      <Link
        href="/"
        className="relative z-[1] inline-flex items-center gap-1.5 text-[15px] font-bold text-brand-mid hover:text-brand-dark transition-colors mt-2"
      >
        <ArrowLeft className="size-4" />
        Back to Discovery
      </Link>
    </div>
  );
}

// ─── Full view ─────────────────────────────────────────────────────────────────

function FullView({
  event,
  host,
  isHost,
  currentUserId,
  isAuthenticated,
}: {
  event: EventDetail;
  host: HostProfile | null;
  isHost: boolean;
  currentUserId: string | null;
  isAuthenticated: boolean;
}) {
  const router = useRouter();

  const { bookmarked, bookmarkCount, going: isGoing, goingCount, toggleBookmark, toggleGoing } =
    useEventInteraction({
      eventId: event.id,
      initialBookmarked: event.is_bookmarked === true,
      initialBookmarkCount: event.bookmark_count ?? 0,
      initialGoing: event.attendance_status === "going",
      initialGoingCount: event.going_count ?? 0,
      fresh: true, // Detail page has fresh server data — overwrite stale card state
    });

  const [showCancelDialog, setShowCancelDialog] = useState(false);
  const [cancelLoading, setCancelLoading] = useState(false);
  const [showMapModal, setShowMapModal] = useState(false);
  const [goingPressed, setGoingPressed] = useState(false);
  const [bookmarkPressed, setBookmarkPressed] = useState(false);

  // Invite & access request state (host only)
  const [invites, setInvites] = useState<Invite[]>([]);
  const [accessRequests, setAccessRequests] = useState<AccessRequest[]>([]);
  const [inviteLoading, setInviteLoading] = useState(false);
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [inviteNotice, setInviteNotice] = useState<string | null>(null);
  const [manualInviteUrl, setManualInviteUrl] = useState<string | null>(null);
  const [copiedToken, setCopiedToken] = useState<string | null>(null);
  const [requestActionLoading, setRequestActionLoading] = useState<string | null>(null);

  const commentScrollRef = useRef<HTMLDivElement>(null);
  const leftColRef = useRef<HTMLDivElement>(null);
  const rightColRef = useRef<HTMLDivElement>(null);
  const leftTrackRef = useRef<HTMLDivElement>(null);
  const rightTrackRef = useRef<HTMLDivElement>(null);

  // Custom scroll indicator — thin line that thickens at current position
  useEffect(() => {
    function updateIndicator(container: HTMLDivElement | null, track: HTMLDivElement | null) {
      if (!container || !track) return;
      const maxScroll = container.scrollHeight - container.clientHeight;
      if (maxScroll <= 0) {
        track.style.opacity = "0";
        return;
      }
      track.style.opacity = "1";
      const ratio = container.scrollTop / maxScroll;
      const thumbHeight = Math.max(20, (container.clientHeight / container.scrollHeight) * 100);
      const topPercent = ratio * (100 - thumbHeight);
      track.style.setProperty("--thumb-top", `${topPercent}%`);
      track.style.setProperty("--thumb-height", `${thumbHeight}%`);
    }

    const left = leftColRef.current;
    const right = rightColRef.current;
    const lt = leftTrackRef.current;
    const rt = rightTrackRef.current;

    const onLeftScroll = () => updateIndicator(left, lt);
    const onRightScroll = () => updateIndicator(right, rt);

    left?.addEventListener("scroll", onLeftScroll, { passive: true });
    right?.addEventListener("scroll", onRightScroll, { passive: true });

    // Initial
    updateIndicator(left, lt);
    updateIndicator(right, rt);

    return () => {
      left?.removeEventListener("scroll", onLeftScroll);
      right?.removeEventListener("scroll", onRightScroll);
    };
  }, []);

  const status = event.status;
  const isActive = status === "published" || status === "updated";
  const isCancelled = status === "cancelled";
  const isEnded = status === "ended";
  const isFull = event.is_full === true || (event.attendee_limit != null && goingCount >= event.attendee_limit);
  const primaryLocation = event.locations && event.locations.length > 0
    ? (event.locations.find((l) => l.is_primary) ?? event.locations[0])
    : null;

  // Fetch invites & access requests for host on private events
  useEffect(() => {
    if (!isHost || event.visibility !== "private") return;
    void fetchInvites(event.id).then(setInvites).catch(() => {});
    void fetchAccessRequests(event.id).then(setAccessRequests).catch(() => {});
  }, [isHost, event.id, event.visibility]);

  async function handleCancel() {
    setCancelLoading(true);
    try {
      await changeEventStatus(event.id, "cancelled");
      router.refresh();
    } finally {
      setCancelLoading(false);
      setShowCancelDialog(false);
    }
  }

  async function handleCreateInvite() {
    setInviteLoading(true);
    setInviteError(null);
    setInviteNotice(null);
    setManualInviteUrl(null);
    try {
      const invite = await createInvite(event.id);
      setInvites((prev) => [invite, ...prev]);
      const copied = await copyTextWithFallback(invite.invite_url);
      if (copied) {
        setCopiedToken(invite.token);
        setTimeout(() => setCopiedToken(null), 2000);
      } else {
        setInviteNotice("Invite created, but automatic copy was blocked. Copy the link manually below.");
        setManualInviteUrl(invite.invite_url);
      }
    } catch (err: unknown) {
      const message = err && typeof err === "object" && "message" in err
        ? (err as { message: string }).message
        : "Failed to generate invite link. Please try again.";
      setInviteError(message);
    } finally {
      setInviteLoading(false);
    }
  }

  async function handleCopyInviteLink(invite: Invite) {
    setInviteError(null);
    const copied = await copyTextWithFallback(invite.invite_url);
    if (copied) {
      setInviteNotice(null);
      setManualInviteUrl(null);
      setCopiedToken(invite.token);
      setTimeout(() => setCopiedToken(null), 2000);
      return;
    }

    setInviteNotice("Copy is blocked in this browser context. Copy the link manually below.");
    setManualInviteUrl(invite.invite_url);
  }

  async function handleAccessRequestAction(requestId: string, action: "approved" | "rejected") {
    setRequestActionLoading(requestId);
    try {
      await updateAccessRequest(event.id, requestId, action);
      setAccessRequests((prev) => prev.filter((r) => r.id !== requestId));
    } finally {
      setRequestActionLoading(null);
    }
  }

  // ── Info banner (full-width strip above back link) ───────────────────────────

  const infoBanner = isCancelled ? (
    <div className="flex items-center gap-2 px-10 py-2.5 text-sm font-bold text-white bg-danger">
      <XCircle className="size-4 shrink-0" />
      This event has been cancelled by the host.
    </div>
  ) : isEnded ? (
    <div className="flex items-center gap-2 px-10 py-2.5 text-sm font-bold text-brand-dark bg-brand-surface">
      <Clock className="size-4 shrink-0" />
      This event has ended.
    </div>
  ) : isFull ? (
    <div className="flex items-center gap-2 px-10 py-2.5 text-sm font-bold text-white bg-warning">
      <Users className="size-4 shrink-0" />
      This event is fully booked. Bookmark it to get notified if a spot opens up.
    </div>
  ) : !isAuthenticated ? (
    <div className="flex items-center gap-2 px-10 py-2.5 text-sm font-bold text-brand-dark bg-brand-surface">
      <Info className="size-4 shrink-0" />
      <span>
        You are browsing as a guest.{" "}
        <Link href={`/login?next=/event/${event.id}`} className="underline hover:text-brand-mid">
          Sign in
        </Link>{" "}
        to interact with this event.
      </span>
    </div>
  ) : null;

  return (
    <>
      <ConfirmDialog
        open={showCancelDialog}
        title="Cancel this event?"
        description="This action cannot be undone. All attendees will be notified that the event has been cancelled."
        confirmLabel="Yes, Cancel Event"
        confirmVariant="danger"
        loading={cancelLoading}
        onConfirm={() => { void handleCancel(); }}
        onCancel={() => setShowCancelDialog(false)}
      />

      {infoBanner}

      {/* Back link — full width */}
      <div className="max-w-screen-xl mx-auto">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 px-4 py-4 sm:px-6 lg:px-10 text-sm font-bold text-brand-mid hover:text-brand-dark transition-colors"
        >
          <ArrowLeft className="size-4" />
          Back to Discovery
        </Link>
      </div>

      {/* Main content */}
      <div
        className={cn(
          "max-w-screen-xl mx-auto px-4 sm:px-6 lg:px-10 pb-16 flex gap-8 lg:h-[calc(100vh-120px)] overflow-x-hidden",
          isCancelled && "opacity-70",
        )}
      >
        {/* ── Left column ─────────────────────────────────────────────────── */}
        <div className="relative w-full min-w-0 lg:flex-[0_0_65%]">
          {/* Scroll indicator track */}
          <div
            ref={leftTrackRef}
            className="pointer-events-none absolute right-0 top-0 bottom-0 w-[3px] z-10 transition-opacity duration-300"
            style={{ opacity: 0 }}
          >
            <div className="absolute inset-x-0 top-0 bottom-0 bg-brand-mid/10 rounded-full" />
            <div
              className="absolute inset-x-0 bg-brand-mid/40 rounded-full transition-all duration-100"
              style={{ top: "var(--thumb-top, 0%)", height: "var(--thumb-height, 20%)" }}
            />
          </div>
        <div ref={leftColRef} className="lg:h-full overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          {/* Carousel */}
          <div className="mb-6">
            <ImageCarousel images={event.images ?? []} title={event.title} />
          </div>

          {/* Title + badges */}
          <div className="mb-4">
            <div className="flex flex-wrap items-center gap-3 mb-2">
              <h1 className="font-heading text-brand-dark text-[24px] sm:text-[28px] lg:text-[32px] font-bold leading-tight">
                {event.title}
              </h1>
              {event.visibility === "private" && <StatusBadge variant="private" />}
              <StatusBadge variant={eventStatusVariant(status, isFull)} />
              {event.is_age_restricted && (
                <span className="inline-flex items-center rounded-full bg-brand-dark px-3 py-1 text-[11px] font-extrabold uppercase tracking-wide text-white">
                  18+
                </span>
              )}
            </div>
            {/* Categories */}
            <div className="flex flex-wrap gap-2 mb-2">
              {(event.categories ?? []).map((cat) => (
                <span
                  key={cat.id}
                  className="bg-brand-dark/10 text-brand-dark rounded-full px-3 py-1 text-[12px] font-bold"
                >
                  {cat.name}
                </span>
              ))}
            </div>
            {/* Meta: Created by · Posted X days ago */}
            <p className="text-brand-mid text-sm font-semibold mt-2">
              {host && (
                <>
                  Created by{" "}
                  <Link
                    href={`/profile/${event.host_id}`}
                    className="text-brand-dark font-bold hover:underline"
                  >
                    {host.username}
                  </Link>
                  {" · "}
                </>
              )}
              Posted {(() => {
                const now = new Date();
                const created = new Date(event.created_at);
                const days = Math.floor((now.getTime() - created.getTime()) / (1000 * 60 * 60 * 24));
                if (days === 0) return "today";
                if (days === 1) return "1 day ago";
                return `${days} days ago`;
              })()}
            </p>
          </div>

          {/* Description */}
          <section className="mb-6">
            <h3 className="font-heading text-brand-dark text-lg font-semibold mb-3">
              About this event
            </h3>
            <p className="text-[15px] leading-[1.7] text-brand-dark whitespace-pre-wrap break-words">
              {event.description}
            </p>
          </section>

          {/* Equipment requirements */}
          {(event.equipment_requirements ?? []).length > 0 && (
            <section className="mb-6">
              <h3 className="font-heading text-brand-dark text-lg font-semibold mb-3">
                What to bring
              </h3>
              <div className="space-y-2">
                {(event.equipment_requirements ?? []).map((eq) => (
                  <div key={eq.id} className="flex items-center gap-2 text-sm text-brand-dark">
                    {eq.is_required ? (
                      <Check className="size-4 text-brand-mid shrink-0" />
                    ) : (
                      <span className="inline-flex size-4 shrink-0 items-center justify-center rounded-full border-2 border-brand-mid-alpha text-[9px] text-brand-mid">○</span>
                    )}
                    <span>
                      {eq.item_name}
                      {!eq.is_required && (
                        <span className="ml-1 text-brand-mid/70">(optional)</span>
                      )}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Venue metadata */}
          {event.venue_metadata && (
            <section className="mb-8">
              <h3 className="font-heading text-brand-dark text-lg font-semibold mb-3">
                Venue details
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {event.venue_metadata.price && (
                  <div className="flex items-center gap-2 text-sm text-brand-dark">
                    <span className="text-base">🎟️</span>
                    {event.venue_metadata.price}
                  </div>
                )}
                {event.venue_metadata.language && (
                  <div className="flex items-center gap-2 text-sm text-brand-dark">
                    <Globe className="size-4 text-brand-mid" />
                    {event.venue_metadata.language}
                  </div>
                )}
                {event.venue_metadata.wheelchair_access && (
                  <div className="flex items-center gap-2 text-sm text-brand-dark">
                    <Accessibility className="size-4 text-brand-mid" />
                    Wheelchair accessible
                  </div>
                )}
                {event.venue_metadata.accessible_restroom && (
                  <div className="flex items-center gap-2 text-sm text-brand-dark">
                    <Shield className="size-4 text-brand-mid" />
                    Accessible restroom
                  </div>
                )}
                {event.venue_metadata.elevator_available && (
                  <div className="flex items-center gap-2 text-sm text-brand-dark">
                    <Car className="size-4 text-brand-mid" />
                    Elevator available
                  </div>
                )}
                {event.venue_metadata.seating_available && (
                  <div className="flex items-center gap-2 text-sm text-brand-dark">
                    <Users className="size-4 text-brand-mid" />
                    Seating available
                  </div>
                )}
                {event.venue_metadata.captions_support && (
                  <div className="flex items-center gap-2 text-sm text-brand-dark">
                    <Info className="size-4 text-brand-mid" />
                    Captions support
                  </div>
                )}
                {event.venue_metadata.quiet_friendly && (
                  <div className="flex items-center gap-2 text-sm text-brand-dark">
                    <Info className="size-4 text-brand-mid" />
                    Quiet-friendly
                  </div>
                )}
              </div>
              {event.venue_metadata.health_requirements && (
                <p className="mt-3 text-sm text-brand-mid">
                  {event.venue_metadata.health_requirements}
                </p>
              )}
            </section>
          )}

          {/* Comments */}
          {!isCancelled ? (
            <section>
              <CommentSection
                eventId={event.id}
                isAuthenticated={isAuthenticated}
                currentUserId={currentUserId}
                scrollRef={commentScrollRef}
                disabled={!isActive}
                disabledReason={!isActive ? "Comments are closed for this event" : undefined}
              />
            </section>
          ) : (
            <div className="flex items-center gap-2 text-sm text-brand-mid py-4">
              <MessageSquareOff className="size-4" />
              Comments are closed for cancelled events.
            </div>
          )}
        </div>
        </div>{/* close relative wrapper for left column */}

        {/* ── Right sidebar ────────────────────────────────────────────── */}
        <div className="hidden lg:flex relative flex-[0_0_calc(35%-2rem)] min-w-0">
          {/* Scroll indicator track */}
          <div
            ref={rightTrackRef}
            className="pointer-events-none absolute right-0 top-0 bottom-0 w-[3px] z-10 transition-opacity duration-300"
            style={{ opacity: 0 }}
          >
            <div className="absolute inset-x-0 top-0 bottom-0 bg-brand-mid/10 rounded-full" />
            <div
              className="absolute inset-x-0 bg-brand-mid/40 rounded-full transition-all duration-100"
              style={{ top: "var(--thumb-top, 0%)", height: "var(--thumb-height, 20%)" }}
            />
          </div>
        <div ref={rightColRef} className="h-full w-full overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden flex-col gap-4 flex">
          {/* Action buttons */}
          <div className="bg-white rounded-xl border border-brand-mid-alpha p-5 space-y-2">
            {isHost ? (
              <>
                <p className="text-[11px] font-bold uppercase tracking-widest text-brand-mid mb-3">
                  Host Actions
                </p>
                <button
                  onClick={() => router.push(`/edit-event/${event.id}`)}
                  disabled={isCancelled || isEnded}
                  className="w-full flex items-center justify-center gap-2 rounded-[10px] border-2 border-brand-dark py-3 text-[15px] font-bold text-brand-dark transition-colors hover:bg-brand-dark/10 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <Edit className="size-[18px]" />
                  Edit Event
                </button>
                {isActive && (
                  <button
                    onClick={() => setShowCancelDialog(true)}
                    className="w-full flex items-center justify-center gap-2 rounded-[10px] border-2 border-danger py-3 text-[15px] font-bold text-danger transition-colors hover:bg-danger/8 cursor-pointer"
                  >
                    <XCircle className="size-[18px]" />
                    Cancel Event
                  </button>
                )}
                <Link
                  href={`/event/${event.id}/attendees`}
                  className="w-full flex items-center justify-center gap-2 rounded-[10px] bg-brand-dark py-3 text-[15px] font-bold text-white transition-colors hover:bg-brand-dark/85"
                >
                  <Users className="size-[18px]" />
                  Manage Attendees
                </Link>
              </>
            ) : isAuthenticated ? (
              <>
                <button
                  onClick={() => { void toggleGoing(); }}
                  onMouseDown={() => setGoingPressed(true)}
                  onMouseUp={() => setGoingPressed(false)}
                  onMouseLeave={() => setGoingPressed(false)}
                  disabled={!isActive || (isFull && !isGoing)}
                  className={cn(
                    "w-full flex items-center justify-center gap-2 rounded-[10px] py-3 text-[15px] font-bold transition-all duration-150 cursor-pointer",
                    isGoing
                      ? "bg-brand-dark text-white hover:bg-brand-dark/80 hover:shadow-md"
                      : !isActive || (isFull && !isGoing)
                      ? "bg-brand-mid-alpha text-brand-dark/40 !cursor-not-allowed"
                      : "bg-brand-mid text-white hover:bg-brand-mid/80 hover:shadow-md",
                    goingPressed && !(!isActive || (isFull && !isGoing))
                      && "scale-[0.97] shadow-none",
                  )}
                >
                  <Check className="size-[18px]" />
                  {isGoing
                    ? "Attended ✓"
                    : isFull
                    ? "Sold Out"
                    : isEnded
                    ? "Event has ended"
                    : isCancelled
                    ? "Event Cancelled"
                    : "Going"}
                </button>
                <button
                  onClick={() => { void toggleBookmark(); }}
                  onMouseDown={() => setBookmarkPressed(true)}
                  onMouseUp={() => setBookmarkPressed(false)}
                  onMouseLeave={() => setBookmarkPressed(false)}
                  className={cn(
                    "w-full flex items-center justify-center gap-2 rounded-[10px] border-2 py-3 text-[15px] font-bold transition-all duration-150 cursor-pointer",
                    bookmarked
                      ? "bg-brand-dark border-brand-dark text-white hover:bg-brand-dark/80 hover:shadow-md"
                      : "border-brand-dark text-brand-dark hover:bg-brand-dark/10 hover:shadow-md",
                    bookmarkPressed && "scale-[0.97] shadow-none",
                  )}
                >
                  {bookmarked ? <BookmarkCheck className="size-[18px]" /> : <Bookmark className="size-[18px]" />}
                  {bookmarked ? "Saved" : "Bookmark"}
                </button>
                <p className="text-[12px] text-brand-mid text-center">
                  {goingCount} going · {bookmarkCount} bookmarked
                </p>
              </>
            ) : (
              <>
                <Link
                  href={`/login?next=/event/${event.id}`}
                  className="w-full flex items-center justify-center gap-2 rounded-[10px] bg-brand-mid-alpha py-3 text-[15px] font-bold text-brand-dark/60 transition-all duration-150 hover:bg-brand-mid/20 hover:text-brand-dark hover:shadow-md active:scale-[0.97]"
                >
                  Sign in to mark as Going
                </Link>
                <Link
                  href={`/login?next=/event/${event.id}`}
                  className="w-full flex items-center justify-center gap-2 rounded-[10px] border-2 border-brand-mid-alpha py-3 text-[15px] font-bold text-brand-dark/60 transition-all duration-150 hover:bg-brand-mid/10 hover:text-brand-dark hover:shadow-md active:scale-[0.97]"
                >
                  Sign in to Bookmark
                </Link>
                <p className="text-[12px] text-brand-mid text-center">
                  {goingCount} going · {bookmarkCount} bookmarked
                </p>
              </>
            )}
          </div>

          {/* Invite management — host only, private events */}
          {isHost && event.visibility === "private" && (
            <div className="bg-white rounded-xl border border-brand-mid-alpha p-5 space-y-4">
              <p className="text-[11px] font-bold uppercase tracking-widest text-brand-mid">
                Manage Invites
              </p>

              {/* Generate invite link */}
              <button
                onClick={() => { void handleCreateInvite(); }}
                disabled={inviteLoading || !isActive}
                className="w-full flex items-center justify-center gap-2 rounded-[10px] border-2 border-brand-dark py-3 text-[15px] font-bold text-brand-dark transition-colors hover:bg-brand-dark/10 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {inviteLoading ? (
                  <Loader2 className="size-[18px] animate-spin" />
                ) : (
                  <Link2 className="size-[18px]" />
                )}
                {inviteLoading ? "Generating…" : "Generate Invite Link"}
              </button>
              {inviteError && (
                <p className="text-[12px] text-red-500">{inviteError}</p>
              )}
              {inviteNotice && (
                <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2">
                  <p className="text-[12px] font-medium text-amber-700">{inviteNotice}</p>
                </div>
              )}
              {manualInviteUrl && (
                <div className="space-y-2 rounded-lg bg-brand-bg px-3 py-3">
                  <p className="text-[11px] font-bold uppercase tracking-widest text-brand-mid">
                    Manual Copy
                  </p>
                  <input
                    readOnly
                    value={manualInviteUrl}
                    onFocus={(e) => e.currentTarget.select()}
                    className="w-full rounded-lg border border-brand-mid-alpha bg-white px-3 py-2 text-[12px] text-brand-dark outline-none"
                  />
                </div>
              )}

              {/* Invite list */}
              {invites.length > 0 && (
                <div className="space-y-2">
                  <p className="text-[12px] font-bold text-brand-mid">
                    {invites.length} invite{invites.length !== 1 ? "s" : ""} created
                  </p>
                  {invites.slice(0, 5).map((inv) => (
                    <div
                      key={inv.id}
                      className="flex items-center justify-between gap-2 rounded-lg bg-brand-bg px-3 py-2"
                    >
                      <span className="text-[13px] text-brand-dark font-mono truncate flex-1">
                        …{inv.token.slice(-8)}
                      </span>
                      <span className={cn(
                        "text-[11px] font-bold",
                        inv.max_uses !== null && inv.use_count >= inv.max_uses
                          ? "text-brand-mid"
                          : "text-green-600",
                      )}>
                        {inv.max_uses !== null && inv.use_count >= inv.max_uses
                          ? `Used (${inv.use_count})`
                          : inv.max_uses !== null
                          ? `Active (${inv.use_count}/${inv.max_uses})`
                          : `Active (${inv.use_count})`}
                      </span>
                      <button
                        onClick={() => { void handleCopyInviteLink(inv); }}
                        className="p-1 rounded hover:bg-brand-mid-alpha transition-colors"
                        title="Copy invite link"
                      >
                        {copiedToken === inv.token ? (
                          <CheckCircle className="size-4 text-green-600" />
                        ) : (
                          <Copy className="size-4 text-brand-mid" />
                        )}
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Pending access requests */}
              {accessRequests.length > 0 && (
                <div className="space-y-2">
                  <p className="text-[12px] font-bold text-brand-dark">
                    Pending Requests ({accessRequests.length})
                  </p>
                  {accessRequests.map((req) => (
                    <div
                      key={req.id}
                      className="flex items-center justify-between gap-2 rounded-lg bg-brand-bg px-3 py-2"
                    >
                      <span className="text-[13px] font-bold text-brand-dark truncate flex-1">
                        {req.username}
                      </span>
                      <div className="flex gap-1.5">
                        <button
                          onClick={() => { void handleAccessRequestAction(req.id, "approved"); }}
                          disabled={requestActionLoading === req.id}
                          className="rounded-md bg-green-600 px-2.5 py-1 text-[11px] font-bold text-white hover:bg-green-700 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                          {requestActionLoading === req.id ? "…" : "Approve"}
                        </button>
                        <button
                          onClick={() => { void handleAccessRequestAction(req.id, "rejected"); }}
                          disabled={requestActionLoading === req.id}
                          className="rounded-md bg-red-500 px-2.5 py-1 text-[11px] font-bold text-white hover:bg-red-600 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                          Reject
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Host card — surface background */}
          {host ? (
            <div className="bg-brand-surface rounded-xl border border-brand-mid-alpha p-5">
              <div className="flex items-center gap-3 mb-3">
                <div className="bg-brand-mid flex size-16 shrink-0 items-center justify-center rounded-full text-[22px] font-bold text-white">
                  {host.username.slice(0, 2).toUpperCase()}
                </div>
                <div>
                  <p className="font-bold text-[16px] text-brand-dark">{host.username}</p>
                  <p className="text-[13px] text-brand-mid">
                    {isHost ? "You are the host" : "Event Host"}
                  </p>
                </div>
              </div>
              {host.average_rating !== null && (
                <div className="flex items-center gap-1.5 mb-1">
                  <div className="flex">{starRating(host.average_rating)}</div>
                  <span className="text-[13px] font-bold text-brand-dark ml-1">
                    {host.average_rating.toFixed(1)}
                  </span>
                </div>
              )}
              <p className="text-[13px] text-brand-mid mb-3">
                {host.hosted_events_count} events hosted
              </p>
              {event.host_id && (
                <Link
                  href={`/profile/${event.host_id}`}
                  className="text-[13px] font-bold text-brand-mid hover:text-brand-dark transition-colors"
                >
                  View Profile →
                </Link>
              )}
            </div>
          ) : (
            <div className="bg-brand-surface rounded-xl border border-brand-mid-alpha p-5 animate-pulse">
              <div className="flex items-center gap-3 mb-3">
                <div className="size-16 rounded-full bg-brand-mid-alpha shrink-0" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-brand-mid-alpha rounded w-24" />
                  <div className="h-3 bg-brand-mid-alpha rounded w-16" />
                </div>
              </div>
              <div className="h-3 bg-brand-mid-alpha rounded w-32" />
            </div>
          )}

          {/* Date & Time */}
          <div className="bg-white rounded-xl border border-brand-mid-alpha p-5">
            <div className="flex items-center gap-2 mb-2">
              <Calendar className="size-[18px] text-brand-mid shrink-0" />
              <strong className="text-[14px] text-brand-dark">Date &amp; Time</strong>
            </div>
            <p className="text-[15px] font-bold text-brand-dark">
              {formatDate(event.start_datetime)}
            </p>
            <p className="text-[14px] text-brand-mid mb-2">
              {formatTime(event.start_datetime)} – {formatTime(event.end_datetime)}
            </p>
            <a
              href={buildGoogleCalendarUrl(event, primaryLocation?.name)}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[13px] font-bold text-brand-mid hover:text-brand-dark transition-colors flex items-center gap-1"
            >
              <Calendar className="size-3.5" />
              Add to Google Calendar
            </a>
          </div>

          {/* Location */}
          {primaryLocation && (
            <div className="bg-white rounded-xl border border-brand-mid-alpha p-5">
              <div className="flex items-center gap-2 mb-2">
                <MapPin className="size-[18px] text-brand-mid shrink-0" />
                <strong className="text-[14px] text-brand-dark">Location</strong>
              </div>
              <p className="text-[15px] font-bold text-brand-dark mb-0.5">
                {primaryLocation.name}
              </p>
              {/* Map placeholder — opens modal */}
              <button
                onClick={() => setShowMapModal(true)}
                className="mt-2 h-[120px] w-full rounded-lg bg-brand-surface flex items-center justify-center text-[14px] font-bold text-brand-dark cursor-pointer hover:bg-brand-mid-alpha hover:shadow-md active:scale-[0.99] transition-all duration-150"
              >
                🗺 VIEW ON MAP
              </button>
            </div>
          )}

          {/* Attendees */}
          {(isActive || isEnded) && (
            <div className="bg-white rounded-xl border border-brand-mid-alpha p-5">
              <div className="flex items-center gap-2 mb-3">
                <Users className="size-[18px] text-brand-mid shrink-0" />
                <strong className="text-[14px] text-brand-dark">Attendees</strong>
              </div>
              {/* Avatar stack */}
              {event.attendees && event.attendees.length > 0 && (
                <div className="mb-3">
                  <AttendeeAvatarStack attendees={event.attendees} maxShow={5} />
                </div>
              )}
              {event.attendee_limit ? (
                <>
                  <div className="h-1.5 rounded-full bg-brand-dark/10 overflow-hidden mb-2">
                    <div
                      className="h-full rounded-full bg-brand-mid transition-all"
                      style={{ width: `${Math.min(100, (goingCount / event.attendee_limit) * 100)}%` }}
                    />
                  </div>
                  <p className="text-[13px] text-brand-mid">
                    {goingCount} of {event.attendee_limit} spots filled
                  </p>
                </>
              ) : (
                <p className="text-[13px] text-brand-mid">{goingCount} attending</p>
              )}
            </div>
          )}

          {/* Requirements */}
          {(event.is_age_restricted || event.venue_metadata?.wheelchair_access) && (
            <div className="bg-white rounded-xl border border-brand-mid-alpha p-5">
              <div className="flex items-center gap-2 mb-2">
                <Shield className="size-[18px] text-brand-mid shrink-0" />
                <strong className="text-[14px] text-brand-dark">Requirements</strong>
              </div>
              {event.is_age_restricted && (
                <p className="text-[14px] text-brand-dark">18+ event · ID required</p>
              )}
              {event.venue_metadata?.wheelchair_access && (
                <p className="text-[14px] text-brand-mid">Wheelchair accessible</p>
              )}
            </div>
          )}
        </div>
        </div>{/* close relative wrapper for right column */}
      </div>

      {/* Map modal */}
      {primaryLocation && (
        <LocationMapModal
          open={showMapModal}
          onClose={() => setShowMapModal(false)}
          latitude={primaryLocation.latitude}
          longitude={primaryLocation.longitude}
          locationName={primaryLocation.name}
        />
      )}
    </>
  );
}

// ─── Page ───────────────────────────────────────────────────────────────────────

export default function EventDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { isAuthenticated, user, isInitialized } = useAuth();

  const [event, setEvent] = useState<AnyEventDetail | null>(null);
  const [host, setHost] = useState<HostProfile | null>(null);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    // Wait for session to initialize so the token is available before fetching.
    // Without this, the request races with refreshSession and may send no token,
    // causing the backend to return a limited/guest response even for logged-in users.
    if (!id || !isInitialized) return;

    let active = true;

    fetchEventDetail(id)
      .then((ev) => {
        if (!active) {
          return;
        }

        setEvent(ev);
        setNotFound(false);
        setHost(null);

        if (ev._type === "full") {
          void fetchHostProfile(ev.host_id)
            .then((profile) => {
              if (active) {
                setHost(profile);
              }
            })
            .catch(() => {
              if (active) {
                setHost(null);
              }
            });
        }
      })
      .catch(() => {
        if (!active) {
          return;
        }

        setEvent(null);
        setHost(null);
        setNotFound(true);
      });

    return () => {
      active = false;
    };
  }, [id, isInitialized]);

  const loading = !id || !isInitialized || (!notFound && event?.id !== id);

  useEffect(() => {
    if (event?._type === "full" && user?.id) {
      clearAccessRequestPending(event.id, user.id);
    }
  }, [event, user?.id]);

  const isHost =
    event?._type === "full" && !!user && !!event.host_id && event.host_id === user.id;

  const isGuest = !isAuthenticated;
  const isAgeBlocked =
    Boolean(
      event?.is_age_restricted &&
      !isHost &&
      (!isAuthenticated || !user?.date_of_birth || !isAtLeast18(user.date_of_birth)),
    );

  return (
    <div className="bg-brand-bg min-h-screen">
      <Navbar />

      {loading ? (
        <div className="flex items-center justify-center py-32">
          <div className="flex flex-col items-center gap-3">
            <div className="size-10 rounded-full border-4 border-brand-mid border-t-transparent animate-spin" />
            <p className="text-sm text-brand-mid">Loading event…</p>
          </div>
        </div>
      ) : notFound || !event ? (
        <div className="flex flex-col items-center justify-center gap-4 text-center px-6 py-32">
          <p className="font-heading text-brand-dark text-2xl font-bold">Event not found</p>
          <p className="text-brand-mid text-sm">
            This event may have been removed or the link is incorrect.
          </p>
          <Link
            href="/"
            className="rounded-lg bg-brand-dark px-5 py-2.5 text-sm font-bold text-white hover:bg-brand-dark/85 transition-colors"
          >
            Back to Discovery
          </Link>
        </div>
      ) : isAgeBlocked ? (
        <AgeGate
          eventId={id}
          isAuthenticated={isAuthenticated}
          userDob={user?.date_of_birth ?? null}
        />
      ) : event._type === "limited" ? (
        <LimitedView event={event} isGuest={isGuest} currentUserId={user?.id ?? null} />
      ) : (
        <FullView
          event={event}
          host={host}
          isHost={isHost}
          currentUserId={user?.id ?? null}
          isAuthenticated={isAuthenticated}
        />
      )}
    </div>
  );
}
