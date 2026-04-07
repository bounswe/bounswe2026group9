"use client";

import { useEffect, useRef, useState } from "react";
import { CornerDownRight, Send, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  fetchComments,
  postComment,
  deleteComment,
  type Comment,
} from "@/lib/events-api";

const MAX_DEPTH = 3;

interface CommentSectionProps {
  eventId: string;
  isAuthenticated: boolean;
  currentUserId: string | null;
  disabled?: boolean;
  disabledReason?: string;
  scrollRef: React.RefObject<HTMLDivElement | null>;
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

function initials(username: string): string {
  return username.slice(0, 2).toUpperCase();
}

const AVATAR_COLORS = [
  "bg-brand-dark",
  "bg-brand-mid",
  "bg-[#7a5d45]",
  "bg-[#c4a882]",
];

function avatarColor(userId: string): string {
  let hash = 0;
  for (const ch of userId) hash = (hash * 31 + ch.charCodeAt(0)) & 0xffff;
  return AVATAR_COLORS[hash % AVATAR_COLORS.length];
}

function countAllComments(comments: Comment[]): number {
  let count = 0;
  for (const c of comments) {
    count += 1;
    if (c.replies?.length) count += countAllComments(c.replies);
  }
  return count;
}

// ─── Single comment + nested replies ──────────────────────────────────────────

interface CommentNodeProps {
  comment: Comment;
  depth: number;
  eventId: string;
  isAuthenticated: boolean;
  currentUserId: string | null;
  disabled: boolean;
  onDelete: (commentId: string) => void;
  onReply: (parentId: string, text: string) => Promise<Comment | null>;
}

function CommentNode({
  comment,
  depth,
  eventId,
  isAuthenticated,
  currentUserId,
  disabled,
  onDelete,
  onReply,
}: CommentNodeProps) {
  const [showReplyInput, setShowReplyInput] = useState(false);
  const [replyText, setReplyText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [localReplies, setLocalReplies] = useState<Comment[]>(comment.replies ?? []);
  const replyInputRef = useRef<HTMLTextAreaElement>(null);
  const canReply = isAuthenticated && !disabled && depth < MAX_DEPTH;
  function handleToggleReply() {
  const next = !showReplyInput;
  setShowReplyInput(next);
  if (next) {
    setTimeout(() => {
      replyInputRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
      replyInputRef.current?.focus();
    }, 50);
  }
}

  async function handleReply() {
    if (!replyText.trim() || submitting) return;
    setSubmitting(true);
    try {
      const newComment = await onReply(comment.id, replyText.trim());
      if (newComment) {
        setLocalReplies((prev) => [newComment, ...prev]);
        setReplyText("");
        setShowReplyInput(false);
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className={cn("flex gap-3 py-3", depth > 0 && "ml-8 border-l-2 border-brand-mid-alpha/40 pl-4")}>
      <div className="flex-1 min-w-0">
        <div className="flex items-start gap-3">
          <div
            className={cn(
              "flex shrink-0 items-center justify-center rounded-full text-xs font-bold text-white",
              depth === 0 ? "size-8" : "size-6 text-[10px]",
              avatarColor(comment.user.id),
            )}
          >
            {initials(comment.user.username)}
          </div>
          <div className="flex-1 min-w-0">
            <div className="mb-1">
              <strong className="text-sm font-bold text-brand-dark">
                {comment.user.username}
              </strong>
              <span className="text-[12px] text-brand-mid ml-2">· {timeAgo(comment.created_at)}</span>
              {currentUserId === comment.user.id && (
                <button
                  onClick={() => onDelete(comment.id)}
                  className="ml-2 text-brand-mid hover:text-danger transition-colors"
                  aria-label="Delete comment"
                >
                  <Trash2 className="size-3" />
                </button>
              )}
            </div>
            <p className="text-[14px] leading-[1.5] text-brand-dark whitespace-pre-wrap break-words">
              {comment.text}
            </p>
            {canReply && (
              <button
                onClick={handleToggleReply}
                className="mt-1 text-[12px] font-bold text-brand-mid hover:text-brand-dark transition-colors flex items-center gap-1"
              >
                <CornerDownRight className="size-3" />
                {showReplyInput ? "Cancel" : "Reply"}
              </button>
            )}
          </div>
        </div>

        {/* Reply input */}
        {showReplyInput && (
          <div className="flex gap-2 items-start mt-2 ml-11">
            <textarea
              ref={replyInputRef}
              value={replyText}
              onChange={(e) => setReplyText(e.target.value)}
              placeholder={`Reply to ${comment.user.username}...`}
              rows={1}
              className="flex-1 resize-none rounded-lg border border-brand-mid-alpha bg-white px-3 py-2 text-[13px] text-brand-dark placeholder:text-brand-mid/60 outline-none focus:border-brand-mid transition-colors h-10"
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void handleReply();
                }
              }}
            />
            <button
              onClick={() => { void handleReply(); }}
              disabled={!replyText.trim() || submitting}
              className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-brand-dark text-white transition-colors hover:bg-brand-dark/85 disabled:bg-brand-mid-alpha disabled:cursor-not-allowed"
            >
              <Send className="size-3.5" />
            </button>
          </div>
        )}

        {/* Nested replies */}
        {localReplies.length > 0 && (
          <div className="mt-1">
            {localReplies.map((reply) => (
              <CommentNode
                key={reply.id}
                comment={reply}
                depth={depth + 1}
                eventId={eventId}
                isAuthenticated={isAuthenticated}
                currentUserId={currentUserId}
                disabled={disabled}
                onDelete={onDelete}
                onReply={onReply}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Main Section ─────────────────────────────────────────────────────────────

export function CommentSection({
  eventId,
  isAuthenticated,
  currentUserId,
  disabled = false,
  disabledReason,
  scrollRef,
}: CommentSectionProps) {
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    fetchComments(eventId)
      .then((res) => setComments(res.items ?? []))
      .catch(() => setComments([]))
      .finally(() => setLoading(false));
  }, [eventId]);

  const totalCount = countAllComments(comments);

  async function handleSubmit(e: React.SyntheticEvent) {
    e.preventDefault();
    if (!text.trim() || submitting) return;
    setSubmitting(true);
    try {
      const comment = await postComment(eventId, text.trim());
      setComments((prev) => [comment, ...prev]);
      setText("");
    } catch (error) {
      console.error("Comment posting failed:", error);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleReply(parentId: string, replyText: string): Promise<Comment | null> {
    try {
      return await postComment(eventId, replyText, parentId);
    } catch (error) {
      console.error("Reply posting failed:", error);
      return null;
    }
  }

  function handleDelete(commentId: string) {
    void deleteComment(eventId, commentId).then(() => {
      // Remove from tree — works for top-level and nested
      function removeFromList(list: Comment[]): Comment[] {
        return list
          .filter((c) => c.id !== commentId)
          .map((c) => ({ ...c, replies: removeFromList(c.replies ?? []) }));
      }
      setComments((prev) => removeFromList(prev));
    }).catch(() => {});
  }

  return (
    <div ref={scrollRef} className="flex flex-col gap-4 pb-24">
      <h3 className="font-heading text-brand-dark text-lg font-semibold">
        Comments{!loading && <span className="text-brand-mid text-sm font-normal ml-1">({totalCount})</span>}
      </h3>

      {/* Top-level input */}
      <form onSubmit={(e) => { void handleSubmit(e); }} className="flex gap-3 items-start mb-4">
        <div
          className={cn(
            "flex size-8 shrink-0 items-center justify-center rounded-full text-xs font-bold mt-1",
            isAuthenticated ? "bg-brand-mid text-white" : "bg-brand-mid-alpha text-brand-mid",
          )}
        >
          {isAuthenticated ? "ME" : "?"}
        </div>
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={!isAuthenticated || disabled}
          placeholder={
            disabled
              ? (disabledReason ?? "Comments are closed")
              : !isAuthenticated
              ? "Sign in to leave a comment"
              : "Write a comment..."
          }
          rows={1}
          className="flex-1 resize-none rounded-[10px] border border-brand-mid-alpha bg-white px-3.5 py-2.5 text-[14px] text-brand-dark placeholder:text-brand-mid/60 outline-none focus:border-brand-mid transition-colors disabled:bg-brand-bg disabled:cursor-not-allowed h-12"
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void handleSubmit(e);
            }
          }}
        />
        <button
          type="submit"
          disabled={!text.trim() || submitting || !isAuthenticated || disabled}
          className="flex size-10 shrink-0 items-center justify-center rounded-[10px] bg-brand-dark text-white transition-colors hover:bg-brand-dark/85 disabled:bg-brand-mid-alpha disabled:cursor-not-allowed"
        >
          <Send className="size-4" />
        </button>
      </form>

      {/* Comment tree */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex gap-3 animate-pulse">
              <div className="size-9 rounded-full bg-brand-mid-alpha shrink-0" />
              <div className="flex-1 space-y-2 pt-1">
                <div className="h-3 w-1/3 rounded bg-brand-mid-alpha" />
                <div className="h-3 w-full rounded bg-brand-mid-alpha opacity-60" />
              </div>
            </div>
          ))}
        </div>
      ) : comments.length === 0 ? (
        <p className="text-muted-foreground text-sm py-4 text-center">
          No comments yet. Be the first!
        </p>
      ) : (
        <div className="divide-y divide-brand-dark/10">
          {comments.map((comment) => (
            <CommentNode
              key={comment.id}
              comment={comment}
              depth={0}
              eventId={eventId}
              isAuthenticated={isAuthenticated}
              currentUserId={currentUserId}
              disabled={disabled}
              onDelete={handleDelete}
              onReply={handleReply}
            />
          ))}
        </div>
      )}
    </div>
  );
}
