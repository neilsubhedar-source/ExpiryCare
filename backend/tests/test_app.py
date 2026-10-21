"""Tests for application startup, health endpoint, error handling, and routing."""
import json


def test_app_created(app):
    """Verify application factory initializes with testing config."""
    assert app is not None
    assert app.config["TESTING"] is True


def test_health_endpoint(client):
    """Verify GET /api/health responds with status ok and metadata."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert "service" in data
    assert "persistence" in data
    assert "ai" in data
    assert "timestamp" in data


def test_404_error_handler(client):
    """Verify non-existent endpoints return structured JSON 404."""
    response = client.get("/api/non-existent-route")
    assert response.status_code == 404
    data = response.get_json()
    assert data["success"] is False
    assert "not found" in data["error"].lower()


def test_405_error_handler(client):
    """Verify method not allowed returns structured JSON 405."""
    response = client.delete("/api/health")
    assert response.status_code == 405
    data = response.get_json()
    assert data["success"] is False
    assert "method not allowed" in data["error"].lower()


def test_cors_headers(client):
    """Verify CORS preflight options request."""
    response = client.open("/api/health", method="OPTIONS")
    assert response.status_code in (200, 204)
