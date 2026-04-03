"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Bell, Plus, Search } from "lucide-react";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/use-auth";
import { cn } from "@/lib/utils";

interface NavbarProps {
  /** Controlled search value — pass only when parent owns search state */
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  onSearchSubmit?: (value: string) => void;
}

export function Navbar({ searchValue, onSearchChange, onSearchSubmit }: NavbarProps) {
  const { isAuthenticated, status, user } = useAuth();
  const router = useRouter();

  // Uncontrolled internal state when parent doesn't own search
  const [internalSearch, setInternalSearch] = useState(searchValue ?? "");
  const inputRef = useRef<HTMLInputElement>(null);

  const currentSearch = searchValue ?? internalSearch;

  function handleSearchChange(e: React.ChangeEvent<HTMLInputElement>) {
    const val = e.target.value;
    setInternalSearch(val);
    onSearchChange?.(val);
  }

  function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSearchSubmit?.(currentSearch);
  }

  // Derive avatar initials from username
  const initials = user?.username?.slice(0, 1).toUpperCase() ?? "?";

  return (
    <header className="bg-brand-dark sticky top-0 z-50 flex h-16 items-center justify-between gap-4 px-6 lg:px-12">
      {/* Logo */}
      <Link
        href="/"
        className="font-heading text-xl font-semibold tracking-[0.02em] text-white transition-opacity hover:opacity-80 shrink-0"
      >
        Social Event Mapper
      </Link>

      {/* Search bar */}
      <form
        onSubmit={handleSearchSubmit}
        className="flex flex-1 max-w-xl items-center gap-2 rounded-lg border border-white/15 bg-white/10 px-4 py-2 transition-colors focus-within:border-white/30 focus-within:bg-white/15"
      >
        <Search className="size-4 shrink-0 text-white/50" />
        <input
          ref={inputRef}
          type="search"
          value={currentSearch}
          onChange={handleSearchChange}
          placeholder="Search events, categories, places..."
          className="w-full bg-transparent text-sm text-white placeholder:text-white/45 outline-none"
        />
      </form>

      {/* Right section — changes based on auth state */}
      <div className="flex shrink-0 items-center gap-3">
        {status === "loading" ? (
          // Skeleton while auth is restoring
          <div className="h-8 w-32 animate-pulse rounded-lg bg-white/10" />
        ) : isAuthenticated ? (
          // Authenticated user
          <>
            {/* Create Event */}
            <Button
              size="sm"
              className="hidden gap-1.5 sm:flex bg-brand-mid hover:bg-brand-mid/80 border-0"
              onClick={() => router.push("/events/create")}
            >
              <Plus className="size-4" />
              Create Event
            </Button>

            {/* Notification bell */}
            <Link href="/notifications" className="relative text-white/70 transition-colors hover:text-white">
              <Bell className="size-5" />
              {/* Unread dot — placeholder, will be wired in notification task */}
              <span className="absolute -top-0.5 -right-0.5 size-2 rounded-full bg-red-500 border-2 border-brand-dark" />
            </Link>

            {/* Avatar + name */}
            <div className="flex items-center gap-2">
              <div className="bg-brand-mid flex size-8 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white">
                {initials}
              </div>
              <span className="hidden text-sm font-semibold text-white/85 sm:block">
                {user?.username}
              </span>
            </div>
          </>
        ) : (
          // Guest
          <>
            <Button
              asChild
              variant="ghost"
              size="sm"
              className="border border-white/30 text-white hover:bg-white/10 hover:text-white"
            >
              <Link href="/login">Sign In</Link>
            </Button>
            <Button
              asChild
              size="sm"
              className="bg-brand-mid hover:bg-brand-mid/80 border-0 text-white"
            >
              <Link href="/register">Sign Up</Link>
            </Button>
          </>
        )}
      </div>
    </header>
  );
}

/** Thin action bar below the navbar — map/list toggle + sort */
interface ActionBarProps {
  view: "map" | "list";
  onViewChange: (view: "map" | "list") => void;
}

export function ActionBar({ view, onViewChange }: ActionBarProps) {
  const { isAuthenticated } = useAuth();
  const router = useRouter();

  return (
    <div className="bg-brand-surface border-brand-mid-alpha flex items-center justify-between border-b px-6 py-2 lg:px-12">
      <div className="flex items-center gap-2">
        <button
          onClick={() => onViewChange("map")}
          className={cn(
            "flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm font-semibold transition-colors",
            view === "map"
              ? "bg-brand-dark border-brand-dark text-white"
              : "border-brand-mid-alpha text-brand-dark hover:bg-brand-mid-alpha",
          )}
        >
          {/* Map icon inline to avoid lucide dep inside navbar */}
          <svg className="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21" />
            <line x1="9" y1="3" x2="9" y2="18" />
            <line x1="15" y1="6" x2="15" y2="21" />
          </svg>
          Map
        </button>

        <button
          onClick={() => onViewChange("list")}
          className={cn(
            "flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm font-semibold transition-colors",
            view === "list"
              ? "bg-brand-dark border-brand-dark text-white"
              : "border-brand-mid-alpha text-brand-dark hover:bg-brand-mid-alpha",
          )}
        >
          <svg className="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <line x1="8" y1="6" x2="21" y2="6" />
            <line x1="8" y1="12" x2="21" y2="12" />
            <line x1="8" y1="18" x2="21" y2="18" />
            <line x1="3" y1="6" x2="3.01" y2="6" />
            <line x1="3" y1="12" x2="3.01" y2="12" />
            <line x1="3" y1="18" x2="3.01" y2="18" />
          </svg>
          List
        </button>

        {isAuthenticated && (
          <Button
            size="sm"
            onClick={() => router.push("/events/create")}
            className="ml-4 gap-1.5 bg-brand-mid hover:bg-brand-mid/80 border-0 text-white"
          >
            <Plus className="size-4" />
            Create Event
          </Button>
        )}
      </div>
    </div>
  );
}
