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
