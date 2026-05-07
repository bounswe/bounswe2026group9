"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Bell, LogOut, Menu, Plus, Search } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/use-auth";
import { CREATE_EVENT_PAGE_PATH } from "@/lib/event-routes";
import { fetchUnreadNotificationCount } from "@/lib/events-api";
import { cn } from "@/lib/utils";

interface NavbarProps {
  /** Controlled search value — pass only when parent owns search state */
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  onSearchSubmit?: (value: string) => void;
  showSearch?: boolean;
}

export function Navbar({
  searchValue,
  onSearchChange,
  onSearchSubmit,
  showSearch = true,
}: NavbarProps) {
  const { isAuthenticated, logout, status, user } = useAuth();
  const pathname = usePathname();

  // Uncontrolled internal state when parent doesn't own search
  const [internalSearch, setInternalSearch] = useState(searchValue ?? "");
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const loadUnreadCount = useCallback(async () => {
    try {
      const count = await fetchUnreadNotificationCount();
      setUnreadCount(count);
    } catch {
      // silently fail
    }
  }, []);

  // Reload unread count on mount, auth change, page navigation, and every 60s
  useEffect(() => {
    if (!isAuthenticated) {
      setUnreadCount(0);
      return;
    }

    void loadUnreadCount();

    const interval = setInterval(() => {
      void loadUnreadCount();
    }, 60_000);

    return () => clearInterval(interval);
  }, [isAuthenticated, loadUnreadCount, pathname]);

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

  async function handleLogout() {
    if (isLoggingOut) {
      return;
    }

    setIsLoggingOut(true);

    try {
      await logout();
    } finally {
      setIsLoggingOut(false);
    }
  }

  function renderDesktopControls() {
    if (status === "loading") {
      return <div className="h-8 w-32 animate-pulse rounded-lg bg-white/10" />;
    }

    if (isAuthenticated) {
      return (
        <>
          <Link href="/inbox" className="relative text-white/70 transition-colors hover:text-white">
            <Bell className="size-5" />
            {unreadCount > 0 && (
              <span className="border-brand-dark absolute -top-1.5 -right-1.5 flex size-4 items-center justify-center rounded-full border-2 bg-red-500 text-[9px] leading-none font-bold text-white">
                {unreadCount > 9 ? "9+" : unreadCount}
              </span>
            )}
          </Link>

          <Link
            href="/profile/me"
            className="flex items-center gap-2 rounded-lg px-1 py-1 text-white/85 transition-colors hover:bg-white/8 hover:text-white"
          >
            <div className="bg-brand-mid flex size-8 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white">
              {initials}
            </div>
            <span className="hidden text-sm font-semibold text-white/85 lg:block">
              {user?.username}
            </span>
          </Link>

          <Button
            type="button"
            variant="ghost"
            size="sm"
            disabled={isLoggingOut}
            onClick={() => {
              void handleLogout();
            }}
            className="border border-white/25 text-white hover:bg-white/10 hover:text-white disabled:border-white/10 disabled:text-white/45"
          >
            <LogOut className="size-3.5" />
            {isLoggingOut ? "Signing out..." : "Logout"}
          </Button>
        </>
      );
    }

    return (
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
    );
  }

  function renderMobileControls() {
    if (status === "loading") {
      return <div className="h-8 w-20 animate-pulse rounded-lg bg-white/10" />;
    }

    if (isAuthenticated) {
      return (
        <>
          <Link
            href="/inbox"
            className="relative rounded-lg border border-white/10 bg-white/5 p-2 text-white/80 transition-colors hover:bg-white/10 hover:text-white"
          >
            <Bell className="size-4" />
            {unreadCount > 0 && (
              <span className="border-brand-dark absolute -top-1 -right-1 flex size-4 items-center justify-center rounded-full border-2 bg-red-500 text-[9px] leading-none font-bold text-white">
                {unreadCount > 9 ? "9+" : unreadCount}
              </span>
            )}
          </Link>
          <Link
            href="/profile/me"
            aria-label="Open my profile settings"
            className="bg-brand-mid flex size-9 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white transition-opacity hover:opacity-85"
          >
            {initials}
          </Link>
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            disabled={isLoggingOut}
            onClick={() => {
              void handleLogout();
            }}
            className="border border-white/10 bg-white/5 text-white/80 hover:bg-white/10 hover:text-white disabled:text-white/35"
            aria-label={isLoggingOut ? "Signing out" : "Logout"}
          >
            <LogOut className="size-4" />
          </Button>
        </>
      );
    }

    return (
      <>
        <Button
          asChild
          variant="ghost"
          size="sm"
          className="border border-white/25 px-2 text-white hover:bg-white/10 hover:text-white"
        >
          <Link href="/login">Sign In</Link>
        </Button>
        <Button
          asChild
          size="sm"
          className="bg-brand-mid hover:bg-brand-mid/80 border-0 px-2 text-white"
        >
          <Link href="/register">Sign Up</Link>
        </Button>
      </>
    );
  }

  return (
    <header className="bg-brand-dark sticky top-0 z-50 border-b border-white/10 px-4 py-2.5 sm:px-6 lg:px-12">
      <div className="relative flex items-center gap-2 sm:gap-4">
        <div className={cn("flex shrink-0 items-center", showSearch && "lg:min-w-[11rem]")}>
          <Link
            href="/"
            aria-label="Go to homepage"
            className="group flex size-10 shrink-0 items-center justify-center rounded-xl border border-white/10 bg-white/8 text-white transition-opacity hover:opacity-80"
          >
            <span className="relative block size-5" aria-hidden="true">
              <span className="bg-brand-mid absolute top-0 left-0 size-3 rounded-full" />
              <span className="absolute right-0 bottom-0 size-3 rounded-full border border-white/70" />
            </span>
          </Link>
        </div>

        {showSearch ? (
          <div className="min-w-0 flex-1 lg:absolute lg:left-1/2 lg:w-[min(40rem,calc(100vw-30rem))] lg:-translate-x-1/2">
            <form
              onSubmit={handleSearchSubmit}
              className="flex w-full max-w-2xl items-center gap-2 rounded-xl border border-white/15 bg-white/10 px-3 py-2 transition-colors focus-within:border-white/30 focus-within:bg-white/15 sm:px-4"
            >
              <Search className="size-4 shrink-0 text-white/50" />
              <input
                ref={inputRef}
                type="search"
                value={currentSearch}
                onChange={handleSearchChange}
                placeholder="Search events, categories, places..."
                className="w-full min-w-0 bg-transparent text-sm text-white outline-none placeholder:text-white/45"
              />
            </form>
          </div>
        ) : null}

        <div
          className={cn(
            "ml-auto flex shrink-0 items-center justify-end gap-2 sm:gap-3",
            showSearch && "lg:min-w-[11rem]",
          )}
        >
          <div className="flex items-center gap-2 sm:hidden">{renderMobileControls()}</div>
          <div className="hidden items-center gap-3 sm:flex">{renderDesktopControls()}</div>
        </div>
      </div>
    </header>
  );
}

/** Thin action bar below the navbar — map/list toggle + sort */
interface ActionBarProps {
  view: "map" | "list";
  onViewChange: (view: "map" | "list") => void;
  activeFilterCount: number;
  onToggleFilters: () => void;
}

export function ActionBar({
  view,
  onViewChange,
  activeFilterCount,
  onToggleFilters,
}: ActionBarProps) {
  const { isAuthenticated } = useAuth();
  const router = useRouter();
  const toggleButtonClassName =
    "appearance-none border-0 shadow-none outline-none ring-0 focus:outline-none focus:ring-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-mid/60 focus-visible:ring-offset-2 focus-visible:ring-offset-brand-surface active:translate-y-0 active:shadow-none [-webkit-tap-highlight-color:transparent]";

  return (
    <div className="bg-brand-surface border-brand-mid-alpha flex items-center gap-2 border-b px-4 py-3 sm:px-6 lg:px-12">
      <button
        onClick={onToggleFilters}
        className={cn(
          "border-brand-mid-alpha text-brand-dark hover:bg-brand-mid-alpha flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm font-semibold transition-colors lg:hidden",
          toggleButtonClassName,
        )}
        aria-label="Open filters"
      >
        <Menu className="size-4" />
        <span>Filters</span>
        {activeFilterCount > 0 && (
          <span className="bg-brand-dark rounded-full px-1.5 py-0.5 text-[10px] font-bold text-white">
            {activeFilterCount}
          </span>
        )}
      </button>

      <div className="border-brand-mid-alpha shadow-brand-floating flex min-w-0 items-center gap-1 overflow-x-auto rounded-xl border bg-white/35 p-1">
        <button
          type="button"
          onClick={() => onViewChange("map")}
          className={cn(
            "flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-semibold transition-colors",
            toggleButtonClassName,
            view === "map"
              ? "bg-brand-dark text-white"
              : "text-brand-dark hover:bg-brand-mid-alpha/80",
          )}
        >
          {/* Map icon inline to avoid lucide dep inside navbar */}
          <svg
            className="size-4"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
          >
            <polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21" />
            <line x1="9" y1="3" x2="9" y2="18" />
            <line x1="15" y1="6" x2="15" y2="21" />
          </svg>
          Map
        </button>

        <button
          type="button"
          onClick={() => onViewChange("list")}
          className={cn(
            "flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-semibold transition-colors",
            toggleButtonClassName,
            view === "list"
              ? "bg-brand-dark text-white"
              : "text-brand-dark hover:bg-brand-mid-alpha/80",
          )}
        >
          <svg
            className="size-4"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
          >
            <line x1="8" y1="6" x2="21" y2="6" />
            <line x1="8" y1="12" x2="21" y2="12" />
            <line x1="8" y1="18" x2="21" y2="18" />
            <line x1="3" y1="6" x2="3.01" y2="6" />
            <line x1="3" y1="12" x2="3.01" y2="12" />
            <line x1="3" y1="18" x2="3.01" y2="18" />
          </svg>
          List
        </button>
      </div>

      {isAuthenticated && (
        <div className="ml-auto flex items-center gap-2">
          <Button
            size="icon-sm"
            onClick={() => router.push(CREATE_EVENT_PAGE_PATH)}
            className="bg-brand-mid hover:bg-brand-mid/80 border-0 text-white sm:hidden"
            aria-label="Create Event"
          >
            <Plus className="size-4" />
          </Button>
          <Button
            size="sm"
            onClick={() => router.push(CREATE_EVENT_PAGE_PATH)}
            className="bg-brand-mid hover:bg-brand-mid/80 hidden gap-1.5 border-0 text-white sm:flex"
          >
            <Plus className="size-4" />
            Create Event
          </Button>
        </div>
      )}
    </div>
  );
}
