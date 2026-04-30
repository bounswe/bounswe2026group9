"""Integration tests for Users/Profiles/Ratings API."""

import uuid

from tests_support import build_test_identity


def test_user_profiles_and_ratings(client, db):
    # Register host
    host_user, host_email = build_test_identity("proftest")
    client.post("/auth/register", json={"username": host_user, "email": host_email, "password": "password123", "date_of_birth": "1990-01-01"})
    login = client.post("/auth/login", json={"email": host_email, "password": "password123"})
    host_token = login.json()["access_token"]

    # Get me
    res = client.get("/auth/me", headers={"Authorization": f"Bearer {host_token}"})
    host_id = res.json()["id"]

    # Register rater
    r_user, r_email = build_test_identity("ratetest")
    client.post("/auth/register", json={"username": r_user, "email": r_email, "password": "password123", "date_of_birth": "1990-01-01"})
    r_token = client.post("/auth/login", json={"email": r_email, "password": "password123"}).json()["access_token"]
    rater_id = client.get("/auth/me", headers={"Authorization": f"Bearer {r_token}"}).json()["id"]

    # Host profile should hide email and phone by default
    res = client.get(f"/users/{host_id}/profile")
    assert res.status_code == 200
    assert res.json()["email"] is None
    assert res.json()["phone_number"] is None

    # Rating a non-host user fails
    res = client.post(f"/users/{rater_id}/ratings", headers={"Authorization": f"Bearer {host_token}"}, json={"score": 4.0})
    assert res.status_code == 400
    assert "never hosted" in res.json()["detail"].lower()

    # Make host an actual host by inserting an ended event
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

    # Host rating fails (self)
    res = client.post(f"/users/{host_id}/ratings", headers={"Authorization": f"Bearer {host_token}"}, json={"score": 5.0})
    assert res.status_code == 400

    # Rating fails when rater has not attended any ended event by this host
    res = client.post(f"/users/{host_id}/ratings", headers={"Authorization": f"Bearer {r_token}"}, json={"score": 4.0})
    assert res.status_code == 403
    assert "attend" in res.json()["detail"].lower()

    # Also: can_rate should be False before attending
    res = client.get(f"/users/{host_id}/profile", headers={"Authorization": f"Bearer {r_token}"})
    assert res.status_code == 200
    assert res.json()["can_rate"] is False

    # Rater attends the ended event
    db.table("attendances").insert({
        "user_id": rater_id,
        "event_id": event_id,
        "status": "going",
    }).execute()

    # Now can_rate should be True
    res = client.get(f"/users/{host_id}/profile", headers={"Authorization": f"Bearer {r_token}"})
    assert res.status_code == 200
    assert res.json()["can_rate"] is True

    # User rates 4.0 — endpoint returns 201 (issue #230 spec)
    res = client.post(f"/users/{host_id}/ratings", headers={"Authorization": f"Bearer {r_token}"}, json={"score": 4.0})
    assert res.status_code == 201
    assert float(res.json()["score"]) == 4.0

    # User updates rating to 5.0 — upsert path also returns 201
    res = client.post(f"/users/{host_id}/ratings", headers={"Authorization": f"Bearer {r_token}"}, json={"score": 5.0})
    assert res.status_code == 201
    assert float(res.json()["score"]) == 5.0

    # Check Host profile average
    res = client.get(f"/users/{host_id}/profile")
    assert res.status_code == 200
    assert res.json()["average_rating"] == 5.0

    # User updates self profile
    res = client.put("/users/me", headers={"Authorization": f"Bearer {r_token}"}, json={
        "phone_number": "+1234567890",
        "email_visibility": "public",
        "phone_visibility": "public",
        "default_location_name": "Home",
        "default_location_lat": 1.0,
        "default_location_lng": 1.0
    })
    assert res.status_code == 200
    assert res.json()["phone_number"] == "+1234567890"
    assert res.json()["email_visibility"] is True
    assert res.json()["phone_visibility"] is True

    # Guest checks rater profile updates (email and phone should be visible now)
    res = client.get(f"/users/{rater_id}/profile")
    assert res.status_code == 200
    assert res.json()["email"] == r_email
    assert res.json()["phone_number"] == "+1234567890"


# --- Rating reviews (issue #235) ------------------------------------------

def _register_and_login(client, prefix: str) -> tuple[str, str, str]:
    """Register a fresh user, log in, return (id, email, access_token)."""
    username, email = build_test_identity(prefix)
    client.post("/auth/register", json={
        "username": username, "email": email,
        "password": "password123", "date_of_birth": "1990-01-01",
    })
    token = client.post("/auth/login", json={
        "email": email, "password": "password123",
    }).json()["access_token"]
    user_id = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()["id"]
    return user_id, email, token


def _make_eligible_rater(client, db, *, host_prefix: str, rater_prefix: str):
    """Set up a host with an ended event and a rater who attended it.

    Returns (host_id, rater_id, host_token, rater_token, event_id) — the
    rater is now eligible to rate the host (passed has_attended_ended_event_by_host).
    """
    host_id, _, host_token = _register_and_login(client, host_prefix)
    rater_id, _, rater_token = _register_and_login(client, rater_prefix)

    event_res = db.table("events").insert({
        "host_id": host_id,
        "title": f"Ended event {uuid.uuid4().hex[:6]}",
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

    return host_id, rater_id, host_token, rater_token, event_id


class TestRatingReviews:
    """End-to-end coverage for the new review_text field and /reviews endpoint."""

    def test_rate_with_text_returns_201_and_persists_text(self, client, db):
        host_id, _rater_id, _host_token, rater_token, _event_id = _make_eligible_rater(
            client, db, host_prefix="revtxt-host", rater_prefix="revtxt-rater",
        )

        res = client.post(
            f"/users/{host_id}/ratings",
            headers={"Authorization": f"Bearer {rater_token}"},
            json={"score": 4.5, "review_text": "Walk was excellent — leader was clear."},
        )
        assert res.status_code == 201, res.json()
        body = res.json()
        assert body["review_text"] == "Walk was excellent — leader was clear."
        assert float(body["score"]) == 4.5

    def test_rate_without_text_returns_201_back_compat(self, client, db):
        # Star-only rating (existing client behaviour) must keep working.
        host_id, _rater_id, _host_token, rater_token, _event_id = _make_eligible_rater(
            client, db, host_prefix="revstar-host", rater_prefix="revstar-rater",
        )

        res = client.post(
            f"/users/{host_id}/ratings",
            headers={"Authorization": f"Bearer {rater_token}"},
            json={"score": 5.0},
        )
        assert res.status_code == 201
        assert res.json()["review_text"] is None

    def test_rate_text_too_long_returns_422(self, client, db):
        host_id, _, _, rater_token, _ = _make_eligible_rater(
            client, db, host_prefix="revlong-host", rater_prefix="revlong-rater",
        )
        res = client.post(
            f"/users/{host_id}/ratings",
            headers={"Authorization": f"Bearer {rater_token}"},
            json={"score": 4.0, "review_text": "x" * 1001},
        )
        assert res.status_code == 422

    def test_rate_text_whitespace_only_normalised_to_null(self, client, db):
        host_id, _, _, rater_token, _ = _make_eligible_rater(
            client, db, host_prefix="revws-host", rater_prefix="revws-rater",
        )
        res = client.post(
            f"/users/{host_id}/ratings",
            headers={"Authorization": f"Bearer {rater_token}"},
            json={"score": 3.5, "review_text": "   \n\t  "},
        )
        assert res.status_code == 201
        assert res.json()["review_text"] is None

    def test_rate_upsert_replaces_review_text(self, client, db):
        # Locked decision #5: upsert overwrites previous text without history.
        host_id, _, _, rater_token, _ = _make_eligible_rater(
            client, db, host_prefix="revups-host", rater_prefix="revups-rater",
        )

        first = client.post(
            f"/users/{host_id}/ratings",
            headers={"Authorization": f"Bearer {rater_token}"},
            json={"score": 4.0, "review_text": "First impression"},
        )
        assert first.status_code == 201
        assert first.json()["review_text"] == "First impression"

        second = client.post(
            f"/users/{host_id}/ratings",
            headers={"Authorization": f"Bearer {rater_token}"},
            json={"score": 5.0, "review_text": "Better on the second visit"},
        )
        assert second.status_code == 201
        assert second.json()["review_text"] == "Better on the second visit"
        # Same row, not a duplicate
        assert second.json()["id"] == first.json()["id"]

    def test_eligibility_unchanged_for_non_attendee(self, client, db):
        # Even with review_text in the body, a rater who never attended an
        # ended event by the host still gets 403 (rule unchanged).
        host_id, _, _host_token = _register_and_login(client, "revelig-host")
        # Make host actually a host (one ended event, but rater didn't attend)
        db.table("events").insert({
            "host_id": host_id, "title": f"H {uuid.uuid4().hex[:6]}",
            "description": "d", "start_datetime": "2025-01-01T10:00:00Z",
            "end_datetime": "2025-01-01T12:00:00Z",
            "visibility": "public", "status": "ended",
        }).execute()
        _rater_id, _, rater_token = _register_and_login(client, "revelig-rater")

        res = client.post(
            f"/users/{host_id}/ratings",
            headers={"Authorization": f"Bearer {rater_token}"},
            json={"score": 4.0, "review_text": "I think it was fine"},
        )
        assert res.status_code == 403

    def test_list_reviews_unknown_host_returns_404(self, client):
        # Locked decision #3: unknown host → 404 (matches GET /users/{id}/profile).
        res = client.get(f"/users/{uuid.uuid4()}/reviews")
        assert res.status_code == 404

    def test_list_reviews_existing_host_no_ratings_returns_empty(self, client, db):
        host_id, _, _ = _register_and_login(client, "revempty-host")
        # Make host eligible to be queried (no ratings yet)
        db.table("events").insert({
            "host_id": host_id, "title": f"H {uuid.uuid4().hex[:6]}",
            "description": "d", "start_datetime": "2025-01-01T10:00:00Z",
            "end_datetime": "2025-01-01T12:00:00Z",
            "visibility": "public", "status": "ended",
        }).execute()

        res = client.get(f"/users/{host_id}/reviews")
        assert res.status_code == 200
        body = res.json()
        assert body["items"] == []
        assert body["total"] == 0
        assert body["total_pages"] == 0

    def test_list_reviews_newest_first_with_text(self, client, db):
        host_id, _r1, _host_token, r1_token, event_id = _make_eligible_rater(
            client, db, host_prefix="revlist-host", rater_prefix="revlist-r1",
        )
        # Second rater attending the same event
        r2_id, _, r2_token = _register_and_login(client, "revlist-r2")
        db.table("attendances").insert({
            "user_id": r2_id, "event_id": event_id, "status": "going",
        }).execute()

        # r1 rates first
        client.post(
            f"/users/{host_id}/ratings",
            headers={"Authorization": f"Bearer {r1_token}"},
            json={"score": 4.0, "review_text": "First review"},
        )
        # r2 rates second (newer created_at)
        client.post(
            f"/users/{host_id}/ratings",
            headers={"Authorization": f"Bearer {r2_token}"},
            json={"score": 5.0, "review_text": "Second review"},
        )

        res = client.get(f"/users/{host_id}/reviews")
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 2
        # Newest-first
        assert items[0]["review_text"] == "Second review"
        assert items[1]["review_text"] == "First review"

    def test_list_reviews_includes_star_only_with_null_text(self, client, db):
        # Locked decision #1: star-only ratings appear in the list with
        # review_text=null so the count mirrors the aggregate.
        host_id, _r1, _host_token, r1_token, event_id = _make_eligible_rater(
            client, db, host_prefix="revstar-list-host", rater_prefix="revstar-list-r1",
        )
        r2_id, _, r2_token = _register_and_login(client, "revstar-list-r2")
        db.table("attendances").insert({
            "user_id": r2_id, "event_id": event_id, "status": "going",
        }).execute()

        # r1: star + text
        client.post(
            f"/users/{host_id}/ratings",
            headers={"Authorization": f"Bearer {r1_token}"},
            json={"score": 4.0, "review_text": "with text"},
        )
        # r2: star only
        client.post(
            f"/users/{host_id}/ratings",
            headers={"Authorization": f"Bearer {r2_token}"},
            json={"score": 5.0},
        )

        res = client.get(f"/users/{host_id}/reviews")
        assert res.status_code == 200
        body = res.json()
        assert body["total"] == 2
        assert len(body["items"]) == 2
        # One has text, one is null
        texts = sorted([i["review_text"] for i in body["items"]], key=lambda v: (v is None, v))
        assert texts == ["with text", None]

    def test_list_reviews_includes_rater_username(self, client, db):
        host_id, rater_id, _host_token, rater_token, _event_id = _make_eligible_rater(
            client, db, host_prefix="revuname-host", rater_prefix="revuname-rater",
        )
        client.post(
            f"/users/{host_id}/ratings",
            headers={"Authorization": f"Bearer {rater_token}"},
            json={"score": 5.0, "review_text": "great"},
        )

        # Grab the rater's actual username from /auth/me
        rater_me = client.get(
            "/auth/me", headers={"Authorization": f"Bearer {rater_token}"},
        ).json()
        expected_username = rater_me["username"]

        res = client.get(f"/users/{host_id}/reviews")
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 1
        assert items[0]["rater_id"] == rater_id
        assert items[0]["rater_username"] == expected_username

    def test_list_reviews_pagination(self, client, db):
        # 3 raters × same host → page_size=2 yields total_pages=2 with 2+1 items.
        host_id, _r1, _host_token, r1_token, event_id = _make_eligible_rater(
            client, db, host_prefix="revpag-host", rater_prefix="revpag-r1",
        )
        r2_id, _, r2_token = _register_and_login(client, "revpag-r2")
        r3_id, _, r3_token = _register_and_login(client, "revpag-r3")
        for uid in (r2_id, r3_id):
            db.table("attendances").insert({
                "user_id": uid, "event_id": event_id, "status": "going",
            }).execute()

        for tok, score, text in (
            (r1_token, 5.0, "first"),
            (r2_token, 4.0, "second"),
            (r3_token, 3.0, "third"),
        ):
            client.post(
                f"/users/{host_id}/ratings",
                headers={"Authorization": f"Bearer {tok}"},
                json={"score": score, "review_text": text},
            )

        # Page 1
        p1 = client.get(f"/users/{host_id}/reviews?page=1&page_size=2")
        assert p1.status_code == 200
        b1 = p1.json()
        assert b1["total"] == 3
        assert b1["total_pages"] == 2
        assert len(b1["items"]) == 2

        # Page 2
        p2 = client.get(f"/users/{host_id}/reviews?page=2&page_size=2")
        assert p2.status_code == 200
        b2 = p2.json()
        assert len(b2["items"]) == 1
        # Combined items match the total
        assert b1["total"] == b2["total"]
