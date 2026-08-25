"""Provider-neutral reviewer email delivery with an optional SMTP adapter."""

import os
import smtplib
import ssl
from email.message import EmailMessage


class EmailConfigurationError(RuntimeError):
    pass


def _safe_header(value, name):
    text = str(value or "")
    if not text or any(ord(character) < 32 for character in text):
        raise EmailConfigurationError(f"{name} contains invalid characters")
    return text


def magic_link_message(sender, recipient, verification_url, expires_minutes):
    sender = _safe_header(sender, "Sender")
    recipient = _safe_header(recipient, "Recipient")
    message = EmailMessage()
    message["Subject"] = "Sign in to DMV Bus Stops"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        "Use this link to sign in to your DMV Bus Stops reviewer profile:\n\n"
        f"{verification_url}\n\n"
        f"This link expires in {expires_minutes} minutes and can only be used once.\n\n"
        "If you did not request this email, you can ignore it."
    )
    return message


def smtp_sender_from_env(environ=None):
    env = os.environ if environ is None else environ
    if env.get("REVIEWER_EMAIL_BACKEND", "").strip().lower() != "smtp":
        raise EmailConfigurationError("Reviewer email backend is not configured")
    sender = env.get("REVIEWER_EMAIL_FROM", "").strip()
    host = env.get("SMTP_HOST", "").strip()
    port_value = env.get("SMTP_PORT", "").strip()
    try:
        port = int(port_value)
    except ValueError as exc:
        raise EmailConfigurationError("SMTP_PORT must be an integer") from exc
    username, password = env.get("SMTP_USERNAME"), env.get("SMTP_PASSWORD")
    if not sender or not host or not port_value or not (1 <= port <= 65535):
        raise EmailConfigurationError("SMTP sender, host, and valid port are required")
    _safe_header(sender, "Sender")
    if bool(username) != bool(password):
        raise EmailConfigurationError("SMTP username and password must be configured together")
    tls_value = env.get("SMTP_USE_TLS", "1")
    if tls_value not in ("0", "1"):
        raise EmailConfigurationError("SMTP_USE_TLS must be 0 or 1")
    use_tls = tls_value == "1"

    def send(recipient, verification_url, expires_minutes):
        message = magic_link_message(sender, recipient, verification_url, expires_minutes)
        with smtplib.SMTP(host, port, timeout=10) as client:
            if use_tls:
                client.starttls(context=ssl.create_default_context())
            if username:
                client.login(username, password)
            client.send_message(message)

    return send


def email_delivery_status(configured_sender=None, environ=None):
    if configured_sender:
        return {"available": True, "backend": "injected"}
    try:
        smtp_sender_from_env(environ)
    except EmailConfigurationError as exc:
        return {"available": False, "backend": None, "reason": str(exc)}
    return {"available": True, "backend": "smtp"}
