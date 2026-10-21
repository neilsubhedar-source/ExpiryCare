"""Authentication service for ExpiryCare.

Provides secure password hashing, user registration, credential verification,
and JWT token generation. Never stores plaintext passwords.
"""
from typing import Dict, Any, Tuple, Optional
from werkzeug.security import generate_password_hash, check_password_hash
from backend.repositories.user_repository import UserRepository
from backend.middleware.auth import generate_jwt_token
from backend.utils.validators import is_valid_email


class AuthService:
    """Handles user identity, registration, login, and profile operations."""

    def __init__(self, user_repo: Optional[UserRepository] = None):
        self.user_repo = user_repo or UserRepository()

    def register(self, data: Dict[str, Any], secret_key: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Register a new user account."""
        name = str(data.get("name", "")).strip()
        email = str(data.get("email", "")).strip().lower()
        password = str(data.get("password", ""))

        if len(name) < 2:
            return False, None, "Please enter your full name (at least 2 characters)"
        if not is_valid_email(email):
            return False, None, "Please enter a valid email address"
        if len(password) < 8:
            return False, None, "Password must be at least 8 characters long"

        existing = self.user_repo.get_by_email(email)
        if existing:
            return False, None, "An account with this email address already exists"

        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")
        user_record = {
            "name": name,
            "email": email,
            "password_hash": hashed_password,
            "settings": {
                "alertThresholds": [3],
                "defaultSort": "expiry-date"
            }
        }

        created = self.user_repo.create(user_record)
        user_id = created["id"]
        token = generate_jwt_token(user_id, email, name, secret_key)

        return True, {
            "token": token,
            "user": {
                "id": user_id,
                "name": name,
                "email": email,
                "settings": created.get("settings", {})
            }
        }, None

    def login(self, data: Dict[str, Any], secret_key: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Authenticate user credentials and issue an access token."""
        email = str(data.get("email", "")).strip().lower()
        password = str(data.get("password", ""))

        if not is_valid_email(email):
            return False, None, "Please enter a valid email address"
        if not password:
            return False, None, "Please enter your password"

        user = self.user_repo.get_by_email(email)
        if not user:
            return False, None, "Incorrect email or password. Please try again."

        pwd_hash = user.get("password_hash")
        # In case demo accounts or mock data had plaintext passwords, handle safely
        password_ok = False
        if pwd_hash and check_password_hash(pwd_hash, password):
            password_ok = True
        elif user.get("password") == password:  # fallback for imported prototype test users
            password_ok = True

        if not password_ok:
            return False, None, "Incorrect email or password. Please try again."

        user_id = user["id"]
        name = user.get("name", "User")
        token = generate_jwt_token(user_id, email, name, secret_key)

        return True, {
            "token": token,
            "user": {
                "id": user_id,
                "name": name,
                "email": email,
                "settings": user.get("settings", {})
            }
        }, None

    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve sanitized user profile."""
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return None
        return {
            "id": user["id"],
            "name": user.get("name", ""),
            "email": user.get("email", ""),
            "settings": user.get("settings", {}),
            "created_at": user.get("created_at")
        }

    def update_profile(self, user_id: str, data: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Update profile name and email."""
        name = str(data.get("name", "")).strip()
        email = str(data.get("email", "")).strip().lower()

        if len(name) < 2:
            return False, None, "Please enter a name (at least 2 characters)"
        if not is_valid_email(email):
            return False, None, "Please enter a valid email address"

        existing = self.user_repo.get_by_email(email)
        if existing and existing.get("id") != user_id:
            return False, None, "That email is already used by another account"

        updated = self.user_repo.update(user_id, {"name": name, "email": email})
        if not updated:
            return False, None, "User not found"

        return True, {
            "id": updated["id"],
            "name": updated["name"],
            "email": updated["email"],
            "settings": updated.get("settings", {})
        }, None

    def update_settings(self, user_id: str, settings: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Update user preferences and alert thresholds."""
        thresholds = settings.get("alertThresholds")
        if thresholds is not None:
            if not isinstance(thresholds, list) or not all(isinstance(x, (int, float)) for x in thresholds):
                return False, None, "alertThresholds must be a list of numbers"
            settings["alertThresholds"] = [int(x) for x in thresholds]

        updated = self.user_repo.update_settings(user_id, settings)
        if not updated:
            return False, None, "User not found"

        return True, updated.get("settings", {}), None
