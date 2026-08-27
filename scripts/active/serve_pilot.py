"""Run the limited pilot with Waitress after strict environment validation."""

from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.api.app import app
from src.api.deployment import configure_logging, validate_pilot_environment
from src.review.assignment_router import DB as ASSIGNMENT_DATABASE
from src.api.app import DATABASE_PATH


def main():
    database = validate_pilot_environment()
    if DATABASE_PATH.resolve() != database or ASSIGNMENT_DATABASE.resolve() != database:
        raise RuntimeError("API and assignment router are not using DMV_BUS_STOPS_DB")
    configure_logging(app)
    try:
        from waitress import serve
    except ImportError as exc:
        raise RuntimeError("Install production dependencies with: pip install -r requirements.txt") from exc
    host = os.environ.get("PILOT_BIND_HOST", "127.0.0.1")
    port = int(os.environ.get("PILOT_BIND_PORT", "8080"))
    app.logger.info(
        "pilot_start database=%s bind=%s:%s secure_cookie=true email_login=%s",
        database, host, port,
        os.environ.get("REVIEWER_EMAIL_BACKEND", "").lower() == "smtp",
    )
    serve(app, host=host, port=port, threads=4)


if __name__ == "__main__":
    main()
