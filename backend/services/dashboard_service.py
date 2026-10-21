"""Dashboard and analytics service for ExpiryCare."""
from typing import Dict, Any, List, Optional
from backend.repositories.product_repository import ProductRepository
from backend.repositories.user_repository import UserRepository
from backend.services.expiry_service import ExpiryService


class DashboardService:
    """Computes aggregate analytics, timeline groupings, smart insights, and alert feeds."""

    def __init__(self, product_repo: Optional[ProductRepository] = None, user_repo: Optional[UserRepository] = None):
        self.product_repo = product_repo or ProductRepository()
        self.user_repo = user_repo or UserRepository()

    def get_dashboard_summary(self, user_id: str) -> Dict[str, Any]:
        """Compute top-level statistics and recent product lists for dashboard."""
        products = self.product_repo.list_by_user(user_id)
        counts = ExpiryService.count_by_status(products)
        timeline = ExpiryService.get_timeline_breakdown(products)

        # Category breakdown
        category_counts: Dict[str, int] = {}
        for p in products:
            cat = p.get("category", "other")
            category_counts[cat] = category_counts.get(cat, 0) + 1

        # Insights
        insights = []
        if counts["expired"] > 0:
            insights.append({
                "type": "danger",
                "message": f"You have {counts['expired']} expired product(s) that should be reviewed and safely disposed of."
            })
        if counts["expiringSoon"] > 0:
            insights.append({
                "type": "warning",
                "message": f"{counts['expiringSoon']} item(s) are expiring within 30 days. Prioritize consumption or use."
            })
        if counts["unknown"] > 0:
            insights.append({
                "type": "info",
                "message": f"{counts['unknown']} product(s) have unverified or estimated expiry dates. Check packaging when convenient."
            })
        if counts["total"] == 0:
            insights.append({
                "type": "info",
                "message": "Your inventory is currently empty. Add your first item or load demo data to get started."
            })

        return {
            "counts": counts,
            "categoryCounts": category_counts,
            "timeline": {
                "expiredCount": len(timeline["expired"]),
                "next7DaysCount": len(timeline["expiring_7_days"]),
                "next14DaysCount": len(timeline["expiring_14_days"]),
                "next30DaysCount": len(timeline["expiring_30_days"]),
                "safeCount": len(timeline["safe"]),
                "unknownCount": len(timeline["unknown"])
            },
            "insights": insights,
            "recentProducts": [ExpiryService.enrich_product(p) for p in products[:5]]
        }

    def get_alerts(self, user_id: str) -> Dict[str, Any]:
        """Compute alerts matching the user's active threshold preferences."""
        user = self.user_repo.get_by_id(user_id) or {}
        settings = user.get("settings", {})
        thresholds = settings.get("alertThresholds", [3])

        products = self.product_repo.list_by_user(user_id)
        alert_items = ExpiryService.filter_alerts(products, thresholds)

        return {
            "thresholds": thresholds,
            "alertCount": len(alert_items),
            "alerts": alert_items
        }
