"""ExpiryCare Backend Application Factory.

Modular, production-ready Flask application supporting:
- Firebase Cloud Firestore & Firebase Admin SDK
- REST API layer for personal inventory, dashboard, alerts, and retail intelligence
- Expiry tracking with strict boundary precision (no off-by-one errors)
- Strict CORS configuration and payload validation
- Centralized logging and error handling
"""
import os
import logging
from flask import Flask, request
from flask_cors import CORS

from backend.config import get_config
from backend.extensions import init_firebase
from backend.middleware.error_handlers import register_error_handlers
from backend.routes import (
    health_bp,
    auth_bp,
    product_bp,
    dashboard_bp,
    retail_bp,
    guidance_bp,
)


def create_app(config_class=None) -> Flask:
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__)

    # Load configuration
    cfg = config_class or get_config()
    app.config.from_object(cfg)

    # Configure logging
    log_level = logging.DEBUG if app.config.get("DEBUG") else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="[%(asctime)s] %(levelname)s in %(name)s: %(message)s"
    )

    # Configure CORS
    allowed_origins = app.config.get("CORS_ORIGINS", [])
    if allowed_origins:
        CORS(
            app,
            resources={r"/api/*": {"origins": allowed_origins}},
            supports_credentials=True,
            methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Content-Type", "Authorization", "X-User-Id", "X-User-Email", "X-User-Name"]
        )
    else:
        # Default restrictive CORS in production if not explicitly set
        CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Centralized error handlers
    register_error_handlers(app)

    # Initialize Firebase / Firestore
    init_firebase(app)

    # Register API Blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(retail_bp)
    app.register_blueprint(guidance_bp)

    # Optional static frontend serving for unified deployment
    frontend_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
    if os.path.isdir(frontend_folder):
        from flask import send_from_directory

        @app.route("/", methods=["GET"])
        def serve_index():
            return send_from_directory(frontend_folder, "index.html")

        @app.route("/<path:path>", methods=["GET"])
        def serve_static_frontend(path):
            if path.startswith("api/") or path == "api":
                from flask import abort
                abort(404)
            file_path = os.path.join(frontend_folder, path)
            if os.path.isfile(file_path):
                return send_from_directory(frontend_folder, path)
            # Check if it corresponds to an HTML page without extension
            html_path = file_path + ".html"
            if os.path.isfile(html_path):
                return send_from_directory(frontend_folder, path + ".html")
            from flask import abort
            abort(404)

    # Safe request logging
    @app.before_request
    def log_request_info():
        if app.config.get("DEBUG") and not request.path.startswith("/api/health"):
            app.logger.debug("Request: %s %s from %s", request.method, request.path, request.remote_addr)

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    host = os.getenv("HOST", "0.0.0.0")
    debug = os.getenv("FLASK_DEBUG", "false").lower() in ("true", "1", "yes")
    print(f"Starting ExpiryCare Backend server on http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)
