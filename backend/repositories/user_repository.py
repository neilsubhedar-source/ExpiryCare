"""User repository for Firestore database operations."""
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from backend.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    """Handles CRUD operations for users and profile/settings in Firestore."""

    def __init__(self):
        super().__init__("users")

    def create(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save a new user record."""
        user_id = user_data.get("id")
        if not user_id:
            import uuid
            user_id = "user_" + uuid.uuid4().hex[:12]
            user_data["id"] = user_id

        now_iso = datetime.now(timezone.utc).isoformat()
        user_data.setdefault("created_at", now_iso)
        user_data.setdefault("updated_at", now_iso)
        user_data.setdefault("settings", {"alertThresholds": [3], "defaultSort": "expiry-date"})

        self.collection.document(user_id).set(user_data)
        return user_data

    def get_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a user by their unique identifier."""
        if not user_id:
            return None
        doc = self.collection.document(user_id).get()
        if doc.exists:
            return doc.to_dict()
        return None

    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Retrieve a user by email address (case-insensitive)."""
        if not email:
            return None
        clean_email = email.strip().lower()
        query = self.collection.where("email", "==", clean_email)
        for doc in query.stream():
            return doc.to_dict()
        return None

    def update(self, user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update fields of an existing user."""
        user = self.get_by_id(user_id)
        if not user:
            return None

        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.collection.document(user_id).update(updates)
        user.update(updates)
        return user

    def update_settings(self, user_id: str, settings: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update user alert thresholds and display settings."""
        user = self.get_by_id(user_id)
        if not user:
            return None

        current_settings = user.get("settings", {})
        current_settings.update(settings)
        return self.update(user_id, {"settings": current_settings})

    def delete(self, user_id: str) -> bool:
        """Delete a user record."""
        user = self.get_by_id(user_id)
        if not user:
            return False
        self.collection.document(user_id).delete()
        return True
