"""Base repository module for ExpiryCare."""
from typing import Any
from backend.extensions import get_firestore


class BaseRepository:
    """Base class for database repositories providing Firestore client access."""

    def __init__(self, collection_name: str):
        self.collection_name = collection_name

    @property
    def db(self) -> Any:
        return get_firestore()

    @property
    def collection(self) -> Any:
        return self.db.collection(self.collection_name)
