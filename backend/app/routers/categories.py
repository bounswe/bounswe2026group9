"""Category endpoints — HTTP layer only."""

from fastapi import APIRouter, Depends, Query, status

from app.database import get_supabase
from app.middleware.auth import get_current_user_id
from app.models.event import CategoryCreateRequest, CategoryResponse
from app.services.category import create_custom_category, list_categories

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryResponse])
def list_categories_endpoint(
    search: str | None = Query(default=None, min_length=1),
):
    db = get_supabase()
    return list_categories(db, search)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CategoryResponse)
def create_category_endpoint(
    body: CategoryCreateRequest,
    user_id: str = Depends(get_current_user_id),
):
    db = get_supabase()
    return create_custom_category(db, body, user_id)
