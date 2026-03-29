"""Bookmark service — business logic for event bookmarks."""

from fastapi import HTTPException, status
from supabase import Client

from app.models.bookmark import (
    BookmarkedEventResponse,
    BookmarkListResponse,
    BookmarkResponse,
)
from app.repositories import bookmark as bookmark_repo
from app.repositories import event as event_repo


def create_bookmark(db: Client, event_id: str, user_id: str) -> BookmarkResponse:
    event = event_repo.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    if event["status"] not in ("published", "updated"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot bookmark this event",
        )

    existing = bookmark_repo.get_bookmark(db, user_id, event_id)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already bookmarked")

    bookmark = bookmark_repo.insert_bookmark(db, {
        "user_id": user_id,
        "event_id": event_id,
    })

    return BookmarkResponse(
        id=bookmark["id"],
        event_id=bookmark["event_id"],
        created_at=bookmark["created_at"],
    )


def remove_bookmark(db: Client, event_id: str, user_id: str) -> None:
    existing = bookmark_repo.get_bookmark(db, user_id, event_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark not found")

    bookmark_repo.delete_bookmark(db, user_id, event_id)


def list_user_bookmarks(
    db: Client, user_id: str, *, page: int = 1, page_size: int = 20
) -> BookmarkListResponse:
    bookmarks, total = bookmark_repo.get_bookmarks_by_user(
        db, user_id, page=page, page_size=page_size,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    if not bookmarks:
        return BookmarkListResponse(
            items=[], total=total, page=page, page_size=page_size, total_pages=total_pages,
        )

    event_ids = [b["event_id"] for b in bookmarks]
    bookmark_dates = {b["event_id"]: b["created_at"] for b in bookmarks}

    # Batch load event data
    events_data = {}
    for eid in event_ids:
        ev = event_repo.get_event_by_id(db, eid)
        if ev:
            events_data[eid] = ev

    valid_event_ids = list(events_data.keys())
    locations_by_event = event_repo.get_primary_locations_for_events(db, valid_event_ids)
    categories_by_event = event_repo.get_categories_for_events(db, valid_event_ids)
    images_by_event = event_repo.get_primary_images_for_events(db, valid_event_ids)

    items = []
    for eid in event_ids:
        ev = events_data.get(eid)
        if not ev:
            continue
        is_private = ev["visibility"] == "private"
        items.append(BookmarkedEventResponse(
            id=ev["id"],
            title=ev["title"],
            start_datetime=ev["start_datetime"],
            end_datetime=ev["end_datetime"],
            visibility=ev["visibility"],
            is_age_restricted=ev["is_age_restricted"],
            status=ev["status"],
            categories=categories_by_event.get(eid, []),
            primary_location=locations_by_event.get(eid) if not is_private else None,
            primary_image_url=images_by_event.get(eid) if not is_private else None,
            bookmarked_at=bookmark_dates[eid],
        ))

    return BookmarkListResponse(
        items=items, total=total, page=page, page_size=page_size, total_pages=total_pages,
    )
