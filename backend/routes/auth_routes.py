"""Authentication and user profile endpoints for ExpiryCare."""
from flask import Blueprint, request, g, current_app
from backend.services.auth_service import AuthService
from backend.middleware.auth import require_auth
from backend.utils.response import success_response, error_response

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")
auth_service = AuthService()


@auth_bp.route("/register", methods=["POST"])
def register():
    """Register a new user account."""
    body = request.get_json(silent=True) or {}
    secret_key = current_app.config.get("SECRET_KEY", "expirycare-dev-secret-key-change-in-production")
    success, data, err = auth_service.register(body, secret_key)
    if not success:
        return error_response(err or "Registration failed", status_code=400)
    return success_response(data=data, message="Registration successful", status_code=201)


@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate user credentials and issue an auth token."""
    body = request.get_json(silent=True) or {}
    secret_key = current_app.config.get("SECRET_KEY", "expirycare-dev-secret-key-change-in-production")
    success, data, err = auth_service.login(body, secret_key)
    if not success:
        return error_response(err or "Login failed", status_code=401)
    return success_response(data=data, message="Login successful", status_code=200)


@auth_bp.route("/profile", methods=["GET"])
@require_auth
def get_profile():
    """Retrieve authenticated user's profile."""
    user_id = g.current_user["id"]
    profile = auth_service.get_profile(user_id)
    if not profile:
        return error_response("User profile not found", status_code=404)
    return success_response(data=profile)


@auth_bp.route("/profile", methods=["PUT"])
@require_auth
def update_profile():
    """Update authenticated user's profile information."""
    user_id = g.current_user["id"]
    body = request.get_json(silent=True) or {}
    success, updated, err = auth_service.update_profile(user_id, body)
    if not success:
        return error_response(err or "Failed to update profile", status_code=400)
    return success_response(data=updated, message="Profile updated successfully")


@auth_bp.route("/settings", methods=["GET"])
@require_auth
def get_settings():
    """Retrieve authenticated user's preferences."""
    user_id = g.current_user["id"]
    profile = auth_service.get_profile(user_id)
    settings = profile.get("settings", {}) if profile else {}
    return success_response(data=settings)


@auth_bp.route("/settings", methods=["PUT"])
@require_auth
def update_settings():
    """Update authenticated user's notification preferences."""
    user_id = g.current_user["id"]
    body = request.get_json(silent=True) or {}
    success, updated_settings, err = auth_service.update_settings(user_id, body)
    if not success:
        return error_response(err or "Failed to update settings", status_code=400)
    return success_response(data=updated_settings, message="Settings updated successfully")


@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    """Forgot password endpoint providing educational prototype instructions."""
    body = request.get_json(silent=True) or {}
    email = str(body.get("email", "")).strip().lower()
    if not email:
        return error_response("Email address is required", status_code=400)
    # Honest response: production email dispatch requires configured SMTP or SendGrid
    return success_response(
        message=f"Password reset instructions would be sent to {email}.",
        note="Email delivery service is in prototype configuration."
    )
