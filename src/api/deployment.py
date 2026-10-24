"""Production-pilot startup validation and non-sensitive logging configuration."""

from __future__ import annotations

import logging
import os
from pathlib import Path


PLACEHOLDER_FRAGMENTS = ("replace-with", "example.invalid")


def configured_database(env=None):
    """Resolve only an explicitly configured absolute web-runtime target.

    No fallback, SQLite connection, file creation, or migration. An unconfigured
    import remains possible for tooling; serving requests fails closed.
    """
    env = os.environ if env is None else env
    raw = env.get('DMV_BUS_STOPS_DB', '')
    if not raw or not Path(raw).is_absolute():
        return None
    return Path(raw).resolve()


def recognition_admin_configuration(target, control, key_file):
    """Explicit local control configuration; no reads, install or permission grant."""
    if not control and not key_file:
        return None
    from src.review.recognition.administration import AdminError, LocalAdministration
    if not target or not control or not key_file:
        raise AdminError("complete_administrative_configuration_required", 503)
    result = LocalAdministration(Path(target), Path(control), Path(key_file))
    result.paths()
    return result


def validate_pilot_environment(env=None):
    env = os.environ if env is None else env
    errors = []
    secret = env.get("FLASK_SECRET_KEY", "")
    if len(secret) < 32 or any(item in secret.lower() for item in PLACEHOLDER_FRAGMENTS):
        errors.append("FLASK_SECRET_KEY must be a persistent non-placeholder value of at least 32 characters")

    raw_database = env.get("DMV_BUS_STOPS_DB", "")
    database = Path(raw_database) if raw_database else None
    if database is None or not database.is_absolute():
        errors.append("DMV_BUS_STOPS_DB must be an explicit absolute path")
    elif not database.is_file():
        errors.append("DMV_BUS_STOPS_DB must identify an existing database file")

    if env.get("SESSION_COOKIE_SECURE") != "1":
        errors.append("SESSION_COOKIE_SECURE must be 1 for the HTTPS pilot")
    if env.get("REVIEWER_AUTH_DEV_MODE") == "1":
        errors.append("REVIEWER_AUTH_DEV_MODE must be unset or 0")

    recognition_capture = env.get("LIVE_RECOGNITION_CAPTURE", "0")
    if recognition_capture not in ("0", "1"):
        errors.append("LIVE_RECOGNITION_CAPTURE must be 0 or 1")
    support = env.get("PILOT_SUPPORT_CONTACT", "").strip()
    if not support or any(item in support.lower() for item in PLACEHOLDER_FRAGMENTS):
        errors.append("PILOT_SUPPORT_CONTACT must name the monitored pilot contact")

    email_backend = env.get("REVIEWER_EMAIL_BACKEND", "").strip().lower()
    if email_backend and email_backend not in ("smtp", "resend"):
        errors.append("REVIEWER_EMAIL_BACKEND must be unset, smtp, or resend")
    if email_backend in ("smtp", "resend"):
        try:
            from src.review.email_delivery import email_sender_from_env
            email_sender_from_env(env)
        except Exception as exc:
            errors.append(f"email login configuration is incomplete: {exc}")

    level = env.get("LOG_LEVEL", "INFO").upper()
    if level not in logging.getLevelNamesMapping():
        errors.append("LOG_LEVEL must be a standard Python logging level")
    port = env.get("PILOT_BIND_PORT", "8080")
    try:
        if not 1 <= int(port) <= 65535:
            raise ValueError
    except ValueError:
        errors.append("PILOT_BIND_PORT must be an integer from 1 through 65535")

    if errors:
        raise RuntimeError("Pilot startup configuration is invalid:\n- " + "\n- ".join(errors))
    return database.resolve()


def configure_logging(app, env=None):
    env = os.environ if env is None else env
    level = getattr(logging, env.get("LOG_LEVEL", "INFO").upper())
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    app.logger.setLevel(level)
    # Ordinary Waitress access lines can contain magic-link query strings.
    # Application audit events below deliberately log path only, never query/body.
    logging.getLogger("waitress").setLevel(logging.WARNING)
