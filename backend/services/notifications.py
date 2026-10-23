"""Provider-backed expiry notification delivery.

Configure SMTP for email and Twilio for SMS using environment variables.
Provider calls return explicit success/failure; this module never pretends an
unconfigured provider has delivered a notification.
"""
import os
import smtplib
import logging
from email.message import EmailMessage
from typing import Dict, Any, Tuple
from urllib.parse import quote
import requests

log = logging.getLogger("expirycare.notifications")


def send_email(to_email: str, subject: str, text_body: str) -> Tuple[bool, str]:
    host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "")
    sender = os.getenv("SMTP_FROM", username).strip()
    if not (username and password and sender and to_email):
        return False, "email_provider_not_configured"
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email
    msg.set_content(text_body)
    try:
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(username, password)
            smtp.send_message(msg)
        return True, "accepted_by_smtp"
    except Exception as exc:
        log.warning("Email provider failed (%s)", type(exc).__name__)
        return False, "email_provider_error"


def send_sms(to_phone: str, text_body: str) -> Tuple[bool, str]:
    sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    token = os.getenv("TWILIO_AUTH_TOKEN", "")
    sender = os.getenv("TWILIO_FROM_NUMBER", "").strip()
    if not (sid and token and sender and to_phone):
        return False, "sms_provider_not_configured"
    try:
        response = requests.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
            auth=(sid, token),
            data={"From": sender, "To": to_phone, "Body": text_body[:1500]},
            timeout=20,
        )
        if response.status_code not in (200, 201):
            log.warning("SMS provider returned HTTP %s", response.status_code)
            return False, "sms_provider_error"
        return True, "accepted_by_twilio"
    except Exception as exc:
        log.warning("SMS provider failed (%s)", type(exc).__name__)
        return False, "sms_provider_error"


def expiry_message(name: str, expiry_date: str, days: int) -> Tuple[str, str]:
    if days < 0:
        state = f"expired {abs(days)} day(s) ago"
    elif days == 0:
        state = "expires today"
    else:
        state = f"expires in {days} day(s)"
    subject = f"ExpiryCare reminder: {name} {state}"
    body = (
        f"ExpiryCare expiry reminder\n\n{name} {state}.\n"
        f"Recorded expiry date: {expiry_date}.\n\n"
        "Please verify the date on the physical package. This reminder is "
        "not a safety assessment. Follow the product label and consult a "
        "qualified professional when needed."
    )
    return subject, body
