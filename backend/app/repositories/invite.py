"""Invite & access request repository — all DB operations."""

from supabase import Client


# --- Invites ---

def insert_invite(db: Client, data: dict) -> dict:
    result = db.table("event_invites").insert(data).execute()
    return result.data[0] if result.data else None


def get_invite_by_token(db: Client, token: str) -> dict | None:
    result = db.table("event_invites").select("*").eq("token", token).execute()
    return result.data[0] if result.data else None


def get_invites_by_event(db: Client, event_id: str) -> list[dict]:
    result = (
        db.table("event_invites")
        .select("*")
        .eq("event_id", event_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


def increment_invite_use_count(db: Client, invite_id: str) -> None:
    invite = db.table("event_invites").select("use_count").eq("id", invite_id).execute()
    if invite.data:
        new_count = invite.data[0]["use_count"] + 1
        db.table("event_invites").update({"use_count": new_count}).eq("id", invite_id).execute()


def delete_invite(db: Client, invite_id: str) -> None:
    db.table("event_invites").delete().eq("id", invite_id).execute()


# --- Access Grants ---

def insert_access_grant(db: Client, data: dict) -> dict:
    result = db.table("event_access_grants").insert(data).execute()
    return result.data[0] if result.data else None


def get_access_grant(db: Client, event_id: str, user_id: str) -> dict | None:
    result = (
        db.table("event_access_grants")
        .select("*")
        .eq("event_id", event_id)
        .eq("user_id", user_id)
        .execute()
    )
    return result.data[0] if result.data else None


def get_granted_user_ids(db: Client, event_id: str) -> list[str]:
    result = (
        db.table("event_access_grants")
        .select("user_id")
        .eq("event_id", event_id)
        .execute()
    )
    return [row["user_id"] for row in (result.data or [])]


# --- Access Requests ---

def insert_access_request(db: Client, data: dict) -> dict:
    result = db.table("event_access_requests").insert(data).execute()
    return result.data[0] if result.data else None


def get_access_request_by_id(db: Client, request_id: str) -> dict | None:
    result = db.table("event_access_requests").select("*").eq("id", request_id).execute()
    return result.data[0] if result.data else None


def get_access_request(db: Client, event_id: str, user_id: str) -> dict | None:
    result = (
        db.table("event_access_requests")
        .select("*")
        .eq("event_id", event_id)
        .eq("user_id", user_id)
        .execute()
    )
    return result.data[0] if result.data else None


def get_pending_requests_by_event(db: Client, event_id: str) -> list[dict]:
    result = (
        db.table("event_access_requests")
        .select("*")
        .eq("event_id", event_id)
        .eq("status", "pending")
        .order("created_at")
        .execute()
    )
    return result.data or []


def update_access_request(db: Client, request_id: str, data: dict) -> dict | None:
    result = db.table("event_access_requests").update(data).eq("id", request_id).execute()
    return result.data[0] if result.data else None
