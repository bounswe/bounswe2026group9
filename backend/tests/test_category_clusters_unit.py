"""Unit tests for app.services.category_clusters.expand_category_ids.

All DB calls are mocked — no network/Supabase required.
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.services.category_clusters import expand_category_ids


@pytest.fixture
def db():
    return MagicMock(name="supabase_client")


# Stable UUIDs for test categories
SPORTS_ID = str(uuid4())
OUTDOOR_ID = str(uuid4())
WELLNESS_ID = str(uuid4())
MUSIC_ID = str(uuid4())
ARTS_ID = str(uuid4())
UNKNOWN_ID = str(uuid4())


class TestExpandCategoryIds:
    def test_empty_input_returns_empty_set(self, db):
        result = expand_category_ids(db, set())
        assert result == set()

    def test_categories_not_in_any_cluster_returned_unchanged(self, db):
        """Categories whose names don't appear in CATEGORY_CLUSTERS are kept
        as-is — expand_category_ids never drops IDs, only adds."""
        with patch(
            "app.services.category_clusters._category_repo.get_categories_by_ids",
            return_value=[{"id": UNKNOWN_ID, "name": "Niche Hobby"}],
        ):
            result = expand_category_ids(db, {UNKNOWN_ID})

        assert UNKNOWN_ID in result

    def test_single_category_expands_to_full_cluster(self, db):
        """A single Sports ID should pull in the whole 'active' cluster."""
        similar_rows = [
            {"id": OUTDOOR_ID, "name": "Outdoor"},
            {"id": WELLNESS_ID, "name": "Health & Wellness"},
        ]
        with (
            patch(
                "app.services.category_clusters._category_repo.get_categories_by_ids",
                return_value=[{"id": SPORTS_ID, "name": "Sports"}],
            ),
            patch(
                "app.services.category_clusters._category_repo.get_categories_by_names",
                return_value=similar_rows,
            ) as mock_by_names,
        ):
            result = expand_category_ids(db, {SPORTS_ID})

        assert SPORTS_ID in result
        assert OUTDOOR_ID in result
        assert WELLNESS_ID in result
        # Should query for the *other* names in the cluster (not Sports itself)
        queried_names = set(mock_by_names.call_args.args[1])
        assert "Sports" not in queried_names
        assert "Outdoor" in queried_names
        assert "Health & Wellness" in queried_names

    def test_multiple_categories_same_cluster_expand_together(self, db):
        """Two IDs in the same cluster produce one DB round-trip for similar names."""
        with (
            patch(
                "app.services.category_clusters._category_repo.get_categories_by_ids",
                return_value=[
                    {"id": SPORTS_ID, "name": "Sports"},
                    {"id": OUTDOOR_ID, "name": "Outdoor"},
                ],
            ),
            patch(
                "app.services.category_clusters._category_repo.get_categories_by_names",
                return_value=[{"id": WELLNESS_ID, "name": "Health & Wellness"}],
            ),
        ):
            result = expand_category_ids(db, {SPORTS_ID, OUTDOOR_ID})

        assert SPORTS_ID in result
        assert OUTDOOR_ID in result
        assert WELLNESS_ID in result

    def test_categories_across_two_clusters_both_expanded(self, db):
        """IDs from different clusters each get their cluster expanded."""
        with (
            patch(
                "app.services.category_clusters._category_repo.get_categories_by_ids",
                return_value=[
                    {"id": SPORTS_ID, "name": "Sports"},
                    {"id": MUSIC_ID, "name": "Music"},
                ],
            ),
            patch(
                "app.services.category_clusters._category_repo.get_categories_by_names",
                return_value=[
                    {"id": WELLNESS_ID, "name": "Health & Wellness"},
                    {"id": OUTDOOR_ID, "name": "Outdoor"},
                    {"id": ARTS_ID, "name": "Arts & Culture"},
                ],
            ) as mock_by_names,
        ):
            result = expand_category_ids(db, {SPORTS_ID, MUSIC_ID})

        assert {SPORTS_ID, MUSIC_ID, WELLNESS_ID, OUTDOOR_ID, ARTS_ID}.issubset(result)
        queried_names = set(mock_by_names.call_args.args[1])
        # Names from both clusters should be queried, minus the exact ones already known
        assert "Sports" not in queried_names
        assert "Music" not in queried_names
        assert "Outdoor" in queried_names
        assert "Arts & Culture" in queried_names

    def test_all_cluster_members_present_returns_exact_ids_only(self, db):
        """When the exact IDs already cover the entire cluster, no similar_names
        remain after subtracting exact_names → get_categories_by_names is not called
        and the original set is returned unchanged."""
        all_active_ids = {SPORTS_ID, OUTDOOR_ID, WELLNESS_ID}
        with (
            patch(
                "app.services.category_clusters._category_repo.get_categories_by_ids",
                return_value=[
                    {"id": SPORTS_ID, "name": "Sports"},
                    {"id": OUTDOOR_ID, "name": "Outdoor"},
                    {"id": WELLNESS_ID, "name": "Health & Wellness"},
                ],
            ),
            patch(
                "app.services.category_clusters._category_repo.get_categories_by_names",
            ) as mock_by_names,
        ):
            result = expand_category_ids(db, all_active_ids)

        assert result == all_active_ids
        mock_by_names.assert_not_called()
