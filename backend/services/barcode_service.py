"""Barcode lookup service using Open Food Facts API."""
import re
import os
import logging
from typing import Dict, Any, Tuple, Optional
import requests

logger = logging.getLogger("expirycare.barcode")


class BarcodeService:
    """Handles barcode queries against Open Food Facts API with caching and error handling."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or os.getenv("OPEN_FOOD_FACTS_BASE_URL", "https://world.openfoodfacts.org")).rstrip("/")

    def lookup_barcode(self, code: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str], int]:
        """Lookup a food product by 8-14 digit barcode.

        Returns (success, product_data, error_message, status_code).
        """
        clean_code = str(code).strip()
        if not re.match(r"^\d{8,14}$", clean_code):
            return False, None, "Enter a valid 8–14 digit barcode", 400

        url = f"{self.base_url}/api/v2/product/{clean_code}.json?fields=product_name,brands,categories,quantity,code"
        try:
            resp = requests.get(url, timeout=8, headers={"User-Agent": "ExpiryCare/2.0 - Student Project Integration"})
            if resp.status_code == 404:
                return False, None, "No matching food product was found. Try the label or manual entry.", 404
            if resp.status_code != 200:
                return False, None, "The product database is currently unavailable. You can enter details manually.", 503

            data = resp.json()
            if data.get("status") != 1 or not data.get("product"):
                return False, None, "No matching food product was found. Try the label or manual entry.", 404

            raw = data["product"]
            product_info = {
                "barcode": clean_code,
                "name": raw.get("product_name", ""),
                "brands": raw.get("brands", ""),
                "categories": raw.get("categories", ""),
                "quantity": raw.get("quantity", ""),
                "suggestedCategory": "grocery" if any(k in (raw.get("categories") or "").lower() for k in ["food", "beverage", "snack"]) else "other"
            }
            return True, product_info, None, 200

        except requests.Timeout:
            return False, None, "Barcode lookup timed out. Please enter details manually.", 504
        except Exception as exc:
            logger.warning("Barcode lookup error: %s", exc)
            return False, None, "The product database is currently unavailable. You can enter details manually.", 503
