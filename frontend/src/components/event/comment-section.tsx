"use client";

import { useEffect, useRef, useState } from "react";
import { CornerDownRight, Send, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { fetchComments, postComment, deleteComment, type Comment } from "@/lib/events-api";

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

const AVATAR_COLORS = ["bg-brand-dark", "bg-brand-mid", "bg-[#7a5d45]", "bg-[#c4a882]"];

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
  const replyInputRef = useRef<HTMLDivElement>(null);

  const canReply = isAuthenticated && !disabled && depth < MAX_DEPTH;

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
    <div
      className={cn(
        "flex gap-3 py-3",
        depth > 0 && "border-brand-mid-alpha/40 ml-8 border-l-2 pl-4",
      )}
    >
      <div className="min-w-0 flex-1">
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
          <div className="min-w-0 flex-1">
            <div className="mb-1">
              <strong className="text-brand-dark text-sm font-bold">{comment.user.username}</strong>
              <span className="text-brand-mid ml-2 text-[12px]">
                · {timeAgo(comment.created_at)}
              </span>
              {currentUserId === comment.user.id && (
                <button
                  onClick={() => onDelete(comment.id)}
                  className="text-brand-mid hover:text-danger ml-2 transition-colors"
                  aria-label="Delete comment"
                >
                  <Trash2 className="size-3" />
                </button>
              )}
            </div>
            <p className="text-brand-dark text-[14px] leading-[1.5] break-words whitespace-pre-wrap">
              {comment.text}
            </p>
            {canReply && (
              <button
                onClick={() => {
                  const next = !showReplyInput;
                  setShowReplyInput(next);
                  if (next) {
                    setTimeout(() => {
                      replyInputRef.current?.scrollIntoView({
                        behavior: "smooth",
                        block: "nearest",
                      });
                    }, 50);
                  }
                }}
                className="text-brand-mid hover:text-brand-dark mt-1 flex items-center gap-1 text-[12px] font-bold transition-colors"
              >
                <CornerDownRight className="size-3" />
                {showReplyInput ? "Cancel" : "Reply"}
              </button>
            )}
          </div>
        </div>

        {/* Reply input */}
        {showReplyInput && (
          <div ref={replyInputRef} className="mt-2 ml-11 flex items-start gap-2">
            <textarea
              value={replyText}
              onChange={(e) => setReplyText(e.target.value)}
              placeholder={`Reply to ${comment.user.username}...`}
              rows={1}
              className="border-brand-mid-alpha text-brand-dark placeholder:text-brand-mid/60 focus:border-brand-mid h-10 flex-1 resize-none rounded-lg border bg-white px-3 py-2 text-[13px] transition-colors outline-none"
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void handleReply();
                }
              }}
            />
            <button
              onClick={() => {
                void handleReply();
              }}
              disabled={!replyText.trim() || submitting}
              className="bg-brand-dark hover:bg-brand-dark/85 disabled:bg-brand-mid-alpha flex size-8 shrink-0 items-center justify-center rounded-lg text-white transition-colors disabled:cursor-not-allowed"
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
    void deleteComment(eventId, commentId)
      .then(() => {
        // Remove from tree — works for top-level and nested
        function removeFromList(list: Comment[]): Comment[] {
          return list
            .filter((c) => c.id !== commentId)
            .map((c) => ({ ...c, replies: removeFromList(c.replies ?? []) }));
        }
        setComments((prev) => removeFromList(prev));
      })
      .catch(() => {});
  }

  return (
    <div ref={scrollRef} className="flex flex-col gap-4 pb-24">
      <h3 className="font-heading text-brand-dark text-lg font-semibold">
        Comments
        {!loading && (
          <span className="text-brand-mid ml-1 text-sm font-normal">({totalCount})</span>
        )}
      </h3>

      {/* Top-level input */}
      <form
        onSubmit={(e) => {
          void handleSubmit(e);
        }}
        className="mb-4 flex items-start gap-3"
      >
        <div
          className={cn(
            "mt-1 flex size-8 shrink-0 items-center justify-center rounded-full text-xs font-bold",
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
          className="border-brand-mid-alpha text-brand-dark placeholder:text-brand-mid/60 focus:border-brand-mid disabled:bg-brand-bg h-12 flex-1 resize-none rounded-[10px] border bg-white px-3.5 py-2.5 text-[14px] transition-colors outline-none disabled:cursor-not-allowed"
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
          className="bg-brand-dark hover:bg-brand-dark/85 disabled:bg-brand-mid-alpha flex size-10 shrink-0 items-center justify-center rounded-[10px] text-white transition-colors disabled:cursor-not-allowed"
        >
          <Send className="size-4" />
        </button>
      </form>

      {/* Comment tree */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex animate-pulse gap-3">
              <div className="bg-brand-mid-alpha size-9 shrink-0 rounded-full" />
              <div className="flex-1 space-y-2 pt-1">
                <div className="bg-brand-mid-alpha h-3 w-1/3 rounded" />
                <div className="bg-brand-mid-alpha h-3 w-full rounded opacity-60" />
              </div>
            </div>
          ))}
        </div>
      ) : comments.length === 0 ? (
        <p className="text-muted-foreground py-4 text-center text-sm">
          No comments yet. Be the first!
        </p>
      ) : (
        <div className="divide-brand-dark/10 divide-y">
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
