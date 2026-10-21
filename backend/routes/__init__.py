"""Routes package for ExpiryCare."""
from backend.routes.health_routes import health_bp
from backend.routes.auth_routes import auth_bp
from backend.routes.product_routes import product_bp
from backend.routes.dashboard_routes import dashboard_bp
from backend.routes.retail_routes import retail_bp
from backend.routes.guidance_routes import guidance_bp

__all__ = [
    "health_bp",
    "auth_bp",
    "product_bp",
    "dashboard_bp",
    "retail_bp",
    "guidance_bp",
]
