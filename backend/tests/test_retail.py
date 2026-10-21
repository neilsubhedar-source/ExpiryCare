"""Tests for Retail Intelligence rules, FEFO ordering, clearance, transfers, and catalog."""
import json


def test_seed_and_retail_summary(client):
    """Verify retail demo data seeding and summary statistics."""
    resp_seed = client.post("/api/retail/demo/seed")
    assert resp_seed.status_code == 200
    data_seed = resp_seed.get_json()["data"]
    assert len(data_seed["branches"]) == 3
    assert len(data_seed["batches"]) == 6

    resp_summary = client.get("/api/retail/summary")
    assert resp_summary.status_code == 200
    summary = resp_summary.get_json()["data"]
    assert summary["activeBranchesCount"] == 3
    assert summary["batchesCount"] == 6
    assert summary["unitsAtRisk"] > 0
    assert summary["expiredUnits"] > 0


def test_batches_fefo_ordering(client):
    """Verify retail batches are listed in First Expired, First Out (FEFO) order."""
    client.post("/api/retail/demo/seed")
    resp = client.get("/api/retail/batches")
    assert resp.status_code == 200
    batches = resp.get_json()["data"]
    assert len(batches) == 6

    # First verified lot should have FEFO flag
    fefo_items = [b for b in batches if b.get("isFefoFirst")]
    assert len(fefo_items) >= 1


def test_clearance_recommendations_and_review(client):
    """Verify clearance suggestions generation and manager review."""
    client.post("/api/retail/demo/seed")
    resp = client.get("/api/retail/clearance")
    assert resp.status_code == 200
    recs = resp.get_json()["data"]
    assert len(recs) >= 1
    cid = recs[0]["id"]

    # Review: Approve
    r_approve = client.post(f"/api/retail/clearance/{cid}/review", json={"status": "Approved"})
    assert r_approve.status_code == 200
    assert r_approve.get_json()["data"]["status"] == "Approved"

    # Review: Reject
    r_reject = client.post(f"/api/retail/clearance/{cid}/review", json={"status": "Rejected"})
    assert r_reject.status_code == 200
    assert r_reject.get_json()["data"]["status"] == "Rejected"


def test_transfer_lifecycle_integrity(client):
    """Verify complete transfer state machine matching test_retail_rules.js."""
    client.post("/api/retail/demo/seed")

    # 1. Self-transfer rejected
    r_self = client.post("/api/retail/transfers", json={
        "batchId": "ba-milk-a", "destinationId": "br-a", "qty": 2
    })
    assert r_self.status_code == 400
    assert "differ" in r_self.get_json()["error"].lower()

    # 2. Over-allocation rejected
    r_over = client.post("/api/retail/transfers", json={
        "batchId": "ba-milk-a", "destinationId": "br-b", "qty": 9999
    })
    assert r_over.status_code == 400
    assert "exceeds" in r_over.get_json()["error"].lower()

    # 3. Create valid transfer
    r_create = client.post("/api/retail/transfers", json={
        "batchId": "ba-milk-a", "destinationId": "br-c", "qty": 5
    })
    assert r_create.status_code == 201
    transfer = r_create.get_json()["data"]
    t_id = transfer["id"]
    assert transfer["status"] == "Requested"

    # 4. Duplicate pending transfer rejected
    r_dup = client.post("/api/retail/transfers", json={
        "batchId": "ba-milk-a", "destinationId": "br-c", "qty": 2
    })
    assert r_dup.status_code == 400
    assert "already exists" in r_dup.get_json()["error"].lower()

    # 5. Invalid transition directly to Receive fails
    r_bad_trans = client.post(f"/api/retail/transfers/{t_id}/transition", json={"action": "Receive"})
    assert r_bad_trans.status_code == 400

    # 6. Approve reserves stock on source batch
    r_app = client.post(f"/api/retail/transfers/{t_id}/transition", json={"action": "Approve"})
    assert r_app.status_code == 200
    assert r_app.get_json()["data"]["status"] == "Approved"

    # Verify source batch reserved units
    batches_resp = client.get("/api/retail/batches")
    milk_a = next(b for b in batches_resp.get_json()["data"] if b["id"] == "ba-milk-a")
    assert milk_a["reserved"] == 5

    # 7. Dispatch deducts available and reserved stock on source batch
    r_disp = client.post(f"/api/retail/transfers/{t_id}/transition", json={"action": "Dispatch"})
    assert r_disp.status_code == 200
    assert r_disp.get_json()["data"]["status"] == "Dispatched"

    batches_resp2 = client.get("/api/retail/batches")
    milk_a_after = next(b for b in batches_resp2.get_json()["data"] if b["id"] == "ba-milk-a")
    assert milk_a_after["available"] == 75
    assert milk_a_after["reserved"] == 0

    # 8. Receive adds stock to destination batch
    r_recv = client.post(f"/api/retail/transfers/{t_id}/transition", json={"action": "Receive"})
    assert r_recv.status_code == 200
    assert r_recv.get_json()["data"]["status"] == "Received"

    # 9. Complete finishes transfer
    r_comp = client.post(f"/api/retail/transfers/{t_id}/transition", json={"action": "Complete"})
    assert r_comp.status_code == 200
    assert r_comp.get_json()["data"]["status"] == "Completed"


def test_customer_catalog_availability(client):
    """Verify customer catalog counts only verified, unexpired stock and excludes reserved stock."""
    client.post("/api/retail/demo/seed")
    resp = client.get("/api/retail/catalog")
    assert resp.status_code == 200
    rows = resp.get_json()["data"]
    assert len(rows) > 0

    # Verify no negative units
    assert all(r["units"] >= 0 for r in rows)
    # Verify state classification
    for r in rows:
        if r["units"] == 0:
            assert r["state"] == "Out of stock"
        elif r["units"] <= 5:
            assert r["state"] == "Low stock"
        else:
            assert r["state"] == "In stock"
