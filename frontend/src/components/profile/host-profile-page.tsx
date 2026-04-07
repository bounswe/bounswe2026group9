"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { CalendarDays, Mail, Phone, Star } from "lucide-react";
import { useEffect, useState } from "react";

import { StatusBadge } from "@/components/event/status-badge";
import { Navbar } from "@/components/layout/navbar";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/use-auth";
import { fetchHostProfile, rateHost, type EventListItem, type HostProfile } from "@/lib/events-api";
import { cn } from "@/lib/utils";

type ProfileTab = "about" | "past" | "upcoming";

function initials(username: string) {
  return username
    .split(/[\s._-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("") || username.slice(0, 2).toUpperCase();
}

function formatEventDate(datetime: string) {
  return new Date(datetime).toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

function formatEventTime(datetime: string) {
  return new Date(datetime).toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function isPastEvent(event: EventListItem) {
  if (event.status === "cancelled" || event.status === "ended") {
    return true;
  }

  return new Date(event.end_datetime).getTime() < Date.now();
}

function statusVariant(event: EventListItem) {
  if (event.status === "cancelled") return "cancelled" as const;
  if (event.status === "ended") return "ended" as const;
  if (event.status === "draft") return "draft" as const;
  return "published" as const;
}

function RatingStars({
  selected,
  onSelect,
  disabled = false,
}: {
  selected: number;
  onSelect?: (value: number) => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex items-center gap-1">
      {Array.from({ length: 5 }, (_, index) => {
        const value = index + 1;
        const active = value <= selected;

        return (
          <button
            key={value}
            type="button"
            disabled={disabled || !onSelect}
            onClick={() => onSelect?.(value)}
            className={cn(
              "rounded-md p-1.5 transition-colors",
              onSelect && !disabled && "cursor-pointer hover:bg-brand-mid-alpha/60",
              disabled && "cursor-default",
            )}
            aria-label={`Rate ${value} stars`}
          >
            <Star
              className={cn(
                "size-5 transition-colors",
                active ? "fill-brand-mid text-brand-mid" : "text-brand-mid/30",
              )}
            />
          </button>
        );
      })}
    </div>
  );
}

function EmptyTabState({ message }: { message: string }) {
  return (
    <div className="rounded-[28px] border border-brand-mid/15 bg-white/70 px-6 py-12 text-center shadow-[0_18px_50px_-32px_rgba(73,54,40,0.45)]">
      <p className="font-heading text-xl text-brand-dark">Nothing here yet</p>
      <p className="mt-2 text-sm text-brand-mid">{message}</p>
    </div>
  );
}

function HostedEventCard({ event }: { event: EventListItem }) {
  const attendeeFill = event.attendee_limit
    ? Math.min(100, Math.round((event.attendee_count / event.attendee_limit) * 100))
    : null;

  return (
    <Link
      href={`/event/${event.id}`}
      className="group overflow-hidden rounded-[24px] border border-brand-mid/12 bg-white shadow-[0_22px_60px_-40px_rgba(73,54,40,0.45)] transition-all duration-200 hover:-translate-y-1 hover:shadow-[0_28px_70px_-38px_rgba(73,54,40,0.5)]"
    >
      <div className="relative h-48 overflow-hidden bg-brand-mid/30">
        {event.primary_image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={event.primary_image_url}
            alt={event.title}
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.03]"
          />
        ) : (
          <div className="flex h-full items-center justify-center bg-[linear-gradient(135deg,rgba(73,54,40,0.92),rgba(171,136,109,0.72))]">
            <CalendarDays className="size-12 text-white/45" />
          </div>
        )}

        <div className="absolute inset-x-0 top-0 flex items-start justify-between gap-2 p-4">
          <StatusBadge variant={statusVariant(event)} className="shadow-sm" />
          {event.visibility === "private" ? (
            <span className="rounded-full bg-brand-dark/85 px-3 py-1 text-[11px] font-extrabold uppercase tracking-wide text-white">
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
              className="rounded-full bg-brand-bg px-2.5 py-1 text-[11px] font-semibold text-brand-mid"
            >
              {category.name}
            </span>
          ))}
        </div>

        <div>
          <h3 className="font-heading text-xl font-semibold text-brand-dark">{event.title}</h3>
          <p className="mt-1 text-sm font-medium text-brand-mid">
            {formatEventDate(event.start_datetime)} · {formatEventTime(event.start_datetime)}
          </p>
        </div>

        {event.description ? (
          <p
            className="text-sm leading-6 text-brand-dark/80"
            style={{
              display: "-webkit-box",
              overflow: "hidden",
              WebkitBoxOrient: "vertical",
              WebkitLineClamp: 3,
            }}
          >
            {event.description}
          </p>
        ) : (
          <p className="text-sm leading-6 text-brand-mid">
            Details are limited for this event, but the public summary is still available.
          </p>
        )}

        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs font-semibold text-brand-dark">
            <span>
              {event.attendee_count}
              {event.attendee_limit ? `/${event.attendee_limit}` : ""} going
            </span>
            {event.primary_location ? (
              <span className="max-w-[60%] truncate text-right text-brand-mid">
                {event.primary_location.name}
              </span>
            ) : (
              <span className="text-brand-mid">
                {event.visibility === "private" ? "Location hidden" : "Location not set"}
              </span>
            )}
          </div>

          {attendeeFill !== null ? (
            <div className="h-2 rounded-full bg-brand-bg">
              <div
                className="h-full rounded-full bg-brand-mid transition-[width]"
                style={{ width: `${attendeeFill}%` }}
              />
            </div>
          ) : null}
        </div>
      </div>
    </Link>
  );
}

export function HostProfilePage() {
  const { id } = useParams<{ id: string }>();
  const { isAuthenticated, isInitialized, user } = useAuth();

  const [profile, setProfile] = useState<HostProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<ProfileTab>("upcoming");
  const [selectedScore, setSelectedScore] = useState(0);
  const [ratingError, setRatingError] = useState<string | null>(null);
  const [ratingSuccess, setRatingSuccess] = useState<string | null>(null);
  const [isSubmittingRating, setIsSubmittingRating] = useState(false);

  useEffect(() => {
    if (!id || !isInitialized) {
      return;
    }

    setLoading(true);
    setError(null);

    fetchHostProfile(id)
      .then((response) => {
        setProfile(response);
      })
      .catch((err: unknown) => {
        const message = err instanceof Error ? err.message : "Failed to load this host profile.";
        setError(message);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [id, isInitialized]);

  const isOwner = !!user?.id && user.id === profile?.id;
  const visibleHostedEvents = profile?.hosted_events.filter((event) => event.status !== "draft") ?? [];
  const upcomingEvents = visibleHostedEvents.filter((event) => !isPastEvent(event));
  const pastEvents = visibleHostedEvents.filter((event) => isPastEvent(event));

  async function handleRatingSubmit() {
    if (!profile || !selectedScore) {
      return;
    }

    setIsSubmittingRating(true);
    setRatingError(null);
    setRatingSuccess(null);

    try {
      await rateHost(profile.id, selectedScore);
      const refreshed = await fetchHostProfile(profile.id);
      setProfile(refreshed);
      setRatingSuccess("Thanks, your rating has been saved.");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "We could not save your rating.";
      setRatingError(message);
    } finally {
      setIsSubmittingRating(false);
    }
  }

  return (
    <div className="min-h-screen bg-brand-bg">
      <Navbar />

      {loading ? (
        <div className="mx-auto flex max-w-[1280px] flex-col gap-8 px-4 pb-20 sm:px-6 lg:px-8">
          <div className="h-52 animate-pulse rounded-[32px] bg-brand-dark/20" />
          <div className="mx-auto -mt-20 flex w-full max-w-3xl flex-col items-center gap-4 px-4 text-center">
            <div className="size-28 animate-pulse rounded-full border-4 border-white bg-brand-mid/30" />
            <div className="h-9 w-60 animate-pulse rounded-full bg-brand-mid/20" />
            <div className="h-4 w-80 animate-pulse rounded-full bg-brand-mid/15" />
          </div>
        </div>
      ) : error || !profile ? (
        <div className="mx-auto max-w-[880px] px-4 pb-20 text-center sm:px-6 lg:px-8">
          <div className="rounded-[28px] border border-brand-mid/15 bg-white px-6 py-14 shadow-[0_22px_60px_-42px_rgba(73,54,40,0.45)]">
            <h1 className="font-heading text-3xl text-brand-dark">Host profile not found</h1>
            <p className="mt-3 text-sm text-brand-mid">
              {error ?? "This host may no longer be available, or the link is incorrect."}
            </p>
            <Button asChild className="mt-6 border-0 bg-brand-dark text-white hover:bg-brand-dark/85">
              <Link href="/">Go to Discovery</Link>
            </Button>
          </div>
        </div>
      ) : (
        <>
          <section className="relative overflow-hidden bg-[linear-gradient(135deg,#493628_0%,#5e4434_48%,#AB886D_100%)]">
            <div className="mx-auto h-56 max-w-[1280px]" />
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.18),transparent_45%)]" />
          </section>

          <section className="relative mx-auto -mt-14 max-w-[1280px] px-4 pb-8 sm:px-6 lg:px-8">
            <div className="mx-auto flex max-w-4xl flex-col items-center text-center">
              <div className="flex size-28 items-center justify-center rounded-full border-4 border-white bg-brand-mid text-3xl font-bold text-white shadow-[0_12px_28px_-18px_rgba(73,54,40,0.55)]">
                {initials(profile.username)}
              </div>

              <h1 className="font-heading mt-5 text-4xl font-bold text-brand-dark">
                {profile.username}
              </h1>
              <p className="mt-1 text-sm text-brand-mid">@{profile.username}</p>

              <p className="mt-4 max-w-2xl text-sm leading-7 text-brand-dark/80">
                Browse the events this host has organized, see what is coming up next, and explore
                past gatherings all in one place.
              </p>

              <div className="mt-6 grid w-full max-w-2xl grid-cols-1 gap-3 sm:grid-cols-3">
                <div className="rounded-[20px] border border-brand-mid/12 bg-white/85 px-5 py-4">
                  <p className="text-2xl font-bold text-brand-dark">{visibleHostedEvents.length}</p>
                  <p className="mt-1 text-xs font-semibold uppercase tracking-[0.18em] text-brand-mid">
                    Events
                  </p>
                </div>
                <div className="rounded-[20px] border border-brand-mid/12 bg-white/85 px-5 py-4">
                  <p className="text-2xl font-bold text-brand-dark">
                    {profile.average_rating !== null ? profile.average_rating.toFixed(1) : "New"}
                  </p>
                  <p className="mt-1 text-xs font-semibold uppercase tracking-[0.18em] text-brand-mid">
                    Average Rating
                  </p>
                </div>
                <div className="rounded-[20px] border border-brand-mid/12 bg-white/85 px-5 py-4">
                  <p className="text-2xl font-bold text-brand-dark">{upcomingEvents.length}</p>
                  <p className="mt-1 text-xs font-semibold uppercase tracking-[0.18em] text-brand-mid">
                    Upcoming
                  </p>
                </div>
              </div>

              <div className="mt-5 flex flex-wrap items-center justify-center gap-3">
                {profile.average_rating !== null ? (
                  <div className="inline-flex items-center gap-2 rounded-full border border-brand-mid/18 bg-white/85 px-4 py-2 text-sm font-medium text-brand-dark">
                    <RatingStars selected={Math.round(profile.average_rating)} disabled />
                    <span>{profile.average_rating.toFixed(1)} host rating</span>
                  </div>
                ) : (
                  <div className="inline-flex items-center gap-2 rounded-full border border-brand-mid/18 bg-white/85 px-4 py-2 text-sm font-medium text-brand-mid">
                    <Star className="size-4 text-brand-mid" />
                    No public ratings yet
                  </div>
                )}

                {profile.email ? (
                  <div className="inline-flex items-center gap-2 rounded-full border border-brand-mid/18 bg-white/85 px-4 py-2 text-sm font-medium text-brand-dark">
                    <Mail className="size-4 text-brand-mid" />
                    {profile.email}
                  </div>
                ) : null}

                {profile.phone_number ? (
                  <div className="inline-flex items-center gap-2 rounded-full border border-brand-mid/18 bg-white/85 px-4 py-2 text-sm font-medium text-brand-dark">
                    <Phone className="size-4 text-brand-mid" />
                    {profile.phone_number}
                  </div>
                ) : null}
              </div>
            </div>
          </section>

          <section className="mx-auto grid max-w-[1280px] gap-8 px-4 pb-20 sm:px-6 lg:grid-cols-[minmax(0,1fr)_320px] lg:px-8">
            <div className="min-w-0">
              <div className="overflow-x-auto rounded-[24px] border border-brand-mid/12 bg-white/75 p-2 shadow-[0_22px_60px_-42px_rgba(73,54,40,0.45)]">
                <div className="flex min-w-max gap-1.5">
                  {([
                    { key: "upcoming", label: "Upcoming Events" },
                    { key: "past", label: "Past Events" },
                    { key: "about", label: "About" },
                  ] as const).map((tab) => (
                    <button
                      key={tab.key}
                      type="button"
                      onClick={() => setActiveTab(tab.key)}
                      className={cn(
                        "rounded-[18px] px-5 py-3 text-sm font-semibold transition-colors cursor-pointer",
                        activeTab === tab.key
                          ? "bg-brand-bg text-brand-dark shadow-[0_6px_20px_-16px_rgba(73,54,40,0.55)]"
                          : "text-brand-mid hover:bg-brand-bg/70 hover:text-brand-dark",
                      )}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="mt-6">
                {activeTab === "upcoming" ? (
                  upcomingEvents.length > 0 ? (
                    <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
                      {upcomingEvents.map((event) => (
                        <HostedEventCard key={event.id} event={event} />
                      ))}
                    </div>
                  ) : (
                    <EmptyTabState message="This host does not have any upcoming public event summaries right now." />
                  )
                ) : null}

                {activeTab === "past" ? (
                  pastEvents.length > 0 ? (
                    <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
                      {pastEvents.map((event) => (
                        <HostedEventCard key={event.id} event={event} />
                      ))}
                    </div>
                  ) : (
                    <EmptyTabState message="Past hosted events will show up here once this host has completed or cancelled events." />
                  )
                ) : null}

                {activeTab === "about" ? (
                  <div className="rounded-[28px] border border-brand-mid/12 bg-white p-6 shadow-[0_22px_60px_-42px_rgba(73,54,40,0.45)] sm:p-8">
                    <h2 className="font-heading text-2xl font-semibold text-brand-dark">
                      About {profile.username}
                    </h2>
                    <p className="mt-4 text-sm leading-7 text-brand-dark/80">
                      This host has not shared extra public profile details yet. You can still
                      browse their hosted events and any contact information they chose to share.
                    </p>

                    <div className="mt-6 grid gap-4 sm:grid-cols-2">
                      <div className="rounded-[20px] bg-brand-bg/75 p-5">
                        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-mid">
                          Public Email
                        </p>
                        <p className="mt-2 text-sm text-brand-dark">
                          {profile.email ?? "Not shared publicly"}
                        </p>
                      </div>
                      <div className="rounded-[20px] bg-brand-bg/75 p-5">
                        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-mid">
                          Public Phone
                        </p>
                        <p className="mt-2 text-sm text-brand-dark">
                          {profile.phone_number ?? "Not shared publicly"}
                        </p>
                      </div>
                    </div>
                  </div>
                ) : null}
              </div>
            </div>

            <aside className="space-y-5">
              <div className="rounded-[28px] border border-brand-mid/12 bg-white p-6 shadow-[0_22px_60px_-42px_rgba(73,54,40,0.45)]">
                <h2 className="font-heading text-2xl font-semibold text-brand-dark">
                  {isOwner ? "Your Host Profile" : "Host Rating"}
                </h2>

                {isOwner ? (
                  <p className="mt-3 text-sm leading-6 text-brand-mid">
                    This is how your public host profile appears to other users. People can browse
                    your hosted events and rate their hosting experience here.
                  </p>
                ) : isAuthenticated ? (
                  <>
                    <p className="mt-3 text-sm leading-6 text-brand-mid">
                      Rate this host based on their hosted events. You can update your score later.
                    </p>
                    <div className="mt-5 rounded-[22px] bg-brand-bg/75 p-4">
                      <RatingStars
                        selected={selectedScore}
                        onSelect={(value) => {
                          setSelectedScore(value);
                          setRatingError(null);
                          setRatingSuccess(null);
                        }}
                        disabled={isSubmittingRating}
                      />
                      <p className="mt-3 text-xs text-brand-mid">
                        {selectedScore > 0
                          ? `Selected score: ${selectedScore} out of 5`
                          : "Choose a score from 1 to 5 stars"}
                      </p>
                    </div>

                    {ratingError ? (
                      <p className="mt-3 text-sm text-danger">{ratingError}</p>
                    ) : null}
                    {ratingSuccess ? (
                      <p className="mt-3 text-sm text-emerald-700">{ratingSuccess}</p>
                    ) : null}

                    <Button
                      type="button"
                      onClick={() => {
                        void handleRatingSubmit();
                      }}
                      disabled={!selectedScore || isSubmittingRating}
                      className="mt-5 w-full border-0 bg-brand-dark text-white hover:bg-brand-dark/85"
                    >
                      {isSubmittingRating ? "Saving..." : "Submit Rating"}
                    </Button>
                  </>
                ) : (
                  <>
                    <p className="mt-3 text-sm leading-6 text-brand-mid">
                      Sign in to rate this host and keep track of the events you want to join.
                    </p>
                    <div className="mt-5 flex gap-3">
                      <Button
                        asChild
                        className="flex-1 border-0 bg-brand-dark text-white hover:bg-brand-dark/85"
                      >
                        <Link href={`/login?next=/profile/${profile.id}`}>Sign In</Link>
                      </Button>
                      <Button
                        asChild
                        variant="outline"
                        className="flex-1 border-brand-mid/25 bg-white text-brand-dark hover:bg-brand-bg"
                      >
                        <Link href={`/register?next=/profile/${profile.id}`}>Sign Up</Link>
                      </Button>
                    </div>
                  </>
                )}
              </div>

            </aside>
          </section>
        </>
      )}
    </div>
  );
}
