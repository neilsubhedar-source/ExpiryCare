"""Comprehensive tests for expiry calculation rules, boundaries, and shelf-life estimations.

Guarantees zero off-by-one errors across yesterday, today, tomorrow, and 30-day limits.
"""
from datetime import date, timedelta
from backend.utils.date_utils import (
    get_days_from_date,
    get_days_remaining,
    get_status_from_days,
    get_status,
    calculate_estimated_expiry,
    to_input_date,
    parse_date
)
from backend.services.expiry_service import ExpiryService


def test_yesterday_expired():
    """A product expiring yesterday must have days = -1 and status = 'expired'."""
    today = date(2026, 10, 20)
    yesterday = today - timedelta(days=1)
    yesterday_str = to_input_date(yesterday)

    days = get_days_from_date(yesterday_str, relative_to=today)
    assert days == -1

    product = {"name": "Milk", "expiryDate": yesterday_str}
    assert get_status(product, relative_to=today) == "expired"
    assert get_status_from_days(days) == "expired"


def test_today_expiring_soon():
    """A product expiring today must have days = 0 and status = 'expiring-soon'."""
    today = date(2026, 10, 20)
    today_str = to_input_date(today)

    days = get_days_from_date(today_str, relative_to=today)
    assert days == 0

    product = {"name": "Fresh Bread", "expiryDate": today_str}
    assert get_status(product, relative_to=today) == "expiring-soon"
    assert get_status_from_days(days) == "expiring-soon"


def test_tomorrow_expiring_soon():
    """A product expiring tomorrow must have days = 1 and status = 'expiring-soon'."""
    today = date(2026, 10, 20)
    tomorrow = today + timedelta(days=1)
    tomorrow_str = to_input_date(tomorrow)

    days = get_days_from_date(tomorrow_str, relative_to=today)
    assert days == 1

    product = {"name": "Yogurt", "expiryDate": tomorrow_str}
    assert get_status(product, relative_to=today) == "expiring-soon"
    assert get_status_from_days(days) == "expiring-soon"


def test_boundary_day_30_and_31():
    """Day 30 is the last day of expiring-soon; Day 31 must be classified as active."""
    today = date(2026, 10, 20)

    # Day 30
    day_30_str = to_input_date(today + timedelta(days=30))
    days_30 = get_days_from_date(day_30_str, relative_to=today)
    assert days_30 == 30
    assert get_status_from_days(days_30) == "expiring-soon"
    assert get_status({"name": "Item 30", "expiryDate": day_30_str}, relative_to=today) == "expiring-soon"

    # Day 31
    day_31_str = to_input_date(today + timedelta(days=31))
    days_31 = get_days_from_date(day_31_str, relative_to=today)
    assert days_31 == 31
    assert get_status_from_days(days_31) == "active"
    assert get_status({"name": "Item 31", "expiryDate": day_31_str}, relative_to=today) == "active"


def test_missing_or_invalid_expiry_date():
    """Products with missing or invalid expiry date are classified as expiry-unknown."""
    today = date(2026, 10, 20)

    p_none = {"name": "Canned Beans", "expiryDate": None}
    assert get_status(p_none, relative_to=today) == "expiry-unknown"

    p_empty = {"name": "Rice Bag", "expiryDate": ""}
    assert get_status(p_empty, relative_to=today) == "expiry-unknown"

    p_invalid = {"name": "Spice Mix", "expiryDate": "invalid-date-string"}
    assert get_status(p_invalid, relative_to=today) == "expiry-unknown"


def test_unidentified_product():
    """Products missing a name or named 'Unidentified Product' get status 'unidentified'."""
    p1 = {"name": "", "expiryDate": "2026-12-01"}
    assert get_status(p1) == "unidentified"

    p2 = {"name": "Unidentified Product", "expiryDate": "2026-12-01"}
    assert get_status(p2) == "unidentified"


def test_estimated_expiry_calculation():
    """Verify estimated expiry calculation from manufacturing date + shelf life in days."""
    mfg = "2026-01-01"
    shelf_life = 90
    estimated = calculate_estimated_expiry(mfg, shelf_life)
    assert estimated == "2026-04-01"

    # Invalid cases
    assert calculate_estimated_expiry("bad-date", 30) is None
    assert calculate_estimated_expiry("2026-01-01", -10) is None
    assert calculate_estimated_expiry("2026-01-01", 0) is None


def test_enrich_product_attachment():
    """Verify enrich_product attaches correct daysRemaining, status, and statusClass."""
    today = date(2026, 10, 20)
    p = {
        "id": "p1",
        "name": "Antibiotic Ointment",
        "expiryDate": to_input_date(today + timedelta(days=10))
    }
    enriched = ExpiryService.enrich_product(p, relative_to=today)
    assert enriched["daysRemaining"] == 10
    assert enriched["status"] == "expiring-soon"
    assert enriched["statusClass"] == "status-badge-expiring"
    assert enriched["statusLabel"] == "Expiring Soon"
