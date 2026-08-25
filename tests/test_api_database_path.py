import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "src" / "api" / "app.py"


class ApiDatabasePathTests(unittest.TestCase):
    def imported_database_path(self, override=None):
        env = os.environ.copy()
        if override is None:
            env.pop("DMV_BUS_STOPS_DB", None)
        else:
            env["DMV_BUS_STOPS_DB"] = str(override)
        output = subprocess.check_output(
            [
                sys.executable,
                "-c",
                "from src.api.app import DATABASE_PATH; print(DATABASE_PATH)",
            ],
            cwd=ROOT,
            env=env,
            text=True,
        )
        return Path(output.strip())

    def test_default_database_path_remains_repo_relative(self):
        self.assertEqual(
            ROOT / "src" / "database" / "dmv_bus_stops.db",
            self.imported_database_path(),
        )

    def test_environment_override_is_honored(self):
        override = ROOT / "configured" / "override.db"
        self.assertEqual(override, self.imported_database_path(override))
        env = os.environ.copy()
        env["DMV_BUS_STOPS_DB"] = str(override)
        output = subprocess.check_output(
            [sys.executable, "-c",
             "from src.api.app import DATABASE_PATH; "
             "from src.review.assignment_router import DB; print(DATABASE_PATH); print(DB)"],
            cwd=ROOT, env=env, text=True,
        ).splitlines()
        self.assertEqual([str(override), str(override)], output)

        with tempfile.TemporaryDirectory() as temp_dir:
            migrated = Path(temp_dir) / "review.db"
            conn = sqlite3.connect(migrated)
            conn.executescript("""
                CREATE TABLE community_reviewers (
                    id INTEGER PRIMARY KEY, reviewer_key TEXT UNIQUE,
                    created_at TEXT
                );
                CREATE TABLE stop_review_assignments (
                    id INTEGER PRIMARY KEY, stop_id INTEGER NOT NULL,
                    reviewer_id INTEGER NOT NULL, scenario TEXT NOT NULL,
                    status TEXT, created_at TEXT, completed_at TEXT
                );
                INSERT INTO stop_review_assignments VALUES
                    (41,7,3,'opportunity','completed','2025-01-01','2025-01-02');
            """)
            conn.commit()
            conn.close()
            migration_env = os.environ.copy()
            migration_env["DMV_BUS_STOPS_DB"] = str(migrated)
            command = [sys.executable, "scripts/active/create_review_tables.py"]
            subprocess.check_call(command, cwd=ROOT, env=migration_env)
            subprocess.check_call(command, cwd=ROOT, env=migration_env)
            conn = sqlite3.connect(migrated)
            self.assertIn("campaign", {
                row[1] for row in conn.execute(
                    "PRAGMA table_info(stop_review_assignments)"
                )
            })
            self.assertEqual(
                (41, 7, 3, "opportunity", None, "completed"),
                conn.execute("""
                    SELECT id,stop_id,reviewer_id,scenario,campaign,status
                    FROM stop_review_assignments WHERE id=41
                """).fetchone(),
            )
            self.assertEqual(1, conn.execute(
                "SELECT COUNT(*) FROM stop_review_assignments"
            ).fetchone()[0])
            conn.close()

    def test_app_has_no_cwd_relative_production_database_literal(self):
        source = APP_PATH.read_text(encoding="utf-8")
        self.assertNotIn('sqlite3.connect("src/database/dmv_bus_stops.db")', source)
        self.assertNotIn('"src/database/dmv_bus_stops.db"', source)


if __name__ == "__main__":
    unittest.main()
