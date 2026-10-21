"""Extensions and database initialization module for ExpiryCare.

Provides access to Firebase Cloud Firestore with automatic graceful fallback
to an in-memory document store when live Firestore is disabled or credentials
are pending. This enables full automated test execution and offline development
without compromising live production Firestore readiness.
"""
import os
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger("expirycare.extensions")

_firestore_client = None
_firebase_app = None
_is_live_firestore = False


class InMemoryDocumentSnapshot:
    """Simulates a Firestore DocumentSnapshot."""
    def __init__(self, doc_id: str, data: Optional[Dict[str, Any]]):
        self.id = doc_id
        self._data = data.copy() if data else None

    @property
    def exists(self) -> bool:
        return self._data is not None

    def to_dict(self) -> Optional[Dict[str, Any]]:
        return self._data.copy() if self._data else None


class InMemoryDocumentReference:
    """Simulates a Firestore DocumentReference."""
    def __init__(self, collection: "InMemoryCollectionReference", doc_id: str):
        self.collection = collection
        self.id = doc_id

    def get(self) -> InMemoryDocumentSnapshot:
        data = self.collection.store.get(self.id)
        return InMemoryDocumentSnapshot(self.id, data)

    def set(self, document_data: Dict[str, Any], merge: bool = False) -> None:
        if merge and self.id in self.collection.store:
            self.collection.store[self.id].update(document_data)
        else:
            self.collection.store[self.id] = document_data.copy()

    def update(self, field_updates: Dict[str, Any]) -> None:
        if self.id not in self.collection.store:
            raise KeyError(f"Document {self.id} does not exist in {self.collection.name}")
        self.collection.store[self.id].update(field_updates)

    def delete(self) -> None:
        if self.id in self.collection.store:
            del self.collection.store[self.id]


class InMemoryQuery:
    """Simulates Firestore queries with filtering and ordering."""
    def __init__(self, collection: "InMemoryCollectionReference", filters: Optional[List[tuple]] = None, order_field: Optional[str] = None, descending: bool = False):
        self.collection = collection
        self.filters = filters or []
        self.order_field = order_field
        self.descending = descending

    def where(self, field_path: str, op_string: str, value: Any) -> "InMemoryQuery":
        new_filters = list(self.filters)
        new_filters.append((field_path, op_string, value))
        return InMemoryQuery(self.collection, new_filters, self.order_field, self.descending)

    def order_by(self, field_path: str, direction: str = "ASCENDING") -> "InMemoryQuery":
        is_desc = direction.upper() in ("DESCENDING", "DESC")
        return InMemoryQuery(self.collection, self.filters, field_path, is_desc)

    def stream(self):
        docs = []
        for doc_id, data in self.collection.store.items():
            matches = True
            for field, op, val in self.filters:
                doc_val = data.get(field)
                if op == "==" and doc_val != val:
                    matches = False
                    break
                elif op == "!=" and doc_val == val:
                    matches = False
                    break
                elif op == ">" and not (doc_val is not None and doc_val > val):
                    matches = False
                    break
                elif op == ">=" and not (doc_val is not None and doc_val >= val):
                    matches = False
                    break
                elif op == "<" and not (doc_val is not None and doc_val < val):
                    matches = False
                    break
                elif op == "<=" and not (doc_val is not None and doc_val <= val):
                    matches = False
                    break
                elif op == "in" and doc_val not in val:
                    matches = False
                    break
            if matches:
                docs.append(InMemoryDocumentSnapshot(doc_id, data))

        if self.order_field:
            def sort_key(snapshot):
                val = snapshot.to_dict().get(self.order_field)
                return (val is None, val)
            docs.sort(key=sort_key, reverse=self.descending)

        for d in docs:
            yield d


class InMemoryCollectionReference(InMemoryQuery):
    """Simulates a Firestore CollectionReference."""
    def __init__(self, name: str, root_storage: Dict[str, Dict[str, Any]]):
        self.name = name
        if name not in root_storage:
            root_storage[name] = {}
        self.store = root_storage[name]
        super().__init__(self)

    def document(self, document_id: Optional[str] = None) -> InMemoryDocumentReference:
        if not document_id:
            import uuid
            document_id = str(uuid.uuid4())
        return InMemoryDocumentReference(self, document_id)


class InMemoryFirestoreClient:
    """In-memory Firestore client providing full CRUD and query compatibility."""
    def __init__(self):
        self._storage: Dict[str, Dict[str, Any]] = {}

    def collection(self, collection_name: str) -> InMemoryCollectionReference:
        return InMemoryCollectionReference(collection_name, self._storage)

    def clear_all(self):
        """Helper to clear test storage between test runs."""
        self._storage.clear()


def init_firebase(app=None) -> Any:
    """Initialize Firebase Admin SDK and Firestore client.

    If FIRESTORE_ENABLED is true and credentials are provided, connects to real Firestore.
    Otherwise initializes an in-memory client and logs the operating mode.
    """
    global _firestore_client, _firebase_app, _is_live_firestore

    firestore_enabled = os.getenv("FIRESTORE_ENABLED", "false").lower() in ("true", "1", "yes")
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

    if firestore_enabled:
        try:
            import firebase_admin
            from firebase_admin import credentials, firestore

            if not firebase_admin._apps:
                if cred_path and os.path.exists(cred_path):
                    cred = credentials.Certificate(cred_path)
                    _firebase_app = firebase_admin.initialize_app(cred)
                    logger.info("Initialized Firebase Admin with credential file: %s", cred_path)
                else:
                    _firebase_app = firebase_admin.initialize_app()
                    logger.info("Initialized Firebase Admin with application default credentials")
            else:
                _firebase_app = firebase_admin.get_app()

            _firestore_client = firestore.client()
            _is_live_firestore = True
            logger.info("Firebase Cloud Firestore connected successfully.")
            return _firestore_client
        except Exception as exc:
            logger.error("Failed to initialize live Firestore: %s", exc)
            if app and not app.config.get("TESTING"):
                raise RuntimeError(f"FIRESTORE_ENABLED=true but initialization failed: {exc}") from exc
            logger.warning("Falling back to in-memory Firestore simulator for testing/development.")

    _firestore_client = InMemoryFirestoreClient()
    _is_live_firestore = False
    logger.info("Operating with In-Memory Document Store (Firestore simulator).")
    return _firestore_client


def get_firestore():
    """Return the active Firestore client."""
    global _firestore_client
    if _firestore_client is None:
        init_firebase()
    return _firestore_client


def is_live_firestore() -> bool:
    """Return True if connected to live Google Cloud Firestore."""
    return _is_live_firestore


def reset_test_db():
    """Reset the database state for tests."""
    global _firestore_client
    if isinstance(_firestore_client, InMemoryFirestoreClient):
        _firestore_client.clear_all()
