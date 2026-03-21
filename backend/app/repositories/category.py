"""Category repository — database operations for categories."""

from supabase import Client


def get_all_available(db: Client) -> list[dict]:
    """Get predefined + approved categories."""
    result = (
        db.table("categories")
        .select("*")
        .or_("is_predefined.eq.true,is_approved.eq.true")
        .order("name")
        .execute()
    )
    return result.data or []


def search_available(db: Client, query: str) -> list[dict]:
    result = (
        db.table("categories")
        .select("*")
        .or_("is_predefined.eq.true,is_approved.eq.true")
        .ilike("name", f"%{query}%")
        .order("name")
        .execute()
    )
    return result.data or []


def get_by_name(db: Client, name: str) -> dict | None:
    result = db.table("categories").select("*").ilike("name", name).execute()
    return result.data[0] if result.data else None


def insert_category(db: Client, data: dict) -> dict | None:
    result = db.table("categories").insert(data).execute()
    return result.data[0] if result.data else None
