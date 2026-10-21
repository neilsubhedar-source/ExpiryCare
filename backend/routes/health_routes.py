"""Health check route for ExpiryCare Backend."""
from datetime import datetime, timezone
from flask import Blueprint, jsonify, current_app
from backend.extensions import is_live_firestore

health_bp = Blueprint("health", __name__)


@health_bp.route("/api/health", methods=["GET"])
def health_check():
    """System health check endpoint.

    Returns operational status, persistence mode, and external service availability.
    """
    has_live_db = is_live_firestore()
    has_ai = bool(current_app.config.get("OPENAI_API_KEY") or current_app.config.get("GEMINI_API_KEY"))

    persistence_label = (
        "connected-google-cloud-firestore"
        if has_live_db
        else "in-memory-document-store-unless-firestore-configured"
    )

    ai_label = (
        "live-provider-configured"
        if has_ai
        else "offline-knowledge-base-enabled-live-provider-optional"
    )

    return jsonify(
        status="ok",
        service="ExpiryCare API",
        version="2.0.0",
        persistence=persistence_label,
        ai=ai_label,
        timestamp=datetime.now(timezone.utc).isoformat()
    ), 200
