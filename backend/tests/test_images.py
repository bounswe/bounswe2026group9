"""Tests for Event Image upload/delete endpoints."""

import io
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

from app.database import get_supabase
from app.main import app
from app.services.auth import create_access_token
from tests_support import build_test_identity

client = TestClient(app)
db = get_supabase()


def _auth_header(user_id: str) -> dict:
    token = create_access_token(user_id, "test@test.com")
    return {"Authorization": f"Bearer {token}"}


def _create_test_user(suffix: str = "") -> dict:
    username, email = build_test_identity("imgtest", suffix=suffix)
    result = db.table("users").insert({
        "username": username,
        "email": email,
        "hashed_password": "fakehash",
        "role": "registered",
        "auth_provider": "local",
        "email_verified": True,
        "is_active": True,
    }).execute()
    return result.data[0]


def _create_test_event(user_id: str) -> str:
    cat_result = db.table("categories").select("id").eq("is_predefined", True).limit(1).execute()
    cat_id = cat_result.data[0]["id"]
    body = {
        "title": "Image Test Event",
        "description": "Testing images",
        "start_datetime": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        "end_datetime": (datetime.now(UTC) + timedelta(days=1, hours=2)).isoformat(),
        "visibility": "public",
        "status": "draft",
        "category_ids": [cat_id],
        "locations": [{"name": "Loc", "latitude": 41.0, "longitude": 29.0, "is_primary": True, "order_index": 0}],
    }
    resp = client.post("/events", json=body, headers=_auth_header(user_id))
    return resp.json()["id"]


def _make_test_image(width=100, height=100, fmt="JPEG") -> io.BytesIO:
    img = Image.new("RGB", (width, height), color="red")
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    buf.seek(0)
    return buf


def _cleanup_event(event_id: str):
    db.table("event_images").delete().eq("event_id", event_id).execute()
    db.table("equipment_requirements").delete().eq("event_id", event_id).execute()
    db.table("venue_metadata").delete().eq("event_id", event_id).execute()
    db.table("event_categories").delete().eq("event_id", event_id).execute()
    db.table("event_locations").delete().eq("event_id", event_id).execute()
    db.table("events").delete().eq("id", event_id).execute()


def _cleanup_user(user_id: str):
    db.table("users").delete().eq("id", user_id).execute()


MOCK_STORAGE_URL = "https://example.com/storage/v1/object/public/event-images/test.jpg"


class TestUploadImage:

    @patch("app.repositories.image.upload_to_storage", return_value=MOCK_STORAGE_URL)
    def test_upload_jpeg(self, mock_upload):
        user = _create_test_user("upjpeg")
        event_id = _create_test_event(user["id"])

        img = _make_test_image()
        resp = client.post(
            f"/events/{event_id}/images",
            files={"file": ("test.jpg", img, "image/jpeg")},
            headers=_auth_header(user["id"]),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["image_url"] == MOCK_STORAGE_URL
        assert "id" in data

        _cleanup_event(event_id)
        _cleanup_user(user["id"])

    @patch("app.repositories.image.upload_to_storage", return_value=MOCK_STORAGE_URL)
    def test_upload_png(self, mock_upload):
        user = _create_test_user("uppng")
        event_id = _create_test_event(user["id"])

        img = _make_test_image(fmt="PNG")
        resp = client.post(
            f"/events/{event_id}/images",
            files={"file": ("test.png", img, "image/png")},
            headers=_auth_header(user["id"]),
        )
        assert resp.status_code == 201

        _cleanup_event(event_id)
        _cleanup_user(user["id"])

    def test_upload_invalid_format(self):
        user = _create_test_user("upbad")
        event_id = _create_test_event(user["id"])

        resp = client.post(
            f"/events/{event_id}/images",
            files={"file": ("test.gif", b"fakegif", "image/gif")},
            headers=_auth_header(user["id"]),
        )
        assert resp.status_code == 400
        assert "file type" in resp.json()["detail"].lower()

        _cleanup_event(event_id)
        _cleanup_user(user["id"])

    def test_upload_not_host(self):
        host = _create_test_user("uphost")
        other = _create_test_user("upother")
        event_id = _create_test_event(host["id"])

        img = _make_test_image()
        resp = client.post(
            f"/events/{event_id}/images",
            files={"file": ("test.jpg", img, "image/jpeg")},
            headers=_auth_header(other["id"]),
        )
        assert resp.status_code == 403

        _cleanup_event(event_id)
        _cleanup_user(host["id"])
        _cleanup_user(other["id"])

    @patch("app.repositories.image.upload_to_storage", return_value=MOCK_STORAGE_URL)
    def test_upload_max_images(self, mock_upload):
        user = _create_test_user("upmax")
        event_id = _create_test_event(user["id"])

        # Insert 10 images directly
        for i in range(10):
            db.table("event_images").insert({
                "event_id": event_id,
                "image_url": f"https://example.com/img{i}.jpg",
            }).execute()

        img = _make_test_image()
        resp = client.post(
            f"/events/{event_id}/images",
            files={"file": ("test.jpg", img, "image/jpeg")},
            headers=_auth_header(user["id"]),
        )
        assert resp.status_code == 400
        assert "10" in resp.json()["detail"]

        _cleanup_event(event_id)
        _cleanup_user(user["id"])

    @patch("app.repositories.image.upload_to_storage", return_value=MOCK_STORAGE_URL)
    def test_upload_resizes_large_image(self, mock_upload):
        user = _create_test_user("upresize")
        event_id = _create_test_event(user["id"])

        img = _make_test_image(width=4000, height=3000)
        resp = client.post(
            f"/events/{event_id}/images",
            files={"file": ("big.jpg", img, "image/jpeg")},
            headers=_auth_header(user["id"]),
        )
        assert resp.status_code == 201

        # Verify mock was called with resized bytes
        call_args = mock_upload.call_args
        uploaded_bytes = call_args[0][2]  # third positional arg (db, path, bytes, ...)
        resized_img = Image.open(io.BytesIO(uploaded_bytes))
        assert resized_img.width <= 2048
        assert resized_img.height <= 2048

        _cleanup_event(event_id)
        _cleanup_user(user["id"])

    def test_upload_no_auth(self):
        resp = client.post(
            "/events/00000000-0000-0000-0000-000000000000/images",
            files={"file": ("test.jpg", b"fake", "image/jpeg")},
        )
        assert resp.status_code == 401


class TestDeleteImage:

    @patch("app.repositories.image.upload_to_storage", return_value=MOCK_STORAGE_URL)
    @patch("app.repositories.image.delete_from_storage")
    def test_delete_image(self, mock_del_storage, mock_upload):
        user = _create_test_user("delimgok")
        event_id = _create_test_event(user["id"])

        # Upload first
        img = _make_test_image()
        upload_resp = client.post(
            f"/events/{event_id}/images",
            files={"file": ("test.jpg", img, "image/jpeg")},
            headers=_auth_header(user["id"]),
        )
        image_id = upload_resp.json()["id"]

        # Delete
        resp = client.delete(
            f"/events/{event_id}/images/{image_id}",
            headers=_auth_header(user["id"]),
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Image deleted successfully"

        _cleanup_event(event_id)
        _cleanup_user(user["id"])

    def test_delete_not_host(self):
        host = _create_test_user("delimghost")
        other = _create_test_user("delimgother")
        event_id = _create_test_event(host["id"])

        # Insert image directly
        img_result = db.table("event_images").insert({
            "event_id": event_id,
            "image_url": "https://example.com/img.jpg",
        }).execute()
        image_id = img_result.data[0]["id"]

        resp = client.delete(
            f"/events/{event_id}/images/{image_id}",
            headers=_auth_header(other["id"]),
        )
        assert resp.status_code == 403

        _cleanup_event(event_id)
        _cleanup_user(host["id"])
        _cleanup_user(other["id"])

    def test_delete_nonexistent_image(self):
        user = _create_test_user("delimgne")
        event_id = _create_test_event(user["id"])

        resp = client.delete(
            f"/events/{event_id}/images/00000000-0000-0000-0000-000000000000",
            headers=_auth_header(user["id"]),
        )
        assert resp.status_code == 404

        _cleanup_event(event_id)
        _cleanup_user(user["id"])
