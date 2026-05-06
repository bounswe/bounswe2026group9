"""Unit tests for `services.comment` — exercises the keyword-DI seam."""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.models.comment import CommentCreateRequest
from app.services import comment as comment_service


EVENT_ID = "00000000-0000-0000-0000-000000000050"
USER_ID = "00000000-0000-0000-0000-000000000051"
HOST_ID = "00000000-0000-0000-0000-000000000052"
COMMENT_ID = "00000000-0000-0000-0000-000000000053"
PARENT_ID = "00000000-0000-0000-0000-000000000054"
ROOT_ID = "00000000-0000-0000-0000-000000000055"


@pytest.fixture
def db():
    return MagicMock(name="supabase_client")


def _published_event(host_id: str = HOST_ID) -> dict:
    return {"id": EVENT_ID, "host_id": host_id, "status": "published"}


def _comment(id_: str, parent_id: str | None = None, user_id: str = USER_ID) -> dict:
    return {
        "id": id_,
        "event_id": EVENT_ID,
        "user_id": user_id,
        "text": "hello",
        "created_at": "2026-01-01T00:00:00+00:00",
        "parent_id": parent_id,
    }


@pytest.fixture
def repos():
    comments = MagicMock()
    events = MagicMock()
    events.get_event_by_id.return_value = _published_event()
    return comments, events


# ── create_comment ──────────────────────────────────────────────────────────


class TestCreateComment:
    def test_404_when_event_missing(self, db, repos):
        comments, events = repos
        events.get_event_by_id.return_value = None

        with pytest.raises(HTTPException) as exc:
            comment_service.create_comment(
                db, EVENT_ID, USER_ID, CommentCreateRequest(text="hi"),
                comments=comments, events=events,
            )
        assert exc.value.status_code == 404
        comments.insert_comment.assert_not_called()

    def test_400_for_draft_or_cancelled_event(self, db, repos):
        comments, events = repos
        events.get_event_by_id.return_value = {**_published_event(), "status": "cancelled"}

        with pytest.raises(HTTPException) as exc:
            comment_service.create_comment(
                db, EVENT_ID, USER_ID, CommentCreateRequest(text="hi"),
                comments=comments, events=events,
            )
        assert exc.value.status_code == 400

    def test_top_level_insert_omits_parent_id(self, db, repos):
        comments, events = repos
        comments.insert_comment.return_value = _comment(COMMENT_ID)
        comments.get_user_by_id.return_value = {"id": USER_ID, "username": "alice"}

        comment_service.create_comment(
            db, EVENT_ID, USER_ID, CommentCreateRequest(text="hello"),
            comments=comments, events=events,
        )

        sent = comments.insert_comment.call_args.args[1]
        assert "parent_id" not in sent
        assert sent["event_id"] == EVENT_ID
        assert sent["user_id"] == USER_ID
        assert sent["text"] == "hello"

    def test_404_when_parent_belongs_to_different_event(self, db, repos):
        comments, events = repos
        comments.get_comment_by_id.return_value = {
            "id": PARENT_ID,
            "event_id": "00000000-0000-0000-0000-000000000099",  # different event
            "parent_id": None,
        }

        with pytest.raises(HTTPException) as exc:
            comment_service.create_comment(
                db, EVENT_ID, USER_ID,
                CommentCreateRequest(text="reply", parent_id=PARENT_ID),
                comments=comments, events=events,
            )
        assert exc.value.status_code == 404
        comments.insert_comment.assert_not_called()

    def test_400_when_max_nesting_reached(self, db, repos):
        comments, events = repos
        # Build a 3-deep chain so the depth check rejects.
        comments.get_comment_by_id.side_effect = lambda _db, cid: {
            PARENT_ID: {"id": PARENT_ID, "event_id": EVENT_ID, "parent_id": ROOT_ID},
            ROOT_ID: {"id": ROOT_ID, "event_id": EVENT_ID, "parent_id": "0" * 8 + "-".join(["0" * 4] * 3) + "-" + "0" * 12},
        }.get(cid)

        # Use a real parent → service walks up 3 hops, hits MAX_NESTING_DEPTH.
        # Patch chain to include the third-level link returning None to terminate.
        chain = {
            PARENT_ID: {"id": PARENT_ID, "event_id": EVENT_ID, "parent_id": ROOT_ID},
            ROOT_ID: {"id": ROOT_ID, "event_id": EVENT_ID, "parent_id": "00000000-0000-0000-0000-000000000056"},
            "00000000-0000-0000-0000-000000000056": {
                "id": "00000000-0000-0000-0000-000000000056",
                "event_id": EVENT_ID,
                "parent_id": None,
            },
        }
        comments.get_comment_by_id.side_effect = lambda _db, cid: chain.get(cid)

        with pytest.raises(HTTPException) as exc:
            comment_service.create_comment(
                db, EVENT_ID, USER_ID,
                CommentCreateRequest(text="too deep", parent_id=PARENT_ID),
                comments=comments, events=events,
            )
        assert exc.value.status_code == 400


# ── list_comments ───────────────────────────────────────────────────────────


class TestListComments:
    def test_404_when_event_missing(self, db, repos):
        comments, events = repos
        events.get_event_by_id.return_value = None

        with pytest.raises(HTTPException) as exc:
            comment_service.list_comments(
                db, EVENT_ID, comments=comments, events=events,
            )
        assert exc.value.status_code == 404

    def test_assembles_replies_into_tree(self, db, repos):
        comments, events = repos
        root = _comment(ROOT_ID)
        reply = _comment(COMMENT_ID, parent_id=ROOT_ID)
        comments.get_comments_by_event.return_value = ([root, reply], 2)
        comments.get_users_by_ids.return_value = {
            USER_ID: {"id": USER_ID, "username": "alice"},
        }

        result = comment_service.list_comments(
            db, EVENT_ID, comments=comments, events=events,
        )

        assert len(result.items) == 1
        assert str(result.items[0].id) == ROOT_ID
        assert len(result.items[0].replies) == 1
        assert str(result.items[0].replies[0].id) == COMMENT_ID

    def test_drops_comments_with_unknown_user(self, db, repos):
        # If the user lookup misses (e.g. dangling row) the comment is omitted
        # rather than crashing the listing.
        comments, events = repos
        comments.get_comments_by_event.return_value = ([_comment(ROOT_ID)], 1)
        comments.get_users_by_ids.return_value = {}

        result = comment_service.list_comments(
            db, EVENT_ID, comments=comments, events=events,
        )

        assert result.items == []


# ── delete_comment ──────────────────────────────────────────────────────────


class TestDeleteComment:
    def test_404_when_missing(self, db, repos):
        comments, events = repos
        comments.get_comment_by_id.return_value = None

        with pytest.raises(HTTPException) as exc:
            comment_service.delete_comment(
                db, EVENT_ID, COMMENT_ID, USER_ID,
                comments=comments, events=events,
            )
        assert exc.value.status_code == 404

    def test_404_when_comment_belongs_to_different_event(self, db, repos):
        comments, events = repos
        comments.get_comment_by_id.return_value = {
            "id": COMMENT_ID,
            "event_id": "00000000-0000-0000-0000-000000000099",
            "user_id": USER_ID,
        }

        with pytest.raises(HTTPException) as exc:
            comment_service.delete_comment(
                db, EVENT_ID, COMMENT_ID, USER_ID,
                comments=comments, events=events,
            )
        assert exc.value.status_code == 404

    def test_403_when_caller_neither_owner_nor_host(self, db, repos):
        comments, events = repos
        comments.get_comment_by_id.return_value = _comment(COMMENT_ID, user_id="other")

        with pytest.raises(HTTPException) as exc:
            comment_service.delete_comment(
                db, EVENT_ID, COMMENT_ID, USER_ID,
                comments=comments, events=events,
            )
        assert exc.value.status_code == 403
        comments.delete_comment.assert_not_called()

    def test_owner_can_delete(self, db, repos):
        comments, events = repos
        comments.get_comment_by_id.return_value = _comment(COMMENT_ID)

        comment_service.delete_comment(
            db, EVENT_ID, COMMENT_ID, USER_ID,
            comments=comments, events=events,
        )
        comments.delete_comment.assert_called_once_with(db, COMMENT_ID)

    def test_host_can_delete_other_users_comment(self, db, repos):
        comments, events = repos
        comments.get_comment_by_id.return_value = _comment(COMMENT_ID, user_id="other")

        comment_service.delete_comment(
            db, EVENT_ID, COMMENT_ID, HOST_ID,  # host_id from _published_event default
            comments=comments, events=events,
        )
        comments.delete_comment.assert_called_once_with(db, COMMENT_ID)
