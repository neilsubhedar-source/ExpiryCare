"""Dashboard analytics and alert notification endpoints for ExpiryCare."""
from flask import Blueprint, g
from backend.services.dashboard_service import DashboardService
from backend.middleware.auth import require_auth
from backend.utils.response import success_response

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api")
dashboard_service = DashboardService()


@dashboard_bp.route("/dashboard/summary", methods=["GET"])
@require_auth
def get_dashboard_summary():
    """Retrieve aggregate statistics, timeline buckets, and insights for the authenticated user."""
    user_id = g.current_user["id"]
    summary = dashboard_service.get_dashboard_summary(user_id)
    return success_response(data=summary)


@dashboard_bp.route("/alerts", methods=["GET"])
@require_auth
def get_alerts():
    """Retrieve active expiry alerts based on the user's configured thresholds."""
    user_id = g.current_user["id"]
    alerts_data = dashboard_service.get_alerts(user_id)
    return success_response(data=alerts_data)
