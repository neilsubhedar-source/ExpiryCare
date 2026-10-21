"""Payload and data validation utilities for ExpiryCare API."""
import re
from typing import Tuple, Optional, Dict, Any
from backend.utils.date_utils import parse_date

EMAIL_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
ALLOWED_CATEGORIES = {"medicine", "grocery", "personal-care", "other"}


def is_valid_email(email: Optional[str]) -> bool:
    """Validate standard email format."""
    if not email or not isinstance(email, str):
        return False
    return bool(EMAIL_REGEX.match(email.strip()))


def validate_product_payload(data: Dict[str, Any], is_update: bool = False) -> Tuple[bool, Optional[str]]:
    """Validate incoming product JSON payload.

    Returns (is_valid, error_message).
    """
    if not isinstance(data, dict):
        return False, "Request body must be a JSON object"

    # For new products: name and category are checked
    name = str(data.get("name", "")).strip()
    if not is_update:
        # Default name allowed if empty per frontend ("Unidentified Product")
        pass
    else:
        if "name" in data and not name:
            return False, "Product name cannot be empty"

    if "category" in data:
        cat = str(data.get("category", "")).strip().lower()
        if cat and cat not in ALLOWED_CATEGORIES:
            return False, f"Invalid category '{cat}'. Allowed: {', '.join(sorted(ALLOWED_CATEGORIES))}"

    if "quantity" in data:
        qty = data.get("quantity")
        try:
            qty_int = int(qty)
            if qty_int < 1:
                return False, "Quantity must be a positive whole number (1 or more)"
        except (ValueError, TypeError):
            return False, "Quantity must be an integer"

    purchase_str = data.get("purchaseDate")
    expiry_str = data.get("expiryDate")

    if purchase_str:
        p_date = parse_date(purchase_str)
        if not p_date:
            return False, "Invalid purchaseDate format; use 'YYYY-MM-DD'"
    else:
        p_date = None

    if expiry_str:
        e_date = parse_date(expiry_str)
        if not e_date:
            return False, "Invalid expiryDate format; use 'YYYY-MM-DD'"
    else:
        e_date = None

    if p_date and e_date and e_date < p_date:
        return False, "Expiry date cannot be before the purchase date"

    return True, None


def validate_transfer_payload(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validate retail transfer creation payload."""
    if not isinstance(data, dict):
        return False, "Request body must be a JSON object"

    batch_id = str(data.get("batchId", "")).strip()
    if not batch_id:
        return False, "batchId is required"

    dest_id = str(data.get("destinationId", "")).strip()
    if not dest_id:
        return False, "destinationId is required"

    qty = data.get("qty")
    if qty is None:
        return False, "Quantity is required"
    try:
        qty_int = int(qty)
        if qty_int < 1:
            return False, "Quantity must be a whole number of 1 or more"
    except (ValueError, TypeError):
        return False, "Quantity must be an integer"

    return True, None


def validate_chat_payload(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validate healthcare chatbot message payload."""
    if not isinstance(data, dict):
        return False, "Request body must be a JSON object"

    msg = str(data.get("message", "")).strip()
    if not msg:
        return False, "message is required"
    if len(msg) > 2000:
        return False, "Message exceeds 2000 character limit"

    return True, None


def validate_image_payload(data: Dict[str, Any], max_bytes: int = 9 * 1024 * 1024) -> Tuple[bool, Optional[str]]:
    """Validate product label OCR image payload."""
    if not isinstance(data, dict):
        return False, "Request body must be a JSON object"

    image_data = data.get("imageData")
    if not isinstance(image_data, str) or not image_data.startswith("data:image/"):
        return False, "imageData must be an image data URL starting with 'data:image/'"

    if len(image_data) > max_bytes:
        return False, "Image size exceeds limit of 9 MB"

    return True, None
