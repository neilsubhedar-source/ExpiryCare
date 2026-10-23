"""Scheduled job: send opted-in expiry reminders for live Firestore users.

Run from the repository root:
    python -m backend.jobs.send_expiry_notifications
Schedule this command daily in Render Cron Jobs after configuring live
Firestore and provider environment variables.
"""
import hashlib
import logging
from datetime import date, datetime
from typing import Dict, Any

from backend.extensions import get_firestore, is_live_firestore
from backend.repositories.user_repository import UserRepository
from backend.repositories.product_repository import ProductRepository
from backend.services.notifications import send_email, send_sms, expiry_message

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("expirycare.expiry_job")


def _days_left(expiry: str):
    try:
        return (date.fromisoformat(str(expiry)[:10]) - date.today()).days
    except (TypeError, ValueError):
        return None


def run_job() -> Dict[str, Any]:
    if not is_live_firestore():
        raise RuntimeError("Live Firestore is not connected. Refusing to send from ephemeral in-memory data.")
    db = get_firestore()
    users = UserRepository()
    products = ProductRepository()
    stats = {"users": 0, "products_checked": 0, "sent": 0, "skipped": 0, "failed": 0}
    for user_doc in users.collection.stream():
        user = user_doc.to_dict() or {}
        user_id = user.get("id") or user_doc.id
        settings = user.get("settings") or {}
        email = str(user.get("email") or "").strip()
        phone = str(settings.get("phoneNumber") or user.get("phoneNumber") or "").strip()
        email_enabled = settings.get("emailNotifications") is True
        sms_enabled = settings.get("smsNotifications") is True
        if not (email_enabled or sms_enabled):
            continue
        stats["users"] += 1
        for product in products.list_by_user(user_id):
            stats["products_checked"] += 1
            expiry = str(product.get("expiryDate") or "")
            days = _days_left(expiry)
            if days is None or days > int(__import__("os").getenv("EXPIRY_REMINDER_DAYS", "7")):
                continue
            if not product.get("name") or product.get("expirySource") == "estimated":
                # Do not send confident-sounding reminders for unverified estimates.
                stats["skipped"] += 1
                continue
            subject, body = expiry_message(str(product.get("name")), expiry, days)
            for channel, enabled, destination, sender in (
                ("email", email_enabled, email, lambda: send_email(email, subject, body)),
                ("sms", sms_enabled, phone, lambda: send_sms(phone, subject + ". " + body.splitlines()[2])),
            ):
                if not enabled:
                    continue
                if not destination:
                    stats["skipped"] += 1
                    continue
                dedupe = hashlib.sha256(f"{user_id}|{product.get('id')}|{expiry}|{date.today().isoformat()}|{channel}".encode()).hexdigest()
                ref = db.collection("notification_logs").document(dedupe)
                if ref.get().exists:
                    stats["skipped"] += 1
                    continue
                ok, status = sender()
                record = {
                    "userId": user_id, "productId": product.get("id", ""),
                    "channel": channel, "expiryDate": expiry,
                    "attemptedAt": datetime.utcnow().isoformat() + "Z",
                    "status": "accepted" if ok else "failed", "providerStatus": status,
                }
                # Log every attempt so transient failures do not silently loop every minute.
                ref.set(record)
                if ok:
                    stats["sent"] += 1
                else:
                    stats["failed"] += 1
    log.info("Expiry notification run summary: %s", stats)
    return stats


if __name__ == "__main__":
    print(run_job())
