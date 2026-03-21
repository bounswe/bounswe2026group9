"""Image repository — database + storage operations for event images."""

from supabase import Client

BUCKET_NAME = "event-images"


def count_event_images(db: Client, event_id: str) -> int:
    result = (
        db.table("event_images")
        .select("id", count="exact")
        .eq("event_id", event_id)
        .execute()
    )
    return result.count or 0


def insert_event_image(db: Client, event_id: str, image_url: str) -> dict:
    result = db.table("event_images").insert({
        "event_id": event_id,
        "image_url": image_url,
    }).execute()
    return result.data[0] if result.data else None


def get_event_image(db: Client, image_id: str) -> dict | None:
    result = db.table("event_images").select("*").eq("id", image_id).execute()
    return result.data[0] if result.data else None


def delete_event_image(db: Client, image_id: str) -> None:
    db.table("event_images").delete().eq("id", image_id).execute()


def upload_to_storage(db: Client, path: str, file_bytes: bytes, content_type: str) -> str:
    db.storage.from_(BUCKET_NAME).upload(path, file_bytes, {"content-type": content_type})
    return db.storage.from_(BUCKET_NAME).get_public_url(path)


def delete_from_storage(db: Client, path: str) -> None:
    db.storage.from_(BUCKET_NAME).remove([path])
