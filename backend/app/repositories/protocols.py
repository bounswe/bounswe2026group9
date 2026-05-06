"""Structural typing protocols for each repository module.

Phase 1 of `backend/TESTING_ROADMAP.md`. Lets services accept their
repository collaborators as keyword arguments with a default that resolves
to the production module — production callers don't change, but unit tests
can pass a mock that implements the same surface.

The protocols intentionally mirror the public function signatures of each
`app/repositories/*.py` module verbatim. Adding a new public function in a
repository module without updating the matching protocol is a code smell:
either the function is internal (prefix with `_`) or its consumers should
type against the protocol so the static analyser can flag dead methods.

These protocols are runtime-friendly (no `runtime_checkable` decorator
needed for the kwarg pattern). When mypy strict mode lands in Phase 4
they may need a small adjustment so module references type-match the
class-shaped protocols (e.g. by switching to module-typing or by wrapping
the modules in lightweight adapter objects); that work belongs to Phase 4
and is not in scope here.
"""
from __future__ import annotations

from typing import Any, Protocol

from supabase import Client


class BookmarkRepoProtocol(Protocol):
    """Surface used by `services.bookmark`."""

    def get_bookmark(self, db: Client, user_id: str, event_id: str) -> dict | None: ...

    def insert_bookmark(self, db: Client, data: dict) -> dict: ...

    def delete_bookmark(self, db: Client, user_id: str, event_id: str) -> None: ...

    def get_bookmarks_by_user(
        self, db: Client, user_id: str, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[dict], int]: ...

    def get_bookmark_count_for_event(self, db: Client, event_id: str) -> int: ...

    def get_bookmark_counts_for_events(
        self, db: Client, event_ids: list[str]
    ) -> dict[str, int]: ...

    def get_bookmark_status_for_events(
        self, db: Client, user_id: str, event_ids: list[str]
    ) -> dict[str, bool]: ...


class CategoryRepoProtocol(Protocol):
    """Surface used by `services.category`."""

    def get_all_available(self, db: Client) -> list[dict]: ...

    def search_available(self, db: Client, query: str) -> list[dict]: ...

    def get_by_name(self, db: Client, name: str) -> dict | None: ...

    def insert_category(self, db: Client, data: dict) -> dict | None: ...


class NotificationRepoProtocol(Protocol):
    """Surface used by `services.notification`, `services.invite`, and the
    notification_emitter service. `insert_notification` is included so
    invite's access-request flow can write through the same handle."""

    def get_notifications_by_user(
        self, db: Client, user_id: str, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[dict], int]: ...

    def get_unread_count(self, db: Client, user_id: str) -> int: ...

    def get_notification_by_id(self, db: Client, notification_id: str) -> dict | None: ...

    def mark_notification_as_read(
        self, db: Client, notification_id: str
    ) -> dict | None: ...

    def mark_all_notifications_as_read(self, db: Client, user_id: str) -> int: ...

    def insert_notification(self, db: Client, data: dict) -> dict | None: ...


class InviteRepoProtocol(Protocol):
    """Surface used by `services.invite`. Covers both invite tokens and
    access requests / grants — all live in the same repo module."""

    def insert_invite(self, db: Client, data: dict) -> dict: ...

    def get_invite_by_token(self, db: Client, token: str) -> dict | None: ...

    def get_invites_by_event(self, db: Client, event_id: str) -> list[dict]: ...

    def increment_invite_use_count(self, db: Client, invite_id: str) -> None: ...

    def delete_invite(self, db: Client, invite_id: str) -> None: ...

    def insert_access_grant(self, db: Client, data: dict) -> dict: ...

    def get_access_grant(
        self, db: Client, event_id: str, user_id: str
    ) -> dict | None: ...

    def get_granted_user_ids(self, db: Client, event_id: str) -> list[str]: ...

    def insert_access_request(self, db: Client, data: dict) -> dict: ...

    def get_access_request_by_id(
        self, db: Client, request_id: str
    ) -> dict | None: ...

    def get_access_request(
        self, db: Client, event_id: str, user_id: str
    ) -> dict | None: ...

    def get_access_request_status_for_events(
        self, db: Client, user_id: str, event_ids: list[str]
    ) -> dict[str, str]: ...

    def get_access_granted_event_ids(
        self, db: Client, user_id: str, event_ids: list[str]
    ) -> set[str]: ...

    def get_pending_requests_by_event(
        self, db: Client, event_id: str
    ) -> list[dict]: ...

    def update_access_request(
        self, db: Client, request_id: str, data: dict
    ) -> dict | None: ...


class RatingRepoProtocol(Protocol):
    """Surface used by `services.rating`."""

    def get_rating(self, db: Client, rater_id: str, host_id: str) -> dict | None: ...

    def upsert_rating(self, db: Client, data: dict) -> dict: ...

    def get_host_rating_stats(self, db: Client, host_id: str) -> dict: ...

    def list_reviews_for_host(
        self, db: Client, host_id: str, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[dict], int]: ...


class ProfileRepoProtocol(Protocol):
    """Surface used by services that read/write user profile rows."""

    def get_full_user_profile(self, db: Client, user_id: str) -> dict | None: ...

    def update_user_profile(self, db: Client, user_id: str, data: dict) -> dict: ...

    def get_hosted_events(
        self, db: Client, user_id: str, include_drafts: bool = False
    ) -> list[dict]: ...


class ImageRepoProtocol(Protocol):
    """Surface used by `services.image`. The `BUCKET_NAME` constant is
    accessed off the live module by `delete_event_image` to extract the
    storage path; tests assign that attribute on the mock."""

    BUCKET_NAME: str

    def count_event_images(self, db: Client, event_id: str) -> int: ...

    def insert_event_image(
        self, db: Client, event_id: str, image_url: str
    ) -> dict | None: ...

    def get_all_event_images(self, db: Client, event_id: str) -> list[dict]: ...

    def get_event_image(self, db: Client, image_id: str) -> dict | None: ...

    def delete_event_image(self, db: Client, image_id: str) -> None: ...

    def upload_to_storage(
        self, db: Client, path: str, file_bytes: bytes, content_type: str
    ) -> str: ...

    def delete_from_storage(self, db: Client, path: str) -> None: ...


class CommentRepoProtocol(Protocol):
    """Surface used by `services.comment`. Note: comment repo carries its own
    user lookup helpers — `get_users_by_ids` returns a dict here (vs. a list
    in user_repo), so they're intentionally not aliased."""

    def insert_comment(self, db: Client, comment_data: dict) -> dict: ...

    def get_comments_by_event(
        self, db: Client, event_id: str, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[dict], int]: ...

    def get_comment_by_id(self, db: Client, comment_id: str) -> dict | None: ...

    def delete_comment(self, db: Client, comment_id: str) -> None: ...

    def get_user_by_id(self, db: Client, user_id: str) -> dict | None: ...

    def get_users_by_ids(
        self, db: Client, user_ids: list[str]
    ) -> dict[str, dict]: ...


class AttendanceRepoProtocol(Protocol):
    """Surface used by `services.attendance`. Tokens excluded — those are
    a thin layer in the service module itself, not the repository."""

    def get_attendance(self, db: Client, user_id: str, event_id: str) -> dict | None: ...

    def insert_attendance(self, db: Client, data: dict) -> dict: ...

    def update_attendance(
        self, db: Client, user_id: str, event_id: str, status: str
    ) -> dict: ...

    def update_attendance_token(
        self, db: Client, user_id: str, event_id: str, token: str | None
    ) -> dict: ...

    def delete_attendance(self, db: Client, user_id: str, event_id: str) -> None: ...

    def get_attendance_by_token(self, db: Client, token: str) -> dict | None: ...

    def mark_checked_in(self, db: Client, attendance_id: str) -> dict: ...

    def list_going_attendees_with_checkin(
        self, db: Client, event_id: str
    ) -> list[dict]: ...

    def get_going_user_ids_for_event(self, db: Client, event_id: str) -> list[str]: ...

    def get_attendance_status_for_events(
        self, db: Client, user_id: str, event_ids: list[str]
    ) -> dict[str, str]: ...

    def has_attended_ended_event_by_host(
        self, db: Client, user_id: str, host_id: str
    ) -> bool: ...

    def find_users_going_on_events(
        self, db: Client, event_ids: list[str]
    ) -> set[str]: ...

    def get_attended_ended_event_categories(
        self, db: Client, user_id: str
    ) -> set[str]: ...


class UserRepoProtocol(Protocol):
    """Surface used by services that look up user records by id."""

    def get_user_by_id(self, db: Client, user_id: str) -> dict | None: ...

    def get_user_email_by_id(self, db: Client, user_id: str) -> str | None: ...

    def get_user_date_of_birth(self, db: Client, user_id: str) -> str | None: ...

    def get_users_by_ids(self, db: Client, user_ids: list[str]) -> list[dict]: ...


class EventRepoProtocol(Protocol):
    """Surface of `repositories.event` consumed by other services.

    Only methods used outside `services.event` are required here today;
    the full surface will be filled in alongside the matching service
    refactor in subsequent commits.
    """

    def get_event_by_id(self, db: Client, event_id: str) -> dict | None: ...

    def get_primary_locations_for_events(
        self, db: Client, event_ids: list[str]
    ) -> dict[str, dict]: ...

    def get_categories_for_events(
        self, db: Client, event_ids: list[str]
    ) -> dict[str, list[dict]]: ...

    def get_primary_images_for_events(
        self, db: Client, event_ids: list[str]
    ) -> dict[str, str]: ...


# Convenience alias for "any module-shaped object that satisfies a repo
# protocol". Useful when a service takes a default-keyword repo and we
# want to accept either the live module or an arbitrary mock without
# pulling in `Module` from `types`.
RepoLike = Any
