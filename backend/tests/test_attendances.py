"""Integration tests for Attendance API."""

from unittest.mock import patch

from tests_support import build_test_identity


@patch("app.repositories.image.upload_to_storage", return_value="https://example.com/test.jpg")
def test_attendance_and_capacity(mock_upload, client, db):
    # Register host
    host_user, host_email = build_test_identity("attndtest")
    client.post("/auth/register", json={"username": host_user, "email": host_email, "password": "password123", "date_of_birth": "1990-01-01"})
    login = client.post("/auth/login", json={"email": host_email, "password": "password123"})
    host_token = login.json()["access_token"]

    cat_res = client.get("/categories")
    cat_id = cat_res.json()[0]["id"]

    # Create event with limit 1
    event_res = client.post("/events", headers={"Authorization": f"Bearer {host_token}"}, json={
        "title": "Attendance Test Event",
        "description": "Test",
        "start_datetime": "2030-01-01T10:00:00Z",
        "end_datetime": "2030-01-01T12:00:00Z",
        "visibility": "public",
        "status": "draft",
        "attendee_limit": 1,
        "is_age_restricted": True,
        "category_ids": [cat_id],
        "locations": [{"name": "Test Location", "latitude": 40.0, "longitude": 29.0}]
    })
    assert event_res.status_code == 201, f"Event creation failed: {event_res.text}"
    event_id = event_res.json()["id"]

    from io import BytesIO

    from PIL import Image as PILImage
    img = PILImage.new("RGB", (100, 100), color="red")
    buf = BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    client.post(f"/events/{event_id}/images", headers={"Authorization": f"Bearer {host_token}"}, files={"file": ("test.jpg", buf, "image/jpeg")})

    pub_res = client.patch(f"/events/{event_id}/status", headers={"Authorization": f"Bearer {host_token}"}, json={"status": "published"})
    assert pub_res.status_code == 200, f"Failed to publish: {pub_res.text}"

    # Host attending their own event fails
    res = client.post(f"/events/{event_id}/attendance", headers={"Authorization": f"Bearer {host_token}"}, json={"status": "going"})
    assert res.status_code == 400

    # User 1
    u1, e1 = build_test_identity("attndtest")
    client.post("/auth/register", json={"username": u1, "email": e1, "password": "password123", "date_of_birth": "1990-01-01"})
    t1 = client.post("/auth/login", json={"email": e1, "password": "password123"}).json()["access_token"]

    # User 2
    u2, e2 = build_test_identity("attndtest")
    client.post("/auth/register", json={"username": u2, "email": e2, "password": "password123", "date_of_birth": "1990-01-01"})
    t2 = client.post("/auth/login", json={"email": e2, "password": "password123"}).json()["access_token"]

    # Underage user
    u3, e3 = build_test_identity("attndtest")
    client.post("/auth/register", json={"username": u3, "email": e3, "password": "password123", "date_of_birth": "2020-01-01"})
    t3 = client.post("/auth/login", json={"email": e3, "password": "password123"}).json()["access_token"]

    # Underage tries to attend
    res = client.post(f"/events/{event_id}/attendance", headers={"Authorization": f"Bearer {t3}"}, json={"status": "going"})
    assert res.status_code == 403

    # User 1 going
    res = client.post(f"/events/{event_id}/attendance", headers={"Authorization": f"Bearer {t1}"}, json={"status": "going"})
    assert res.status_code == 200

    # Check counts
    res = client.get(f"/events/{event_id}", headers={"Authorization": f"Bearer {t1}"})
    assert res.status_code == 200
    assert res.json()["going_count"] == 1
    assert res.json()["is_full"] is True

    # User 2 going — should be rejected (event full)
    res = client.post(f"/events/{event_id}/attendance", headers={"Authorization": f"Bearer {t2}"}, json={"status": "going"})
    assert res.status_code == 400  # full

    # User 1 removes attendance — frees up the spot
    res = client.delete(f"/events/{event_id}/attendance", headers={"Authorization": f"Bearer {t1}"})
    assert res.status_code == 200

    # User 2 can now go
    res = client.post(f"/events/{event_id}/attendance", headers={"Authorization": f"Bearer {t2}"}, json={"status": "going"})
    assert res.status_code == 200
