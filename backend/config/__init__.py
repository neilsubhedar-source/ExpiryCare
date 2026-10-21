"""Configuration module for ExpiryCare Backend.

Supports Development, Production, and Testing configurations.
All secrets and provider credentials are read strictly from environment variables.
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

# Load backend/.env independent of the working directory. Environment variables already
# supplied by the shell or hosting platform take precedence (override=False).
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"), override=False)


class BaseConfig:
    """Base application configuration."""
    SECRET_KEY = os.getenv("SECRET_KEY", "expirycare-dev-secret-key-change-in-production")
    PORT = int(os.getenv("PORT", "5000"))
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 10 * 1024 * 1024))  # 10 MB limit
    JWT_EXPIRATION_DELTA = timedelta(days=7)
    
    # Firebase configuration
    FIRESTORE_ENABLED = os.getenv("FIRESTORE_ENABLED", "false").lower() in ("true", "1", "yes")
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "")
    
    # External AI / OCR providers
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    OPEN_FOOD_FACTS_BASE_URL = os.getenv("OPEN_FOOD_FACTS_BASE_URL", "https://world.openfoodfacts.org")
    
    # Expiry logic configuration
    SOON_LIMIT_DAYS = int(os.getenv("SOON_LIMIT_DAYS", "30"))
    
    # CORS allowed origins
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:5000,http://127.0.0.1:5000,http://localhost:8000,http://127.0.0.1:8000").split(",")
        if origin.strip()
    ]


class DevelopmentConfig(BaseConfig):
    """Development configuration."""
    DEBUG = True
    TESTING = False
    # In development, accept localhost and local IP origins
    CORS_ORIGINS = [
        "http://localhost:5000",
        "http://127.0.0.1:5000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:5501",
        "http://127.0.0.1:5501",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]


class ProductionConfig(BaseConfig):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    # In production, require strict environment-based CORS origins
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "").split(",")
        if origin.strip()
    ]


class TestingConfig(BaseConfig):
    """Testing configuration."""
    DEBUG = True
    TESTING = True
    SECRET_KEY = "test-secret-key-expirycare"
    FIRESTORE_ENABLED = False  # Use fast, fully-featured in-memory mock during tests
    CORS_ORIGINS = ["*"]


def get_config():
    """Retrieve configuration based on FLASK_ENV or ENVIRONMENT."""
    env = os.getenv("FLASK_ENV", os.getenv("ENVIRONMENT", "development")).lower()
    if env == "production":
        return ProductionConfig
    if env == "testing":
        return TestingConfig
    return DevelopmentConfig
