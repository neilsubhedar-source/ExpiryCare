"""Tests for product CRUD operations, validation, ownership checks, and multi-user isolation."""
import json
from datetime import date, timedelta
from backend.utils.date_utils import to_input_date, get_today


def test_create_product_success(client, auth_headers):
    """Verify creating a product persists to database and attaches expiry calculations."""
    today = get_today()
    payload = {
        "name": "Amoxicillin 500mg",
        "category": "medicine",
        "quantity": 2,
        "notes": "Take with meals",
        "purchaseDate": to_input_date(today - timedelta(days=10)),
        "expiryDate": to_input_date(today + timedelta(days=20)),
        "batchNumber": "AMX-99"
    }
    response = client.post("/api/products", headers=auth_headers, json=payload)
    assert response.status_code == 201
    data = response.get_json()["data"]
    assert data["name"] == "Amoxicillin 500mg"
    assert data["category"] == "medicine"
    assert data["quantity"] == 2
    assert data["daysRemaining"] == 20
    assert data["status"] == "expiring-soon"
    assert data["statusClass"] == "status-badge-expiring"


def test_create_product_invalid_dates(client, auth_headers):
    """Verify expiry date earlier than purchase date is rejected."""
    today = get_today()
    payload = {
        "name": "Invalid Date Item",
        "category": "grocery",
        "quantity": 1,
        "purchaseDate": to_input_date(today),
        "expiryDate": to_input_date(today - timedelta(days=5))  # Before purchase
    }
    response = client.post("/api/products", headers=auth_headers, json=payload)
    assert response.status_code == 400
    assert "cannot be before the purchase date" in response.get_json()["error"].lower()


def test_create_product_invalid_quantity(client, auth_headers):
    """Verify non-positive or non-integer quantities are rejected."""
    payload = {
        "name": "Zero Qty",
        "category": "other",
        "quantity": 0
    }
    response = client.post("/api/products", headers=auth_headers, json=payload)
    assert response.status_code == 400
    assert "positive whole number" in response.get_json()["error"].lower()


def test_list_products_and_filters(client, auth_headers):
    """Verify listing products and applying category / search filters."""
    today = get_today()
    p1 = {"name": "Milk Cartons", "category": "grocery", "quantity": 1, "expiryDate": to_input_date(today + timedelta(days=2))}
    p2 = {"name": "Aspirin Pills", "category": "medicine", "quantity": 1, "expiryDate": to_input_date(today + timedelta(days=100))}
    client.post("/api/products", headers=auth_headers, json=p1)
    client.post("/api/products", headers=auth_headers, json=p2)

    # List all
    r_all = client.get("/api/products", headers=auth_headers)
    assert r_all.status_code == 200
    assert len(r_all.get_json()["data"]) >= 2

    # Filter by category
    r_cat = client.get("/api/products?category=grocery", headers=auth_headers)
    assert r_cat.status_code == 200
    items = r_cat.get_json()["data"]
    assert all(i["category"] == "grocery" for i in items)

    # Filter by search query
    r_search = client.get("/api/products?search=aspirin", headers=auth_headers)
    assert r_search.status_code == 200
    assert len(r_search.get_json()["data"]) == 1
    assert "Aspirin" in r_search.get_json()["data"][0]["name"]


def test_user_ownership_isolation(client, auth_headers, second_auth_headers):
    """Verify User B cannot view, update, or delete User A's products."""
    today = get_today()
    payload = {
        "name": "Secret Medicine of User A",
        "category": "medicine",
        "quantity": 1,
        "expiryDate": to_input_date(today + timedelta(days=50))
    }
    # User A creates a product
    create_resp = client.post("/api/products", headers=auth_headers, json=payload)
    product_id = create_resp.get_json()["data"]["id"]

    # User B tries to get it -> 404
    r_get = client.get(f"/api/products/{product_id}", headers=second_auth_headers)
    assert r_get.status_code == 404

    # User B tries to update it -> 400 or 404
    r_put = client.put(f"/api/products/{product_id}", headers=second_auth_headers, json={"name": "Hacked Name"})
    assert r_put.status_code in (400, 404)

    # User B tries to delete it -> 404
    r_del = client.delete(f"/api/products/{product_id}", headers=second_auth_headers)
    assert r_del.status_code == 404

    # User A can still retrieve and delete it
    r_user_a = client.get(f"/api/products/{product_id}", headers=auth_headers)
    assert r_user_a.status_code == 200
    r_del_a = client.delete(f"/api/products/{product_id}", headers=auth_headers)
    assert r_del_a.status_code == 200


def test_demo_data_loading(client, auth_headers):
    """Verify demo data loads standard 10 products when inventory is empty."""
    resp = client.post("/api/products/demo", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["count"] == 10
    assert len(data["data"]) == 10

    # Second call should be rejected because inventory is no longer empty
    resp_again = client.post("/api/products/demo", headers=auth_headers)
    assert resp_again.status_code == 400
    assert "only loaded when inventory is empty" in resp_again.get_json()["error"].lower()
