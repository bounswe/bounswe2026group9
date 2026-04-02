"""Rating repository — database operations for host ratings."""

from supabase import Client


def get_rating(db: Client, rater_id: str, host_id: str) -> dict | None:
    result = (
        db.table("ratings")
        .select("id,rater_id,host_id,score,created_at")
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
