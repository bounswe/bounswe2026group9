"""Category service — business logic for categories."""

from fastapi import HTTPException, status
from supabase import Client

from app.models.event import CategoryCreateRequest, CategoryResponse
from app.repositories import category as category_repo


def list_categories(db: Client, search: str | None = None) -> list[CategoryResponse]:
    if search:
        rows = category_repo.search_available(db, search)
    else:
        rows = category_repo.get_all_available(db)
    return [CategoryResponse(**row) for row in rows]


def create_custom_category(
    db: Client, body: CategoryCreateRequest, user_id: str,
) -> CategoryResponse:
    existing = category_repo.get_by_name(db, body.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category '{body.name}' already exists",
        )

    data = {
        "name": body.name.strip(),
        "is_predefined": False,
        "is_approved": False,
    }
    try:
        row = category_repo.insert_category(db, data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category '{body.name}' already exists",
        ) from e
    if not row:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create category")
    return CategoryResponse(**row)
