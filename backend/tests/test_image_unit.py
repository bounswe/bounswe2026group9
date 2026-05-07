"""Unit tests for `services.image` — exercises the keyword-DI seam.

Image processing (PIL resize) stays live because it's pure CPU work; the
two storage operations and all DB queries are intercepted via the new
`images` and `events` kwargs.
"""

import io
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException, UploadFile
from PIL import Image as PILImage
from starlette.datastructures import Headers

from app.services import image as image_service

EVENT_ID = "00000000-0000-0000-0000-000000000080"
HOST_ID = "00000000-0000-0000-0000-000000000081"
USER_ID = "00000000-0000-0000-0000-000000000082"
IMAGE_ID = "00000000-0000-0000-0000-000000000083"


@pytest.fixture
def db():
    return MagicMock(name="supabase_client")


def _event(*, status: str = "published", host_id: str = HOST_ID) -> dict:
    return {"id": EVENT_ID, "host_id": host_id, "status": status}


def _png_upload(*, content_type: str = "image/png", w: int = 50, h: int = 50) -> UploadFile:
    """Build a real PNG UploadFile so the in-process image validation runs."""
    buf = io.BytesIO()
    PILImage.new("RGB", (w, h), color="red").save(buf, format="PNG")
    buf.seek(0)
    return UploadFile(
        filename="test.png",
        file=buf,
        headers=Headers({"content-type": content_type}),
    )


def _bogus_upload(content_type: str = "image/png", payload: bytes = b"not really an image") -> UploadFile:
    return UploadFile(
        filename="bogus.png",
        file=io.BytesIO(payload),
        headers=Headers({"content-type": content_type}),
    )


@pytest.fixture
def repos():
    images = MagicMock()
    events = MagicMock()
    events.get_event_by_id.return_value = _event()
    images.count_event_images.return_value = 0
    images.upload_to_storage.return_value = (
        "https://example.com/storage/v1/object/public/event-images/path.png"
    )
    images.insert_event_image.return_value = {
        "id": IMAGE_ID,
        "event_id": EVENT_ID,
        "image_url": "https://example.com/storage/v1/object/public/event-images/path.png",
        "upload_date": "2026-01-01T00:00:00+00:00",
    }
    images.BUCKET_NAME = "event-images"
    return images, events


# ── upload_event_image ──────────────────────────────────────────────────────


class TestUploadEventImage:
    def test_404_when_event_missing(self, db, repos):
        images, events = repos
        events.get_event_by_id.return_value = None
        with pytest.raises(HTTPException) as exc:
            image_service.upload_event_image(
                db, EVENT_ID, HOST_ID, _png_upload(),
                images=images, events=events,
            )
        assert exc.value.status_code == 404

    def test_403_when_not_host(self, db, repos):
        images, events = repos
        with pytest.raises(HTTPException) as exc:
            image_service.upload_event_image(
                db, EVENT_ID, USER_ID, _png_upload(),
                images=images, events=events,
            )
        assert exc.value.status_code == 403

    def test_400_when_event_cancelled_or_ended(self, db, repos):
        images, events = repos
        events.get_event_by_id.return_value = _event(status="cancelled")
        with pytest.raises(HTTPException) as exc:
            image_service.upload_event_image(
                db, EVENT_ID, HOST_ID, _png_upload(),
                images=images, events=events,
            )
        assert exc.value.status_code == 400

    def test_400_when_content_type_disallowed(self, db, repos):
        images, events = repos
        with pytest.raises(HTTPException) as exc:
            image_service.upload_event_image(
                db, EVENT_ID, HOST_ID, _png_upload(content_type="image/gif"),
                images=images, events=events,
            )
        assert exc.value.status_code == 400

    def test_400_when_max_images_per_event_reached(self, db, repos):
        images, events = repos
        images.count_event_images.return_value = 10  # MAX_IMAGES_PER_EVENT
        with pytest.raises(HTTPException) as exc:
            image_service.upload_event_image(
                db, EVENT_ID, HOST_ID, _png_upload(),
                images=images, events=events,
            )
        assert exc.value.status_code == 400

    def test_400_when_payload_is_not_a_real_image(self, db, repos):
        images, events = repos
        with pytest.raises(HTTPException) as exc:
            image_service.upload_event_image(
                db, EVENT_ID, HOST_ID, _bogus_upload(),
                images=images, events=events,
            )
        assert exc.value.status_code == 400

    def test_500_when_storage_upload_raises(self, db, repos):
        images, events = repos
        images.upload_to_storage.side_effect = Exception("supabase 5xx")
        with pytest.raises(HTTPException) as exc:
            image_service.upload_event_image(
                db, EVENT_ID, HOST_ID, _png_upload(),
                images=images, events=events,
            )
        assert exc.value.status_code == 500

    def test_happy_path_uploads_and_records(self, db, repos):
        images, events = repos

        result = image_service.upload_event_image(
            db, EVENT_ID, HOST_ID, _png_upload(),
            images=images, events=events,
        )

        # Storage path is event-scoped + has a uuid hex segment.
        sent_path = images.upload_to_storage.call_args.args[1]
        assert sent_path.startswith(f"{EVENT_ID}/")
        # DB record returned to caller.
        assert str(result.id) == IMAGE_ID


# ── delete_event_image ──────────────────────────────────────────────────────


class TestDeleteEventImage:
    def test_404_when_event_missing(self, db, repos):
        images, events = repos
        events.get_event_by_id.return_value = None
        with pytest.raises(HTTPException) as exc:
            image_service.delete_event_image(
                db, EVENT_ID, IMAGE_ID, HOST_ID,
                images=images, events=events,
            )
        assert exc.value.status_code == 404

    def test_403_when_not_host(self, db, repos):
        images, events = repos
        with pytest.raises(HTTPException) as exc:
            image_service.delete_event_image(
                db, EVENT_ID, IMAGE_ID, USER_ID,
                images=images, events=events,
            )
        assert exc.value.status_code == 403

    def test_404_when_image_belongs_to_other_event(self, db, repos):
        images, events = repos
        images.get_event_image.return_value = {
            "id": IMAGE_ID,
            "event_id": "00000000-0000-0000-0000-000000000099",
            "image_url": "https://x/event-images/p.png",
        }
        with pytest.raises(HTTPException) as exc:
            image_service.delete_event_image(
                db, EVENT_ID, IMAGE_ID, HOST_ID,
                images=images, events=events,
            )
        assert exc.value.status_code == 404

    def test_deletes_db_row_even_when_storage_delete_raises(self, db, repos):
        images, events = repos
        images.get_event_image.return_value = {
            "id": IMAGE_ID,
            "event_id": EVENT_ID,
            "image_url": "https://example.com/storage/v1/object/public/event-images/path.png",
        }
        images.delete_from_storage.side_effect = Exception("network blip")

        # Service must not raise — storage delete is best-effort.
        image_service.delete_event_image(
            db, EVENT_ID, IMAGE_ID, HOST_ID,
            images=images, events=events,
        )
        images.delete_event_image.assert_called_once_with(db, IMAGE_ID)

    def test_extracts_storage_path_from_url(self, db, repos):
        images, events = repos
        images.get_event_image.return_value = {
            "id": IMAGE_ID,
            "event_id": EVENT_ID,
            "image_url": "https://x/storage/v1/object/public/event-images/abc/file.png",
        }
        image_service.delete_event_image(
            db, EVENT_ID, IMAGE_ID, HOST_ID,
            images=images, events=events,
        )
        images.delete_from_storage.assert_called_once_with(db, "abc/file.png")
