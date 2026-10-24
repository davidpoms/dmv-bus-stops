"""Slice A: disposable targets, independent TOTP expectations, no issuance."""

import base64
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import shutil
import sqlite3
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from cryptography.fernet import Fernet

from src.api import app as api
from src.review import auth as reviewer_auth
from src.review.recognition import administration as a, administration_schema as s, admin_auth as m, admin_routes
from src.review.recognition import execution_schema, permanent, execution, activation, authority
from src.review.recognition.rules import digest
from tests import test_recognition_operations as fixture


NOW = "2099-01-01T00:00:00Z"
INSTALLATION = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
SEED = b"12345678901234567890"  # RFC 6238 SHA-1 test key, synthetic only.


def at(seconds):
    return (datetime.strptime(NOW, "%Y-%m-%dT%H:%M:%SZ") + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


def independent_code(now):
    counter = int(datetime.strptime(now, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()) // 30
    raw = hmac.new(SEED, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = raw[-1] & 15
    return f"{(int.from_bytes(raw[offset:offset+4], 'big') & 0x7fffffff) % 1000000:06d}"


class AdministrationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture.OperationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.path = self.fixture.path
        with closing(sqlite3.connect(self.path)) as conn, conn:
            for definition in ("reviewer_key TEXT", "email TEXT", "email_verified_at TEXT", "role TEXT"):
                conn.execute("ALTER TABLE community_reviewers ADD COLUMN " + definition)
            conn.execute("UPDATE community_reviewers SET reviewer_key='owner-key',email='owner@example.test',email_verified_at='2026-01-01',role='owner' WHERE id=1")
            conn.execute("UPDATE community_reviewers SET reviewer_key='reviewer-key',email='reviewer@example.test',email_verified_at='2026-01-01',role='reviewer' WHERE id=2")
            conn.execute("CREATE TABLE reviewer_login_tokens(id INTEGER PRIMARY KEY,reviewer_id INTEGER,normalized_email TEXT,token_hash TEXT UNIQUE,action TEXT,expires_at TEXT,used_at TEXT)")
        self.operation = self.fixture.make()
        self.oid = self.operation["envelope"]["operation_id"]
        self.op_sha = hashlib.sha256(json.dumps(self.operation["envelope"], sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
        self.control = self.path.parent / "local-control.sqlite"
        self.control.touch()
        self.key_file = self.path.parent / "host-mfa.key"
        self.key_file.write_bytes(Fernet.generate_key())
        self.key_file.chmod(0o600)
        self.config = a.LocalAdministration(self.path, self.control, self.key_file)
        a.install(self.config, installation_id=INSTALLATION, owner_id=1, operator="synthetic-operator", reason="fixture", now=NOW)
        self.primary = m.record_primary_authentication(self.config, actor_id=1, reviewer_key="owner-key", now=NOW)

    def enrolled(self):
        with patch.object(m.secrets, "token_bytes", return_value=SEED):
            uri = m.begin_enrollment(self.config, self.primary, now=NOW)
        m.finish_enrollment(self.config, self.primary, independent_code(NOW), now=NOW)
        return uri

    def authenticated(self):
        self.enrolled()
        return m.open_admin_session(self.config, self.primary, independent_code(at(30)), now=at(30))

    def confirmation(self):
        session = self.authenticated()
        step = m.create_step_up(self.config, session, independent_code(at(60)), action="approve", operation_id=self.oid, now=at(60))
        token = m.begin_operation_confirmation(self.config, session, step, operation_id=self.oid, now=at(60))
        return session, step, token

    def consume(self, session, token, **kwargs):
        return m.consume_operation_confirmation(self.config, session, token, operation_id=kwargs.get("operation_id", self.oid),
            operation_sha256=kwargs.get("operation_sha256", self.op_sha), now=kwargs.get("now", at(60)))

    def sql(self, statement, values=(), *, control=False):
        with closing(sqlite3.connect(self.control if control else self.path)) as conn, conn:
            return conn.execute(statement, values).fetchall()

    def test_explicit_installation_target_schema_and_no_activation(self):
        control = a.get_installation_control(self.config)
        self.assertEqual((INSTALLATION, 1, 1, "NOT_ACTIVATED"),
            (control["installation_id"], control["generation"], control["owner_id"], control["production_state"]))
        self.assertNotEqual(control["target_id"], INSTALLATION)
        self.assertEqual(control["target_id"], self.sql("SELECT target_id FROM recognition_local_installation")[0][0])
        self.assertEqual("NOT_ACTIVATED", activation.get_activation_state().state)
        with self.assertRaises(Exception):
            authority.provision_production_authority()

    def test_owner_identity_is_server_derived_and_role_specific(self):
        self.assertEqual(1, m.get_admin_identity(self.config, self.primary, now=NOW).actor_id)
        for role in ("reviewer", "review_lead", "owner"):
            with self.subTest(role=role):
                self.sql("UPDATE community_reviewers SET role=? WHERE id=2", (role,))
                with self.assertRaises(a.AdminError):
                    m.record_primary_authentication(self.config, actor_id=2, reviewer_key="reviewer-key", now=NOW)

    def test_rfc6238_sha1_vectors_with_standard_library_implementation(self):
        for timestamp, code in ((59, "287082"), (1111111109, "081804"), (1111111111, "050471"),
                                (1234567890, "005924"), (2000000000, "279037"), (20000000000, "353130")):
            with self.subTest(timestamp=timestamp):
                m._totp(SEED).verify(code.encode(), timestamp)

    def test_deliberate_enrollment_encrypts_seed_and_exposes_uri_only_once(self):
        uri = self.enrolled()
        self.assertEqual(base64.b32encode(SEED).decode(), parse_qs(urlsplit(uri).query)["secret"][0])
        for path in (self.path, self.control):
            content = path.read_bytes()
            self.assertNotIn(SEED, content)
            self.assertNotIn(base64.b32encode(SEED), content)
            self.assertNotIn(base64.b64encode(SEED), content)
        with self.assertRaises(a.AdminError):
            m.begin_enrollment(self.config, self.primary, now=NOW)
        self.assertNotIn("seed", json.dumps(a.get_installation_control(self.config)))

    def test_enrollment_requires_recent_primary_and_cannot_transfer(self):
        with self.assertRaisesRegex(a.AdminError, "recent_primary"):
            m.begin_enrollment(self.config, self.primary, now=at(600))
        # New fixture timestamp stays monotonic after denied request.
        primary = m.record_primary_authentication(self.config, actor_id=1, reviewer_key="owner-key", now=at(600))
        with patch.object(m.secrets, "token_bytes", return_value=SEED):
            m.begin_enrollment(self.config, primary, now=at(600))
        other = m.record_primary_authentication(self.config, actor_id=1, reviewer_key="owner-key", now=at(600))
        with self.assertRaisesRegex(a.AdminError, "pending_enrollment"):
            m.finish_enrollment(self.config, other, independent_code(at(600)), now=at(600))

    def test_valid_invalid_and_replayed_totp(self):
        self.enrolled()
        with self.assertRaisesRegex(a.AdminError, "replayed"):
            m.open_admin_session(self.config, self.primary, independent_code(NOW), now=NOW)
        invalid = "999999" if independent_code(at(30)) != "999999" else "000000"
        with self.assertRaises(a.AdminError):
            m.open_admin_session(self.config, self.primary, invalid, now=at(30))
        token = m.open_admin_session(self.config, self.primary, independent_code(at(30)), now=at(30))
        self.assertEqual(1, m.require_recognition_admin(self.config, token, now=at(30)).actor_id)

    def test_mfa_rate_limit_persists_across_connections(self):
        self.enrolled()
        for _ in range(5):
            with self.assertRaises(a.AdminError):
                m.open_admin_session(self.config, self.primary, "bad", now=at(30))
        with self.assertRaisesRegex(a.AdminError, "rate_limited"):
            m.open_admin_session(self.config, self.primary, independent_code(at(30)), now=at(30))
        self.assertEqual([(5,)], self.sql("SELECT failures FROM recognition_admin_attempts", control=True))

    def test_admin_session_exact_eight_hour_boundary(self):
        token = self.authenticated()
        self.assertEqual(1, m.require_recognition_admin(self.config, token, now=at(30 + 28799)).actor_id)
        with self.assertRaises(a.AdminError):
            m.require_recognition_admin(self.config, token, now=at(30 + 28800))

    def test_logout_invalidates_copied_session_token(self):
        token = self.authenticated()
        m.invalidate_primary(self.config, self.primary, now=at(30))
        with self.assertRaises(a.AdminError):
            m.require_recognition_admin(self.config, token, now=at(30))

    def test_demotion_and_repromotion_invalidates_even_without_intermediate_request(self):
        token = self.authenticated()
        self.sql("UPDATE community_reviewers SET role='review_lead' WHERE id=1")
        self.sql("UPDATE community_reviewers SET role='owner' WHERE id=1")
        with self.assertRaises(a.AdminError):
            m.require_recognition_admin(self.config, token, now=at(30))

    def test_operator_mfa_reset_invalidates_sessions_and_confirmation(self):
        session, step, token = self.confirmation()
        a.reset_mfa(self.config, expected_generation=1, operator="synthetic-host-owner", reason="deliberate recovery", now=at(60))
        for call in (lambda: m.require_recognition_admin(self.config, session, now=at(60)),
                     lambda: self.consume(session, token)):
            with self.assertRaises(a.AdminError):
                call()
        self.assertEqual([("UNENROLLED", None)], self.sql("SELECT state,seed_ciphertext FROM recognition_admin_mfa", control=True))

    def test_step_up_exact_scope_expiration_and_session_binding(self):
        session, step, _ = self.confirmation()
        self.assertEqual(1, m.require_recent_step_up(self.config, session, step, action="approve", operation_id=self.oid, now=at(659)).actor_id)
        for changes in ({"now": at(660)}, {"action": "recover", "now": at(660)}, {"operation_id": "other", "now": at(660)}):
            options = dict(action="approve", operation_id=self.oid, now=at(660))
            options.update(changes)
            with self.assertRaises(a.AdminError):
                m.require_recent_step_up(self.config, session, step, **options)
        other_primary = m.record_primary_authentication(self.config, actor_id=1, reviewer_key="owner-key", now=at(660))
        other = m.open_admin_session(self.config, other_primary, independent_code(at(690)), now=at(690))
        with self.assertRaises(a.AdminError):
            m.require_recent_step_up(self.config, other, step, action="approve", operation_id=self.oid, now=at(690))

    def test_step_up_accepts_valid_eight_hour_session_with_fresh_totp(self):
        session = self.authenticated()
        token = m.create_step_up(self.config, session, independent_code(at(600)), action="activate", now=at(600))
        self.assertEqual(1, m.require_recent_step_up(self.config, session, token, action="activate", now=at(600)).actor_id)

    def test_confirmation_binds_digest_id_actor_and_is_not_approval(self):
        before = self.fixture.get(self.oid)
        session, _, token = self.confirmation()
        for updates in ({"operation_id": "other"}, {"operation_sha256": "0" * 64}):
            with self.subTest(updates=updates), self.assertRaises(a.AdminError):
                self.consume(session, token, **updates)
        body = self.consume(session, token)
        self.assertEqual((1, self.oid, self.op_sha, 1), tuple(body[k] for k in ("actor_id", "operation_id", "operation_sha256", "generation")))
        self.assertEqual(before, self.fixture.get(self.oid))
        with self.assertRaises(a.AdminError):
            self.consume(session, token)

    def test_expired_confirmation_rejected(self):
        session, _, token = self.confirmation()
        with self.assertRaises(a.AdminError):
            self.consume(session, token, now=at(660))

    def test_changed_operation_state_invalidates_confirmation(self):
        session, _, token = self.confirmation()
        self.fixture.decision(self.operation, "REJECTED")
        with self.assertRaisesRegex(a.AdminError, "operation_changed"):
            self.consume(session, token)
        self.assertEqual([(1,)], self.sql("SELECT used FROM recognition_admin_confirmations", control=True))

    def test_changed_digest_invalidates_confirmation(self):
        session, _, token = self.confirmation()
        with self.assertRaises(a.AdminError):
            self.consume(session, token, operation_sha256="b" * 64)

    def test_confirmation_cannot_transfer_between_live_sessions(self):
        first, step, token = self.confirmation()
        second = m.open_admin_session(self.config, self.primary, independent_code(at(90)), now=at(90))
        with self.assertRaises(a.AdminError):
            self.consume(second, token, now=at(90))
        with self.assertRaises(a.AdminError):
            m.require_recent_step_up(self.config, second, step, action="approve", operation_id=self.oid, now=at(90))
        self.assertEqual(1, self.consume(first, token, now=at(90))["actor_id"])

    def test_concurrent_confirmation_consumption_exactly_once(self):
        session, _, token = self.confirmation()
        def consume(_):
            try:
                self.consume(session, token)
                return "consumed"
            except a.AdminError:
                return "rejected"
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(["consumed", "rejected"], sorted(pool.map(consume, range(2))))

    def test_target_filename_alone_does_not_verify_replacement(self):
        replacement = self.path.parent / "copy.sqlite"
        shutil.copyfile(self.path, replacement)
        replacement.replace(self.path)
        with self.assertRaisesRegex(a.AdminError, "target_identity"):
            a.verify_target_control(self.config)

    def test_schema_change_rejected(self):
        self.sql("CREATE TABLE accidental_change (id INTEGER)")
        with self.assertRaisesRegex(a.AdminError, "schema"):
            a.verify_target_control(self.config)

    def test_restore_generation_durable_and_invalidates_authentication(self):
        session, step, token = self.confirmation()
        with a.connect(self.path) as conn:
            preview = digest(a.observe_target(conn))
        generation = a.advance_restore_generation(self.config, expected_generation=1, expected_target_sha256=preview,
            operator="synthetic-operator", reason="restored target", now=at(60))
        self.assertEqual(2, generation)
        self.assertEqual(2, a.get_installation_control(self.config)["generation"])
        self.assertEqual("NOT_ACTIVATED", a.get_installation_control(self.config)["production_state"])
        with self.assertRaises(a.AdminError):
            self.consume(session, token)
        with self.assertRaises(a.AdminError):
            m.require_recent_step_up(self.config, session, step, action="approve", operation_id=self.oid, now=at(60))
        self.assertEqual("PREPARED", self.fixture.get(self.oid)["decisions"][-1]["state"])

    def test_target_only_restore_does_not_restore_control_generation(self):
        backup = self.path.parent / "backup.sqlite"
        shutil.copyfile(self.path, backup)
        with a.connect(self.path) as conn:
            preview = digest(a.observe_target(conn))
        a.advance_restore_generation(self.config, expected_generation=1, expected_target_sha256=preview,
            operator="synthetic-operator", reason="new generation", now=NOW)
        shutil.copyfile(backup, self.path)  # Simulates an in-place old target restore.
        with self.assertRaises(a.AdminError):
            a.get_installation_control(self.config)
        self.assertEqual([(2,)], self.sql("SELECT MAX(generation) FROM recognition_admin_bindings", control=True))

    def test_restore_requires_expected_generation_and_exact_preview(self):
        for generation, sha in ((2, "a" * 64), (1, "a" * 64)):
            with self.subTest(generation=generation), self.assertRaises(a.AdminError):
                a.advance_restore_generation(self.config, expected_generation=generation, expected_target_sha256=sha,
                    operator="synthetic-operator", reason="test", now=NOW)
        self.assertEqual(1, a.get_installation_control(self.config)["generation"])

    def test_install_idempotent_and_control_v1_explicit_upgrade(self):
        before = self.sql("SELECT * FROM recognition_admin_audit", control=True)
        a.install(self.config, installation_id=INSTALLATION, owner_id=1, operator="synthetic-operator", reason="repeat", now=NOW)
        self.assertEqual(before, self.sql("SELECT * FROM recognition_admin_audit", control=True))
        with a.connect(self.control) as conn:
            with self.assertRaises(Exception):
                execution_schema.check_control(conn)  # Synthetic v1 must not accept local v2.

    def test_target_install_savepoint_rollback(self):
        with closing(sqlite3.connect(":memory:")) as conn:
            conn.execute("CREATE TABLE community_reviewers(id INTEGER,role TEXT,reviewer_key TEXT,email_verified_at TEXT)")
            conn.execute("BEGIN IMMEDIATE")
            with patch.object(s, "check_target", side_effect=ValueError("injected")):
                with self.assertRaises(ValueError):
                    s.install_target(conn)
            conn.commit()
            self.assertEqual([("community_reviewers",)], conn.execute("SELECT name FROM sqlite_master").fetchall())

    def test_missing_control_never_auto_installs(self):
        missing = self.path.parent / "does-not-exist.sqlite"
        with self.assertRaises(a.AdminError):
            a.get_installation_control(replace(self.config, control=missing))
        self.assertFalse(missing.exists())

    def test_owner_key_change_invalidates_sessions(self):
        token = self.authenticated()
        self.sql("UPDATE community_reviewers SET reviewer_key='replacement-key' WHERE id=1")
        with self.assertRaises(a.AdminError):
            m.require_recognition_admin(self.config, token, now=at(30))

    def test_migration_savepoint_rolls_back_even_when_error_caught(self):
        with closing(sqlite3.connect(self.path.parent / "migration-test.sqlite")) as conn:
            conn.execute("BEGIN IMMEDIATE")
            with patch.object(s, "check_control", side_effect=ValueError("injected")):
                with self.assertRaises(ValueError):
                    s.install_control(conn)
            conn.commit()
            self.assertEqual([], conn.execute("SELECT name FROM sqlite_master").fetchall())
            conn.execute("BEGIN IMMEDIATE")
            execution_schema.install_control(conn)
            conn.commit()
            conn.execute("BEGIN IMMEDIATE")
            s.install_control(conn)
            conn.rollback()
            execution_schema.check_control(conn)

    def test_control_history_is_application_immutable(self):
        for table in ("recognition_admin_bindings", "recognition_admin_audit"):
            for statement in (f"DELETE FROM {table}", f"UPDATE {table} SET body_sha256='bad'", f"INSERT OR REPLACE INTO {table} SELECT * FROM {table}"):
                with self.subTest(statement=statement), self.assertRaises(sqlite3.IntegrityError):
                    self.sql(statement, control=True)

    def test_clock_rollback_and_missing_key_fail_closed(self):
        self.enrolled()
        m.open_admin_session(self.config, self.primary, independent_code(at(30)), now=at(30))
        with self.assertRaises(a.AdminError):
            m.get_admin_identity(self.config, self.primary, now=NOW)
        with self.assertRaises((a.AdminError, OSError)):
            m.open_admin_session(replace(self.config, key_file=self.path.parent / "missing.key"), self.primary, independent_code(at(60)), now=at(60))

    def test_no_recognition_writer_recovery_activation_or_synthetic_factory(self):
        with patch.object(permanent, "finalize", side_effect=AssertionError("writer")), \
             patch.object(execution, "execute_operation", side_effect=AssertionError("execute")), \
             patch.object(execution, "reconcile_operation", side_effect=AssertionError("recovery")), \
             patch.object(activation, "activate_production", side_effect=AssertionError("activation")), \
             patch.object(authority, "DisposableWorkspace", side_effect=AssertionError("synthetic")):
            session, _, token = self.confirmation()
            self.consume(session, token)
        self.assertEqual([], self.sql("SELECT * FROM recognition_operation_receipts"))


    def web(self):
        self.web_now = NOW
        for item in (patch.object(api, "DATABASE_PATH", self.path),
                     patch.dict(api.app.config, dict(TESTING=True, SECRET_KEY="slice-a-test-only-secret",
                         RECOGNITION_ADMIN_CONTROL=str(self.control), RECOGNITION_ADMIN_KEY_FILE=str(self.key_file))),
                     patch.object(admin_routes, "now_utc", side_effect=lambda: self.web_now),
                     patch.object(api, "consume_login_token", side_effect=lambda c, token:
                         reviewer_auth.consume_login_token(c, token, now=datetime.strptime(self.web_now, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)))):
            item.start()
            self.addCleanup(item.stop)
        return api.app.test_client()

    def login(self, client, email="owner@example.test"):
        with closing(sqlite3.connect(self.path)) as conn:
            token = reviewer_auth.issue_login_token(conn, 1 if email == "owner@example.test" else 2, email,
                now=datetime.strptime(self.web_now, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc))
        self.assertEqual(302, client.get("/reviewer/verify", query_string={"token": token}).status_code)

    def post(self, client, suffix, **values):
        with client.session_transaction() as browser:
            csrf = browser.get("auth_csrf")
        return client.post("/api/admin/recognition-control/" + suffix, json=dict(values, csrf_token=csrf))

    def web_session(self):
        client = self.web()
        self.login(client)
        with patch.object(m.secrets, "token_bytes", return_value=SEED):
            result = self.post(client, "mfa/enrollment")
        self.assertEqual(200, result.status_code, result.get_json())
        self.assertEqual("no-store", result.headers["Cache-Control"])
        self.assertEqual(200, self.post(client, "mfa/verify", code=independent_code(NOW)).status_code)
        self.web_now = at(30)
        self.assertEqual(200, self.post(client, "session", code=independent_code(self.web_now)).status_code)
        return client

    def test_web_anonymous_reviewer_and_review_lead_cannot_administer(self):
        client = self.web()
        path = "/api/admin/recognition-control/identity"
        self.assertEqual(403, client.get(path).status_code)
        self.login(client, "reviewer@example.test")
        self.assertEqual(403, client.get(path).status_code)
        self.sql("UPDATE community_reviewers SET role='review_lead' WHERE id=2")
        self.assertEqual(403, client.get(path).status_code)
        with client.session_transaction() as browser:
            browser["authenticated_reviewer_id"] = 1
            browser["reviewer_key"] = "owner-key"
            browser["is_admin"] = True
        self.assertEqual(401, client.get(path).status_code)

    def test_web_login_hooks_identity_logout_and_copied_cookie_revocation(self):
        client = self.web_session()
        info = client.get("/api/admin/recognition-control/session")
        self.assertEqual(1, info.get_json()["actor_id"])
        with client.session_transaction() as browser:
            copied_session = browser["recognition_admin"]
            csrf = browser["auth_csrf"]
        self.assertEqual(200, client.post("/reviewer/sign-out", json={"csrf_token": csrf}).status_code)
        with self.assertRaises(a.AdminError):
            m.require_recognition_admin(self.config, copied_session, now=self.web_now)

    def test_web_no_actor_csrf_or_session_flag_bypass(self):
        client = self.web_session()
        self.assertEqual(400, self.post(client, "step-up", code="123456", action="activate", operation_id=None, actor_id=1).status_code)
        self.assertEqual(400, client.post("/api/admin/recognition-control/step-up", json=dict(code="123456", action="activate", operation_id=None)).status_code)
        self.assertEqual(400, client.post("/api/admin/recognition-control/step-up", json=dict(code="123456", action="activate", operation_id=None, csrf_token="wrong")).status_code)
        self.assertEqual(400, client.post("/api/admin/recognition-control/step-up", json=dict(code="123456", action="activate", operation_id=None, csrf_token="\u2603")).status_code)
        self.assertEqual(403, self.post(client, "step-up", code="123456", action=[], operation_id=None).status_code)

    def test_bad_administration_configuration_does_not_break_reviewer_login(self):
        client = self.web()
        with patch.dict(api.app.config, dict(RECOGNITION_ADMIN_CONTROL=None)):
            self.login(client)
        with client.session_transaction() as browser:
            self.assertEqual(1, browser["authenticated_reviewer_id"])
            self.assertNotIn("recognition_primary", browser)

    def test_web_confirmation_never_approves_and_seed_not_exposed_after_setup(self):
        client = self.web_session()
        self.web_now = at(60)
        step = self.post(client, "step-up", code=independent_code(self.web_now), action="approve", operation_id=self.oid)
        self.assertEqual(200, step.status_code, step.get_json())
        confirmation = self.post(client, "confirmations", operation_id=self.oid, step_up_token=step.get_json()["step_up_token"])
        result = self.post(client, "confirmations/consume", operation_id=self.oid, operation_sha256=self.op_sha,
                           confirmation_token=confirmation.get_json()["confirmation_token"])
        self.assertEqual(200, result.status_code, result.get_json())
        self.assertFalse(result.get_json()["recognition_approved"])
        self.assertEqual("PREPARED", self.fixture.get(self.oid)["decisions"][-1]["state"])
        for response in (step, confirmation, result, client.get("/api/admin/recognition-control/installation"), self.post(client, "mfa/enrollment")):
            self.assertNotIn(base64.b32encode(SEED).decode(), response.get_data(as_text=True))
            self.assertNotIn("otpauth://", response.get_data(as_text=True))

    def test_web_invalid_totp_never_logs_secret_and_logout_failure_is_not_success(self):
        import io
        import logging
        client = self.web_session()
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        api.app.logger.addHandler(handler)
        self.addCleanup(api.app.logger.removeHandler, handler)
        result = self.post(client, "session", code="bad")
        self.assertEqual(401, result.status_code)
        self.assertNotIn(base64.b32encode(SEED).decode(), stream.getvalue())
        self.assertNotIn(SEED.decode(), stream.getvalue())
        with client.session_transaction() as browser:
            csrf = browser["auth_csrf"]
        with patch.object(m, "invalidate_primary", side_effect=OSError("fixture unavailable")):
            self.assertEqual(503, client.post("/reviewer/sign-out", json={"csrf_token": csrf}).status_code)

    def test_installer_and_auth_controls_preserve_explorer_records(self):
        from src.review.recognition.schema import TABLES
        before = {table: self.sql(f"SELECT * FROM {table}") for table in TABLES}
        session, _, token = self.confirmation()
        self.consume(session, token)
        self.assertEqual(before, {table: self.sql(f"SELECT * FROM {table}") for table in TABLES})

    def test_web_session_cannot_be_transferred_between_primary_logins(self):
        client = self.web_session()
        with client.session_transaction() as browser:
            first_session = browser["recognition_admin"]
        other = api.app.test_client()
        self.login(other)
        with other.session_transaction() as browser:
            browser["recognition_admin"] = first_session
        self.assertEqual(403, other.get("/api/admin/recognition-control/session").status_code)

    def test_startup_import_no_install_authority_connection_or_activation(self):
        code = '''
import sqlite3
from unittest.mock import patch
with patch.object(sqlite3, "connect", side_effect=AssertionError("startup opened database")):
    from src.api.app import app
    from src.review.recognition import DISABLED
    assert DISABLED.issuance is False
    assert app.config["LIVE_FIRST_LOOK_GATE"].issuance is False
    assert app.config["LIVE_RECOGNITION_GATE"].issuance is False
'''
        result = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
