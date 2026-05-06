"""Image service — business logic for event image upload/delete."""

import io
import uuid

from fastapi import HTTPException, UploadFile, status
from PIL import Image
from supabase import Client

from app.models.event import EventImageResponse
from app.repositories import event as _event_repo
from app.repositories import image as _image_repo
from app.repositories.protocols import EventRepoProtocol, ImageRepoProtocol

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
MAX_IMAGES_PER_EVENT = 10
MAX_DIMENSION = 2048


def _resize_image(file_bytes: bytes, content_type: str) -> tuple[bytes, str]:
    """Resize image if larger than MAX_DIMENSION. Returns (bytes, content_type)."""
    img = Image.open(io.BytesIO(file_bytes))

    if img.width > MAX_DIMENSION or img.height > MAX_DIMENSION:
        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)

    output = io.BytesIO()
    fmt_map = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}
    fmt = fmt_map.get(content_type, "JPEG")

    if fmt == "JPEG" and img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    img.save(output, format=fmt, quality=85)
    return output.getvalue(), content_type


def upload_event_image(
    db: Client,
    event_id: str,
    user_id: str,
    file: UploadFile,
    *,
    images: ImageRepoProtocol = _image_repo,
    events: EventRepoProtocol = _event_repo,
) -> EventImageResponse:
    # Check event exists and user is host
    event = events.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if event["host_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the host can upload images")
    if event["status"] in ("cancelled", "ended"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot upload images to a cancelled or ended event",
        )

    # Validate content type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Allowed: JPEG, PNG, WebP",
        )

    # Check image count
    count = images.count_event_images(db, event_id)
    if count >= MAX_IMAGES_PER_EVENT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {MAX_IMAGES_PER_EVENT} images per event",
        )

    # Read in chunks to prevent memory exhaustion (DoS protection)
    chunks = []
    total_size = 0
    while True:
        chunk = file.file.read(1024 * 1024)  # 1MB chunks
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size exceeds 20MB limit",
            )
        chunks.append(chunk)
    file_bytes = b"".join(chunks)

    # Verify actual image format server-side (don't trust client content_type)
    try:
        img_check = Image.open(io.BytesIO(file_bytes))
        actual_format = img_check.format  # e.g. "JPEG", "PNG", "WEBP"
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image file") from e

    allowed_formats = {"JPEG", "PNG", "WEBP"}
    if actual_format not in allowed_formats:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image format: {actual_format}. Allowed: JPEG, PNG, WebP",
        )

    # Map actual format to content_type for storage
    format_to_ct = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
    verified_content_type = format_to_ct[actual_format]

    # Resize
    resized_bytes, content_type = _resize_image(file_bytes, verified_content_type)

    # Upload to storage
    ext_map = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
    ext = ext_map.get(content_type, "jpg")
    storage_path = f"{event_id}/{uuid.uuid4().hex}.{ext}"

    try:
        image_url = images.upload_to_storage(db, storage_path, resized_bytes, content_type)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Storage upload failed") from e

    # Save to DB
    row = images.insert_event_image(db, event_id, image_url)
    if not row:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save image record")

    return EventImageResponse(**row)


def delete_event_image(
    db: Client,
    event_id: str,
    image_id: str,
    user_id: str,
    *,
    images: ImageRepoProtocol = _image_repo,
    events: EventRepoProtocol = _event_repo,
) -> None:
    # Check event exists and user is host
    event = events.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if event["host_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the host can delete images")

    # Check image exists and belongs to event
    image = images.get_event_image(db, image_id)
    if not image or image["event_id"] != event_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    # Extract storage path from URL and delete from storage
    image_url = image["image_url"]
    try:
        # URL format: .../storage/v1/object/public/event-images/{path}
        path = image_url.split(f"/{images.BUCKET_NAME}/")[-1]
        images.delete_from_storage(db, path)
    except Exception:
        pass  # Storage delete is best-effort, DB record is authoritative

    images.delete_event_image(db, image_id)
