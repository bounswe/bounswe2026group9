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
