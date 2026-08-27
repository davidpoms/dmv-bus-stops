import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from scripts.active.backup_database import create_verified_backup
from src.api import app as api
from src.api.deployment import validate_pilot_environment


class PilotDeploymentTests(unittest.TestCase):
    def valid_environment(self, database):
        return {
            "FLASK_SECRET_KEY": "x" * 64,
            "DMV_BUS_STOPS_DB": str(database.resolve()),
            "SESSION_COOKIE_SECURE": "1",
            "PILOT_SUPPORT_CONTACT": "pilot@example.org",
            "PILOT_BIND_PORT": "8080",
            "LOG_LEVEL": "INFO",
        }

    def test_production_environment_requires_explicit_safe_values(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / ".tmp") as raw:
            database = Path(raw) / "pilot.db"
            sqlite3.connect(database).close()
            self.assertEqual(database.resolve(), validate_pilot_environment(
                self.valid_environment(database)
            ))
            for key in ("FLASK_SECRET_KEY", "DMV_BUS_STOPS_DB",
                        "SESSION_COOKIE_SECURE", "PILOT_SUPPORT_CONTACT"):
                broken = self.valid_environment(database)
                broken.pop(key)
                with self.subTest(key=key), self.assertRaises(RuntimeError):
                    validate_pilot_environment(broken)

    def test_email_is_optional_but_partial_smtp_fails(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / ".tmp") as raw:
            database = Path(raw) / "pilot.db"
            sqlite3.connect(database).close()
            environment = self.valid_environment(database)
            environment["REVIEWER_EMAIL_BACKEND"] = "smtp"
            with self.assertRaisesRegex(RuntimeError, "email login configuration"):
                validate_pilot_environment(environment)

    def test_backup_is_verified_preserves_rows_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / ".tmp") as raw:
            root = Path(raw)
            source, backup = root / "source.db", root / "backup.db"
            with closing(sqlite3.connect(source)) as conn, conn:
                conn.executescript("""
                  CREATE TABLE stop_gtfs_status(physical_stop_id INTEGER,current_gtfs INTEGER);
                  INSERT INTO stop_gtfs_status VALUES(1,1);
                  CREATE TABLE community_reviewers(id INTEGER PRIMARY KEY);
                  INSERT INTO community_reviewers VALUES(7);
                  CREATE TABLE stop_observations(id INTEGER PRIMARY KEY);
                  INSERT INTO stop_observations VALUES(9);
                """)
            result = create_verified_backup(source, backup)
            self.assertEqual("ok", result["integrity_check"])
            self.assertEqual((1, 1, 1), (
                result["active_stops"], result["reviewers"], result["observations"]
            ))
            with self.assertRaises(FileExistsError):
                create_verified_backup(source, backup)

    def test_support_contact_is_visible_without_exposing_configuration(self):
        with patch.dict("os.environ", {"PILOT_SUPPORT_CONTACT": "help@example.org"}):
            api.app.config.update(TESTING=True)
            page = api.app.test_client().get("/dashboard").get_data(as_text=True)
        self.assertIn("help@example.org", page)
        self.assertNotIn("FLASK_SECRET_KEY", page)

    def test_runtime_has_no_request_body_or_session_debug_prints(self):
        source = (Path(__file__).resolve().parents[1] / "src/api/app.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("SUBMIT DATA:", source)
        self.assertNotIn("ASSIGNMENT DEBUG:", source)
        self.assertNotIn('"REVIEWER:"', source)
        self.assertIn("pilot_request_failed", source)


if __name__ == "__main__":
    unittest.main()
