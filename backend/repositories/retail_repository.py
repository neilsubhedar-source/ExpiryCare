"""Retail Intelligence repository for Firestore database operations.

Persists retail branches, batches, clearance suggestions, transfers, and inventory events.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from backend.repositories.base import BaseRepository
from backend.extensions import get_firestore


class RetailRepository:
    """Manages Firestore collections for Retail Intelligence:
    - retail_branches
    - retail_products
    - retail_batches
    - retail_clearance
    - retail_transfers
    - retail_events
    """

    def __init__(self):
        self.db = get_firestore()
        self.branches_col = self.db.collection("retail_branches")
        self.products_col = self.db.collection("retail_products")
        self.batches_col = self.db.collection("retail_batches")
        self.clearance_col = self.db.collection("retail_clearance")
        self.transfers_col = self.db.collection("retail_transfers")
        self.events_col = self.db.collection("retail_events")

    # Branches
    def get_branches(self, active_only: bool = True) -> List[Dict[str, Any]]:
        query = self.branches_col
        if active_only:
            query = query.where("active", "==", True)
        return [doc.to_dict() for doc in query.stream()]

    def get_branch_by_id(self, branch_id: str) -> Optional[Dict[str, Any]]:
        doc = self.branches_col.document(branch_id).get()
        return doc.to_dict() if doc.exists else None

    def save_branch(self, branch_data: Dict[str, Any]) -> Dict[str, Any]:
        self.branches_col.document(branch_data["id"]).set(branch_data)
        return branch_data

    # Products
    def get_products(self) -> List[Dict[str, Any]]:
        return [doc.to_dict() for doc in self.products_col.stream()]

    def get_product_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        doc = self.products_col.document(product_id).get()
        return doc.to_dict() if doc.exists else None

    def save_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        self.products_col.document(product_data["id"]).set(product_data)
        return product_data

    # Batches
    def get_batches(self, branch_id: Optional[str] = None, product_id: Optional[str] = None) -> List[Dict[str, Any]]:
        query = self.batches_col
        if branch_id:
            query = query.where("branchId", "==", branch_id)
        if product_id:
            query = query.where("productId", "==", product_id)
        return [doc.to_dict() for doc in query.stream()]

    def get_batch_by_id(self, batch_id: str) -> Optional[Dict[str, Any]]:
        doc = self.batches_col.document(batch_id).get()
        return doc.to_dict() if doc.exists else None

    def save_batch(self, batch_data: Dict[str, Any]) -> Dict[str, Any]:
        self.batches_col.document(batch_data["id"]).set(batch_data)
        return batch_data

    def update_batch(self, batch_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        batch = self.get_batch_by_id(batch_id)
        if not batch:
            return None
        self.batches_col.document(batch_id).update(updates)
        batch.update(updates)
        return batch

    # Clearance
    def get_clearance_records(self) -> List[Dict[str, Any]]:
        return [doc.to_dict() for doc in self.clearance_col.stream()]

    def get_clearance_by_id(self, clearance_id: str) -> Optional[Dict[str, Any]]:
        doc = self.clearance_col.document(clearance_id).get()
        return doc.to_dict() if doc.exists else None

    def save_clearance_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        self.clearance_col.document(record["id"]).set(record)
        return record

    def update_clearance_status(self, clearance_id: str, status: str) -> Optional[Dict[str, Any]]:
        rec = self.get_clearance_by_id(clearance_id)
        if not rec:
            return None
        updates = {"status": status, "reviewedAt": datetime.now(timezone.utc).isoformat()}
        self.clearance_col.document(clearance_id).update(updates)
        rec.update(updates)
        return rec

    # Transfers
    def get_transfers(self) -> List[Dict[str, Any]]:
        return [doc.to_dict() for doc in self.transfers_col.stream()]

    def get_transfer_by_id(self, transfer_id: str) -> Optional[Dict[str, Any]]:
        doc = self.transfers_col.document(transfer_id).get()
        return doc.to_dict() if doc.exists else None

    def create_transfer(self, transfer_data: Dict[str, Any]) -> Dict[str, Any]:
        self.transfers_col.document(transfer_data["id"]).set(transfer_data)
        return transfer_data

    def update_transfer(self, transfer_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        transfer = self.get_transfer_by_id(transfer_id)
        if not transfer:
            return None
        self.transfers_col.document(transfer_id).update(updates)
        transfer.update(updates)
        return transfer

    # Events
    def log_event(self, event_type: str, record_id: str, detail: str) -> Dict[str, Any]:
        import time, uuid
        event = {
            "id": f"ev-{int(time.time() * 1000)}-{uuid.uuid4().hex[:5]}",
            "type": event_type,
            "recordId": record_id,
            "detail": detail,
            "at": datetime.now(timezone.utc).isoformat()
        }
        self.events_col.document(event["id"]).set(event)
        return event

    # Demo seeding
    def seed_demo_data(self) -> Dict[str, Any]:
        """Seed retail database with the standard demo branches, products, and batches."""
        today = datetime.now(timezone.utc).date()

        def date_in(n: int) -> str:
            return (today + timedelta(days=n)).strftime("%Y-%m-%d")

        branches = [
            {"id": "br-a", "name": "Store A", "code": "A-101", "location": "Central market", "active": True},
            {"id": "br-b", "name": "Store B", "code": "B-202", "location": "North district", "active": True},
            {"id": "br-c", "name": "Store C", "code": "C-303", "location": "South district", "active": True}
        ]
        products = [
            {"id": "p-milk", "name": "Milk 500 ml", "category": "grocery", "price": 30, "cost": 22},
            {"id": "p-yogurt", "name": "Yogurt cup", "category": "grocery", "price": 25, "cost": 16},
            {"id": "p-juice", "name": "Orange juice 1 L", "category": "grocery", "price": 90, "cost": 60}
        ]
        batches = [
            {"id": "ba-milk-a", "productId": "p-milk", "branchId": "br-a", "lot": "ML-A1", "received": 80, "available": 80, "reserved": 0, "expiryDate": date_in(4), "verification": "Verified", "evidence": "Demo label confirmed", "dailyDemand": 10, "demandSource": "Synthetic demo estimate"},
            {"id": "ba-milk-b", "productId": "p-milk", "branchId": "br-b", "lot": "ML-B1", "received": 12, "available": 12, "reserved": 0, "expiryDate": date_in(12), "verification": "Verified", "evidence": "Demo label confirmed", "dailyDemand": 9, "demandSource": "Synthetic demo estimate"},
            {"id": "ba-milk-c", "productId": "p-milk", "branchId": "br-c", "lot": "ML-C1", "received": 24, "available": 24, "reserved": 0, "expiryDate": date_in(38), "verification": "Verified", "evidence": "Demo label confirmed", "dailyDemand": 6, "demandSource": "Synthetic demo estimate"},
            {"id": "ba-yogurt-a", "productId": "p-yogurt", "branchId": "br-a", "lot": "YG-A1", "received": 25, "available": 25, "reserved": 0, "expiryDate": date_in(-2), "verification": "Verified", "evidence": "Demo label confirmed", "dailyDemand": 5, "demandSource": "Synthetic demo estimate"},
            {"id": "ba-juice-a", "productId": "p-juice", "branchId": "br-a", "lot": "OJ-A1", "received": 20, "available": 20, "reserved": 0, "expiryDate": None, "verification": "Needs Verification", "evidence": "Expiry not recorded", "dailyDemand": 2, "demandSource": "Synthetic demo estimate"},
            {"id": "ba-juice-b", "productId": "p-juice", "branchId": "br-b", "lot": "OJ-B1", "received": 6, "available": 6, "reserved": 0, "expiryDate": date_in(9), "verification": "Verified", "evidence": "Demo label confirmed", "dailyDemand": 4, "demandSource": "Synthetic demo estimate"}
        ]

        for b in branches:
            self.save_branch(b)
        for p in products:
            self.save_product(p)
        for ba in batches:
            self.save_batch(ba)

        return {"branches": branches, "products": products, "batches": batches, "demo": True}
