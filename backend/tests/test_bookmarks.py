"""Integration tests for Bookmark API."""

from tests_support import build_test_identity
from unittest.mock import patch


@patch("app.repositories.image.upload_to_storage", return_value="https://example.com/test.jpg")
def test_create_bookmark(mock_upload, client, db):
    # Register host and create event
    host_user, host_email = build_test_identity("bmtest")
    client.post("/auth/register", json={
        "username": host_user,
        "email": host_email,
        "password": "password123",
        "date_of_birth": "1990-01-01"
    })
    
    login = client.post("/auth/login", json={"email": host_email, "password": "password123"})
    host_token = login.json()["access_token"]
    
    cat_res = client.get("/categories")
    cat_id = cat_res.json()[0]["id"]
    
    event_res = client.post("/events", headers={"Authorization": f"Bearer {host_token}"}, json={
        "title": "Bookmark Test Event",
        "description": "Test",
        "start_datetime": "2030-01-01T10:00:00Z",
        "end_datetime": "2030-01-01T12:00:00Z",
        "visibility": "public",
        "status": "draft",
        "category_ids": [cat_id],
        "locations": [{"name": "Test Location", "latitude": 40.0, "longitude": 29.0}]
    })
    assert event_res.status_code == 201, f"Event creation failed: {event_res.text}"
    event_id = event_res.json()["id"]
    
    # Needs to be published/updated
    # Actually wait. Publishing requires image upload.
    # We must patch get_event_images to bypass or upload an image.
    from io import BytesIO
    from PIL import Image as PILImage
    img = PILImage.new("RGB", (100, 100), color="red")
    buf = BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    client.post(f"/events/{event_id}/images", headers={"Authorization": f"Bearer {host_token}"}, files={"file": ("test.jpg", buf, "image/jpeg")})
    
    pub_res = client.patch(f"/events/{event_id}/status", headers={"Authorization": f"Bearer {host_token}"}, json={"status": "published"})
    assert pub_res.status_code == 200, f"Failed to publish: {pub_res.text}"
    
    # Register a rater/bookmark user
    b_user, b_email = build_test_identity("bmtest")
    client.post("/auth/register", json={"username": b_user, "email": b_email, "password": "password123", "date_of_birth": "1990-01-01"})
    login2 = client.post("/auth/login", json={"email": b_email, "password": "password123"})
    b_token = login2.json()["access_token"]
    
    # Create bookmark
    res = client.post(f"/events/{event_id}/bookmark", headers={"Authorization": f"Bearer {b_token}"})
    assert res.status_code == 201
    assert res.json()["event_id"] == event_id
    
    # Duplicate bookmark
    res = client.post(f"/events/{event_id}/bookmark", headers={"Authorization": f"Bearer {b_token}"})
    assert res.status_code == 409
    
    # Get user bookmarks
    res = client.get("/users/me/bookmarks", headers={"Authorization": f"Bearer {b_token}"})
    assert res.status_code == 200
    assert len(res.json()["items"]) == 1
    assert res.json()["items"][0]["title"] == "Bookmark Test Event"
    
    # Event detail response is_bookmarked
    res = client.get(f"/events/{event_id}", headers={"Authorization": f"Bearer {b_token}"})
    assert res.status_code == 200
    assert res.json()["is_bookmarked"] is True
    
    # Delete bookmark
    res = client.delete(f"/events/{event_id}/bookmark", headers={"Authorization": f"Bearer {b_token}"})
    assert res.status_code == 200
    
    # Event detail response is_bookmarked again
    res = client.get(f"/events/{event_id}", headers={"Authorization": f"Bearer {b_token}"})
    assert res.status_code == 200
    assert res.json()["is_bookmarked"] is False
    
    # Delete non-existent
    res = client.delete(f"/events/{event_id}/bookmark", headers={"Authorization": f"Bearer {b_token}"})
    assert res.status_code == 404
