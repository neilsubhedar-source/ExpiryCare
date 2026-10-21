"""Centralized JSON response serialization utilities."""
from typing import Any, Optional, Dict, Tuple
from flask import jsonify, Response


# Type alias for Flask response tuple. Define before using it in annotations.
TupleResponse = Tuple[Response, int]


def success_response(
    data: Any = None,
    message: Optional[str] = None,
    status_code: int = 200,
    **kwargs: Any
) -> TupleResponse:
    """Build a standard JSON success response."""
    payload: Dict[str, Any] = {"success": True}
    if message is not None:
        payload["message"] = message
    if data is not None:
        payload["data"] = data
    payload.update(kwargs)
    return jsonify(payload), status_code


def error_response(
    error_message: str,
    status_code: int = 400,
    details: Optional[Any] = None,
    **kwargs: Any
) -> TupleResponse:
    """Build a standard JSON error response preserving required frontend error shape."""
    payload: Dict[str, Any] = {
        "success": False,
        "error": error_message
    }
    if details is not None:
        payload["details"] = details
    payload.update(kwargs)
    return jsonify(payload), status_code
