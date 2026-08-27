import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import src.api.app as public_api
import scripts.active.set_reviewer_role as role_script
from scripts.active.set_reviewer_role import set_reviewer_role
from src.review.admin_dashboard import build_pilot_summary, review_lead_access


ROOT = Path(__file__).resolve().parents[1]


class PilotAdminDashboardTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = Path(self.temp_dir.name) / "admin.db"
        self.now = datetime(2026, 8, 27, 12, tzinfo=timezone.utc)
        conn = sqlite3.connect(self.db)
        conn.executescript(
            """
            CREATE TABLE community_reviewers(
              id INTEGER PRIMARY KEY,reviewer_key TEXT UNIQUE,display_name TEXT,
              email TEXT,email_verified_at TEXT,role TEXT NOT NULL DEFAULT 'reviewer');
            CREATE TABLE physical_stops(id INTEGER PRIMARY KEY,primary_name TEXT);
            CREATE TABLE stop_gtfs_status(physical_stop_id INTEGER,current_gtfs INTEGER);
            CREATE TABLE stop_jurisdiction(
              stop_id INTEGER PRIMARY KEY,state TEXT,dc_ward TEXT,dc_anc TEXT,
              county TEXT,municipality TEXT);
            CREATE TABLE stop_observations(
              id INTEGER PRIMARY KEY,physical_stop_id INTEGER,reviewer_id INTEGER,
              source TEXT,review_mode TEXT,observed_at TEXT,
              shelter_present TEXT,bench_present TEXT);
            CREATE TABLE stop_amenity_status(
              physical_stop_id INTEGER,amenity_type TEXT,derived_status TEXT,
              evidence_conflict INTEGER,consensus_conflicts_with_other_evidence INTEGER,
              community_yes_count INTEGER,community_no_count INTEGER);
            CREATE TABLE stop_amenity_review_priority(
              physical_stop_id INTEGER,amenity_type TEXT,workflow_state TEXT,
              review_priority_score REAL);
            CREATE TABLE physical_stop_identity_state(
              physical_stop_id INTEGER,identity_status TEXT);
            CREATE TABLE bus_stops(id INTEGER PRIMARY KEY);
            CREATE TABLE physical_stop_members(physical_stop_id INTEGER,bus_stop_id INTEGER);
            CREATE TABLE routes(id INTEGER PRIMARY KEY,route_id TEXT);
            CREATE TABLE stop_routes(stop_id INTEGER,route_id INTEGER);
            """
        )
        conn.executemany(
            "INSERT INTO community_reviewers VALUES (?,?,?,?,?,?)",
            [
                (1, "lead", "Lead Person", "lead@example.com", "2026-01-01", "review_lead"),
                (2, "reviewer", "", "reviewer@example.com", "2026-01-01", "reviewer"),
                (3, "anon", None, None, None, "reviewer"),
            ],
        )
        conn.executemany("INSERT INTO physical_stops VALUES (?,?)",
                         [(1, "DC Stop"), (2, "Retired Stop"), (3, "Virginia Stop")])
        conn.executemany("INSERT INTO stop_gtfs_status VALUES (?,?)",
                         [(1, 1), (2, 0), (3, 1)])
        conn.executemany("INSERT INTO stop_jurisdiction VALUES (?,?,?,?,?,?)", [
            (1, "DC", "1", "1A", None, "Washington"),
            (2, "MD", None, None, "Old County", None),
            (3, "VA", None, None, "Arlington County", "Arlington"),
        ])
        conn.executemany(
            "INSERT INTO stop_observations VALUES (?,?,?,?,?,?,?,?)",
            [
                (1, 1, 1, "community_review", "in_person",
                 (self.now - timedelta(days=1)).isoformat(), "yes", "yes"),
                (2, 1, 1, "community_review", "remote",
                 (self.now - timedelta(days=10)).isoformat(), "yes", "no"),
                (3, 2, 2, "community_review", "in_person",
                 (self.now - timedelta(days=40)).isoformat(), "no", "no"),
                (4, 3, 2, "community_review", "in_person",
                 (self.now - timedelta(days=2)).isoformat(), "unknown", "unknown"),
            ],
        )
        conn.executemany(
            "INSERT INTO stop_amenity_status VALUES (?,?,?,?,?,?,?)",
            [
                (1, "bench", "confirmed_yes", 0, 0, 1, 1),
                (1, "shelter", "likely_yes", 0, 0, 2, 0),
                (3, "bench", "unknown", 1, 0, 0, 0),
                (3, "shelter", "unknown", 0, 0, 0, 0),
            ],
        )
        conn.executemany(
            "INSERT INTO stop_amenity_review_priority VALUES (?,?,?,?)",
            [(1, "bench", "consensus_reached", 90),
             (1, "shelter", "one_observation_short", 80),
             (3, "bench", "no_evidence", 20),
             (3, "shelter", "no_evidence", 10)],
        )
        conn.executemany("INSERT INTO physical_stop_identity_state VALUES (?,?)",
                         [(1, "current"), (2, "retired"), (3, "manual_exception")])
        conn.executemany("INSERT INTO bus_stops VALUES (?)", [(1,), (2,), (3,)])
        conn.executemany("INSERT INTO physical_stop_members VALUES (?,?)",
                         [(1, 1), (2, 2), (3, 3)])
        conn.execute("INSERT INTO routes VALUES (1,'A1')")
        conn.executemany("INSERT INTO stop_routes VALUES (?,1)", [(1,), (3,)])
        conn.commit()
        conn.close()
        self.path_patch = patch.object(public_api, "DATABASE_PATH", self.db)
        self.path_patch.start()
        public_api.app.config.update(TESTING=True, SECRET_KEY="admin-test-secret")
        self.client = public_api.app.test_client()

    def tearDown(self):
        self.path_patch.stop()
        self.temp_dir.cleanup()

    def login(self, reviewer_id, reviewer_key):
        with self.client.session_transaction() as session:
            session["authenticated_reviewer_id"] = reviewer_id
            session["reviewer_key"] = reviewer_key

    def test_authorization_is_server_side_for_page_and_api(self):
        for path in ("/admin", "/api/admin/pilot-summary"):
            self.assertEqual(401, self.client.get(path).status_code)
        with self.client.session_transaction() as session:
            session["reviewer_key"] = "anon"
        self.assertEqual(401, self.client.get("/admin").status_code)
        self.login(2, "reviewer")
        self.assertEqual(403, self.client.get("/admin").status_code)
        self.assertEqual(403, self.client.get("/api/admin/pilot-summary").status_code)
        self.login(1, "wrong-key")
        self.assertEqual(401, self.client.get("/admin").status_code)
        self.login(1, "lead")
        self.assertEqual(200, self.client.get("/admin").status_code)
        self.assertEqual(200, self.client.get("/api/admin/pilot-summary").status_code)

    def test_profile_admin_link_uses_the_same_server_authorization(self):
        self.login(2, "reviewer")
        ordinary = self.client.get("/reviewer/profile").get_data(as_text=True)
        self.assertNotIn('href="/admin"', ordinary)
        self.assertIn("Set or update favorite routes", ordinary)
        self.assertNotIn("reviewer@example.com", ordinary)

        self.login(1, "lead")
        lead = self.client.get("/reviewer/profile").get_data(as_text=True)
        self.assertIn('href="/admin"', lead)
        self.assertIn("Pilot review dashboard", lead)
        self.assertNotIn("lead@example.com", lead)

    def test_missing_role_schema_fails_admin_routes_safely(self):
        conn = sqlite3.connect(self.db)
        conn.execute("ALTER TABLE community_reviewers RENAME TO reviewers_with_role")
        conn.execute("""CREATE TABLE community_reviewers(
            id INTEGER PRIMARY KEY,reviewer_key TEXT,display_name TEXT,
            email TEXT,email_verified_at TEXT)""")
        conn.execute("""INSERT INTO community_reviewers
            SELECT id,reviewer_key,display_name,email,email_verified_at
            FROM reviewers_with_role""")
        conn.commit(); conn.close()
        self.login(1, "lead")
        self.assertEqual(503, self.client.get("/admin").status_code)
        self.assertEqual(503, self.client.get("/api/admin/pilot-summary").status_code)
        profile = self.client.get("/reviewer/profile").get_data(as_text=True)
        self.assertNotIn('href="/admin"', profile)

    def test_metrics_privacy_active_scope_and_read_only_get(self):
        before = hashlib.sha256(self.db.read_bytes()).hexdigest()
        self.login(1, "lead")
        self.assertEqual(200, self.client.get("/admin").status_code)
        response = self.client.get("/api/admin/pilot-summary")
        self.assertEqual(200, response.status_code)
        data = response.get_json()
        self.assertEqual({
            "total_reviewers": 3, "active_reviewers_7d": 2,
            "active_reviewers_30d": 2, "reviews_total": 4,
            "reviews_7d": 2, "reviews_30d": 3,
            "median_reviews_per_contributor": 2.0,
            "repeat_reviewers": 2, "repeat_observation_rate": 0.5,
        }, data["activity"])
        self.assertEqual(2, data["coverage"]["active_stops"])
        self.assertEqual(2, data["coverage"]["distinct_active_stops_reviewed"])
        self.assertEqual(1, data["coverage"]["stops_with_2plus_observations"])
        self.assertEqual(1, data["quality"]["stops_with_reached_consensus"])
        self.assertEqual(1, data["quality"]["stops_near_consensus"])
        self.assertEqual(1, data["quality"]["community_conflict_stops"])
        self.assertEqual(1, data["quality"]["canonical_evidence_conflict_stops"])
        self.assertEqual(1, data["quality"]["unknown_bench_stops"])
        self.assertEqual(1, data["quality"]["unknown_shelter_stops"])
        states = {row["value"] for row in data["coverage"]["geography"]["state"]}
        self.assertEqual({"DC", "VA"}, states)
        self.assertEqual(1, data["needs_attention"]["manual_identity_exceptions"])
        self.assertTrue(any(not row["active_stop"] for row in data["recent_reviews"]))
        body = response.get_data(as_text=True).lower()
        for private in ("lead@example.com", "reviewer@example.com", '"email":',
                        '"token_hash":', '"auth_csrf":', '"session_id":',
                        '"source_key":', '"email_verified_at":'):
            self.assertNotIn(private, body)
        self.assertEqual(before, hashlib.sha256(self.db.read_bytes()).hexdigest())

    def test_metric_window_definitions_use_observation_timestamps(self):
        conn = sqlite3.connect(self.db)
        try:
            result = build_pilot_summary(conn, now=self.now)
        finally:
            conn.close()
        self.assertIn("submitted community observation",
                      result["definitions"]["active_reviewer"])
        self.assertIn("may represent multiple served routes",
                      result["definitions"]["route_coverage"])
        self.assertEqual(2, result["activity"]["active_reviewers_7d"])
        self.assertEqual(3, result["activity"]["reviews_30d"])


class ReviewerRoleMigrationAndCommandTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = Path(self.temp_dir.name) / "legacy.db"
        conn = sqlite3.connect(self.db)
        conn.executescript("""
          CREATE TABLE community_reviewers(
            id INTEGER PRIMARY KEY,reviewer_key TEXT,created_at TEXT);
          INSERT INTO community_reviewers VALUES (7,'keep','2020-01-01');
        """)
        conn.commit()
        conn.close()

    def tearDown(self):
        self.temp_dir.cleanup()

    def run_migration(self):
        env = os.environ.copy()
        env["DMV_BUS_STOPS_DB"] = str(self.db)
        return subprocess.run(
            [sys.executable, "scripts/active/create_review_tables.py"],
            cwd=ROOT, env=env, text=True, capture_output=True,
        )

    def test_migration_is_idempotent_preserves_rows_and_constrains_roles(self):
        self.assertEqual(0, self.run_migration().returncode)
        self.assertEqual(0, self.run_migration().returncode)
        conn = sqlite3.connect(self.db)
        self.assertEqual((7, "keep", "reviewer"), conn.execute(
            "SELECT id,reviewer_key,role FROM community_reviewers"
        ).fetchone())
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("UPDATE community_reviewers SET role='owner' WHERE id=7")
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("UPDATE community_reviewers SET role=NULL WHERE id=7")
        conn.close()
        schema = (ROOT / "src" / "database" / "schema.sql").read_text(
            encoding="utf-8"
        )
        self.assertIn("role IN ('reviewer', 'review_lead')", schema)

    def test_role_command_promotes_demotes_and_rejects_invalid_input(self):
        self.assertEqual(0, self.run_migration().returncode)
        conn = sqlite3.connect(self.db)
        self.assertEqual("review_lead", set_reviewer_role(
            conn, 7, "review_lead"
        )["after"])
        self.assertEqual("reviewer", set_reviewer_role(conn, 7, "reviewer")["after"])
        with self.assertRaises(ValueError):
            set_reviewer_role(conn, 99, "review_lead")
        with self.assertRaises(ValueError):
            set_reviewer_role(conn, 7, "administrator")
        conn.close()
        result = subprocess.run(
            [sys.executable, "scripts/active/set_reviewer_role.py",
             "--db", str(self.db), "--reviewer-id", "7", "--role", "review_lead"],
            cwd=ROOT, text=True, capture_output=True,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("reviewer -> review_lead", result.stdout)

    def test_role_migration_is_required_and_protected_path_needs_override(self):
        conn = sqlite3.connect(self.db)
        self.assertEqual(
            (False, "role_migration_required"),
            review_lead_access(conn, 7, "keep"),
        )
        conn.close()
        with patch.object(role_script, "DEFAULT_PRODUCTION_DB", self.db.resolve()):
            with self.assertRaises(SystemExit):
                role_script.main([
                    "--db", str(self.db), "--reviewer-id", "7",
                    "--role", "review_lead",
                ])


if __name__ == "__main__":
    unittest.main()
