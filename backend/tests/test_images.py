"""Contract tests for /events/{event_id}/images endpoints.

Phase 2 retains one happy-path integration test per HTTP endpoint.
Branch coverage (auth, format/size validation, max-images cap, resize)
lives in tests/test_image_unit.py.
"""

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
MOCK_STORAGE_URL = "https://example.com/storage/v1/object/public/event-images/test.jpg"


def _auth_header(user_id: str) -> dict:
    token = create_access_token(user_id, "test@test.com")
    return {"Authorization": f"Bearer {token}"}


def _create_test_user() -> dict:
    username, email = build_test_identity("imgtest")
    result = db.table("users").insert({
        "username": username, "email": email,
        "hashed_password": "fakehash", "role": "registered",
        "auth_provider": "local", "email_verified": True, "is_active": True,
    }).execute()
    return result.data[0]


def _create_test_event(user_id: str) -> str:
    cat_id = db.table("categories").select("id").eq("is_predefined", True).limit(1).execute().data[0]["id"]
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
    return client.post("/events", json=body, headers=_auth_header(user_id)).json()["id"]


def _make_test_image() -> io.BytesIO:
    img = Image.new("RGB", (100, 100), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf


# --- Contract tests (one happy path per endpoint) ---


class TestUploadImage:
    """POST /events/{event_id}/images"""

    @patch("app.repositories.image.upload_to_storage", return_value=MOCK_STORAGE_URL)
    def test_upload_jpeg(self, mock_upload):  # noqa: ARG002
        user = _create_test_user()
        event_id = _create_test_event(user["id"])

        resp = client.post(
            f"/events/{event_id}/images",
            files={"file": ("test.jpg", _make_test_image(), "image/jpeg")},
            headers=_auth_header(user["id"]),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["image_url"] == MOCK_STORAGE_URL
        assert "id" in data


class TestDeleteImage:
    """DELETE /events/{event_id}/images/{image_id}"""

    @patch("app.repositories.image.upload_to_storage", return_value=MOCK_STORAGE_URL)
    @patch("app.repositories.image.delete_from_storage")
    def test_delete_image(self, mock_del_storage, mock_upload):  # noqa: ARG002
        user = _create_test_user()
        event_id = _create_test_event(user["id"])

        upload_resp = client.post(
            f"/events/{event_id}/images",
            files={"file": ("test.jpg", _make_test_image(), "image/jpeg")},
            headers=_auth_header(user["id"]),
        )
        image_id = upload_resp.json()["id"]

        resp = client.delete(
            f"/events/{event_id}/images/{image_id}",
            headers=_auth_header(user["id"]),
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Image deleted successfully"
