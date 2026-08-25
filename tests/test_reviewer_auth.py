import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from src.api import app as review_api
from src.review import assignment_router
from src.review.auth import issue_login_token, consume_login_token, token_hash


ROOT = Path(__file__).resolve().parents[1]


class ReviewerAuthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "auth.db"
        conn = sqlite3.connect(self.db)
        conn.executescript("""
        CREATE TABLE community_reviewers(id INTEGER PRIMARY KEY AUTOINCREMENT,
          reviewer_key TEXT UNIQUE,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          display_name TEXT,profile_token TEXT,email TEXT,profile_created_at TIMESTAMP,
          email_verified_at TIMESTAMP,claimed_at TIMESTAMP);
        CREATE UNIQUE INDEX idx_community_reviewers_verified_email
          ON community_reviewers(email) WHERE email_verified_at IS NOT NULL;
        CREATE TABLE reviewer_login_tokens(id INTEGER PRIMARY KEY,reviewer_id INTEGER,
          normalized_email TEXT,token_hash TEXT UNIQUE,action TEXT,expires_at TEXT,
          used_at TEXT,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE stop_review_assignments(id INTEGER PRIMARY KEY,stop_id INTEGER,
          reviewer_id INTEGER,scenario TEXT,status TEXT);
        CREATE TABLE stop_observations(id INTEGER PRIMARY KEY,physical_stop_id INTEGER,
          reviewer_id INTEGER);
        CREATE TABLE community_stewardships(reviewer_id INTEGER,stop_id INTEGER);
        INSERT INTO community_reviewers(id,reviewer_key,display_name) VALUES(42,'anon','Alex');
        INSERT INTO stop_review_assignments VALUES(7,1,42,'direct','completed');
        INSERT INTO stop_observations VALUES(9,1,42);
        INSERT INTO community_stewardships VALUES(42,1);
        """)
        conn.commit(); conn.close()
        self.patches = [
            patch.object(review_api, "DATABASE_PATH", self.db),
            patch.object(assignment_router, "DB", self.db),
        ]
        for item in self.patches: item.start()
        review_api.app.config.update(TESTING=True, SECRET_KEY="test-secret")

    def tearDown(self):
        for item in reversed(self.patches): item.stop()
        self.temp.cleanup()

    def test_claim_same_id_then_new_device_login_and_privacy(self):
        client = review_api.app.test_client()
        with client.session_transaction() as session: session["reviewer_key"] = "anon"
        response = client.post("/reviewer/sign-in", json={"email": " Alex@Example.COM "})
        link = response.get_json()["magic_link"]
        raw = parse_qs(urlparse(link).query)["token"][0]
        conn = sqlite3.connect(self.db)
        stored = conn.execute("SELECT token_hash FROM reviewer_login_tokens").fetchone()[0]
        self.assertEqual(token_hash(raw), stored)
        self.assertNotEqual(raw, stored)
        conn.close()
        self.assertEqual(302, client.get(urlparse(link).path + "?token=" + raw).status_code)
        conn = sqlite3.connect(self.db)
        self.assertEqual((42,"Alex","alex@example.com"), conn.execute(
            "SELECT id,display_name,email FROM community_reviewers WHERE id=42").fetchone())
        self.assertEqual(1, conn.execute("SELECT count(*) FROM stop_review_assignments WHERE reviewer_id=42").fetchone()[0])
        self.assertEqual(1, conn.execute("SELECT count(*) FROM stop_observations WHERE reviewer_id=42").fetchone()[0])
        self.assertEqual(1, conn.execute("SELECT count(*) FROM community_stewardships WHERE reviewer_id=42").fetchone()[0])
        conn.close()
        self.assertEqual(400, client.get(urlparse(link).path + "?token=" + raw).status_code)
        self.assertTrue(client.get("/api/reviewer/status").get_json()["signed_in"])
        with client.session_transaction() as session:
            csrf = session["auth_csrf"]
        self.assertEqual(400, client.post("/reviewer/sign-out", json={}).status_code)
        client.post("/reviewer/sign-out", json={"csrf_token": csrf})
        other = review_api.app.test_client()
        self.assertEqual(200, other.get("/reviewer/sign-in").status_code)
        login = other.post("/reviewer/sign-in", json={"email":"alex@example.com"}).get_json()["magic_link"]
        self.assertEqual(302, other.get(urlparse(login).path + "?" + urlparse(login).query).status_code)
        self.assertEqual(42, self._session_id(other))
        self.assertEqual("alex@example.com", other.get("/api/reviewer/status").get_json()["email"])
        conn = sqlite3.connect(self.db)
        self.assertEqual(1, conn.execute("SELECT count(*) FROM community_reviewers").fetchone()[0])
        conn.close()

    def _session_id(self, client):
        with client.session_transaction() as session:
            return session.get("authenticated_reviewer_id")

    def test_conflict_does_not_merge_and_expired_invalid_rejected(self):
        conn = sqlite3.connect(self.db)
        conn.execute("INSERT INTO community_reviewers(id,reviewer_key,email,email_verified_at) VALUES(50,'owner','used@example.com','2026-01-01')")
        conn.commit()
        raw = issue_login_token(conn, 42, "used@example.com")
        with self.assertRaises(PermissionError): consume_login_token(conn, raw)
        self.assertEqual(42, conn.execute("SELECT reviewer_id FROM stop_observations WHERE id=9").fetchone()[0])
        expired = issue_login_token(conn, 42, "new@example.com",
                                    now=datetime.now(timezone.utc)-timedelta(hours=1))
        with self.assertRaises(ValueError): consume_login_token(conn, expired)
        with self.assertRaises(ValueError): consume_login_token(conn, "invalid")
        conn.close()

    def test_production_response_does_not_expose_token_and_empty_anonymous_is_preserved(self):
        conn = sqlite3.connect(self.db)
        conn.execute("INSERT INTO community_reviewers(id,reviewer_key,email,email_verified_at) VALUES(50,'owner','used@example.com','2026-01-01')")
        conn.execute("INSERT INTO community_reviewers(id,reviewer_key) VALUES(51,'empty')")
        conn.commit(); conn.close()
        sent = []
        client = review_api.app.test_client()
        with client.session_transaction() as session:
            session["reviewer_key"] = "empty"
            session["auth_csrf"] = "csrf"
        with patch.dict(review_api.app.config, {
            "TESTING": False, "REVIEWER_EMAIL_SENDER": lambda email, link: sent.append((email, link))
        }):
            response = client.post("/reviewer/sign-in", json={
                "email": " USED@EXAMPLE.COM ", "csrf_token": "csrf"
            })
        self.assertEqual(200, response.status_code)
        self.assertNotIn("magic_link", response.get_json())
        self.assertNotIn("used@example.com", response.get_data(as_text=True))
        self.assertEqual(1, len(sent))
        raw = parse_qs(urlparse(sent[0][1]).query)["token"][0]
        self.assertEqual(302, client.get("/reviewer/verify?token=" + raw).status_code)
        self.assertEqual(50, self._session_id(client))
        conn = sqlite3.connect(self.db)
        self.assertEqual((51,"empty"), conn.execute(
            "SELECT id,reviewer_key FROM community_reviewers WHERE id=51").fetchone())
        conn.close()

    def test_missing_deployment_secret_fails_clearly(self):
        client = review_api.app.test_client()
        with patch.dict(review_api.app.config, {"TESTING": False, "SECRET_KEY": None}):
            response = client.get("/test-route")
        self.assertEqual(503, response.status_code)
        self.assertEqual("server_configuration_required", response.get_json()["code"])

    def test_missing_mail_sender_fails_without_exposing_token(self):
        client = review_api.app.test_client()
        with client.session_transaction() as session:
            session["auth_csrf"] = "csrf"
        with patch.dict(review_api.app.config, {
            "TESTING": False, "REVIEWER_EMAIL_SENDER": None
        }):
            response = client.post("/reviewer/sign-in", json={
                "email": "new@example.com", "csrf_token": "csrf"
            })
        self.assertEqual(503, response.status_code)
        self.assertEqual({"error": "Email sign-in is not configured"}, response.get_json())

    def test_active_migration_upgrades_legacy_schema_idempotently(self):
        legacy = Path(self.temp.name) / "legacy.db"
        conn = sqlite3.connect(legacy)
        conn.execute("CREATE TABLE community_reviewers(id INTEGER PRIMARY KEY,reviewer_key TEXT UNIQUE,created_at TIMESTAMP,email TEXT)")
        conn.execute("INSERT INTO community_reviewers VALUES(7,'keep','2020-01-01','duplicate@example.com')")
        conn.execute("INSERT INTO community_reviewers VALUES(8,'keep2','2020-01-02','duplicate@example.com')")
        conn.commit(); conn.close()
        env = {**os.environ, "DMV_BUS_STOPS_DB": str(legacy)}
        command = [sys.executable, "scripts/active/create_review_tables.py"]
        subprocess.run(command, cwd=ROOT, env=env, check=True, capture_output=True)
        subprocess.run(command, cwd=ROOT, env=env, check=True, capture_output=True)
        conn = sqlite3.connect(legacy)
        cols = {row[1] for row in conn.execute("PRAGMA table_info(community_reviewers)")}
        self.assertTrue({"email","email_verified_at","claimed_at"} <= cols)
        self.assertEqual([(7,"keep",None,None),(8,"keep2",None,None)], conn.execute(
            "SELECT id,reviewer_key,email_verified_at,claimed_at FROM community_reviewers ORDER BY id").fetchall())
        self.assertTrue(conn.execute("SELECT 1 FROM sqlite_master WHERE name='reviewer_login_tokens'").fetchone())
        conn.close()


if __name__ == "__main__": unittest.main()
