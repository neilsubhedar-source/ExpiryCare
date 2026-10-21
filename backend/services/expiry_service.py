"""Expiry calculation service for ExpiryCare.

Provides deterministic calculations matching frontend UI expectations.
Ensures zero off-by-one errors across yesterday, today, tomorrow, and boundary days.
"""
from datetime import date
from typing import Dict, Any, List, Optional
from backend.utils.date_utils import (
    parse_date,
    get_today,
    get_days_from_date,
    get_days_remaining,
    get_status_from_days,
    get_status,
    get_status_label,
    calculate_estimated_expiry,
    to_input_date,
    SOON_LIMIT_DAYS
)


class ExpiryService:
    """Core domain logic for calculating product shelf life, status, and alerts."""

    @staticmethod
    def enrich_product(product: Dict[str, Any], relative_to: Optional[date] = None) -> Dict[str, Any]:
        """Attach dynamically calculated expiry status fields to a product dictionary."""
        enriched = product.copy()
        days = get_days_remaining(enriched, relative_to)
        status = get_status(enriched, relative_to)
        status_label = get_status_label(status)

        enriched["daysRemaining"] = days
        enriched["status"] = status
        enriched["statusLabel"] = status_label

        # Map to frontend badge CSS class
        if status in ("unidentified", "expiry-unknown", "needs-verification", "estimated-expiry"):
            enriched["statusClass"] = "status-badge-expiring"
        elif status == "expired":
            enriched["statusClass"] = "status-badge-expired"
        elif status == "expiring-soon":
            enriched["statusClass"] = "status-badge-expiring"
        else:
            enriched["statusClass"] = "status-badge-active"

        return enriched

    @staticmethod
    def count_by_status(products: List[Dict[str, Any]], relative_to: Optional[date] = None) -> Dict[str, int]:
        """Aggregate product counts by status category."""
        counts = {
            "total": len(products),
            "active": 0,
            "expiringSoon": 0,
            "expired": 0,
            "unknown": 0,
            "unidentified": 0
        }

        for p in products:
            status = get_status(p, relative_to)
            if status == "active":
                counts["active"] += 1
            elif status == "expiring-soon":
                counts["expiringSoon"] += 1
            elif status == "expired":
                counts["expired"] += 1
            elif status in ("expiry-unknown", "estimated-expiry", "needs-verification"):
                counts["unknown"] += 1
            elif status == "unidentified":
                counts["unidentified"] += 1

        return counts

    @staticmethod
    def get_timeline_breakdown(products: List[Dict[str, Any]], relative_to: Optional[date] = None) -> Dict[str, List[Dict[str, Any]]]:
        """Group products into dashboard timeline groups:
        - expired (< 0 days)
        - expiring_7_days (0 to 7 days)
        - expiring_14_days (8 to 14 days)
        - expiring_30_days (15 to 30 days)
        - safe (> 30 days)
        - unknown (no verified date)
        """
        timeline = {
            "expired": [],
            "expiring_7_days": [],
            "expiring_14_days": [],
            "expiring_30_days": [],
            "safe": [],
            "unknown": []
        }

        for p in products:
            enriched = ExpiryService.enrich_product(p, relative_to)
            days = enriched["daysRemaining"]
            if days is None:
                timeline["unknown"].append(enriched)
            elif days < 0:
                timeline["expired"].append(enriched)
            elif days <= 7:
                timeline["expiring_7_days"].append(enriched)
            elif days <= 14:
                timeline["expiring_14_days"].append(enriched)
            elif days <= 30:
                timeline["expiring_30_days"].append(enriched)
            else:
                timeline["safe"].append(enriched)

        return timeline

    @staticmethod
    def filter_alerts(products: List[Dict[str, Any]], alert_thresholds: List[int], relative_to: Optional[date] = None) -> List[Dict[str, Any]]:
        """Return products that trigger alerts based on the user's configured thresholds (e.g., [1, 3, 7])."""
        threshold_set = set(alert_thresholds) if alert_thresholds else {3}
        alerts = []

        for p in products:
            enriched = ExpiryService.enrich_product(p, relative_to)
            days = enriched["daysRemaining"]
            if days is not None:
                # Include already expired products and products within any threshold
                if days < 0 or days in threshold_set or any(days <= t and days >= 0 for t in threshold_set):
                    alerts.append(enriched)

        alerts.sort(key=lambda x: (x["daysRemaining"] is None, x["daysRemaining"]))
        return alerts
