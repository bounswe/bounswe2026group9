"""Contract tests for /notifications endpoints.

Phase 2 retains one happy-path integration test per HTTP endpoint.
Branch coverage (auth, ownership, idempotency, pagination edges) lives in
tests/test_notification_unit.py.
"""

from tests_support import build_test_identity


def _register_user(client, prefix="notiftest"):
    username, email = build_test_identity(prefix)
    resp = client.post("/auth/register", json={
        "username": username, "email": email,
        "password": "testpass123", "date_of_birth": "2000-01-15",
    })
    assert resp.status_code == 201
    body = resp.json()
    return body["user"]["id"], {"Authorization": f"Bearer {body['access_token']}"}


def _insert_notification(db, user_id, **overrides):
    data = {
        "user_id": user_id,
        "type": "event_updated",
        "message": "Test notification",
        "is_read": False,
        **overrides,
    }
    return db.table("notifications").insert(data).execute().data[0]


def _cleanup(db, user_id):
    db.table("notifications").delete().eq("user_id", user_id).execute()


# --- Contract tests (one happy path per endpoint) ---


class TestListNotifications:
    """GET /notifications"""

    def test_returns_items_newest_first(self, client, db):
        user_id, headers = _register_user(client)
        _insert_notification(db, user_id, message="Older")
        _insert_notification(db, user_id, message="Newer")

        resp = client.get("/notifications", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        items = body["items"]
        assert len(items) == 2
        assert items[0]["created_at"] >= items[1]["created_at"]

        _cleanup(db, user_id)


class TestUnreadCount:
    """GET /notifications/unread-count"""

    def test_unread_count_excludes_read(self, client, db):
        user_id, headers = _register_user(client)
        _insert_notification(db, user_id, is_read=False)
        _insert_notification(db, user_id, is_read=False)
        _insert_notification(db, user_id, is_read=True)

        resp = client.get("/notifications/unread-count", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["unread_count"] == 2

        _cleanup(db, user_id)


class TestMarkAsRead:
    """PATCH /notifications/{notification_id}/read"""

    def test_mark_as_read(self, client, db):
        user_id, headers = _register_user(client)
        notif = _insert_notification(db, user_id)

        resp = client.patch(f"/notifications/{notif['id']}/read", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["is_read"] is True

        _cleanup(db, user_id)


class TestMarkAllAsRead:
    """PATCH /notifications/read-all"""

    def test_mark_all_marks_all_unread(self, client, db):
        user_id, headers = _register_user(client)
        _insert_notification(db, user_id, message="A")
        _insert_notification(db, user_id, message="B")
        _insert_notification(db, user_id, message="C")

        resp = client.patch("/notifications/read-all", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["updated_count"] == 3

        list_resp = client.get("/notifications", headers=headers)
        for item in list_resp.json()["items"]:
            assert item["is_read"] is True

        _cleanup(db, user_id)
