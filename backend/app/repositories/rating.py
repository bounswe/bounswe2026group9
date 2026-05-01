"""Rating repository — database operations for host ratings."""

from supabase import Client

_RATING_COLS = "id,rater_id,host_id,score,review_text,created_at"


def get_rating(db: Client, rater_id: str, host_id: str) -> dict | None:
    result = (
        db.table("ratings")
        .select(_RATING_COLS)
        .eq("rater_id", rater_id)
        .eq("host_id", host_id)
        .execute()
    )
    return result.data[0] if result.data else None


def upsert_rating(db: Client, data: dict) -> dict:
    # Supabase unique constraint on (rater_id, host_id) allows upsert
    result = db.table("ratings").upsert(data, on_conflict="rater_id,host_id").execute()
    return result.data[0]


def get_host_rating_stats(db: Client, host_id: str) -> dict:
    """Returns average score and count of ratings for a host."""
    result = (
        db.table("ratings")
        .select("score", count="exact")
        .eq("host_id", host_id)
        .execute()
    )
    if not result.data:
        return {"average": None, "count": 0}

    total_score = sum(float(row["score"]) for row in result.data)
    count = len(result.data)
    return {"average": total_score / count, "count": count}


def list_reviews_for_host(
    db: Client, host_id: str, *, page: int = 1, page_size: int = 20,
) -> tuple[list[dict], int]:
    """Return (rows, total_count) of ratings for a host, newest-first.

    Uses a two-query pattern (count + page) to avoid PostgREST's
    embedded-relationship name coupling (`users!ratings_rater_id_fkey(...)`)
    — the FK name is environment-specific and silently fails if it differs
    in Supabase. The service layer joins `rater_username` separately via
    `user_repo.get_users_by_ids`.
    """
    count_result = (
        db.table("ratings")
        .select("id", count="exact")
        .eq("host_id", host_id)
        .execute()
    )
    total = count_result.count or 0

    if total == 0:
        return [], 0

    offset = (page - 1) * page_size
    if offset >= total:
        return [], total

    result = (
        db.table("ratings")
        .select(_RATING_COLS)
        .eq("host_id", host_id)
        .order("created_at", desc=True)
        .order("id", desc=True)
        .range(offset, offset + page_size - 1)
        .execute()
    )
    return result.data or [], total
