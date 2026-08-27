import os
import sqlite3
import smtplib
import socket
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import requests

from src.api import app as review_api
from src.review import assignment_router
from src.review.auth import (
    RateLimitError, consume_login_token, enforce_login_rate_limits,
    issue_login_token, token_hash,
)
from src.review.email_delivery import (
    EmailConfigurationError, magic_link_message, smtp_sender_from_env,
)


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
        CREATE TABLE reviewer_auth_attempts(id INTEGER PRIMARY KEY,email_key TEXT,
          source_key TEXT,outcome TEXT,created_at TEXT);
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
            "TESTING": False, "REVIEWER_EMAIL_SENDER": lambda email, link, minutes: sent.append((email, link, minutes))
        }):
            response = client.post("/reviewer/sign-in", json={
                "email": " USED@EXAMPLE.COM ", "csrf_token": "csrf"
            })
        self.assertEqual(200, response.status_code)
        self.assertNotIn("magic_link", response.get_json())
        self.assertNotIn("used@example.com", response.get_data(as_text=True))
        self.assertEqual(1, len(sent))
        raw = parse_qs(urlparse(sent[0][1]).query)["token"][0]
        self.assertEqual(20, sent[0][2])
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
        self.assertEqual({"error": "Email sign-in is temporarily unavailable. You can still review anonymously."}, response.get_json())
        conn = sqlite3.connect(self.db)
        self.assertIsNotNone(conn.execute(
            "SELECT used_at FROM reviewer_login_tokens ORDER BY id DESC LIMIT 1"
        ).fetchone()[0])
        conn.close()

    def test_resend_failure_keeps_public_response_private(self):
        client = review_api.app.test_client()
        with client.session_transaction() as session:
            session["auth_csrf"] = "csrf"
        secret = "re_private_test_key"
        recipient = "private-recipient@example.com"
        with patch.dict(review_api.app.config, {
            "TESTING": False, "REVIEWER_EMAIL_SENDER": None
        }), patch.dict(os.environ, {
            "REVIEWER_EMAIL_BACKEND": "resend",
            "REVIEWER_EMAIL_FROM": "DMV Bus Stops <login@dmvbusstop.org>",
            "RESEND_API_KEY": secret,
            "REVIEWER_AUTH_DEV_MODE": "",
        }, clear=False), patch(
            "src.review.email_delivery.requests.post",
            side_effect=requests.Timeout("provider timeout"),
        ), self.assertLogs(review_api.app.logger, level="WARNING") as captured:
            response = client.post("/reviewer/sign-in?source=private-token", json={
                "email": recipient, "csrf_token": "csrf"
            })
        body = response.get_data(as_text=True)
        logs = "\n".join(captured.output)
        self.assertEqual(503, response.status_code)
        for rendered in (body, logs):
            self.assertNotIn(secret, rendered)
            self.assertNotIn(recipient, rendered)
            self.assertNotIn("private-token", rendered)

    def test_email_and_source_rate_limits_are_persistent_and_private(self):
        sender = lambda email, link, minutes: None
        client = review_api.app.test_client()
        with patch.dict(review_api.app.config, {"REVIEWER_EMAIL_SENDER": sender}):
            for _ in range(3):
                self.assertEqual(200, client.post(
                    "/reviewer/sign-in", json={"email": "limit@example.com"}
                ).status_code)
            limited = review_api.app.test_client().post(
                "/reviewer/sign-in", json={"email": "limit@example.com"}
            )
            self.assertEqual(429, limited.status_code)
            self.assertNotIn("account", limited.get_data(as_text=True).lower())
            self.assertEqual(200, client.post(
                "/reviewer/sign-in", json={"email": "other@example.com"}
            ).status_code)
        conn = sqlite3.connect(self.db)
        self.assertEqual(4, conn.execute("SELECT COUNT(*) FROM reviewer_login_tokens").fetchone()[0])
        self.assertEqual(4, conn.execute("SELECT COUNT(*) FROM reviewer_auth_attempts").fetchone()[0])
        conn.close()

        conn = sqlite3.connect(self.db)
        now = datetime.now(timezone.utc)
        for number in range(20):
            enforce_login_rate_limits(
                conn, f"source{number}@example.com", "198.51.100.1", "secret", now
            )
        with self.assertRaises(RateLimitError):
            enforce_login_rate_limits(
                conn, "new@example.com", "198.51.100.1", "secret", now
            )
        enforce_login_rate_limits(
            conn, "new@example.com", "198.51.100.2", "secret", now
        )
        old = now - timedelta(hours=49)
        for number in range(20):
            enforce_login_rate_limits(
                conn, f"old{number}@example.com", "203.0.113.10", "secret", old
            )
        enforce_login_rate_limits(
            conn, "current@example.com", "203.0.113.10", "secret", now
        )
        self.assertEqual(0, conn.execute(
            "SELECT COUNT(*) FROM reviewer_auth_attempts WHERE created_at<?",
            ((now - timedelta(hours=48)).isoformat(),)
        ).fetchone()[0])
        conn.close()

    def test_new_link_supersedes_old_and_forwarded_header_is_not_trusted(self):
        client = review_api.app.test_client()
        first = client.post("/reviewer/sign-in", json={"email": "links@example.com"})
        second = client.post(
            "/reviewer/sign-in", json={"email": "links@example.com"},
            headers={"X-Forwarded-For": "203.0.113.99"},
        )
        first_token = parse_qs(urlparse(first.get_json()["magic_link"]).query)["token"][0]
        second_token = parse_qs(urlparse(second.get_json()["magic_link"]).query)["token"][0]
        self.assertEqual(400, client.get("/reviewer/verify?token=" + first_token).status_code)
        self.assertEqual(302, client.get("/reviewer/verify?token=" + second_token).status_code)

    def test_plain_text_mail_and_smtp_configuration_validation(self):
        message = magic_link_message(
            "sender@example.org", "review@example.org",
            "https://example.org/reviewer/verify?token=secret", 20
        )
        self.assertEqual("Sign in to DMV Bus Stops", message["Subject"])
        self.assertIn("expires in 20 minutes", message.get_content())
        self.assertNotIn("reviewer ID", message.get_content())
        with self.assertRaises(EmailConfigurationError):
            smtp_sender_from_env({})
        with self.assertRaises(EmailConfigurationError):
            smtp_sender_from_env({"REVIEWER_EMAIL_BACKEND":"smtp", "SMTP_PORT":"bad"})
        valid = {"REVIEWER_EMAIL_BACKEND":"smtp", "REVIEWER_EMAIL_FROM":"a@example.org",
                 "SMTP_HOST":"smtp.example.org", "SMTP_PORT":"587"}
        with self.assertRaises(EmailConfigurationError):
            smtp_sender_from_env({**valid, "SMTP_USE_TLS":"yes"})
        with self.assertRaises(EmailConfigurationError):
            smtp_sender_from_env({**valid, "SMTP_USERNAME":"user"})
        with self.assertRaises(EmailConfigurationError):
            magic_link_message("good@example.org\r\nBcc: bad@example.org",
                               "review@example.org", "https://example.org", 20)

    def test_delivery_exceptions_invalidate_new_token_and_preserve_prior_link(self):
        client = review_api.app.test_client()
        first = client.post("/reviewer/sign-in", json={"email":"failure@example.com"})
        first_token = parse_qs(urlparse(first.get_json()["magic_link"]).query)["token"][0]
        failures = [
            socket.gaierror("dns"), smtplib.SMTPNotSupportedError("tls"),
            smtplib.SMTPAuthenticationError(535, b"auth"),
            smtplib.SMTPSenderRefused(550, b"sender", "sender@example.org"),
            smtplib.SMTPRecipientsRefused({"failure@example.com": (550, b"recipient")}),
        ]
        for number, failure in enumerate(failures):
            with self.subTest(failure=type(failure).__name__), patch.dict(
                review_api.app.config,
                {"REVIEWER_EMAIL_SENDER": lambda *_args, error=failure: (_ for _ in ()).throw(error)},
            ):
                response = client.post(
                    "/reviewer/sign-in", json={"email": f"failure{number}@example.com"}
                )
                self.assertEqual(503, response.status_code)
                self.assertNotIn("token", response.get_data(as_text=True).lower())
        conn = sqlite3.connect(self.db)
        failed_rows = conn.execute(
            "SELECT used_at FROM reviewer_login_tokens WHERE normalized_email LIKE 'failure%@example.com' "
            "AND normalized_email!='failure@example.com'"
        ).fetchall()
        self.assertTrue(all(row[0] is not None for row in failed_rows))
        original = conn.execute(
            "SELECT used_at FROM reviewer_login_tokens WHERE normalized_email='failure@example.com'"
        ).fetchone()[0]
        self.assertIsNone(original)
        conn.close()
        self.assertEqual(302, client.get("/reviewer/verify?token=" + first_token).status_code)

    def test_rate_table_failure_does_not_create_or_corrupt_identity(self):
        conn = sqlite3.connect(self.db)
        before = conn.execute("SELECT COUNT(*) FROM community_reviewers").fetchone()[0]
        conn.execute("DROP TABLE reviewer_auth_attempts")
        conn.commit(); conn.close()
        response = review_api.app.test_client().post(
            "/reviewer/sign-in", json={"email":"db-failure@example.com"}
        )
        self.assertEqual(503, response.status_code)
        conn = sqlite3.connect(self.db)
        self.assertEqual(before, conn.execute("SELECT COUNT(*) FROM community_reviewers").fetchone()[0])
        conn.close()

    def test_health_endpoint_contains_no_credentials(self):
        response = review_api.app.test_client().get("/api/reviewer/email-auth-health")
        payload = response.get_json()
        self.assertNotIn("SMTP_PASSWORD", payload["required_configuration"])
        self.assertNotIn("password", response.get_data(as_text=True).lower())

    def test_health_reports_resend_without_secret_value(self):
        secret = "re_private_health_key"
        with patch.dict(os.environ, {
            "REVIEWER_EMAIL_BACKEND": "resend",
            "REVIEWER_EMAIL_FROM": "DMV Bus Stops <login@dmvbusstop.org>",
            "RESEND_API_KEY": secret,
            "REVIEWER_AUTH_DEV_MODE": "",
        }, clear=False), patch.dict(review_api.app.config, {
            "TESTING": False, "REVIEWER_EMAIL_SENDER": None,
        }):
            response = review_api.app.test_client().get("/api/reviewer/email-auth-health")
        payload = response.get_json()
        self.assertTrue(payload["available"])
        self.assertEqual("resend", payload["backend"])
        self.assertIn("RESEND_API_KEY", payload["required_configuration"])
        self.assertNotIn(secret, response.get_data(as_text=True))

    def test_unconfigured_login_ui_keeps_anonymous_review_available(self):
        client = review_api.app.test_client()
        with patch.dict(os.environ, {
            "REVIEWER_AUTH_DEV_MODE": "", "REVIEWER_EMAIL_BACKEND": ""
        }), patch.dict(
            review_api.app.config, {"TESTING": False, "REVIEWER_EMAIL_SENDER": None}
        ):
            page = client.get("/reviewer/sign-in")
        self.assertEqual(200, page.status_code)
        self.assertIn("temporarily unavailable", page.get_data(as_text=True))
        self.assertIn("still review anonymously", page.get_data(as_text=True))

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
        self.assertTrue(conn.execute("SELECT 1 FROM sqlite_master WHERE name='reviewer_auth_attempts'").fetchone())
        conn.close()


if __name__ == "__main__": unittest.main()
