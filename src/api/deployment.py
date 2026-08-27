"""Production-pilot startup validation and non-sensitive logging configuration."""

from __future__ import annotations

import logging
import os
from pathlib import Path


PLACEHOLDER_FRAGMENTS = ("replace-with", "example.invalid")


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
    support = env.get("PILOT_SUPPORT_CONTACT", "").strip()
    if not support or any(item in support.lower() for item in PLACEHOLDER_FRAGMENTS):
        errors.append("PILOT_SUPPORT_CONTACT must name the monitored pilot contact")

    email_backend = env.get("REVIEWER_EMAIL_BACKEND", "").strip().lower()
    if email_backend and email_backend != "smtp":
        errors.append("REVIEWER_EMAIL_BACKEND must be unset or smtp")
    if email_backend == "smtp":
        try:
            from src.review.email_delivery import smtp_sender_from_env
            smtp_sender_from_env(env)
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
