"""Integration tests for Users/Profiles/Ratings API."""

from tests_support import build_test_identity


def test_user_profiles_and_ratings(client, db):
    # Register host
    host_user, host_email = build_test_identity("proftest")
    client.post("/auth/register", json={"username": host_user, "email": host_email, "password": "password123", "date_of_birth": "1990-01-01"})
    login = client.post("/auth/login", json={"email": host_email, "password": "password123"})
    host_token = login.json()["access_token"]

    # Get me
    res = client.get("/auth/me", headers={"Authorization": f"Bearer {host_token}"})
    host_id = res.json()["id"]

    # Register rater
    r_user, r_email = build_test_identity("ratetest")
    client.post("/auth/register", json={"username": r_user, "email": r_email, "password": "password123", "date_of_birth": "1990-01-01"})
    r_token = client.post("/auth/login", json={"email": r_email, "password": "password123"}).json()["access_token"]

    # Host rating fails (self)
    res = client.post(f"/users/{host_id}/ratings", headers={"Authorization": f"Bearer {host_token}"}, json={"score": 5.0})
    assert res.status_code == 400

    # User rates 4.0
    res = client.post(f"/users/{host_id}/ratings", headers={"Authorization": f"Bearer {r_token}"}, json={"score": 4.0})
    assert res.status_code == 200
    assert float(res.json()["score"]) == 4.0

    # User updates rating to 5.0
    res = client.post(f"/users/{host_id}/ratings", headers={"Authorization": f"Bearer {r_token}"}, json={"score": 5.0})
    assert res.status_code == 200
    assert float(res.json()["score"]) == 5.0

    # Check Host profile
    res = client.get(f"/users/{host_id}/profile")
    assert res.status_code == 200
    assert res.json()["average_rating"] == 5.0

    # User updates self profile
    res = client.put("/users/me", headers={"Authorization": f"Bearer {r_token}"}, json={
        "phone_number": "+1234567890",
        "email_visibility": "public",
        "default_location_name": "Home",
        "default_location_lat": 1.0,
        "default_location_lng": 1.0
    })
    assert res.status_code == 200
    assert res.json()["phone_number"] == "+1234567890"

    # Guest checks rater profile updates (email should be visible now)
    rater_id = client.get("/auth/me", headers={"Authorization": f"Bearer {r_token}"}).json()["id"]
    res = client.get(f"/users/{rater_id}/profile")
    assert res.status_code == 200
    assert res.json()["email"] == r_email
