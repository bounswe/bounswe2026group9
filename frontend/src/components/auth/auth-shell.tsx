import Link from "next/link";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

const featuredEvents = [
  {
    className: "left-[8%] top-[14%] -rotate-6",
    tag: "Music",
    time: "Sat, 21:00",
    title: "Kadikoy Beach Party",
  },
  {
    className: "bottom-[22%] right-[6%] rotate-3",
    tag: "Nature",
    time: "Sun, 08:00",
    title: "Bird Watching",
  },
  {
    className: "bottom-[8%] left-[15%] -rotate-2",
    tag: "Tech",
    time: "Fri, 19:00",
    title: "Startup Pitch Night",
  },
];

interface AuthShellProps {
  children: ReactNode;
}

export function AuthShell({ children }: AuthShellProps) {
  return (
    <main className="flex min-h-screen flex-1">
      <section className="grid w-full lg:grid-cols-[1fr_0.95fr]">
        <div className="bg-brand-dark relative hidden overflow-hidden px-10 py-12 text-white lg:flex lg:min-h-screen lg:flex-col lg:justify-center xl:px-14">
          <Link
            className="font-heading absolute top-8 left-10 text-xl font-semibold tracking-[0.02em] text-white transition-opacity hover:opacity-80 xl:left-14"
            href="/"
          >
            Social Event Mapper
          </Link>

          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(214,192,179,0.18),_transparent_34%),radial-gradient(circle_at_bottom_right,_rgba(214,192,179,0.12),_transparent_28%)]" />

          <div className="relative z-10 mx-auto max-w-xl text-center">
            <h1 className="text-5xl leading-tight text-white xl:text-6xl">
              Discover events around you
            </h1>
            <p className="mx-auto mt-4 max-w-md text-base leading-7 text-white/70">
              Browse, create, and join community events happening across your city.
            </p>
          </div>

          <div className="pointer-events-none absolute inset-0">
            {featuredEvents.map((event) => (
              <div
                key={event.title}
                className={cn(
                  "shadow-brand-card absolute w-56 rounded-xl border border-white/15 bg-white/[0.08] px-5 py-4 text-white backdrop-blur-[2px]",
                  event.className,
                )}
              >
                <p className="font-heading text-sm font-semibold">{event.title}</p>
                <p className="mt-1 text-xs text-white/70">{event.time}</p>
                <span className="mt-3 inline-flex rounded-full border border-white/15 bg-white/10 px-2.5 py-1 text-[0.68rem] font-bold tracking-[0.18em] text-white/90 uppercase">
                  {event.tag}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-background flex min-h-screen items-center justify-center px-6 py-12 sm:px-8 lg:px-10">
          <div className="w-full max-w-[28rem]">
            <div className="mb-8 lg:hidden">
              <Link className="font-heading text-foreground text-2xl font-semibold" href="/">
                Social Event Mapper
              </Link>
              <p className="text-muted-foreground mt-3 max-w-sm text-sm leading-6">
                Browse, create, and join community events happening across your city.
              </p>
            </div>
            {children}
          </div>
        </div>
      </section>
    </main>
  );
}
