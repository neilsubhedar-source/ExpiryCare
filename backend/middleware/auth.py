"""Authentication and authorization middleware for ExpiryCare.

Supports dual-mode verification:
1. Standard HMAC-SHA256 JWT tokens for REST API clients and frontend integration.
2. Google Firebase ID tokens via Firebase Admin SDK.
Enforces strict per-user ownership and protection of personal data.
"""
import time
import hmac
import hashlib
import json
import base64
from functools import wraps
from typing import Optional, Dict, Any, Tuple
from flask import request, g, current_app
from backend.utils.response import error_response


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64_decode(data: str) -> bytes:
    padding = "=" * (4 - (len(data) % 4))
    return base64.urlsafe_b64decode(data + padding)


def generate_jwt_token(user_id: str, email: str, name: str, secret_key: str, expires_in_seconds: int = 7 * 86400) -> str:
    """Generate a signed JWT token without external crypto dependencies."""
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {
        "sub": user_id,
        "email": email,
        "name": name,
        "iat": now,
        "exp": now + expires_in_seconds
    }

    header_b64 = _b64_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")

    signature = hmac.new(secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = _b64_encode(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def verify_jwt_token(token: str, secret_key: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """Verify and decode a signed JWT token."""
    parts = token.split(".")
    if len(parts) != 3:
        return False, None, "Invalid token format"

    header_b64, payload_b64, sig_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_sig = hmac.new(secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()

    try:
        provided_sig = _b64_decode(sig_b64)
    except Exception:
        return False, None, "Invalid signature encoding"

    if not hmac.compare_digest(expected_sig, provided_sig):
        return False, None, "Invalid token signature"

    try:
        payload_bytes = _b64_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception:
        return False, None, "Invalid token payload"

    now = int(time.time())
    if "exp" in payload and payload["exp"] < now:
        return False, None, "Token has expired"

    return True, payload, None


def verify_firebase_id_token(token: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """Attempt verification with Firebase Admin SDK if active."""
    try:
        import firebase_admin
        from firebase_admin import auth
        if firebase_admin._apps:
            decoded = auth.verify_id_token(token)
            return True, {
                "sub": decoded.get("uid"),
                "email": decoded.get("email", ""),
                "name": decoded.get("name", "")
            }, None
    except Exception as exc:
        return False, None, str(exc)
    return False, None, "Firebase Admin not active"


def get_token_from_header() -> Optional[str]:
    """Extract Bearer token from Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    return None


def require_auth(f):
    """Decorator to require valid authentication on protected routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_from_header()
        if not token:
            # Check development user header if permitted
            dev_user = request.headers.get("X-User-Id")
            if dev_user and (current_app.config.get("DEBUG") or current_app.config.get("TESTING")):
                g.current_user = {
                    "id": dev_user,
                    "email": request.headers.get("X-User-Email", f"{dev_user}@example.com"),
                    "name": request.headers.get("X-User-Name", "Development User")
                }
                return f(*args, **kwargs)
            return error_response("Authentication token is required", status_code=401)

        secret_key = current_app.config.get("SECRET_KEY", "expirycare-dev-secret-key-change-in-production")

        # First try JWT verification
        valid, payload, err = verify_jwt_token(token, secret_key)
        if valid and payload:
            g.current_user = {
                "id": payload.get("sub"),
                "email": payload.get("email"),
                "name": payload.get("name")
            }
            return f(*args, **kwargs)

        # Then try Firebase token verification
        fb_valid, fb_payload, fb_err = verify_firebase_id_token(token)
        if fb_valid and fb_payload:
            g.current_user = {
                "id": fb_payload.get("sub"),
                "email": fb_payload.get("email"),
                "name": fb_payload.get("name")
            }
            return f(*args, **kwargs)

        return error_response(f"Unauthorized: {err or 'Invalid authentication token'}", status_code=401)

    return decorated


def optional_auth(f):
    """Decorator to attach user identity if token is present, without failing if missing."""
    @wraps(f)
    def decorated(*args, **kwargs):
        g.current_user = None
        token = get_token_from_header()
        if token:
            secret_key = current_app.config.get("SECRET_KEY", "expirycare-dev-secret-key-change-in-production")
            valid, payload, _ = verify_jwt_token(token, secret_key)
            if valid and payload:
                g.current_user = {
                    "id": payload.get("sub"),
                    "email": payload.get("email"),
                    "name": payload.get("name")
                }
            else:
                fb_valid, fb_payload, _ = verify_firebase_id_token(token)
                if fb_valid and fb_payload:
                    g.current_user = {
                        "id": fb_payload.get("sub"),
                        "email": fb_payload.get("email"),
                        "name": fb_payload.get("name")
                    }
        return f(*args, **kwargs)

    return decorated
