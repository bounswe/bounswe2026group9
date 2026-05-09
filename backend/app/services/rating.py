"""Rating service — business logic for host ratings and review listing."""

from decimal import Decimal

from fastapi import HTTPException, status
from supabase import Client

from app.models.rating import (
    RatingResponse,
    ReviewListItemResponse,
    ReviewListResponse,
)
from app.repositories import attendance as _attendance_repo
from app.repositories import profile as _profile_repo
from app.repositories import rating as _rating_repo
from app.repositories import user as _user_repo
from app.repositories.protocols import (
    AttendanceRepoProtocol,
    ProfileRepoProtocol,
    RatingRepoProtocol,
    UserRepoProtocol,
)


def _normalise_review_text(text: str | None) -> str | None:
    """Trim surrounding whitespace; whitespace-only → None.

    Decided in the issue planning: locked decision #4 — keep DB free of
    sham reviews; placeholder rendering on frontend works correctly.
    """
    if text is None:
        return None
    cleaned = text.strip()
    return cleaned if cleaned else None


def rate_host(
    db: Client,
    rater_id: str,
    host_id: str,
    score: Decimal,
    review_text: str | None = None,
    *,
    users: UserRepoProtocol = _user_repo,
    profiles: ProfileRepoProtocol = _profile_repo,
    attendances: AttendanceRepoProtocol = _attendance_repo,
    ratings: RatingRepoProtocol = _rating_repo,
) -> RatingResponse:
    if rater_id == host_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot rate yourself",
        )

    # Check if host exists
    host = users.get_user_by_id(db, host_id)
    if not host:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Host not found")

    events = profiles.get_hosted_events(db, host_id)
    if not events:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target user has never hosted an event. Only hosts can be rated"
        )

    # Only allow rating if the rater attended at least one ended event by this host
    if not attendances.has_attended_ended_event_by_host(db, rater_id, host_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only rate a host after attending one of their ended events"
        )

    # Upsert the rating (review_text overwrites previous value — locked decision #5)
    rating = ratings.upsert_rating(db, {
        "rater_id": rater_id,
        "host_id": host_id,
        "score": float(score),
        "review_text": _normalise_review_text(review_text),
    })

    return RatingResponse(
        id=rating["id"],
        rater_id=rating["rater_id"],
        host_id=rating["host_id"],
        score=Decimal(str(rating["score"])),
        review_text=rating.get("review_text"),
        created_at=rating["created_at"],
    )


def list_reviews(
    db: Client,
    host_id: str,
    *,
    page: int = 1,
    page_size: int = 20,
    users: UserRepoProtocol = _user_repo,
    ratings: RatingRepoProtocol = _rating_repo,
) -> ReviewListResponse:
    """Return paginated reviews for a host, newest-first.

    Mirrors `GET /users/{id}/profile`: 404 if the host does not exist,
    200 with empty `items` if the host exists but has no ratings yet.
    """
    host = users.get_user_by_id(db, host_id)
    if not host:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    rows, total = ratings.list_reviews_for_host(
        db, host_id, page=page, page_size=page_size,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    if not rows:
        return ReviewListResponse(
            items=[], total=total, page=page, page_size=page_size, total_pages=total_pages,
        )

    rater_ids = list({row["rater_id"] for row in rows})
    rater_users = users.get_users_by_ids(db, rater_ids)
    username_by_id = {u["id"]: u.get("username", "unknown") for u in rater_users}

    items = [
        ReviewListItemResponse(
            id=row["id"],
            rater_id=row["rater_id"],
            rater_username=username_by_id.get(row["rater_id"], "unknown"),
            score=Decimal(str(row["score"])),
            review_text=row.get("review_text"),
            created_at=row["created_at"],
        )
        for row in rows
    ]

    return ReviewListResponse(
        items=items, total=total, page=page, page_size=page_size, total_pages=total_pages,
    )
