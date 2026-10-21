"""Tests for dashboard analytics, timeline breakdowns, and user alerts."""
import json
from datetime import timedelta
from backend.utils.date_utils import to_input_date, get_today


def test_dashboard_summary_metrics(client, auth_headers):
    """Verify dashboard endpoint calculates real status counts and category distributions."""
    today = get_today()
    # Add expired, expiring-soon, and active products
    client.post("/api/products", headers=auth_headers, json={
        "name": "Expired Bread", "category": "grocery", "quantity": 1,
        "expiryDate": to_input_date(today - timedelta(days=2))
    })
    client.post("/api/products", headers=auth_headers, json={
        "name": "Soon Milk", "category": "grocery", "quantity": 1,
        "expiryDate": to_input_date(today + timedelta(days=5))
    })
    client.post("/api/products", headers=auth_headers, json={
        "name": "Active Vitamins", "category": "medicine", "quantity": 2,
        "expiryDate": to_input_date(today + timedelta(days=60))
    })

    response = client.get("/api/dashboard/summary", headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()["data"]

    counts = data["counts"]
    assert counts["total"] == 3
    assert counts["expired"] == 1
    assert counts["expiringSoon"] == 1
    assert counts["active"] == 1

    assert data["categoryCounts"]["grocery"] == 2
    assert data["categoryCounts"]["medicine"] == 1
    assert len(data["insights"]) > 0


def test_alerts_filtering_by_thresholds(client, auth_headers):
    """Verify alerts endpoint filters products matching the user's notification thresholds."""
    today = get_today()
    # Set threshold to 3 days
    client.put("/api/auth/settings", headers=auth_headers, json={"alertThresholds": [3]})

    # Create product expiring in 2 days (within 3 days threshold)
    client.post("/api/products", headers=auth_headers, json={
        "name": "Item within threshold", "category": "grocery", "quantity": 1,
        "expiryDate": to_input_date(today + timedelta(days=2))
    })

    # Create product expiring in 20 days (outside 3 days threshold)
    client.post("/api/products", headers=auth_headers, json={
        "name": "Item outside threshold", "category": "medicine", "quantity": 1,
        "expiryDate": to_input_date(today + timedelta(days=20))
    })

    response = client.get("/api/alerts", headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()["data"]
    alerts = data["alerts"]

    assert any(a["name"] == "Item within threshold" for a in alerts)
    assert not any(a["name"] == "Item outside threshold" for a in alerts)
