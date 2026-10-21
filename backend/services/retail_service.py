"""Retail Intelligence and Retail Catalog service for ExpiryCare.

Implements deterministic inventory rules:
- FEFO (First Expired, First Out) ordering
- Clearance discount recommendations based on shelf-life and local demand surplus
- Multi-branch transfer state machine with atomic stock reservation and movement
- Customer-facing store availability calculations excluding unverified/expired/reserved stock
"""
import math
from datetime import datetime, timezone, date
from typing import Dict, Any, List, Optional, Tuple
from backend.repositories.retail_repository import RetailRepository
from backend.utils.date_utils import parse_date, get_today


class RetailService:
    """Business logic for Retail Intelligence and Store Catalog."""

    def __init__(self, retail_repo: Optional[RetailRepository] = None):
        self.retail_repo = retail_repo or RetailRepository()

    def days_to_expiry(self, batch: Dict[str, Any], relative_to: Optional[date] = None) -> Optional[int]:
        """Calculate days to expiry for a batch.

        Returns None if expiryDate is missing or verification is not 'Verified'.
        """
        if not batch or not batch.get("expiryDate") or batch.get("verification") != "Verified":
            return None
        target = parse_date(batch.get("expiryDate"))
        if not target:
            return None
        ref = relative_to or get_today()
        return (target - ref).days

    def is_eligible(self, batch: Dict[str, Any], relative_to: Optional[date] = None) -> bool:
        """A batch is eligible for sale/transfer if verified, unexpired, and has free stock."""
        d = self.days_to_expiry(batch, relative_to)
        if d is None or d < 0:
            return False
        available = int(batch.get("available", 0))
        reserved = int(batch.get("reserved", 0))
        return (available - reserved) > 0

    def get_summary(self) -> Dict[str, Any]:
        """Compute top-level summary metrics across branches and batches."""
        branches = self.retail_repo.get_branches(active_only=True)
        products = self.retail_repo.get_products()
        batches = self.retail_repo.get_batches()
        transfers = self.retail_repo.get_transfers()

        at_risk_units = 0
        expired_units = 0
        unknown_batches = 0
        total_available = 0

        for b in batches:
            avail = int(b.get("available", 0))
            res = int(b.get("reserved", 0))
            free = max(0, avail - res)
            total_available += avail

            d = self.days_to_expiry(b)
            if d is None:
                unknown_batches += 1
            elif d < 0:
                expired_units += avail
            elif d <= 7:
                at_risk_units += free

        pending_transfers = len([t for t in transfers if t.get("status") in ("Requested", "Approved", "Dispatched", "Received")])
        completed_transfers = len([t for t in transfers if t.get("status") == "Completed"])

        return {
            "activeBranchesCount": len(branches),
            "productsCount": len(products),
            "batchesCount": len(batches),
            "totalAvailableUnits": total_available,
            "unitsAtRisk": at_risk_units,
            "expiredUnits": expired_units,
            "unknownBatchesCount": unknown_batches,
            "transfersPending": pending_transfers,
            "transfersCompleted": completed_transfers
        }

    def list_batches(self, branch_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List batches enriched with FEFO order and status."""
        batches = self.retail_repo.get_batches(branch_id=branch_id)
        products_map = {p["id"]: p for p in self.retail_repo.get_products()}
        branches_map = {b["id"]: b for b in self.retail_repo.get_branches(active_only=False)}

        enriched = []
        for b in batches:
            item = b.copy()
            d = self.days_to_expiry(b)
            item["daysRemaining"] = d
            item["isEligible"] = self.is_eligible(b)
            item["product"] = products_map.get(b.get("productId"), {"name": "Unknown product"})
            item["branch"] = branches_map.get(b.get("branchId"), {"name": "Unknown branch"})
            enriched.append(item)

        # Sort: verified earliest expiry first, then unknown/unverified
        def sort_key(x):
            d = x["daysRemaining"]
            return (1 if d is None else 0, d if d is not None else 999999)

        enriched.sort(key=sort_key)

        # Assign FEFO first flags
        for item in enriched:
            p_id = item.get("productId")
            if item["isEligible"]:
                eligible_for_prod = [x for x in enriched if x.get("productId") == p_id and x["isEligible"]]
                item["isFefoFirst"] = bool(eligible_for_prod and eligible_for_prod[0]["id"] == item["id"])
            else:
                item["isFefoFirst"] = False

        return enriched

    def generate_clearance_recommendations(self) -> List[Dict[str, Any]]:
        """Compute clearance suggestions for batches with surplus beyond local demand."""
        batches = self.retail_repo.get_batches()
        existing_records = {c["id"]: c for c in self.retail_repo.get_clearance_records()}
        recommendations = []

        for b in batches:
            d = self.days_to_expiry(b)
            if d is None or d < 0 or d > 14 or not self.is_eligible(b):
                continue

            available = int(b.get("available", 0))
            reserved = int(b.get("reserved", 0))
            free = max(0, available - reserved)
            daily_demand = float(b.get("dailyDemand") or 0)
            demand_surplus = max(0, free - math.ceil(daily_demand * max(d, 0)))

            discount = 25 if d <= 6 else 15
            cid = f"cl-{b['id']}"
            old = existing_records.get(cid)

            if demand_surplus > 0:
                rec = {
                    "id": cid,
                    "batchId": b["id"],
                    "productId": b.get("productId"),
                    "branchId": b.get("branchId"),
                    "discount": discount,
                    "surplus": demand_surplus,
                    "reason": f"{demand_surplus} units estimated beyond local demand before expiry ({b.get('demandSource', 'demo estimate')}).",
                    "status": old.get("status", "Suggested") if old else "Suggested",
                    "createdAt": old.get("createdAt") if old else datetime.now(timezone.utc).isoformat()
                }
                self.retail_repo.save_clearance_record(rec)
                recommendations.append(rec)

        return recommendations

    def review_clearance(self, clearance_id: str, new_status: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Approve or reject a clearance suggestion."""
        if new_status not in ("Approved", "Rejected"):
            return False, None, "Status must be 'Approved' or 'Rejected'"
        updated = self.retail_repo.update_clearance_status(clearance_id, new_status)
        if not updated:
            return False, None, "Clearance record not found"
        self.retail_repo.log_event("clearance-" + new_status.lower(), clearance_id, "Manager review")
        return True, updated, None

    def create_transfer(self, batch_id: str, destination_id: str, qty: int) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Create a transfer request between branches."""
        batch = self.retail_repo.get_batch_by_id(batch_id)
        if not batch or not isinstance(qty, int) or qty < 1:
            return False, None, "Choose a valid batch and a whole-number quantity of 1 or more"

        if batch.get("branchId") == destination_id:
            return False, None, "Source and destination branches must differ"

        if not self.is_eligible(batch):
            return False, None, "Only available stock with verified, unexpired expiry can be transferred"

        free_stock = int(batch.get("available", 0)) - int(batch.get("reserved", 0))
        if qty > free_stock:
            return False, None, "Quantity exceeds unreserved available stock"

        # Check for active pending transfers
        pending_transfers = self.retail_repo.get_transfers()
        for t in pending_transfers:
            if (t.get("batchId") == batch_id and
                t.get("destinationId") == destination_id and
                t.get("status") in ("Requested", "Approved", "Dispatched", "Received")):
                return False, None, "A pending transfer already exists for this batch and destination"

        import time
        now_iso = datetime.now(timezone.utc).isoformat()
        transfer_id = f"tr-{int(time.time() * 1000)}"
        transfer = {
            "id": transfer_id,
            "batchId": batch_id,
            "productId": batch.get("productId"),
            "sourceId": batch.get("branchId"),
            "destinationId": destination_id,
            "qty": qty,
            "status": "Requested",
            "createdAt": now_iso,
            "history": [{"status": "Requested", "at": now_iso}]
        }

        self.retail_repo.create_transfer(transfer)
        self.retail_repo.log_event("transfer-requested", transfer_id, f"{qty} units")
        return True, transfer, None

    def transition_transfer(self, transfer_id: str, action: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Execute a state transition on a transfer request."""
        transfer = self.retail_repo.get_transfer_by_id(transfer_id)
        if not transfer:
            return False, None, "Transfer not found"

        batch = self.retail_repo.get_batch_by_id(transfer.get("batchId"))
        if not batch:
            return False, None, "Referenced batch not found"

        transition_map = {
            "Approve": ("Requested", "Approved"),
            "Rejected": ("Requested", "Rejected"),
            "Cancel": ("Approved", "Cancelled"),
            "Dispatch": ("Approved", "Dispatched"),
            "Receive": ("Dispatched", "Received"),
            "Complete": ("Received", "Completed")
        }

        if action not in transition_map:
            return False, None, f"Unknown action: {action}"

        expected_initial, next_status = transition_map[action]
        current_status = transfer.get("status")
        if current_status != expected_initial:
            return False, None, f"Invalid transition: cannot '{action}' from status '{current_status}'"

        qty = int(transfer.get("qty", 0))

        if action == "Approve":
            free_stock = int(batch.get("available", 0)) - int(batch.get("reserved", 0))
            if not self.is_eligible(batch) or qty > free_stock:
                return False, None, "Stock is no longer eligible or available"
            batch["reserved"] = int(batch.get("reserved", 0)) + qty
            self.retail_repo.update_batch(batch["id"], {"reserved": batch["reserved"]})

        elif action in ("Rejected", "Cancel"):
            if current_status == "Approved":
                batch["reserved"] = max(0, int(batch.get("reserved", 0)) - qty)
                self.retail_repo.update_batch(batch["id"], {"reserved": batch["reserved"]})

        elif action == "Dispatch":
            avail = int(batch.get("available", 0))
            res = int(batch.get("reserved", 0))
            if res < qty or avail < qty:
                return False, None, "Reserved stock is insufficient for dispatch"
            batch["available"] = avail - qty
            batch["reserved"] = res - qty
            self.retail_repo.update_batch(batch["id"], {"available": batch["available"], "reserved": batch["reserved"]})
            transfer["dispatchedQty"] = qty
            transfer["dispatchedAt"] = datetime.now(timezone.utc).isoformat()

        elif action == "Receive":
            transfer["receivedQty"] = transfer.get("dispatchedQty", qty)
            transfer["receivedAt"] = datetime.now(timezone.utc).isoformat()
            dest_id = transfer.get("destinationId")

            # Check if matching batch already exists at destination
            dest_batches = self.retail_repo.get_batches(branch_id=dest_id, product_id=transfer.get("productId"))
            matching = None
            for db in dest_batches:
                if db.get("expiryDate") == batch.get("expiryDate") and db.get("verification") == batch.get("verification"):
                    matching = db
                    break

            if matching:
                matching["available"] = int(matching.get("available", 0)) + qty
                matching["received"] = int(matching.get("received", 0)) + qty
                self.retail_repo.update_batch(matching["id"], {"available": matching["available"], "received": matching["received"]})
            else:
                new_batch = batch.copy()
                new_batch["id"] = f"ba-xfer-{transfer_id}"
                new_batch["branchId"] = dest_id
                new_batch["lot"] = f"{batch.get('lot', 'LOT')}-XFER"
                new_batch["available"] = qty
                new_batch["received"] = qty
                new_batch["reserved"] = 0
                new_batch["createdFromTransfer"] = transfer_id
                self.retail_repo.save_batch(new_batch)

        transfer["status"] = next_status
        history = transfer.get("history", [])
        history.append({"status": next_status, "at": datetime.now(timezone.utc).isoformat()})
        transfer["history"] = history
        self.retail_repo.update_transfer(transfer_id, transfer)
        self.retail_repo.log_event(f"transfer-{next_status.lower()}", transfer_id, f"{action} applied")

        return True, transfer, None

    def get_customer_catalog(self, search_query: Optional[str] = None, branch_id: Optional[str] = "all", status_filter: Optional[str] = "all") -> List[Dict[str, Any]]:
        """Public store catalog availability view matching retail-catalog.html."""
        products = self.retail_repo.get_products()
        branches = self.retail_repo.get_branches(active_only=True)
        batches = self.retail_repo.get_batches()

        q = (search_query or "").strip().lower()
        rows = []

        filtered_products = [p for p in products if q in str(p.get("name", "")).lower()]

        for p in filtered_products:
            for br in branches:
                if branch_id and branch_id != "all" and br["id"] != branch_id:
                    continue

                branch_batches = [
                    b for b in batches
                    if b.get("productId") == p["id"] and b.get("branchId") == br["id"]
                ]

                # Count only verified, unexpired stock minus reservations
                units = 0
                for b in branch_batches:
                    if self.is_eligible(b):
                        free = max(0, int(b.get("available", 0)) - int(b.get("reserved", 0)))
                        units += free

                if units == 0:
                    state = "Out of stock"
                elif units <= 5:
                    state = "Low stock"
                else:
                    state = "In stock"

                if status_filter and status_filter != "all" and state != status_filter:
                    continue

                rows.append({
                    "product": p,
                    "branch": br,
                    "units": units,
                    "state": state
                })

        return rows
