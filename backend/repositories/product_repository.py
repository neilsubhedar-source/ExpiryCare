"""Product repository for Firestore database operations."""
import time
from typing import Optional, Dict, Any, List
from backend.repositories.base import BaseRepository
from backend.utils.date_utils import get_status


class ProductRepository(BaseRepository):
    """Handles CRUD operations for personal inventory products in Firestore.

    Enforces strict user ownership checks to ensure users only access their own products.
    """

    def __init__(self):
        super().__init__("products")

    def create(self, product_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Save a new product associated with the specified user."""
        product_id = product_data.get("id")
        if not product_id:
            product_id = f"product_{int(time.time() * 1000)}"
            product_data["id"] = product_id

        product_data["userId"] = user_id
        product_data.setdefault("createdAt", int(time.time() * 1000))
        product_data.setdefault("updatedAt", int(time.time() * 1000))
        product_data.setdefault("notes", "")
        product_data.setdefault("batchNumber", "")
        product_data.setdefault("purchaseDate", "")
        product_data.setdefault("expiryDate", "")

        self.collection.document(product_id).set(product_data)
        return product_data

    def get_by_id(self, product_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieve a product by ID, verifying ownership if user_id is provided."""
        if not product_id:
            return None
        doc = self.collection.document(product_id).get()
        if not doc.exists:
            return None
        data = doc.to_dict()
        if user_id and data.get("userId") != user_id:
            # Unauthorized access to another user's product
            return None
        return data

    def list_by_user(
        self,
        user_id: str,
        category: Optional[str] = None,
        search_query: Optional[str] = None,
        sort_by: Optional[str] = "expiry-date"
    ) -> List[Dict[str, Any]]:
        """Retrieve all products for a user with optional category and search filtering."""
        if not user_id:
            return []

        query = self.collection.where("userId", "==", user_id)
        products = [doc.to_dict() for doc in query.stream()]

        # Filter by category if specified
        if category and category.lower() != "all":
            cat_clean = category.strip().lower()
            products = [p for p in products if str(p.get("category", "")).lower() == cat_clean]

        # Filter by search query if specified (search name, notes, batchNumber)
        if search_query:
            q = search_query.strip().lower()
            products = [
                p for p in products
                if q in str(p.get("name", "")).lower()
                or q in str(p.get("notes", "")).lower()
                or q in str(p.get("batchNumber", "")).lower()
            ]

        # Sort products
        if sort_by == "name":
            products.sort(key=lambda p: str(p.get("name", "")).lower())
        elif sort_by == "date-added":
            products.sort(key=lambda p: p.get("createdAt", 0), reverse=True)
        else:
            # Default: sort by expiry date (earliest first; missing expiry at the end)
            def expiry_sort_key(p):
                exp = p.get("expiryDate") or ""
                return (0 if exp else 1, exp)
            products.sort(key=expiry_sort_key)

        return products

    def update(self, product_id: str, user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing product owned by user_id."""
        product = self.get_by_id(product_id, user_id=user_id)
        if not product:
            return None

        # Prevent overriding critical ownership fields
        updates.pop("userId", None)
        updates.pop("id", None)
        updates["updatedAt"] = int(time.time() * 1000)

        self.collection.document(product_id).update(updates)
        product.update(updates)
        return product

    def delete(self, product_id: str, user_id: str) -> bool:
        """Delete a product owned by user_id."""
        product = self.get_by_id(product_id, user_id=user_id)
        if not product:
            return False
        self.collection.document(product_id).delete()
        return True

    def bulk_create(self, products_list: List[Dict[str, Any]], user_id: str) -> List[Dict[str, Any]]:
        """Bulk create products (used for demo data loading or migrations)."""
        created = []
        for p in products_list:
            res = self.create(p, user_id)
            created.append(res)
        return created
