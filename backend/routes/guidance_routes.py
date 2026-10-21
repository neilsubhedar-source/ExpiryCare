"""Healthcare guidance chatbot route for ExpiryCare."""
from flask import Blueprint, request, jsonify
from backend.services.guidance_service import GuidanceService

guidance_bp = Blueprint("guidance", __name__, url_prefix="/api/guidance")
guidance_service = GuidanceService()


@guidance_bp.route("/chat", methods=["POST"])
def guidance_chat():
    """Chat endpoint for practical expiry, shelf-life, and storage guidance.

    Directly matches the request/response contract expected by js/app.js:
    Request: { "message": "..." }
    Response on success: { "reply": "...", "disclaimer": "..." }
    Response without provider credentials: HTTP 200 with a clearly labelled offline knowledge-base answer.
    """
    body = request.get_json(silent=True) or {}
    message = str(body.get("message", "")).strip()
    if not message:
        return jsonify(error="message is required"), 400

    success, data, err, status_code = guidance_service.answer_query(message)
    if not success:
        return jsonify(data or {"error": err or "AI guidance is unavailable"}), status_code

    return jsonify(data), status_code
