"""Proof-of-concept: drive supabase-py against the hermetic stack.

Tighter end-to-end smoke than ``test_migrate.py``: spins up the full
Postgres + PostgREST stack, builds a real ``supabase.Client`` against
it, and round-trips a row through the public users table. If this
passes against Docker, the rest of the integration suite can be ported
to the hermetic lane in a follow-up. The legacy lane (which talks to a
remote Supabase) stays untouched for now.
"""
from __future__ import annotations

from tests.db.postgrest import StackEndpoints


def test_insert_and_select_user_through_supabase_client(
    hermetic_supabase_client,
    supabase_stack: StackEndpoints,  # noqa: ARG001 — only here to enforce session deps
    pg_isolation: None,  # noqa: ARG001 — TRUNCATE after this test runs
) -> None:
    db = hermetic_supabase_client

    inserted = (
        db.table("users")
        .insert({
            "username": "hermetic_alice",
            "email": "alice@hermetic.test",
            "hashed_password": "fakehash",
            "role": "registered",
            "auth_provider": "local",
            "email_verified": True,
            "is_active": True,
        })
        .execute()
    )
    assert inserted.data, inserted
    user_id = inserted.data[0]["id"]

    fetched = (
        db.table("users")
        .select("username,email,role")
        .eq("id", user_id)
        .single()
        .execute()
    )
    assert fetched.data == {
        "username": "hermetic_alice",
        "email": "alice@hermetic.test",
        "role": "registered",
    }


def test_unaccent_search_returns_empty_on_clean_db(
    hermetic_supabase_client,
    supabase_stack: StackEndpoints,  # noqa: ARG001
    pg_isolation: None,  # noqa: ARG001
) -> None:
    """Migration 016's RPC must be callable through the supabase RPC surface."""
    db = hermetic_supabase_client
    result = db.rpc("search_events_text", {"search_term": "anything"}).execute()
    assert result.data == []
