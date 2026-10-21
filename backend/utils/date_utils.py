"""Date and expiry calculation utilities for ExpiryCare.

Faithfully implements the exact status rules from ExpiryCare frontend:
- Expired: date passed (< 0 days remaining)
- Expiring Soon: 30 days or fewer left (0 to 30 days remaining)
- Active: more than 30 days left (> 30 days remaining)
- Special statuses:
  - 'unidentified': product name missing or 'Unidentified Product'
  - 'expiry-unknown': missing expiry date
  - 'estimated-expiry': estimated from manufacturing date + shelf life
  - 'needs-verification': unconfirmed or ambiguous expiry
"""
from datetime import date, datetime, timedelta
from typing import Optional, Dict, Any

SOON_LIMIT_DAYS = 30


def get_today() -> date:
    """Return today's date in local system time."""
    return date.today()


def parse_date(date_string: Optional[str]) -> Optional[date]:
    """Parse a 'YYYY-MM-DD' date string into a datetime.date object."""
    if not date_string or not isinstance(date_string, str):
        return None
    cleaned = date_string.strip()
    if not cleaned:
        return None
    try:
        # Standard ISO YYYY-MM-DD format
        return datetime.strptime(cleaned[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def to_input_date(d: Optional[date]) -> str:
    """Format a date object as 'YYYY-MM-DD'."""
    if not d:
        return ""
    if isinstance(d, datetime):
        d = d.date()
    return d.strftime("%Y-%m-%d")


def get_days_from_date(date_string: Optional[str], relative_to: Optional[date] = None) -> Optional[int]:
    """Calculate the whole number of calendar days from reference date to target date.

    If target is in the past: returns negative integer.
    If target is today: returns 0.
    If target is in the future: returns positive integer.
    """
    target = parse_date(date_string)
    if not target:
        return None
    reference = relative_to or get_today()
    delta = target - reference
    return delta.days


def get_days_remaining(product: Dict[str, Any], relative_to: Optional[date] = None) -> Optional[int]:
    """Calculate remaining days for a product based on its expiryDate."""
    if not product or not isinstance(product, dict):
        return None
    expiry_str = product.get("expiryDate") or product.get("expiry_date")
    if not expiry_str:
        return None
    return get_days_from_date(expiry_str, relative_to)


def get_status_from_days(days: Optional[int], soon_limit_days: int = SOON_LIMIT_DAYS) -> str:
    """Determine expiry status from number of days remaining."""
    if days is None:
        return "expiry-unknown"
    if days < 0:
        return "expired"
    if days <= soon_limit_days:
        return "expiring-soon"
    return "active"


def get_status(product: Dict[str, Any], relative_to: Optional[date] = None) -> str:
    """Determine full product status matching frontend logic exactly.

    Order of evaluation:
    1. Unidentified if name is missing or 'Unidentified Product'
    2. Expiry-unknown if expiry date is absent
    3. Estimated-expiry if source is 'estimated'
    4. Derived from days remaining: 'expired', 'expiring-soon', 'active'
    """
    if not product or not isinstance(product, dict):
        return "unidentified"

    name = str(product.get("name", "")).strip()
    if not name or name.lower() == "unidentified product":
        return "unidentified"

    expiry_str = product.get("expiryDate") or product.get("expiry_date")
    if not expiry_str:
        return product.get("trackingStatus") or "expiry-unknown"

    source = str(product.get("expirySource", "")).lower()
    if source == "estimated":
        return "estimated-expiry"

    days = get_days_remaining(product, relative_to)
    return get_status_from_days(days)


def get_status_label(status: str) -> str:
    """Human readable status label."""
    labels = {
        "unidentified": "Unidentified Product",
        "expiry-unknown": "Expiry Unknown",
        "needs-verification": "Needs Verification",
        "estimated-expiry": "Estimated Expiry",
        "expired": "Expired",
        "expiring-soon": "Expiring Soon",
        "active": "Active",
    }
    return labels.get(status, status.capitalize())


def calculate_estimated_expiry(manufacturing_date_str: str, shelf_life_days: int) -> Optional[str]:
    """Calculate estimated expiry date from manufacturing date and positive shelf-life in days."""
    mfg = parse_date(manufacturing_date_str)
    if not mfg or not isinstance(shelf_life_days, int) or shelf_life_days <= 0:
        return None
    estimated = mfg + timedelta(days=shelf_life_days)
    return to_input_date(estimated)
