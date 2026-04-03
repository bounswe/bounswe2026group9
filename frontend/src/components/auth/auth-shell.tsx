import Link from "next/link";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

const featuredEvents = [
  {
    desktopClassName: "left-[8%] top-[14%] -rotate-6",
    tag: "Music",
    time: "Sat, 21:00",
    title: "Kadikoy Beach Party",
  },
  {
    desktopClassName: "bottom-[22%] right-[6%] rotate-3",
    tag: "Nature",
    time: "Sun, 08:00",
    title: "Bird Watching",
  },
  {
    desktopClassName: "bottom-[8%] left-[15%] -rotate-2",
    tag: "Tech",
    time: "Fri, 19:00",
    title: "Startup Pitch Night",
  },
];

interface AuthShellProps {
  children: ReactNode;
}

function AuthHero({ mobile = false }: { mobile?: boolean }) {
  const visibleEvents = mobile ? featuredEvents.slice(0, 1) : featuredEvents;

  return (
    <div
      className={cn(
        "bg-brand-dark relative overflow-hidden text-white",
        mobile
          ? "w-full px-6 py-8"
          : "hidden px-10 py-12 lg:flex lg:min-h-screen lg:flex-col lg:justify-center xl:px-14",
      )}
    >
      <Link
        className={cn(
          "font-heading text-xl font-semibold tracking-[0.02em] text-white transition-opacity hover:opacity-80",
          mobile ? "relative z-10 mx-auto inline-block w-fit" : "absolute top-8 left-10 xl:left-14",
        )}
        href="/"
      >
        Social Event Mapper
      </Link>

      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(214,192,179,0.18),_transparent_34%),radial-gradient(circle_at_bottom_right,_rgba(214,192,179,0.12),_transparent_28%)]" />

      <div
        className={cn(
          "relative z-10 text-center",
          mobile ? "mx-auto mt-8 max-w-[17rem]" : "mx-auto max-w-xl",
        )}
      >
        <h1 className={cn("leading-tight text-white", mobile ? "text-3xl" : "text-5xl xl:text-6xl")}>
          Discover events around you
        </h1>
        <p
          className={cn(
            "mt-4 text-white/70",
            mobile ? "mx-auto max-w-[16rem] text-sm leading-6" : "mx-auto max-w-md text-base leading-7",
          )}
        >
          Browse, create, and join community events happening across your city.
        </p>
      </div>

      <div className="pointer-events-none absolute inset-0">
        {visibleEvents.map((event) => (
          <div
            key={event.title}
            className={cn(
              "shadow-brand-card absolute rounded-xl border border-white/15 bg-white/[0.08] text-white backdrop-blur-[2px]",
              mobile ? "top-14 right-4 w-36 rotate-3 px-3 py-3" : "w-56 px-5 py-4",
              mobile ? null : event.desktopClassName,
            )}
          >
            <p className={cn("font-heading font-semibold", mobile ? "text-xs" : "text-sm")}>
              {event.title}
            </p>
            <p className={cn("mt-1 text-white/70", mobile ? "text-[0.65rem]" : "text-xs")}>
              {event.time}
            </p>
            <span
              className={cn(
                "mt-3 inline-flex rounded-full border border-white/15 bg-white/10 font-bold text-white/90 uppercase",
                mobile
                  ? "px-2 py-1 text-[0.55rem] tracking-[0.16em]"
                  : "px-2.5 py-1 text-[0.68rem] tracking-[0.18em]",
              )}
            >
              {event.tag}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function AuthShell({ children }: AuthShellProps) {
  return (
    <main className="flex min-h-screen flex-1">
      <section className="grid w-full lg:grid-cols-[1fr_0.95fr]">
        <AuthHero />

        <div className="bg-background flex min-h-screen flex-col items-stretch lg:items-center lg:justify-center lg:px-10 lg:py-12">
          <div className="lg:hidden">
            <AuthHero mobile />
          </div>
          <div className="mx-auto w-full max-w-[28rem] px-6 py-6 sm:px-8 sm:py-8 lg:px-0 lg:py-0">
            {children}
          </div>
        </div>
      </section>
    </main>
  );
}
