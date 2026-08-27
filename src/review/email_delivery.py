"""Provider-neutral reviewer email delivery with SMTP and Resend adapters."""

import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import parseaddr

import requests


RESEND_EMAIL_URL = "https://api.resend.com/emails"
EMAIL_TIMEOUT_SECONDS = 10


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


def _resend_sender_address(value):
    sender = _safe_header(value, "Sender")
    _display_name, address = parseaddr(sender)
    local, separator, domain = address.rpartition("@")
    has_display = "<" in sender or ">" in sender
    format_valid = (
        sender.endswith(">") and sender.count("<") == sender.count(">") == 1
        if has_display else address == sender
    )
    if (not format_valid or not separator or not local or not domain
            or "." not in domain or any(character.isspace() for character in address)):
        raise EmailConfigurationError("Reviewer email sender is malformed")
    return sender


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


def resend_sender_from_env(environ=None):
    env = os.environ if environ is None else environ
    if env.get("REVIEWER_EMAIL_BACKEND", "").strip().lower() != "resend":
        raise EmailConfigurationError("Reviewer email backend is not configured")
    sender = _resend_sender_address(env.get("REVIEWER_EMAIL_FROM", "").strip())
    api_key = env.get("RESEND_API_KEY", "").strip()
    if not api_key:
        raise EmailConfigurationError("RESEND_API_KEY is required")

    def send(recipient, verification_url, expires_minutes):
        message = magic_link_message(sender, recipient, verification_url, expires_minutes)
        try:
            response = requests.post(
                RESEND_EMAIL_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "dmv-bus-stops-reviewer-email/1",
                },
                json={
                    "from": sender,
                    "to": [str(message["To"])],
                    "subject": str(message["Subject"]),
                    "text": message.get_content(),
                },
                timeout=EMAIL_TIMEOUT_SECONDS,
            )
            if not 200 <= response.status_code < 300:
                raise RuntimeError("Resend email delivery failed")
            payload = response.json()
            if not isinstance(payload, dict) or not isinstance(payload.get("id"), str) \
                    or not payload["id"].strip():
                raise RuntimeError("Resend email delivery failed")
        except (requests.RequestException, ValueError):
            raise RuntimeError("Resend email delivery failed") from None

    return send


def email_sender_from_env(environ=None):
    env = os.environ if environ is None else environ
    backend = env.get("REVIEWER_EMAIL_BACKEND", "").strip().lower()
    if backend == "smtp":
        return smtp_sender_from_env(env)
    if backend == "resend":
        return resend_sender_from_env(env)
    raise EmailConfigurationError("Reviewer email backend is not configured")


def email_required_configuration(environ=None):
    env = os.environ if environ is None else environ
    backend = env.get("REVIEWER_EMAIL_BACKEND", "").strip().lower()
    common = ["REVIEWER_EMAIL_BACKEND", "REVIEWER_EMAIL_FROM"]
    if backend == "resend":
        return common + ["RESEND_API_KEY"]
    if backend == "smtp":
        return common + ["SMTP_HOST", "SMTP_PORT", "SMTP_USE_TLS"]
    return common


def email_delivery_status(configured_sender=None, environ=None):
    if configured_sender:
        return {"available": True, "backend": "injected"}
    env = os.environ if environ is None else environ
    backend = env.get("REVIEWER_EMAIL_BACKEND", "").strip().lower() or None
    try:
        email_sender_from_env(env)
    except EmailConfigurationError as exc:
        return {"available": False, "backend": backend, "reason": str(exc)}
    return {"available": True, "backend": backend}
