"""Rating service — business logic for host ratings."""

from decimal import Decimal

from fastapi import HTTPException, status
from supabase import Client

from app.models.rating import RatingResponse
from app.repositories import rating as rating_repo
from app.repositories import user as user_repo
from app.repositories import profile as profile_repo


def rate_host(db: Client, rater_id: str, host_id: str, score: Decimal) -> RatingResponse:
    if rater_id == host_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot rate yourself",
        )

    # Check if host exists
    host = user_repo.get_user_by_id(db, host_id)
    if not host:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Host not found")

    events = profile_repo.get_hosted_events(db, host_id)
    if not events:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target user has never hosted an event. Only hosts can be rated"
        )

    # Upsert the rating
    rating = rating_repo.upsert_rating(db, {
        "rater_id": rater_id,
        "host_id": host_id,
        "score": float(score)
    })

    return RatingResponse(
        id=rating["id"],
        rater_id=rating["rater_id"],
        host_id=rating["host_id"],
        score=Decimal(str(rating["score"])),
        created_at=rating["created_at"],
    )
