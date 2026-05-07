"""Contract tests for /users endpoints.

Phase 2 retains a flow-style happy path for /users/me, /users/{id}/profile,
and /users/{id}/ratings, plus a dedicated /users/{id}/reviews contract that
pins the listing order. Branch coverage (rating eligibility, review-text
normalization, pagination edges) lives in tests/test_rating_unit.py and
tests/test_reviews_unit.py.
"""

import uuid

from tests_support import build_test_identity


def test_user_profiles_and_ratings_flow(client, db):
    """Single integration flow exercising profile + /me update + ratings."""
    host_user, host_email = build_test_identity("proftest")
    client.post("/auth/register", json={
        "username": host_user, "email": host_email,
        "password": "password123", "date_of_birth": "1990-01-01",
    })
    host_token = client.post("/auth/login", json={
        "email": host_email, "password": "password123",
    }).json()["access_token"]
    host_id = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {host_token}"},
    ).json()["id"]

    rater_user, rater_email = build_test_identity("ratetest")
    client.post("/auth/register", json={
        "username": rater_user, "email": rater_email,
        "password": "password123", "date_of_birth": "1990-01-01",
    })
    r_token = client.post("/auth/login", json={
        "email": rater_email, "password": "password123",
    }).json()["access_token"]
    rater_id = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {r_token}"},
    ).json()["id"]

    # Default privacy: email/phone redacted on public profile.
    res = client.get(f"/users/{host_id}/profile")
    assert res.status_code == 200
    assert res.json()["email"] is None
    assert res.json()["phone_number"] is None

    # Make host an actual host with an ended event the rater attended.
    event_res = db.table("events").insert({
        "host_id": host_id,
        "title": "Test host event",
        "description": "desc",
        "start_datetime": "2025-01-01T10:00:00Z",
        "end_datetime": "2025-01-01T12:00:00Z",
        "visibility": "public",
        "status": "ended",
    }).execute()
    event_id = event_res.data[0]["id"]
    db.table("attendances").insert({
        "user_id": rater_id, "event_id": event_id, "status": "going",
    }).execute()

    # Now rater can rate; profile reflects that.
    profile_res = client.get(
        f"/users/{host_id}/profile",
        headers={"Authorization": f"Bearer {r_token}"},
    )
    assert profile_res.json()["can_rate"] is True

    # Rate 4 → 5 (upsert returns 201 each time per locked decision)
    res = client.post(
        f"/users/{host_id}/ratings",
        headers={"Authorization": f"Bearer {r_token}"},
        json={"score": 5.0},
    )
    assert res.status_code == 201
    assert float(res.json()["score"]) == 5.0

    res = client.get(f"/users/{host_id}/profile")
    assert res.json()["average_rating"] == 5.0

    # PUT /users/me — visibility flip
    res = client.put(
        "/users/me",
        headers={"Authorization": f"Bearer {r_token}"},
        json={
            "phone_number": "+1234567890",
            "email_visibility": "public",
            "phone_visibility": "public",
        },
    )
    assert res.status_code == 200
    assert res.json()["phone_number"] == "+1234567890"

    # Email/phone now visible to guests on rater profile.
    res = client.get(f"/users/{rater_id}/profile")
    assert res.json()["email"] == rater_email
    assert res.json()["phone_number"] == "+1234567890"


def _register_and_login(client, prefix: str) -> tuple[str, str, str]:
    username, email = build_test_identity(prefix)
    reg = client.post("/auth/register", json={
        "username": username, "email": email,
        "password": "password123", "date_of_birth": "1990-01-01",
    })
    assert reg.status_code == 201, reg.json()
    token = client.post("/auth/login", json={
        "email": email, "password": "password123",
    }).json()["access_token"]
    user_id = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token}"},
    ).json()["id"]
    return user_id, email, token


class TestListReviews:
    """GET /users/{host_id}/reviews — listing contract (ordering + serialization)."""

    def test_list_reviews_newest_first_with_text(self, client, db):
        host_id, _, _host_token = _register_and_login(client, "revlist-host")
        r1_id, _, r1_token = _register_and_login(client, "revlist-r1")
        r2_id, _, r2_token = _register_and_login(client, "revlist-r2")

        event_id = db.table("events").insert({
            "host_id": host_id,
            "title": f"Ended event {uuid.uuid4().hex[:6]}",
            "description": "desc",
            "start_datetime": "2025-01-01T10:00:00Z",
            "end_datetime": "2025-01-01T12:00:00Z",
            "visibility": "public",
            "status": "ended",
        }).execute().data[0]["id"]
        db.table("attendances").insert([
            {"user_id": r1_id, "event_id": event_id, "status": "going"},
            {"user_id": r2_id, "event_id": event_id, "status": "going"},
        ]).execute()

        client.post(
            f"/users/{host_id}/ratings",
            headers={"Authorization": f"Bearer {r1_token}"},
            json={"score": 4.0, "review_text": "First review"},
        )
        client.post(
            f"/users/{host_id}/ratings",
            headers={"Authorization": f"Bearer {r2_token}"},
            json={"score": 5.0, "review_text": "Second review"},
        )

        res = client.get(f"/users/{host_id}/reviews")
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 2
        # Newest-first contract.
        assert items[0]["review_text"] == "Second review"
        assert items[1]["review_text"] == "First review"
        # Each item carries the rater's username.
        assert items[0]["rater_id"] == r2_id
        assert items[0]["rater_username"]
