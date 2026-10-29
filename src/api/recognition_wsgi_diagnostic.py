"""Temporary private, once-per-worker observation; grants no recognition authority."""

import json
import os
from pathlib import Path
import socket
import sqlite3
import sys
import threading


MARKER = "RECOGNITION_WSGI_IDENTITY_DIAGNOSTIC"


def _error(exc):
    # Never include exception text, SQL, environment, key paths or file contents.
    if isinstance(exc, FileNotFoundError):
        return "missing_file"
    if isinstance(exc, PermissionError):
        return "permission_denied"
    if isinstance(exc, sqlite3.Error):
        return "sqlite_error"
    return "observation_failed"


def log_observation(logger, target, control):
    """Stat both configured files; inspect only target schema over read-only SQLite."""
    record = {"event": MARKER, "hostname": socket.gethostname(), "pid": os.getpid(),
              "python_version": sys.version, "python_executable": sys.executable}
    for name, configured in (("target", target), ("control", control)):
        result = record[name] = {}
        try:
            if not configured or not Path(configured).is_absolute():
                result["error"] = "absolute_path_not_configured"
                continue
            path = Path(configured).resolve(strict=True)
            result["resolved_path"] = str(path)
            stat = path.stat()
            result.update(st_dev=stat.st_dev, st_ino=stat.st_ino)
            if not path.is_file():
                result["error"] = "not_regular_file"
                continue
            if name == "target":
                from src.review.recognition.administration import observe_target
                conn = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=1)
                try:
                    conn.execute("PRAGMA query_only=ON")
                    conn.execute("BEGIN")
                    observed = observe_target(conn)
                    result["schema_sha256"] = observed["schema_sha256"]
                    result["observation_matches_stat"] = observed["observation"] == {
                        "hostname": record["hostname"], "database": str(path),
                        "device": stat.st_dev, "inode": stat.st_ino}
                finally:
                    conn.close()
        except Exception as exc:
            result["error"] = _error(exc)
    logger.warning("%s %s", MARKER, json.dumps(record, sort_keys=True))


def register(app, target_path):
    """Use a private request hook so preloaded imports cannot impersonate workers.

    No route or response data is added. One attempt per PID, including failures.
    Remove this temporary hook/module after collecting the deployment evidence.
    """
    lock = threading.Lock()
    attempted = set()

    @app.before_request
    def recognition_wsgi_identity_diagnostic():
        if app.testing:
            return
        with lock:
            pid = os.getpid()
            if pid in attempted:
                return
            attempted.add(pid)
        try:
            log_observation(app.logger, target_path(), app.config.get("RECOGNITION_ADMIN_CONTROL"))
        except Exception:
            # Even observation/logging failures must never prevent serving requests.
            try:
                app.logger.warning("%s %s", MARKER,
                                   '{"error":"diagnostic_failed"}')
            except Exception:
                pass
