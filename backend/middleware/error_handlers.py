"""Centralized error handling middleware for ExpiryCare."""
import logging
from flask import Flask, jsonify, Request
from werkzeug.exceptions import HTTPException

logger = logging.getLogger("expirycare.errors")


def register_error_handlers(app: Flask) -> None:
    """Register HTTP exception handlers to return consistent JSON error objects."""

    @app.errorhandler(400)
    def bad_request(error):
        msg = error.description if isinstance(error, HTTPException) and error.description else "Bad request"
        return jsonify(success=False, error=msg), 400

    @app.errorhandler(401)
    def unauthorized(error):
        msg = error.description if isinstance(error, HTTPException) and error.description else "Authentication required"
        return jsonify(success=False, error=msg), 401

    @app.errorhandler(403)
    def forbidden(error):
        msg = error.description if isinstance(error, HTTPException) and error.description else "Forbidden: access denied"
        return jsonify(success=False, error=msg), 403

    @app.errorhandler(404)
    def not_found(error):
        msg = error.description if isinstance(error, HTTPException) and error.description else "Resource not found"
        return jsonify(success=False, error=msg), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify(success=False, error="Method not allowed for this endpoint"), 405

    @app.errorhandler(413)
    def payload_too_large(error):
        return jsonify(success=False, error="Payload too large: exceeds maximum permitted size"), 413

    @app.errorhandler(429)
    def ratelimit_exceeded(error):
        return jsonify(success=False, error="Rate limit exceeded. Please try again later."), 429

    @app.errorhandler(500)
    def internal_error(error):
        logger.error("Internal Server Error: %s", error, exc_info=True)
        return jsonify(success=False, error="An internal server error occurred"), 500

    @app.errorhandler(501)
    def not_implemented(error):
        msg = error.description if isinstance(error, HTTPException) and error.description else "Endpoint not implemented"
        return jsonify(success=False, error=msg), 501

    @app.errorhandler(503)
    def service_unavailable(error):
        msg = error.description if isinstance(error, HTTPException) and error.description else "Service unavailable"
        return jsonify(success=False, error=msg), 503
