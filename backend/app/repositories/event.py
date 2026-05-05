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

# Accessibility filter mapping: API canonical name → DB column.
# `captions` deliberately maps to the existing `captions_support` column.
# Sign-language interpretation is a separate accessibility feature; modelling
# it as a column is a follow-up (would require a venue_metadata migration +
# create-event UI). The previous `sign_language` API name was misleading
# because it claimed support that the underlying column does not guarantee.
_ACCESSIBILITY_COLS = (
    "wheelchair_access",
    "accessible_restroom",
    "elevator",
    "seating",
    "captions",
    "quiet_friendly",
)
_ACCESSIBILITY_DB_MAP = {
    "wheelchair_access": "wheelchair_access",
    "accessible_restroom": "accessible_restroom",
    "elevator": "elevator_available",
    "seating": "seating_available",
    "captions": "captions_support",
    "quiet_friendly": "quiet_friendly",
}


def _bounding_box(lat: float, lng: float, radius_km: float) -> tuple[float, float, float, float]:
    """Return (lat_min, lat_max, lng_min, lng_max) for a degree-approximation bounding box."""
    # 1 degree latitude ≈ 111.32 km. Longitude scales with cos(latitude).
    import math

    lat_delta = radius_km / 111.32
    cos_lat = max(math.cos(math.radians(lat)), 0.01)
    lng_delta = radius_km / (111.32 * cos_lat)
    return lat - lat_delta, lat + lat_delta, lng - lng_delta, lng + lng_delta


def _weekend_window(now: datetime) -> tuple[datetime, datetime]:
    """Return (saturday_00:00, monday_00:00) for the upcoming weekend in UTC."""
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    # Monday=0 ... Saturday=5, Sunday=6
    days_until_saturday = (5 - today_start.weekday()) % 7
    saturday = today_start + timedelta(days=days_until_saturday)
    monday = saturday + timedelta(days=2)
    return saturday, monday


def list_events(
    db: Client,
    *,
    search: str | None = None,
    category_id: str | None = None,
    quick_filter: str | None = None,
    start_after: datetime | None = None,
    end_before: datetime | None = None,
    near_lat: float | None = None,
    near_lng: float | None = None,
    radius_km: float | None = None,
    accessibility: dict[str, bool | None] | None = None,
    sort: str = "start_time",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    """Return (events, total_count) honouring all discovery filters.

    For sort in {"distance", "category"} the repo returns the FULL filtered
    candidate set (without DB-side pagination) so the service can sort by a
    Python-computed key and slice. For sort="start_time" pagination happens
    at the database for cheaper reads.
    """
    now = datetime.now(UTC)
    accessibility = accessibility or {}

    # Whitelist event IDs from related tables ── intersected at the end.
    whitelists: list[set[str]] = []

    if category_id:
        cat_result = (
            db.table("event_categories")
            .select("event_id")
            .eq("category_id", category_id)
            .execute()
        )
        ids = {row["event_id"] for row in (cat_result.data or [])}
        if not ids:
            return [], 0
        whitelists.append(ids)

    accessibility_required = {k: v for k, v in accessibility.items() if v is True}
    if accessibility_required:
        venue_q = db.table("venue_metadata").select("event_id")
        for canonical, db_col in _ACCESSIBILITY_DB_MAP.items():
            if accessibility_required.get(canonical):
                venue_q = venue_q.eq(db_col, True)
        venue_result = venue_q.execute()
        ids = {row["event_id"] for row in (venue_result.data or [])}
        if not ids:
            return [], 0
        whitelists.append(ids)

    if near_lat is not None and near_lng is not None and radius_km is not None:
        lat_min, lat_max, lng_min, lng_max = _bounding_box(near_lat, near_lng, radius_km)
        loc_result = (
            db.table("event_locations")
            .select("event_id")
            .eq("is_primary", True)
            .gte("latitude", lat_min)
            .lte("latitude", lat_max)
            .gte("longitude", lng_min)
            .lte("longitude", lng_max)
            .execute()
        )
        ids = {row["event_id"] for row in (loc_result.data or [])}
        if not ids:
            return [], 0
        whitelists.append(ids)

    final_whitelist: list[str] | None = None
    if whitelists:
        intersection = set.intersection(*whitelists)
        if not intersection:
            return [], 0
        final_whitelist = list(intersection)

    is_past = quick_filter == "past"

    def _apply_filters(q):
        if is_past:
            q = q.in_("status", ["ended", "cancelled", "updated", "published"])
            q = q.lt("end_datetime", now.isoformat())
        else:
            q = q.in_("status", ["published", "updated"])
            q = q.gte("end_datetime", now.isoformat())

        if search:
            safe = search.replace("%", r"\%").replace("_", r"\_")
            q = q.or_(f"title.ilike.%{safe}%,description.ilike.%{safe}%")
        if final_whitelist is not None:
            q = q.in_("id", final_whitelist)

        if quick_filter == "now":
            q = q.lte("start_datetime", now.isoformat()).gte("end_datetime", now.isoformat())
        elif quick_filter == "today":
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow = today_start + timedelta(days=1)
            q = q.gte("start_datetime", today_start.isoformat()).lt("start_datetime", tomorrow.isoformat())
        elif quick_filter == "this_week":
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_end = today_start + timedelta(days=7)
            q = q.gte("start_datetime", today_start.isoformat()).lt("start_datetime", week_end.isoformat())
        elif quick_filter == "weekend":
            sat, mon = _weekend_window(now)
            q = q.gte("start_datetime", sat.isoformat()).lt("start_datetime", mon.isoformat())
        elif quick_filter == "upcoming":
            q = q.gte("start_datetime", now.isoformat())

        if start_after is not None:
            q = q.gte("start_datetime", start_after.isoformat())
        if end_before is not None:
            q = q.lte("end_datetime", end_before.isoformat())

        return q

    count_result = _apply_filters(db.table("events").select("id", count="exact")).execute()
    total = count_result.count or 0
    if total == 0:
        return [], 0

    if sort == "start_time":
        offset = (page - 1) * page_size
        if offset >= total:
            return [], total
        order_desc = is_past  # past events: most recent first
        result = (
            _apply_filters(db.table("events").select(_EVENT_COLS))
            .order("start_datetime", desc=order_desc)
            .order("id")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        return result.data or [], total

    # Distance / category sort: fetch full candidate set so the service layer
    # can sort by a Python-computed key and slice for pagination.
    result = (
        _apply_filters(db.table("events").select(_EVENT_COLS))
        .order("start_datetime")
        .order("id")
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


def get_similar_candidates(db: Client, event_id: str, limit: int = 30) -> list[dict]:
    """Return published/updated future public events excluding the source event."""
    now = datetime.now(UTC)
    result = (
        db.table("events")
        .select(_EVENT_COLS)
        .in_("status", ["published", "updated"])
        .gte("end_datetime", now.isoformat())
        .neq("id", event_id)
        .eq("visibility", "public")
        .order("start_datetime")
        .order("id")
        .limit(limit)
        .execute()
    )
    return result.data or []
