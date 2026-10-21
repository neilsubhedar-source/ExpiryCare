"""Pytest fixtures and test configuration for ExpiryCare backend."""
import sys
import os
import pytest

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.app import create_app
from backend.config import TestingConfig
from backend.extensions import reset_test_db
from backend.middleware.auth import generate_jwt_token


@pytest.fixture(scope="session")
def app():
    """Create a Flask application configured for testing."""
    test_app = create_app(TestingConfig)
    yield test_app


@pytest.fixture(autouse=True)
def clean_database():
    """Reset the in-memory test database before each test run."""
    reset_test_db()
    yield
    reset_test_db()


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def test_user(app):
    """Create a verified test user in the test database."""
    from backend.services.auth_service import AuthService
    auth_service = AuthService()
    user_data = {
        "name": "Test Engineer",
        "email": "test.engineer@example.com",
        "password": "Password123!"
    }
    success, data, err = auth_service.register(user_data, app.config["SECRET_KEY"])
    assert success, f"Failed to register test user: {err}"
    return data["user"]


@pytest.fixture
def auth_headers(app, test_user):
    """Generate authorization headers for the primary test user."""
    token = generate_jwt_token(
        test_user["id"],
        test_user["email"],
        test_user["name"],
        app.config["SECRET_KEY"]
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def second_user(app):
    """Create a second distinct user to test multi-user isolation."""
    from backend.services.auth_service import AuthService
    auth_service = AuthService()
    user_data = {
        "name": "Second User",
        "email": "second.user@example.com",
        "password": "Password123!"
    }
    success, data, err = auth_service.register(user_data, app.config["SECRET_KEY"])
    assert success
    return data["user"]


@pytest.fixture
def second_auth_headers(app, second_user):
    """Generate authorization headers for the second user."""
    token = generate_jwt_token(
        second_user["id"],
        second_user["email"],
        second_user["name"],
        app.config["SECRET_KEY"]
    )
    return {"Authorization": f"Bearer {token}"}
