"""Event repository — all database operations for events and related tables."""

from datetime import UTC, datetime, timedelta

from supabase import Client

_EVENT_COLS = (
    "id,host_id,title,description,start_datetime,end_datetime,"
    "visibility,is_age_restricted,attendee_limit,attendee_count,"
    "status,created_at,updated_at"
)
_LOCATION_COLS = "id,event_id,name,latitude,longitude,is_primary,order_index"
_IMAGE_COLS = "id,event_id,image_url,upload_date"
_VENUE_COLS = (
    "id,event_id,price,language,health_requirements,wheelchair_access,accessible_restroom,"
    "elevator_available,seating_available,captions_support,quiet_friendly"
)
_EQUIPMENT_COLS = "id,event_id,item_name,is_required"
_SEGMENT_COLS = "id,event_id,location_id,order_index,start_datetime,end_datetime,description"
_RATE_LIMIT_COLS = "id,max_events_per_user,time_window_hours,updated_at"


# --- Atomic event creation via RPC ---

def create_event_atomic(
    db: Client,
    event_data: dict,
    locations: list[dict],
    category_ids: list[str],
    venue_metadata: dict | None = None,
    equipment: list[dict] | None = None,
    segments: list[dict] | None = None,
) -> dict:
    """Create event + locations + categories + venue + equipment + segments in a single DB transaction."""
    params = {
        "p_event": event_data,
        "p_locations": locations,
        "p_categories": [{"category_id": cid} for cid in category_ids],
        "p_venue_metadata": venue_metadata,
        "p_equipment": equipment,
        "p_segments": segments,
    }
    result = db.rpc("create_event_atomic", params).execute()
    return result.data


def update_event_atomic(
    db: Client,
    event_id: str,
    event_data: dict | None = None,
    locations: list[dict] | None = None,
    category_ids: list[str] | None = None,
    venue_metadata: dict | None = None,
    equipment: list[dict] | None = None,
    segments: list[dict] | None = None,
) -> dict:
    """Update event + related tables in a single DB transaction."""
    params = {
        "p_event_id": event_id,
        "p_event_data": event_data if event_data else None,
        "p_locations": locations,
        "p_categories": [{"category_id": cid} for cid in category_ids] if category_ids is not None else None,
        "p_venue_metadata": venue_metadata,
        "p_equipment": equipment,
        "p_segments": segments,
    }
    result = db.rpc("update_event_atomic", params).execute()
    return result.data


# --- Legacy individual inserts (kept for tests) ---

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
    result = db.table("events").select(_EVENT_COLS).eq("id", event_id).execute()
    return result.data[0] if result.data else None


def get_event_locations(db: Client, event_id: str) -> list[dict]:
    # Deterministic order — matches the fallback in update_event_atomic so
    # that SegmentRequest.location_index against an *existing* location set
    # (a PATCH that only sends `segments`) refers to the same position the
    # client saw from this read.
    result = (
        db.table("event_locations")
        .select(_LOCATION_COLS)
        .eq("event_id", event_id)
        .order("created_at")
        .order("order_index")
        .order("id")
        .execute()
    )
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
    result = db.table("event_images").select(_IMAGE_COLS).eq("event_id", event_id).execute()
    return result.data or []


def get_venue_metadata(db: Client, event_id: str) -> dict | None:
    result = db.table("venue_metadata").select(_VENUE_COLS).eq("event_id", event_id).execute()
    return result.data[0] if result.data else None


def get_equipment(db: Client, event_id: str) -> list[dict]:
    result = db.table("equipment_requirements").select(_EQUIPMENT_COLS).eq("event_id", event_id).execute()
    return result.data or []


def get_event_segments(db: Client, event_id: str) -> list[dict]:
    result = (
        db.table("event_segments")
        .select(_SEGMENT_COLS)
        .eq("event_id", event_id)
        .order("order_index")
        .execute()
    )
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
    """Return matching primary-location rows for the event.

    Scoped to is_primary=True so duplicate-event detection only fires when the
    *primary* location matches (issue #149 FRS-2: "identical title +
    start_datetime + primary location"). A non-primary stop with the same name
    on the candidate event is intentionally not treated as a collision.
    """
    result = (
        db.table("event_locations")
        .select("name")
        .eq("event_id", event_id)
        .eq("name", name)
        .eq("is_primary", True)
        .execute()
    )
    return result.data or []


def get_rate_limit_config(db: Client) -> dict | None:
    result = db.table("rate_limit_config").select(_RATE_LIMIT_COLS).limit(1).execute()
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
    """Return (events, total_count) for all published/updated events (public + private)."""
    now = datetime.now(UTC)

    # Resolve category event IDs upfront (shared by both count and data queries)
    category_event_ids: list[str] | None = None
    if category_id:
        cat_result = (
            db.table("event_categories")
            .select("event_id")
            .eq("category_id", category_id)
            .execute()
        )
        category_event_ids = [row["event_id"] for row in (cat_result.data or [])]
        if not category_event_ids:
            return [], 0

    def _apply_filters(q):
        q = q.in_("status", ["published", "updated"])
        q = q.gte("end_datetime", now.isoformat())  # Exclude events whose end time has passed
        if search:
            safe = search.replace("%", r"\%").replace("_", r"\_")
            q = q.or_(f"title.ilike.%{safe}%,description.ilike.%{safe}%")
        if category_event_ids is not None:
            q = q.in_("id", category_event_ids)
        if temporal_filter == "upcoming":
            q = q.gte("start_datetime", now.isoformat())
        elif temporal_filter == "today":
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow = today_start + timedelta(days=1)
            q = q.gte("start_datetime", today_start.isoformat()).lt("start_datetime", tomorrow.isoformat())
        elif temporal_filter == "this_week":
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_end = today_start + timedelta(days=7)
            q = q.gte("start_datetime", today_start.isoformat()).lt("start_datetime", week_end.isoformat())
        return q

    # Count query: fetch only IDs to avoid transferring all columns just for counting
    count_result = _apply_filters(db.table("events").select("id", count="exact")).execute()
    total = count_result.count or 0

    offset = (page - 1) * page_size
    if offset >= total:
        return [], total

    # Data query: fetch full rows, sorted deterministically
    result = (
        _apply_filters(db.table("events").select(_EVENT_COLS))
        .order("start_datetime")
        .order("id")
        .range(offset, offset + page_size - 1)
        .execute()
    )
    return result.data or [], total


def get_primary_locations_for_events(db: Client, event_ids: list[str]) -> dict[str, dict]:
    """Return {event_id: primary_location_row} for a batch of events."""
    if not event_ids:
        return {}
    result = (
        db.table("event_locations")
        .select(_LOCATION_COLS)
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
        .order("upload_date")
        .execute()
    )
    images: dict[str, str] = {}
    for row in (result.data or []):
        eid = row["event_id"]
        if eid not in images:
            images[eid] = row["image_url"]
    return images
