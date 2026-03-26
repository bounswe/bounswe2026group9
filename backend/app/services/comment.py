"""Comment service — business logic for event comments."""

from fastapi import HTTPException, status
from supabase import Client

from app.models.comment import (
    CommentAuthor,
    CommentCreateRequest,
    CommentListResponse,
    CommentResponse,
)
from app.repositories import comment as comment_repo
from app.repositories import event as event_repo


def create_comment(
    db: Client, event_id: str, user_id: str, body: CommentCreateRequest
) -> CommentResponse:
    event = event_repo.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    if event["status"] not in ("published", "updated"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot comment on this event",
        )

    comment = comment_repo.insert_comment(db, {
        "event_id": event_id,
        "user_id": user_id,
        "text": body.text,
    })

    user = comment_repo.get_user_by_id(db, user_id)
    return CommentResponse(
        id=comment["id"],
        event_id=comment["event_id"],
        user=CommentAuthor(id=user["id"], username=user["username"]),
        text=comment["text"],
        created_at=comment["created_at"],
    )


def list_comments(
    db: Client, event_id: str, *, page: int = 1, page_size: int = 20
) -> CommentListResponse:
    event = event_repo.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    comments, total = comment_repo.get_comments_by_event(
        db, event_id, page=page, page_size=page_size
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    if not comments:
        return CommentListResponse(
            items=[], total=total, page=page, page_size=page_size, total_pages=total_pages
        )

    user_ids = list({c["user_id"] for c in comments})
    users = comment_repo.get_users_by_ids(db, user_ids)

    items = [
        CommentResponse(
            id=c["id"],
            event_id=c["event_id"],
            user=CommentAuthor(
                id=users[c["user_id"]]["id"],
                username=users[c["user_id"]]["username"],
            ),
            text=c["text"],
            created_at=c["created_at"],
        )
        for c in comments
        if c["user_id"] in users
    ]

    return CommentListResponse(
        items=items, total=total, page=page, page_size=page_size, total_pages=total_pages
    )


def delete_comment(db: Client, event_id: str, comment_id: str, user_id: str) -> None:
    comment = comment_repo.get_comment_by_id(db, comment_id)
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found"
        )

    if comment["event_id"] != event_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found"
        )

    event = event_repo.get_event_by_id(db, event_id)

    is_owner = comment["user_id"] == user_id
    is_host = event and event["host_id"] == user_id

    if not is_owner and not is_host:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the comment owner or event host can delete this comment",
        )

    comment_repo.delete_comment(db, comment_id)
