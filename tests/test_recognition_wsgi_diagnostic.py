"""Temporary worker diagnostics must never grant authority or mutate storage."""

import hashlib
import builtins
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock, patch

from flask import Flask

from src.api import recognition_wsgi_diagnostic as diagnostic
from src.review.recognition import administration as administration


class WsgiDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory()
        self.addCleanup(self.workspace.cleanup)
        root = Path(self.workspace.name)
        self.target, self.control, self.key = (root / name for name in ("target.db", "control.db", "key"))
        with closing(sqlite3.connect(self.target)) as conn:
            with conn:
                conn.execute("CREATE TABLE sentinel(value TEXT)")
                conn.execute("INSERT INTO sentinel VALUES('PRIVATE_TARGET_CONTENT')")
        self.control.write_bytes(b"PRIVATE_CONTROL_CONTENT_NOT_SQLITE")
        self.key.write_text("PRIVATE_KEY_CONTENT")
        self.logger = Mock()

    def record(self):
        args = self.logger.warning.call_args.args
        self.assertEqual(args[:2], ("%s %s", diagnostic.MARKER))
        return json.loads(args[2])

    def test_read_only_observation_no_authority_key_or_control_reads(self):
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in (self.target, self.control, self.key)}
        real_connect = sqlite3.connect
        real_observe = administration.observe_target
        real_open = builtins.open
        queries = []

        def guarded_open(path, *args, **kwargs):
            self.assertNotIn(Path(path), (self.key, self.control))
            return real_open(path, *args, **kwargs)

        def reveal(exc):
            raise exc

        def connect(database, **kwargs):
            self.assertEqual(database, self.target.as_uri() + "?mode=ro")
            self.assertTrue(kwargs["uri"])
            conn = real_connect(database, **kwargs)
            conn.set_trace_callback(queries.append)
            return conn

        def observe(conn):
            self.assertEqual(conn.execute("PRAGMA query_only").fetchone()[0], 1)
            with self.assertRaises(sqlite3.OperationalError):
                conn.execute("INSERT INTO sentinel VALUES('forbidden')")
            # Even clearing query_only cannot make a mode=ro connection writable.
            conn.execute("PRAGMA query_only=OFF")
            with self.assertRaises(sqlite3.OperationalError):
                conn.execute("INSERT INTO sentinel VALUES('forbidden')")
            conn.execute("PRAGMA query_only=ON")
            return real_observe(conn)

        with patch.object(diagnostic, "_error", side_effect=reveal), \
             patch.object(diagnostic.sqlite3, "connect", side_effect=connect) as opened, \
             patch.object(administration, "observe_target", side_effect=observe), \
             patch.object(administration, "transaction", side_effect=AssertionError("no transaction")), \
             patch("src.review.recognition.authorization.verify", side_effect=AssertionError("no authorization")), \
             patch("builtins.open", side_effect=guarded_open), \
             patch.object(Path, "open", side_effect=AssertionError("no file contents")):
            diagnostic.log_observation(self.logger, self.target, self.control)
            opened.assert_called_once()
        record = self.record()
        self.assertNotIn("error", record["target"])
        self.assertNotIn("error", record["control"])
        self.assertTrue(record["target"]["observation_matches_stat"])
        self.assertEqual(len(record["target"]["schema_sha256"]), 64)
        for name, path in (("target", self.target), ("control", self.control)):
            self.assertEqual(record[name]["resolved_path"], str(path.resolve()))
            self.assertEqual(record[name]["st_dev"], path.stat().st_dev)
            self.assertEqual(record[name]["st_ino"], path.stat().st_ino)
        for field in ("hostname", "pid", "python_version", "python_executable"):
            self.assertTrue(record[field])
        serialized = json.dumps(record)
        for secret in ("PRIVATE_TARGET_CONTENT", "PRIVATE_CONTROL_CONTENT", "PRIVATE_KEY_CONTENT", str(self.key)):
            self.assertNotIn(secret, serialized)
        self.assertIn("PRAGMA query_only=ON", queries)
        self.assertEqual(before, {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in before})

    def test_private_hook_once_per_pid_uses_live_config_and_does_not_read_key(self):
        app = Flask(__name__)
        app.config["RECOGNITION_ADMIN_CONTROL"] = str(self.control)
        app.config["RECOGNITION_ADMIN_KEY_FILE"] = str(self.key)
        app.add_url_rule("/", view_func=lambda: "ordinary response")
        original_rules = list(app.url_map.iter_rules())
        diagnostic.register(app, lambda: self.target)
        self.assertEqual(original_rules, list(app.url_map.iter_rules()))
        with patch.object(diagnostic, "log_observation") as observe, \
             patch.object(app.config, "get", wraps=app.config.get) as config_get:
            client = app.test_client()
            for _ in range(2):
                self.assertEqual(client.get("/").data, b"ordinary response")
            observe.assert_called_once_with(app.logger, self.target, str(self.control))
            self.assertNotIn("RECOGNITION_ADMIN_KEY_FILE", [c.args[0] for c in config_get.call_args_list])
            with patch.object(diagnostic.os, "getpid", return_value=-100):
                self.assertEqual(client.get("/").status_code, 200)
            self.assertEqual(observe.call_count, 2)

    def test_missing_files_are_classified_and_not_created(self):
        missing = self.target.parent / "missing"
        diagnostic.log_observation(self.logger, missing, missing)
        record = self.record()
        self.assertEqual(record["target"]["error"], "missing_file")
        self.assertEqual(record["control"]["error"], "missing_file")
        self.assertFalse(missing.exists())

    def test_unreadable_target_error_is_sanitized(self):
        with patch.object(diagnostic.sqlite3, "connect", side_effect=PermissionError("PRIVATE_KEY_CONTENT")):
            diagnostic.log_observation(self.logger, self.target, self.control)
        self.assertEqual(self.record()["target"]["error"], "permission_denied")
        self.assertNotIn("PRIVATE_KEY_CONTENT", str(self.logger.warning.call_args))

    def test_failure_does_not_interrupt_worker_or_repeat(self):
        app = Flask(__name__)
        app.add_url_rule("/", view_func=lambda: "ok")
        diagnostic.register(app, lambda: self.target)
        with patch.object(diagnostic, "log_observation", side_effect=RuntimeError("private")) as observe, \
             patch.object(app.logger, "warning") as logged:
            for _ in range(2):
                self.assertEqual(app.test_client().get("/").data, b"ok")
            observe.assert_called_once()
            logged.assert_called_once()
            self.assertNotIn("private", str(logged.call_args))

    def test_missing_files_do_not_interrupt_worker(self):
        app = Flask(__name__)
        missing = self.target.parent / "missing"
        app.config["RECOGNITION_ADMIN_CONTROL"] = str(missing)
        app.add_url_rule("/", view_func=lambda: "ok")
        diagnostic.register(app, lambda: missing)
        with patch.object(app.logger, "warning") as logged:
            self.assertEqual(app.test_client().get("/").status_code, 200)
            self.assertEqual(json.loads(logged.call_args.args[2])["target"]["error"], "missing_file")


if __name__ == "__main__":
    unittest.main()
