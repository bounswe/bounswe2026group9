"""Event repository — all database operations for events and related tables."""

from supabase import Client


def insert_event(db: Client, event_data: dict) -> dict:
    result = db.table("events").insert(event_data).execute()
    if not result.data:
        return None
    return result.data[0]


def insert_locations(db: Client, locations: list[dict]) -> list[dict]:
    result = db.table("event_locations").insert(locations).execute()
    return result.data or []


def insert_event_categories(db: Client, rows: list[dict]) -> None:
    db.table("event_categories").insert(rows).execute()


def insert_venue_metadata(db: Client, data: dict) -> dict | None:
    result = db.table("venue_metadata").insert(data).execute()
    return result.data[0] if result.data else None


def insert_equipment(db: Client, rows: list[dict]) -> list[dict]:
    result = db.table("equipment_requirements").insert(rows).execute()
    return result.data or []


def get_event_by_id(db: Client, event_id: str) -> dict | None:
    result = db.table("events").select("*").eq("id", event_id).execute()
    return result.data[0] if result.data else None


def get_event_locations(db: Client, event_id: str) -> list[dict]:
    result = db.table("event_locations").select("*").eq("event_id", event_id).execute()
    return result.data or []


def get_event_categories(db: Client, event_id: str) -> list[dict]:
    result = (
        db.table("event_categories")
        .select("category_id, categories(id, name, is_predefined, is_approved)")
        .eq("event_id", event_id)
        .execute()
    )
    return [row["categories"] for row in result.data] if result.data else []


def get_event_images(db: Client, event_id: str) -> list[dict]:
    result = db.table("event_images").select("*").eq("event_id", event_id).execute()
    return result.data or []


def get_venue_metadata(db: Client, event_id: str) -> dict | None:
    result = db.table("venue_metadata").select("*").eq("event_id", event_id).execute()
    return result.data[0] if result.data else None


def get_equipment(db: Client, event_id: str) -> list[dict]:
    result = db.table("equipment_requirements").select("*").eq("event_id", event_id).execute()
    return result.data or []


def update_event(db: Client, event_id: str, data: dict) -> dict | None:
    result = db.table("events").update(data).eq("id", event_id).execute()
    return result.data[0] if result.data else None


def update_event_status(db: Client, event_id: str, new_status: str) -> dict | None:
    result = db.table("events").update({"status": new_status}).eq("id", event_id).execute()
    return result.data[0] if result.data else None


def delete_event(db: Client, event_id: str) -> None:
    db.table("events").delete().eq("id", event_id).execute()


def delete_event_locations(db: Client, event_id: str) -> None:
    db.table("event_locations").delete().eq("event_id", event_id).execute()


def delete_event_categories(db: Client, event_id: str) -> None:
    db.table("event_categories").delete().eq("event_id", event_id).execute()


def delete_venue_metadata(db: Client, event_id: str) -> None:
    db.table("venue_metadata").delete().eq("event_id", event_id).execute()


def delete_equipment(db: Client, event_id: str) -> None:
    db.table("equipment_requirements").delete().eq("event_id", event_id).execute()


def count_events_by_host_since(db: Client, host_id: str, cutoff_iso: str) -> int:
    result = (
        db.table("events")
        .select("id", count="exact")
        .eq("host_id", host_id)
        .gte("created_at", cutoff_iso)
        .execute()
    )
    return result.count or 0


def find_duplicate_events(db: Client, host_id: str, title: str, start_datetime: str) -> list[dict]:
    result = (
        db.table("events")
        .select("id")
        .eq("host_id", host_id)
        .eq("title", title)
        .eq("start_datetime", start_datetime)
        .in_("status", ["draft", "published", "updated"])
        .execute()
    )
    return result.data or []


def find_location_by_event_and_name(db: Client, event_id: str, name: str) -> list[dict]:
    result = (
        db.table("event_locations")
        .select("name")
        .eq("event_id", event_id)
        .eq("name", name)
        .execute()
    )
    return result.data or []


def get_rate_limit_config(db: Client) -> dict | None:
    result = db.table("rate_limit_config").select("*").limit(1).execute()
    return result.data[0] if result.data else None


def get_valid_category_ids(db: Client, category_ids: list[str]) -> set[str]:
    result = (
        db.table("categories")
        .select("id")
        .in_("id", category_ids)
        .or_("is_predefined.eq.true,is_approved.eq.true")
        .execute()
    )
    return {row["id"] for row in result.data}


# --- Discovery ---

def list_events(
    db: Client,
    *,
    search: str | None = None,
    category_id: str | None = None,
    temporal_filter: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    """Return (events, total_count) for public published/updated events."""
    from datetime import UTC, datetime, timedelta

    query = db.table("events").select("*", count="exact")
    query = query.in_("status", ["published", "updated"])
    query = query.eq("visibility", "public")

    if search:
        safe = search.replace("%", r"\%").replace("_", r"\_")
        query = query.or_(f"title.ilike.%{safe}%,description.ilike.%{safe}%")

    if category_id:
        cat_result = (
            db.table("event_categories")
            .select("event_id")
            .eq("category_id", category_id)
            .execute()
        )
        event_ids = [row["event_id"] for row in (cat_result.data or [])]
        if not event_ids:
            return [], 0
        query = query.in_("id", event_ids)

    now = datetime.now(UTC)
    if temporal_filter == "upcoming":
        query = query.gte("start_datetime", now.isoformat())
    elif temporal_filter == "today":
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today_start + timedelta(days=1)
        query = (
            query
            .gte("start_datetime", today_start.isoformat())
            .lt("start_datetime", tomorrow.isoformat())
        )
    elif temporal_filter == "this_week":
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = today_start + timedelta(days=7)
        query = (
            query
            .gte("start_datetime", today_start.isoformat())
            .lt("start_datetime", week_end.isoformat())
        )

    offset = (page - 1) * page_size
    # First get total count without range to avoid PGRST103 when offset > total
    count_result = query.execute()
    total = count_result.count or 0
    if offset >= total:
        return [], total
    result = query.order("start_datetime").range(offset, offset + page_size - 1).execute()
    return result.data or [], total


def get_primary_locations_for_events(db: Client, event_ids: list[str]) -> dict[str, dict]:
    """Return {event_id: primary_location_row} for a batch of events."""
    if not event_ids:
        return {}
    result = (
        db.table("event_locations")
        .select("*")
        .in_("event_id", event_ids)
        .eq("is_primary", True)
        .execute()
    )
    return {row["event_id"]: row for row in (result.data or [])}


def get_categories_for_events(db: Client, event_ids: list[str]) -> dict[str, list[dict]]:
    """Return {event_id: [category_rows]} for a batch of events."""
    if not event_ids:
        return {}
    result = (
        db.table("event_categories")
        .select("event_id, categories(id, name, is_predefined, is_approved)")
        .in_("event_id", event_ids)
        .execute()
    )
    cats: dict[str, list[dict]] = {}
    for row in (result.data or []):
        cats.setdefault(row["event_id"], []).append(row["categories"])
    return cats


def get_primary_images_for_events(db: Client, event_ids: list[str]) -> dict[str, str]:
    """Return {event_id: first_image_url} for a batch of events."""
    if not event_ids:
        return {}
    result = (
        db.table("event_images")
        .select("event_id, image_url")
        .in_("event_id", event_ids)
        .execute()
    )
    images: dict[str, str] = {}
    for row in (result.data or []):
        eid = row["event_id"]
        if eid not in images:
            images[eid] = row["image_url"]
    return images
