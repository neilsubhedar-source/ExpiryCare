"""Tests for authentication, registration, login, JWT issuance, and profile security."""
import json


def test_register_success(client):
    """Verify new user registration succeeds and returns JWT token."""
    payload = {
        "name": "Jane Doe",
        "email": "jane.doe@example.com",
        "password": "SecurePassword123"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data["success"] is True
    assert "token" in data["data"]
    assert data["data"]["user"]["email"] == "jane.doe@example.com"
    assert data["data"]["user"]["name"] == "Jane Doe"


def test_register_duplicate_email(client, test_user):
    """Verify duplicate email registration is rejected."""
    payload = {
        "name": "Duplicate Test",
        "email": test_user["email"],
        "password": "Password123!"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "already exists" in data["error"].lower()


def test_register_validation_errors(client):
    """Verify invalid email or short password rejected with 400."""
    # Invalid email
    r1 = client.post("/api/auth/register", json={"name": "Test", "email": "invalid-email", "password": "Password123!"})
    assert r1.status_code == 400
    assert "valid email" in r1.get_json()["error"].lower()

    # Short password
    r2 = client.post("/api/auth/register", json={"name": "Test", "email": "valid@example.com", "password": "short"})
    assert r2.status_code == 400
    assert "8 characters" in r2.get_json()["error"].lower()


def test_login_success(client, test_user):
    """Verify login with correct credentials returns token and user data."""
    payload = {
        "email": test_user["email"],
        "password": "Password123!"
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "token" in data["data"]
    assert data["data"]["user"]["id"] == test_user["id"]


def test_login_wrong_password(client, test_user):
    """Verify login with incorrect password returns 401."""
    payload = {
        "email": test_user["email"],
        "password": "WrongPassword!"
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 401
    data = response.get_json()
    assert data["success"] is False
    assert "incorrect email or password" in data["error"].lower()


def test_profile_protected(client, auth_headers, test_user):
    """Verify GET and PUT /api/auth/profile for authenticated user."""
    # Unauthenticated request fails
    r_unauth = client.get("/api/auth/profile")
    assert r_unauth.status_code == 401

    # Authenticated get
    r_auth = client.get("/api/auth/profile", headers=auth_headers)
    assert r_auth.status_code == 200
    profile = r_auth.get_json()["data"]
    assert profile["email"] == test_user["email"]

    # Authenticated update
    update_payload = {"name": "Updated Name", "email": test_user["email"]}
    r_update = client.put("/api/auth/profile", headers=auth_headers, json=update_payload)
    assert r_update.status_code == 200
    assert r_update.get_json()["data"]["name"] == "Updated Name"


def test_settings_update(client, auth_headers):
    """Verify user can update notification alert threshold preferences."""
    payload = {"alertThresholds": [1, 3, 7, 14]}
    response = client.put("/api/auth/settings", headers=auth_headers, json=payload)
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["alertThresholds"] == [1, 3, 7, 14]
