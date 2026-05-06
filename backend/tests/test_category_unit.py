"""Unit tests for `services.category` — exercises the keyword-DI seam."""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.models.event import CategoryCreateRequest
from app.services import category as category_service


CATEGORY_ID = "00000000-0000-0000-0000-000000000010"


@pytest.fixture
def db():
    return MagicMock(name="supabase_client")


# ── list_categories ─────────────────────────────────────────────────────────


class TestListCategories:
    def test_returns_all_when_no_search(self, db):
        categories = MagicMock()
        categories.get_all_available.return_value = [
            {"id": CATEGORY_ID, "name": "Music", "is_predefined": True, "is_approved": True},
        ]

        result = category_service.list_categories(db, categories=categories)

        assert len(result) == 1
        assert result[0].name == "Music"
        categories.get_all_available.assert_called_once_with(db)
        categories.search_available.assert_not_called()

    def test_runs_search_when_query_provided(self, db):
        categories = MagicMock()
        categories.search_available.return_value = []

        category_service.list_categories(db, "jazz", categories=categories)

        categories.search_available.assert_called_once_with(db, "jazz")
        categories.get_all_available.assert_not_called()


# ── create_custom_category ──────────────────────────────────────────────────


class TestCreateCustomCategory:
    def test_creates_when_name_is_unique(self, db):
        categories = MagicMock()
        categories.get_by_name.return_value = None
        categories.insert_category.return_value = {
            "id": CATEGORY_ID,
            "name": "Indie Rock",
            "is_predefined": False,
            "is_approved": False,
        }

        body = CategoryCreateRequest(name="Indie Rock")
        result = category_service.create_custom_category(
            db, body, "user-1", categories=categories
        )

        assert result.name == "Indie Rock"
        assert result.is_predefined is False
        # insert payload must trim and mark unapproved.
        categories.insert_category.assert_called_once_with(
            db, {"name": "Indie Rock", "is_predefined": False, "is_approved": False}
        )

    def test_409_when_name_already_taken(self, db):
        categories = MagicMock()
        categories.get_by_name.return_value = {"id": CATEGORY_ID, "name": "Music"}

        with pytest.raises(HTTPException) as exc:
            category_service.create_custom_category(
                db, CategoryCreateRequest(name="Music"), "user-1", categories=categories
            )

        assert exc.value.status_code == 409
        categories.insert_category.assert_not_called()

    def test_unique_constraint_during_insert_maps_to_409(self, db):
        # Race window: get_by_name says clear, but the unique index trips
        # at insert time. Repository raises any exception — service maps
        # to 409 and chains the cause.
        categories = MagicMock()
        categories.get_by_name.return_value = None
        categories.insert_category.side_effect = Exception("duplicate key")

        with pytest.raises(HTTPException) as exc:
            category_service.create_custom_category(
                db, CategoryCreateRequest(name="Jazz"), "user-1", categories=categories
            )

        assert exc.value.status_code == 409

    def test_500_when_insert_returns_none(self, db):
        categories = MagicMock()
        categories.get_by_name.return_value = None
        categories.insert_category.return_value = None

        with pytest.raises(HTTPException) as exc:
            category_service.create_custom_category(
                db, CategoryCreateRequest(name="Latin"), "user-1", categories=categories
            )

        assert exc.value.status_code == 500
