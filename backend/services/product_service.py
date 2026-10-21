"""Product management service for ExpiryCare."""
import time
from typing import Dict, Any, List, Optional, Tuple
from backend.repositories.product_repository import ProductRepository
from backend.services.expiry_service import ExpiryService
from backend.utils.validators import validate_product_payload
from backend.utils.date_utils import (
    calculate_estimated_expiry,
    parse_date,
    to_input_date,
    get_today,
    get_status,
    get_status_label,
)


class ProductService:
    """Handles personal inventory CRUD, expiry enrichment, validation, and demo data loading."""

    def __init__(self, product_repo: Optional[ProductRepository] = None):
        self.product_repo = product_repo or ProductRepository()

    def create_product(self, user_id: str, data: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Validate and create a new product for a user."""
        is_valid, error = validate_product_payload(data)
        if not is_valid:
            return False, None, error

        entered_expiry = data.get("expiryDate") or ""
        mfg_date = data.get("manufacturingDate") or ""
        shelf_life_days = data.get("verifiedShelfLifeDays")
        shelf_life_source = data.get("shelfLifeSource", "").strip()

        estimated_expiry = ""
        if not entered_expiry and mfg_date and isinstance(shelf_life_days, int) and shelf_life_days > 0 and shelf_life_source:
            estimated_expiry = calculate_estimated_expiry(mfg_date, shelf_life_days) or ""

        saved_expiry = entered_expiry or estimated_expiry

        if entered_expiry:
            expiry_source = "user-confirmed"
        elif estimated_expiry:
            expiry_source = "estimated"
        else:
            expiry_source = "unknown"

        name = data.get("name", "").strip() or "Unidentified Product"
        category = data.get("category", "").strip().lower() or "other"

        if not name or name == "Unidentified Product":
            tracking_status = "unidentified"
        elif estimated_expiry:
            tracking_status = "estimated-expiry"
        elif not saved_expiry:
            tracking_status = "expiry-unknown"
        else:
            tracking_status = "verified-expiry"

        product_record = {
            "name": name,
            "category": category,
            "quantity": int(data.get("quantity", 1)),
            "notes": str(data.get("notes", "")).strip(),
            "purchaseDate": data.get("purchaseDate", ""),
            "batchNumber": str(data.get("batchNumber", "")).strip(),
            "manufacturingDate": mfg_date,
            "verifiedShelfLifeDays": shelf_life_days if estimated_expiry else None,
            "shelfLifeSource": shelf_life_source if estimated_expiry else "",
            "barcode": str(data.get("barcode", "")).strip(),
            "expiryDate": saved_expiry,
            "expirySource": expiry_source,
            "trackingStatus": tracking_status,
            "reviewReminderDate": data.get("reviewReminderDate", ""),
            "evidence": data.get("evidence", {
                "name": "user-entered" if name != "Unidentified Product" else "not-found",
                "expiry": expiry_source,
                "shelfLifeSource": shelf_life_source or "not-provided",
                "barcode": "lookup-input" if data.get("barcode") else "not-provided"
            })
        }

        created = self.product_repo.create(product_record, user_id)
        enriched = ExpiryService.enrich_product(created)
        return True, enriched, None

    def get_product(self, user_id: str, product_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a product by ID, verifying user ownership and enriching with live status."""
        product = self.product_repo.get_by_id(product_id, user_id=user_id)
        if not product:
            return None
        return ExpiryService.enrich_product(product)

    def list_products(
        self,
        user_id: str,
        category: Optional[str] = None,
        search_query: Optional[str] = None,
        sort_by: Optional[str] = "expiry-date"
    ) -> List[Dict[str, Any]]:
        """List and enrich all products owned by user_id."""
        raw_products = self.product_repo.list_by_user(
            user_id=user_id,
            category=category,
            search_query=search_query,
            sort_by=sort_by
        )
        return [ExpiryService.enrich_product(p) for p in raw_products]

    def update_product(self, user_id: str, product_id: str, updates: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Update an existing product owned by user_id."""
        is_valid, error = validate_product_payload(updates, is_update=True)
        if not is_valid:
            return False, None, error

        existing = self.product_repo.get_by_id(product_id, user_id=user_id)
        if not existing:
            return False, None, "Product not found or access denied"

        # If expiry date changed, adjust tracking status
        if "expiryDate" in updates:
            exp = updates["expiryDate"]
            if exp:
                updates.setdefault("expirySource", "user-confirmed")
                updates.setdefault("trackingStatus", "verified-expiry")
            else:
                updates.setdefault("expirySource", "unknown")
                updates.setdefault("trackingStatus", "expiry-unknown")

        updated = self.product_repo.update(product_id, user_id, updates)
        if not updated:
            return False, None, "Failed to update product"

        enriched = ExpiryService.enrich_product(updated)
        return True, enriched, None

    def delete_product(self, user_id: str, product_id: str) -> bool:
        """Delete a product owned by user_id."""
        return self.product_repo.delete(product_id, user_id=user_id)

    def load_demo_data(self, user_id: str) -> Tuple[bool, List[Dict[str, Any]], str]:
        """Seed initial inventory with standard demo products if empty."""
        existing = self.product_repo.list_by_user(user_id)
        if len(existing) > 0:
            return False, [], "Demo data is only loaded when inventory is empty"

        today = get_today()
        from datetime import timedelta

        def in_days(n: int) -> str:
            return to_input_date(today + timedelta(days=n))

        rows = [
            ("Paracetamol 500mg", "medicine", 1, 3),
            ("Cough Syrup", "medicine", 1, -5),
            ("Vitamin C Tablets", "medicine", 2, 210),
            ("Antiseptic Solution", "medicine", 1, 14),
            ("Milk (1 litre)", "grocery", 2, 2),
            ("Packaged Noodles", "grocery", 6, 120),
            ("Brown Bread", "grocery", 1, -2),
            ("Face Cream", "personal-care", 1, 20),
            ("Sunscreen SPF 50", "personal-care", 1, 75),
            ("First-Aid Bandages", "other", 3, 400)
        ]

        demo_records = []
        for index, row in enumerate(rows):
            demo_records.append({
                "id": f"product_demo_{int(time.time() * 1000) + index}",
                "name": row[0],
                "category": row[1],
                "quantity": row[2],
                "notes": "Demo record — example data.",
                "purchaseDate": in_days(-60),
                "expiryDate": in_days(row[3]),
                "batchNumber": "",
                "isDemo": True
            })

        created = self.product_repo.bulk_create(demo_records, user_id)
        enriched = [ExpiryService.enrich_product(p) for p in created]
        return True, enriched, f"Loaded {len(enriched)} demo products successfully"
