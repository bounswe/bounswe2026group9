"""Integration tests for Users/Profiles/Ratings API."""

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

    # User rates 4.0
    res = client.post(f"/users/{host_id}/ratings", headers={"Authorization": f"Bearer {r_token}"}, json={"score": 4.0})
    assert res.status_code == 200
    assert float(res.json()["score"]) == 4.0

    # User updates rating to 5.0
    res = client.post(f"/users/{host_id}/ratings", headers={"Authorization": f"Bearer {r_token}"}, json={"score": 5.0})
    assert res.status_code == 200
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
