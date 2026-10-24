import os
import smtplib
import logging
from email.message import EmailMessage

from flask import Blueprint, jsonify, request

notification_bp = Blueprint("notifications", __name__)
logger = logging.getLogger(__name__)

# Temporary in-memory preferences.
# These reset when the server restarts.
_preferences = {
    "emailNotifications": True,
    "expiryAlerts": True,
    "dailyDigest": False,
}


def smtp_is_configured():
    required = [
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USER",
        "SMTP_PASSWORD",
        "SMTP_FROM_EMAIL",
    ]
    return all(os.environ.get(key, "").strip() for key in required)


def send_email(to_email, subject, body):
    if not smtp_is_configured():
        raise RuntimeError("SMTP is not configured.")

    host = os.environ["SMTP_HOST"].strip()
    port = int(os.environ.get("SMTP_PORT", "587"))
    username = os.environ["SMTP_USER"].strip()
    password = os.environ["SMTP_PASSWORD"].strip()
    from_email = os.environ["SMTP_FROM_EMAIL"].strip()
    use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() == "true"

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = from_email
    message["To"] = to_email
    message.set_content(body)

    with smtplib.SMTP(host, port, timeout=20) as server:
        server.ehlo()

        if use_tls:
            server.starttls()
            server.ehlo()

        server.login(username, password)
        server.send_message(message)


def response_data(**kwargs):
    return jsonify({
        "success": True,
        "data": {
            "emailConfigured": smtp_is_configured(),
            **kwargs,
        },
    })




@notification_bp.route("/status", methods=["GET"])
def notification_status():
    """Expose provider readiness without leaking credentials."""
    # SMS sending is not implemented in this project yet; credentials alone are not enough.
    sms_configured = False
    return response_data(
        emailConfigured=smtp_is_configured(),
        smsConfigured=sms_configured,
        message="Gmail SMTP is configured." if smtp_is_configured() else "Email delivery requires Gmail SMTP environment variables.",
        smsMessage="SMS delivery is not implemented yet.",
    )

@notification_bp.route("/preferences", methods=["GET"])
def get_preferences():
    return response_data(preferences=_preferences.copy())


@notification_bp.route("/preferences", methods=["PUT"])
def update_preferences():
    data = request.get_json(silent=True) or {}

    allowed = {
        "emailNotifications",
        "expiryAlerts",
        "dailyDigest",
    }

    for key in allowed:
        if key in data:
            _preferences[key] = bool(data[key])

    return response_data(
        preferences=_preferences.copy(),
        message="Preferences updated.",
    )


@notification_bp.route("/test-email", methods=["POST"])
def test_email():
    if not smtp_is_configured():
        return jsonify({
            "success": False,
            "error": "SMTP is not configured. Check the Render environment variables.",
        }), 503

    data = request.get_json(silent=True) or {}
    recipient = (
        data.get("email")
        or data.get("to")
        or os.environ.get("SMTP_USER", "")
    ).strip()

    if not recipient or "@" not in recipient:
        return jsonify({
            "success": False,
            "error": "Provide a valid email address.",
        }), 400

    try:
        send_email(
            recipient,
            "ExpiryCare - Test Email",
            (
                "Hello!\n\n"
                "This is a test email from ExpiryCare.\n"
                "Your Gmail SMTP connection is working.\n\n"
                "ExpiryCare"
            ),
        )

        return response_data(
            message="Test email sent successfully."
        )

    except Exception:
        logger.exception("ExpiryCare test email failed")
        return jsonify({
            "success": False,
            "error": (
                "Email could not be sent. Check the SMTP settings "
                "and Render logs."
            ),
        }), 500


@notification_bp.route("/process", methods=["POST"])
def process_notifications():
    if not smtp_is_configured():
        return jsonify({
            "success": False,
            "error": "SMTP is not configured.",
        }), 503

    # This endpoint does not yet scan saved products.
    # Product database integration is required for real expiry alerts.
    return response_data(
        processed=0,
        message=(
            "Notification API is running. Automatic expiry scanning "
            "still needs to be connected to the product database."
        ),
    )
