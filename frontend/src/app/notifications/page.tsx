"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Bell,
  Calendar,
  Check,
  CheckCheck,
  ChevronLeft,
  ChevronRight,
  Loader2,
  MessageSquare,
  UserPlus,
  XCircle,
} from "lucide-react";

import { Navbar } from "@/components/layout/navbar";
import { ProtectedRoute } from "@/components/auth/protected-route";
import {
  type Notification,
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from "@/lib/events-api";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 20;

function formatTimeAgo(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diff = now - then;

  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;

  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

function getNotificationIcon(type: string, isRead: boolean) {
  const baseClass = "size-[18px]";

  switch (type) {
    case "event_cancelled":
      return {
        icon: <XCircle className={baseClass} />,
        bg: isRead ? "bg-red-500/20" : "bg-red-500",
        fg: isRead ? "text-red-500" : "text-white",
      };
    case "event_updated":
      return {
        icon: <Calendar className={baseClass} />,
        bg: isRead ? "bg-brand-mid/20" : "bg-brand-mid",
        fg: isRead ? "text-brand-mid" : "text-white",
      };
    case "comment_reply":
    case "new_comment":
      return {
        icon: <MessageSquare className={baseClass} />,
        bg: isRead ? "bg-brand-mid/20" : "bg-brand-mid",
        fg: isRead ? "text-brand-mid" : "text-white",
      };
    case "attendance_confirmed":
      return {
        icon: <Check className={baseClass} />,
        bg: isRead ? "bg-green-600/20" : "bg-green-600",
        fg: isRead ? "text-green-600" : "text-white",
      };
    case "access_request":
      return {
        icon: <UserPlus className={baseClass} />,
        bg: isRead ? "bg-brand-dark/20" : "bg-brand-dark",
        fg: isRead ? "text-brand-dark" : "text-white",
      };
    default:
      return {
        icon: <Bell className={baseClass} />,
        bg: isRead ? "bg-brand-mid/20" : "bg-brand-mid",
        fg: isRead ? "text-brand-mid" : "text-white",
      };
  }
}

function NotificationItem({
  notification,
  onMarkRead,
}: {
  notification: Notification;
  onMarkRead: (id: string) => void;
}) {
  const router = useRouter();
  const { icon, bg, fg } = getNotificationIcon(
    notification.type,
    notification.is_read,
  );

  function handleClick() {
    if (!notification.is_read) {
      onMarkRead(notification.id);
    }
    if (notification.event_id) {
      router.push(`/event/${notification.event_id}`);
    }
  }

  return (
    <div
      onClick={handleClick}
      className={cn(
        "group flex cursor-pointer items-start gap-3 px-5 py-4 transition-colors hover:bg-brand-surface/50 sm:px-6",
        !notification.is_read &&
          "border-l-[3px] border-l-brand-mid bg-brand-surface/30",
        notification.is_read && "border-l-[3px] border-l-transparent",
      )}
    >
      {/* Icon */}
      <div
        className={cn(
          "flex size-10 shrink-0 items-center justify-center rounded-full",
          bg,
          fg,
        )}
      >
        {icon}
      </div>

      {/* Content */}
      <div className="min-w-0 flex-1">
        <p
          className={cn(
            "text-sm leading-tight text-brand-dark",
            !notification.is_read && "font-bold",
            notification.is_read && "font-medium",
          )}
        >
          {notification.message}
        </p>
        <p
          className={cn(
            "mt-1 text-xs font-medium",
            !notification.is_read ? "text-brand-mid" : "text-brand-mid/60",
          )}
        >
          {formatTimeAgo(notification.created_at)}
        </p>
      </div>

      {/* Actions */}
      <div className="flex shrink-0 items-center gap-1.5 pt-0.5">
        {!notification.is_read && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onMarkRead(notification.id);
            }}
            className="size-3 rounded-full bg-brand-mid transition-transform hover:scale-125"
            title="Mark as read"
          />
        )}
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-20">
      <div className="flex size-20 items-center justify-center rounded-full bg-brand-mid/10">
        <Bell className="size-10 text-brand-mid/40" />
      </div>
      <h3 className="font-heading mt-6 text-lg font-bold text-brand-dark">
        No notifications yet
      </h3>
      <p className="mt-2 max-w-xs text-center text-sm text-brand-mid">
        When events you follow are updated or cancelled, you&apos;ll see
        notifications here.
      </p>
      <Link
        href="/"
        className="mt-6 rounded-lg bg-brand-mid px-5 py-2 text-sm font-bold text-white transition-colors hover:bg-brand-mid/80"
      >
        Discover Events
      </Link>
    </div>
  );
}

function NotificationsContent() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [markingAll, setMarkingAll] = useState(false);

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  const loadNotifications = useCallback(async (p: number) => {
    setLoading(true);
    try {
      const res = await fetchNotifications(p, PAGE_SIZE);
      setNotifications(res.items);
      setTotalPages(res.total_pages);
      setTotal(res.total);
      setPage(res.page);
    } catch {
      // silently fail — page will show empty
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadNotifications(1);
  }, [loadNotifications]);

  async function handleMarkRead(id: string) {
    // Optimistic update
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)),
    );
    try {
      await markNotificationRead(id);
    } catch {
      // Revert on error
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: false } : n)),
      );
    }
  }

  async function handleMarkAllRead() {
    setMarkingAll(true);
    const previousState = [...notifications];
    // Optimistic update
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    try {
      await markAllNotificationsRead();
    } catch {
      setNotifications(previousState);
    } finally {
      setMarkingAll(false);
    }
  }

  function handlePageChange(newPage: number) {
    if (newPage >= 1 && newPage <= totalPages) {
      void loadNotifications(newPage);
    }
  }

  return (
    <div className="mx-auto w-full max-w-2xl px-4 py-6 sm:px-6 sm:py-8">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="font-heading text-2xl font-bold text-brand-dark sm:text-3xl">
            Notifications
          </h1>
          {total > 0 && (
            <p className="mt-1 text-sm text-brand-mid">
              {unreadCount > 0
                ? `${unreadCount} unread of ${total} total`
                : `${total} notifications`}
            </p>
          )}
        </div>
        {unreadCount > 0 && (
          <button
            onClick={() => {
              void handleMarkAllRead();
            }}
            disabled={markingAll}
            className="flex items-center gap-1.5 rounded-lg border border-brand-mid px-3 py-1.5 text-xs font-bold text-brand-dark transition-all hover:bg-brand-mid-alpha active:scale-[0.96] disabled:opacity-50"
          >
            {markingAll ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              <CheckCheck className="size-3.5" />
            )}
            Mark all as read
          </button>
        )}
      </div>

      {/* Content */}
      <div className="overflow-hidden rounded-xl border border-brand-mid-alpha bg-white shadow-brand-panel">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="size-8 animate-spin text-brand-mid" />
          </div>
        ) : notifications.length === 0 ? (
          <EmptyState />
        ) : (
          <>
            <div className="divide-y divide-brand-mid-alpha/50">
              {notifications.map((n) => (
                <NotificationItem
                  key={n.id}
                  notification={n}
                  onMarkRead={handleMarkRead}
                />
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between border-t border-brand-mid-alpha/50 px-5 py-3 sm:px-6">
                <button
                  onClick={() => handlePageChange(page - 1)}
                  disabled={page <= 1}
                  className="flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-bold text-brand-dark transition-colors hover:bg-brand-mid-alpha disabled:opacity-30"
                >
                  <ChevronLeft className="size-3.5" />
                  Previous
                </button>
                <span className="text-xs font-medium text-brand-mid">
                  Page {page} of {totalPages}
                </span>
                <button
                  onClick={() => handlePageChange(page + 1)}
                  disabled={page >= totalPages}
                  className="flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-bold text-brand-dark transition-colors hover:bg-brand-mid-alpha disabled:opacity-30"
                >
                  Next
                  <ChevronRight className="size-3.5" />
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function NotificationsInner() {
  return (
    <ProtectedRoute>
      <Navbar showSearch={false} />
      <main className="min-h-[calc(100vh-60px)] bg-brand-bg">
        <NotificationsContent />
      </main>
    </ProtectedRoute>
  );
}

export default function NotificationsPage() {
  return (
    <Suspense>
      <NotificationsInner />
    </Suspense>
  );
}
