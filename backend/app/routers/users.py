"""User endpoints — HTTP layer for profiles, ratings, bookmarks."""

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.database import get_supabase
from app.middleware.auth import get_current_user_id, get_optional_user_id
from app.models.bookmark import BookmarkListResponse
from app.models.profile import HostProfileResponse, ProfileUpdateRequest
from app.models.rating import RatingRequest, RatingResponse, ReviewListResponse
from app.models.user import UserResponse
from app.services.bookmark import list_user_bookmarks
from app.services.profile import get_host_profile, update_profile
from app.services.rating import list_reviews, rate_host

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me/bookmarks", response_model=BookmarkListResponse)
def get_my_bookmarks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
):
    db = get_supabase()
    return list_user_bookmarks(db, user_id, page=page, page_size=page_size)


@router.put("/me", response_model=UserResponse)
def update_my_profile(
    body: ProfileUpdateRequest,
    user_id: str = Depends(get_current_user_id),
):
    db = get_supabase()
    return update_profile(db, user_id, body)


@router.get("/{target_user_id}/profile", response_model=HostProfileResponse)
def get_user_profile(
    target_user_id: UUID,
    current_user_id: str | None = Depends(get_optional_user_id),
):
    db = get_supabase()
    return get_host_profile(db, str(target_user_id), current_user_id)


@router.post("/{host_id}/ratings", response_model=RatingResponse, status_code=201)
def rate_host_endpoint(
    host_id: UUID,
    body: RatingRequest,
    rater_id: str = Depends(get_current_user_id),
):
    db = get_supabase()
    return rate_host(
        db, rater_id, str(host_id), Decimal(str(body.score)), body.review_text,
    )


@router.get("/{host_id}/reviews", response_model=ReviewListResponse)
def list_host_reviews(
    host_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    db = get_supabase()
    return list_reviews(db, str(host_id), page=page, page_size=page_size)
