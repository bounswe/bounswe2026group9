"""Comment service — business logic for event comments."""

from fastapi import HTTPException, status
from supabase import Client

from app.models.comment import (
    CommentAuthor,
    CommentCreateRequest,
    CommentListResponse,
    CommentResponse,
)
from app.repositories import comment as _comment_repo
from app.repositories import event as _event_repo
from app.repositories.protocols import CommentRepoProtocol, EventRepoProtocol

MAX_NESTING_DEPTH = 3


def _get_nesting_depth(
    db: Client, parent_id: str, comments: CommentRepoProtocol
) -> int:
    """Walk up the parent chain to calculate depth (1-indexed). Capped to prevent cycles."""
    depth = 0
    current = parent_id
    while current:
        depth += 1
        if depth > MAX_NESTING_DEPTH + 1:
            break  # Safety valve against data corruption cycles
        comment = comments.get_comment_by_id(db, current)
        if not comment:
            break
        current = comment.get("parent_id")
    return depth


def _build_comment_tree(flat: list[CommentResponse]) -> list[CommentResponse]:
    """Assemble flat comment list into a nested tree."""
    by_id: dict[str, CommentResponse] = {str(c.id): c for c in flat}
    roots: list[CommentResponse] = []
    for c in flat:
        if c.parent_id and str(c.parent_id) in by_id:
            by_id[str(c.parent_id)].replies.append(c)
        else:
            roots.append(c)
    return roots


def create_comment(
    db: Client,
    event_id: str,
    user_id: str,
    body: CommentCreateRequest,
    *,
    comments: CommentRepoProtocol = _comment_repo,
    events: EventRepoProtocol = _event_repo,
) -> CommentResponse:
    event = events.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    if event["status"] not in ("published", "updated"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot comment on this event",
        )

    parent_id_str: str | None = None
    if body.parent_id:
        parent_id_str = str(body.parent_id)
        parent = comments.get_comment_by_id(db, parent_id_str)
        if not parent or parent["event_id"] != event_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent comment not found",
            )
        depth = _get_nesting_depth(db, parent_id_str, comments)
        if depth >= MAX_NESTING_DEPTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum nesting depth of {MAX_NESTING_DEPTH} reached",
            )

    data: dict = {
        "event_id": event_id,
        "user_id": user_id,
        "text": body.text,
    }
    if parent_id_str:
        data["parent_id"] = parent_id_str

    comment = comments.insert_comment(db, data)

    user = comments.get_user_by_id(db, user_id)
    return CommentResponse(
        id=comment["id"],
        event_id=comment["event_id"],
        user=CommentAuthor(id=user["id"], username=user["username"]),
        text=comment["text"],
        created_at=comment["created_at"],
        parent_id=comment.get("parent_id"),
    )


def list_comments(
    db: Client,
    event_id: str,
    *,
    page: int = 1,
    page_size: int = 20,
    comments: CommentRepoProtocol = _comment_repo,
    events: EventRepoProtocol = _event_repo,
) -> CommentListResponse:
    event = events.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    rows, total = comments.get_comments_by_event(
        db, event_id, page=page, page_size=page_size
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    if not rows:
        return CommentListResponse(
            items=[], total=total, page=page, page_size=page_size, total_pages=total_pages
        )

    user_ids = list({c["user_id"] for c in rows})
    user_map = comments.get_users_by_ids(db, user_ids)

    flat = [
        CommentResponse(
            id=c["id"],
            event_id=c["event_id"],
            user=CommentAuthor(
                id=user_map[c["user_id"]]["id"],
                username=user_map[c["user_id"]]["username"],
            ),
            text=c["text"],
            created_at=c["created_at"],
            parent_id=c.get("parent_id"),
        )
        for c in rows
        if c["user_id"] in user_map
    ]

    items = _build_comment_tree(flat)

    return CommentListResponse(
        items=items, total=total, page=page, page_size=page_size, total_pages=total_pages
    )


def delete_comment(
    db: Client,
    event_id: str,
    comment_id: str,
    user_id: str,
    *,
    comments: CommentRepoProtocol = _comment_repo,
    events: EventRepoProtocol = _event_repo,
) -> None:
    comment = comments.get_comment_by_id(db, comment_id)
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found"
        )

    if comment["event_id"] != event_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found"
        )

    event = events.get_event_by_id(db, event_id)

    is_owner = comment["user_id"] == user_id
    is_host = event and event["host_id"] == user_id

    if not is_owner and not is_host:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the comment owner or event host can delete this comment",
        )

    comments.delete_comment(db, comment_id)
