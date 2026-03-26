"""Tests for notification endpoints."""

import uuid


# --- Helpers ---

def _register_user(client, prefix="notiftest"):
    """Register a unique user and return (user_id, access_token, headers)."""
    unique = uuid.uuid4().hex[:8]
    data = {
        "username": f"{prefix}_{unique}",
        "email": f"{prefix}_{unique}@example.com",
        "password": "testpass123",
        "date_of_birth": "2000-01-15",
    }
    resp = client.post("/auth/register", json=data)
    assert resp.status_code == 201
    body = resp.json()
    token = body["access_token"]
    user_id = body["user"]["id"]
    headers = {"Authorization": f"Bearer {token}"}
    return user_id, token, headers


def _insert_notification(db, user_id, **overrides):
    """Insert a notification directly into the DB for testing."""
    data = {
        "user_id": user_id,
        "type": "event_updated",
        "message": "Test notification",
        "is_read": False,
        **overrides,
    }
    result = db.table("notifications").insert(data).execute()
    return result.data[0]


def _cleanup_notifications(db, user_id):
    """Remove all notifications for a user."""
    db.table("notifications").delete().eq("user_id", user_id).execute()


# --- GET /notifications ---

class TestListNotifications:
    def test_empty_list(self, client, db):
        _, _, headers = _register_user(client)
        resp = client.get("/notifications", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["total"] == 0
        assert body["page"] == 1
        assert body["total_pages"] == 0

    def test_returns_items(self, client, db):
        user_id, _, headers = _register_user(client)
        _insert_notification(db, user_id, message="First")
        _insert_notification(db, user_id, message="Second")

        resp = client.get("/notifications", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert len(body["items"]) == 2

        _cleanup_notifications(db, user_id)

    def test_pagination(self, client, db):
        user_id, _, headers = _register_user(client)
        for i in range(25):
            _insert_notification(db, user_id, message=f"Notif {i}")

        resp = client.get("/notifications?page=2&page_size=10", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 25
        assert body["page"] == 2
        assert body["page_size"] == 10
        assert len(body["items"]) == 10
        assert body["total_pages"] == 3

        _cleanup_notifications(db, user_id)

    def test_ordered_newest_first(self, client, db):
        user_id, _, headers = _register_user(client)
        _insert_notification(db, user_id, message="Older")
        _insert_notification(db, user_id, message="Newer")

        resp = client.get("/notifications", headers=headers)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert items[0]["created_at"] >= items[1]["created_at"]

        _cleanup_notifications(db, user_id)

    def test_unauthenticated(self, client):
        resp = client.get("/notifications")
        assert resp.status_code == 401

    def test_only_own_notifications(self, client, db):
        user1_id, _, headers1 = _register_user(client)
        user2_id, _, headers2 = _register_user(client)
        _insert_notification(db, user1_id, message="User1 notif")
        _insert_notification(db, user2_id, message="User2 notif")

        resp = client.get("/notifications", headers=headers1)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["message"] == "User1 notif"

        _cleanup_notifications(db, user1_id)
        _cleanup_notifications(db, user2_id)


# --- PATCH /notifications/{id}/read ---

class TestMarkNotificationAsRead:
    def test_mark_as_read(self, client, db):
        user_id, _, headers = _register_user(client)
        notif = _insert_notification(db, user_id)

        resp = client.patch(f"/notifications/{notif['id']}/read", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == notif["id"]
        assert body["is_read"] is True

        _cleanup_notifications(db, user_id)

    def test_already_read_is_idempotent(self, client, db):
        user_id, _, headers = _register_user(client)
        notif = _insert_notification(db, user_id, is_read=True)

        resp = client.patch(f"/notifications/{notif['id']}/read", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["is_read"] is True

        _cleanup_notifications(db, user_id)

    def test_not_found(self, client, db):
        _, _, headers = _register_user(client)
        fake_id = str(uuid.uuid4())

        resp = client.patch(f"/notifications/{fake_id}/read", headers=headers)
        assert resp.status_code == 404

    def test_other_users_notification(self, client, db):
        user1_id, _, _ = _register_user(client)
        _, _, headers2 = _register_user(client)
        notif = _insert_notification(db, user1_id)

        resp = client.patch(f"/notifications/{notif['id']}/read", headers=headers2)
        assert resp.status_code == 403

        _cleanup_notifications(db, user1_id)


# --- PATCH /notifications/read-all ---

class TestMarkAllAsRead:
    def test_mark_all(self, client, db):
        user_id, _, headers = _register_user(client)
        _insert_notification(db, user_id, message="A")
        _insert_notification(db, user_id, message="B")
        _insert_notification(db, user_id, message="C")

        resp = client.patch("/notifications/read-all", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["updated_count"] == 3

        # Verify all are read
        list_resp = client.get("/notifications", headers=headers)
        for item in list_resp.json()["items"]:
            assert item["is_read"] is True

        _cleanup_notifications(db, user_id)

    def test_none_unread(self, client, db):
        user_id, _, headers = _register_user(client)
        _insert_notification(db, user_id, is_read=True)

        resp = client.patch("/notifications/read-all", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["updated_count"] == 0

        _cleanup_notifications(db, user_id)

    def test_only_affects_own(self, client, db):
        user1_id, _, headers1 = _register_user(client)
        user2_id, _, headers2 = _register_user(client)
        _insert_notification(db, user1_id, message="U1")
        _insert_notification(db, user2_id, message="U2")

        # User1 marks all as read
        client.patch("/notifications/read-all", headers=headers1)

        # User2's notification should still be unread
        resp = client.get("/notifications", headers=headers2)
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["is_read"] is False

        _cleanup_notifications(db, user1_id)
        _cleanup_notifications(db, user2_id)
