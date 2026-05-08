"""Category repository — database operations for categories."""

from supabase import Client


def get_all_available(db: Client) -> list[dict]:
    """Get predefined + approved categories."""
    result = (
        db.table("categories")
        .select("id,name,is_predefined,is_approved")
        .or_("is_predefined.eq.true,is_approved.eq.true")
        .order("name")
        .execute()
    )
    return result.data or []


def search_available(db: Client, query: str) -> list[dict]:
    result = (
        db.table("categories")
        .select("id,name,is_predefined,is_approved")
        .or_("is_predefined.eq.true,is_approved.eq.true")
        .ilike("name", f"%{query}%")
        .order("name")
        .execute()
    )
    return result.data or []


def get_by_name(db: Client, name: str) -> dict | None:
    """Case-insensitive exact match using lower() to align with DB constraint."""
    result = db.table("categories").select("id,name,is_predefined,is_approved").ilike("name", name.strip()).execute()
    return result.data[0] if result.data else None


def insert_category(db: Client, data: dict) -> dict | None:
    result = db.table("categories").insert(data).execute()
    return result.data[0] if result.data else None


def get_categories_by_ids(db: Client, ids: list[str]) -> list[dict]:
    """Fetch name for a list of category UUIDs (used by suggestion cluster expansion)."""
    if not ids:
        return []
    result = (
        db.table("categories")
        .select("id,name")
        .in_("id", ids)
        .execute()
    )
    return result.data or []


def get_categories_by_names(db: Client, names: list[str]) -> list[dict]:
    """Fetch id for a list of exact category names (used by suggestion cluster expansion)."""
    if not names:
        return []
    result = (
        db.table("categories")
        .select("id,name")
        .in_("name", names)
        .execute()
    )
    return result.data or []
