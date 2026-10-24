"""Slice B: disposable local records, deterministic crash and lock tests."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import hashlib
import json
import sqlite3
import threading
import unittest
from unittest.mock import patch

from src.review.recognition import approvals as b, approval_schema, administration as a
from src.review.recognition import admin_auth as m, permanent, execution, activation
from src.review.recognition import operation_schema, live_first_looks, authority
from tests import test_recognition_administration as slice_a
from tests.test_recognition_administration import at, NOW, independent_code


class ApprovalTests(unittest.TestCase):
    setUp = slice_a.AdministrationTests.setUp
    sql = slice_a.AdministrationTests.sql
    enrolled = slice_a.AdministrationTests.enrolled
    authenticated = slice_a.AdministrationTests.authenticated
    confirmation = slice_a.AdministrationTests.confirmation
    web = slice_a.AdministrationTests.web
    login = slice_a.AdministrationTests.login
    post = slice_a.AdministrationTests.post
    web_session = slice_a.AdministrationTests.web_session

    def ready(self):
        b.install(self.config, operator="test-host", reason="disposable migration", now=NOW)
        self.session, self.step, self.token = self.confirmation()

    def approve(self, **overrides):
        args = dict(operation_id=self.oid, reason="Reviewed exact frozen population", now=at(60))
        args.update(overrides)
        return b.create_approval(self.config, self.session, self.step, self.token, **args)

    def durable(self):
        return (self.sql("SELECT used FROM recognition_admin_confirmations WHERE token_hash=?", (a.token_hash(self.token),), control=True)[0][0],
                self.sql("SELECT COUNT(*) FROM recognition_approvals", control=True)[0][0],
                self.sql("SELECT COUNT(*) FROM recognition_approval_history", control=True)[0][0])

    def test_valid_exact_binding_and_history_no_execution(self):
        self.ready()
        with closing(sqlite3.connect(self.path)) as conn:
            before = list(conn.iterdump())
        with patch.object(permanent, "finalize", side_effect=AssertionError("writer called")), \
             patch.object(live_first_looks, "seal_pending", side_effect=AssertionError("live writer")), \
             patch.object(execution, "execute_operation", side_effect=AssertionError("execution")), \
             patch.object(execution, "reconcile_operation", side_effect=AssertionError("recovery")), \
             patch.object(activation, "activate_production", side_effect=AssertionError("activation")), \
             patch.object(authority, "DisposableWorkspace", side_effect=AssertionError("synthetic provider")):
            result = self.approve()
        body = result["approval"]
        sha = lambda value: hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
        self.assertEqual(self.op_sha, body["binding"]["operation_sha256"])
        self.assertEqual(sha(body), result["approval_sha256"])
        e = self.operation["envelope"]
        for key in ("event_id", "preparation_id", "event_sha256", "preparation_sha256", "population_sha256"):
            self.assertEqual(e[key], body["binding"][key])
        self.assertEqual(a.token_hash(self.session), body["session_sha256"])
        self.assertEqual(a.token_hash(self.token), body["confirmation_sha256"])
        self.assertEqual((1, 1, 1), self.durable())
        self.assertEqual(("PENDING", "APPROVED"), (result["history"][0]["prior_state"], result["state"]))
        self.assertTrue(result["execution_pending"])
        self.assertFalse(body["execution_authority"])
        self.assertEqual("NOT_STARTED", self.fixture.get(self.oid)["executions"][-1]["state"])
        self.assertEqual("PREPARED", self.fixture.get(self.oid)["decisions"][-1]["state"])
        self.assertEqual("NOT_ACTIVATED", activation.get_activation_state().state)
        self.assertEqual([], self.sql("SELECT name FROM sqlite_master WHERE name IN ('recognition_first_look_claims','recognition_geography_awards')"))
        with closing(sqlite3.connect(self.path)) as conn:
            self.assertEqual(before, list(conn.iterdump()))  # Entire target, including Explorer.

    def test_crash_matrix(self):
        self.ready()
        for stage in "ABCDE":
            with self.subTest(stage=stage):
                def fail(point):
                    if point == stage:
                        raise RuntimeError("deterministic crash " + point)
                with patch.object(b, "_fault", side_effect=fail), self.assertRaises(RuntimeError):
                    self.approve()
                self.assertEqual((0, 0, 0), self.durable())
        with patch.object(b, "_fault", side_effect=lambda point: (_ for _ in ()).throw(RuntimeError("lost acknowledgement")) if point == "F" else None):
            with self.assertRaises(RuntimeError):
                self.approve()
        self.assertEqual((1, 1, 1), self.durable())
        rows = b.list_operation_approvals(self.config, self.session, self.oid, now=at(60))
        self.assertEqual(1, len(rows))
        with self.assertRaises(a.AdminError):
            self.approve()

    def test_confirmation_binding_failures_preserve_valid_token(self):
        self.ready()
        cases = {"actor": 2, "session_hash": "b"*64, "operation_id": "another-operation",
                 "operation_sha256": "b"*64, "state_sha256": "b"*64, "generation": 2,
                 "expires": a.timestamp(at(60)), "used": 1}
        for column, value in cases.items():
            with self.subTest(column=column):
                old = self.sql(f"SELECT {column} FROM recognition_admin_confirmations", control=True)[0][0]
                self.sql(f"UPDATE recognition_admin_confirmations SET {column}=?", (value,), control=True)
                with self.assertRaises(a.AdminError):
                    self.approve()
                self.assertEqual(0, self.durable()[1])
                self.sql(f"UPDATE recognition_admin_confirmations SET {column}=?", (old,), control=True)
        self.assertEqual((0, 0, 0), self.durable())

    def test_missing_session_step_confirmation(self):
        self.ready()
        for attr in ("session", "step", "token"):
            for invalid in (None, "invalid", "x"*40):
                with self.subTest(attr=attr, invalid=invalid):
                    old = getattr(self, attr)
                    setattr(self, attr, invalid)
                    with self.assertRaises(a.AdminError):
                        self.approve()
                    setattr(self, attr, old)
        self.assertEqual((0, 0, 0), self.durable())

    def test_expired_step(self):
        self.ready()
        with self.assertRaises(a.AdminError):
            self.approve(now=at(660))
        self.assertEqual((0, 0, 0), self.durable())

    def test_another_session_cannot_approve(self):
        self.ready()
        self.session = m.open_admin_session(self.config, self.primary, independent_code(at(90)), now=at(90))
        with self.assertRaises(a.AdminError):
            self.approve(now=at(90))
        self.assertEqual((0, 0, 0), self.durable())

    def test_reviewer_and_review_lead_cannot_approve(self):
        self.ready()
        for role in ("reviewer", "review_lead"):
            with self.subTest(role=role):
                self.sql("UPDATE community_reviewers SET role=? WHERE id=1", (role,))
                with self.assertRaises(a.AdminError):
                    self.approve()
        self.assertEqual(0, self.durable()[1])

    def test_invalid_totp_cannot_mint_step(self):
        self.ready()
        with self.assertRaises(a.AdminError):
            m.create_step_up(self.config, self.session, "bad", action="approve", operation_id=self.oid, now=at(90))
        self.assertEqual((0, 0, 0), self.durable())

    def test_rejected_superseded_and_execution_state_fail(self):
        self.ready()
        self.fixture.decision(self.operation, "SUPERSEDED")
        with self.assertRaises(Exception):
            self.approve()
        self.assertEqual((0, 0, 0), self.durable())

    def test_rejected_operation_does_not_consume(self):
        self.ready()
        self.fixture.decision(self.operation, "REJECTED")
        with self.assertRaises(Exception):
            self.approve()
        self.assertEqual((0, 0, 0), self.durable())

    def test_missing_or_corrupted_operation_bindings(self):
        self.ready()
        table = "recognition_operation_contracts"
        original_json, original_sha = self.sql(f"SELECT body_json,body_sha256 FROM {table} WHERE operation_id=?", (self.oid,))[0]
        triggers = [(name, sql) for name, sql in operation_schema.definitions().items()
                    if name.startswith(table + "_immutable_")]
        def replace(body_json, body_sha):
            with closing(sqlite3.connect(self.path)) as conn, conn:
                for name, _ in triggers:
                    conn.execute("DROP TRIGGER " + name)
                conn.execute(f"UPDATE {table} SET body_json=?,body_sha256=? WHERE operation_id=?", (body_json, body_sha, self.oid))
                for _, sql in triggers:
                    conn.execute(sql)
        for key, changed in (("event_id", "wrong-event"), ("preparation_id", "wrong-preparation"),
                             ("population_sha256", "b"*64), ("member_ids", []),
                             ("provenance", {}), ("accounting_policy", {})):
            with self.subTest(key=key):
                body = json.loads(original_json)
                body[key] = changed
                replace(b.canonical(body), b.digest(body))
                with self.assertRaises(Exception):
                    self.approve()
                self.assertEqual((0, 0, 0), self.durable())
                replace(original_json, original_sha)
        with self.assertRaises(Exception):
            self.approve(operation_id="missing-operation")

    def test_different_operation_cannot_use_confirmation(self):
        self.ready()
        event = self.fixture.freeze(self.fixture.create()["preparation_id"])["event"]["event_id"]
        second = self.fixture.make(event=event)["envelope"]["operation_id"]
        with self.assertRaises(a.AdminError):
            self.approve(operation_id=second)
        self.assertEqual((0, 0, 0), self.durable())

    def test_stale_dependencies_fail_without_consumption(self):
        self.ready()
        self.sql("UPDATE stop_review_assignments SET status='pending' WHERE id=(SELECT MIN(id) FROM stop_review_assignments)")
        with self.assertRaisesRegex(a.AdminError, "dependencies"):
            self.approve()
        self.assertEqual((0, 0, 0), self.durable())

    def test_verification_failure_is_not_invalidation(self):
        self.ready()
        value = self.approve()
        with patch.object(b.dependencies, "recheck", return_value={"state": "VERIFICATION_FAILURE"}):
            with self.assertRaises(a.AdminError):
                b.get_approval(self.config, self.session, value["approval"]["approval_id"], now=at(60))
        self.assertEqual((1, 1, 1), self.durable())

    def test_operation_supersession_preserves_and_invalidates(self):
        self.ready()
        value = self.approve()
        self.fixture.decision(self.operation, "SUPERSEDED")
        current = b.get_approval(self.config, self.session, value["approval"]["approval_id"], now=at(60))
        self.assertEqual("INVALIDATED", current["state"])
        self.assertEqual(value["approval"], current["approval"])
        self.assertEqual(2, len(current["history"]))

    def test_restore_invalidates_in_same_control_commit(self):
        self.ready()
        value = self.approve()
        with a.connect(self.path) as conn:
            expected = b.digest(a.observe_target(conn))
        a.advance_restore_generation(self.config, expected_generation=1, expected_target_sha256=expected,
                                     operator="test-host", reason="disposable restore", now=at(90))
        with a.connect(self.control) as conn:
            current = b._read(conn, value["approval"]["approval_id"])
        self.assertEqual("INVALIDATED", current["state"])
        with self.assertRaises(a.AdminError):
            self.approve(now=at(90))

    def test_target_installation_mismatch_fails(self):
        self.ready()
        for column in ("target_id", "installation_id"):
            with self.subTest(column=column):
                old = self.sql(f"SELECT {column} FROM recognition_local_installation")[0][0]
                self.sql(f"UPDATE recognition_local_installation SET {column}='wrong'")
                with self.assertRaises(a.AdminError):
                    self.approve()
                self.sql(f"UPDATE recognition_local_installation SET {column}=?", (old,))
        self.assertEqual((0, 0, 0), self.durable())

    def test_explicit_invalidation_cannot_reapprove(self):
        self.ready()
        value = self.approve()
        current = b.invalidate_approval(self.config, self.session, self.step, value["approval"]["approval_id"], reason="revised review", now=at(60), superseded=True)
        self.assertEqual("SUPERSEDED", current["state"])
        with self.assertRaises(a.AdminError):
            b.invalidate_approval(self.config, self.session, self.step, value["approval"]["approval_id"], reason="again", now=at(60))

    def test_concurrent_same_confirmation(self):
        self.ready()
        barrier = threading.Barrier(2)
        def attempt():
            barrier.wait()
            try:
                return self.approve()["state"]
            except a.AdminError:
                return "DENIED"
        with ThreadPoolExecutor(2) as pool:
            result = list(pool.map(lambda _: attempt(), range(2)))
        self.assertEqual(["APPROVED", "DENIED"], sorted(result))
        self.assertEqual((1, 1, 1), self.durable())

    def test_concurrent_different_confirmations(self):
        self.ready()
        second = m.begin_operation_confirmation(self.config, self.session, self.step, operation_id=self.oid, now=at(60))
        barrier = threading.Barrier(2)
        def attempt(token):
            barrier.wait()
            try:
                return b.create_approval(self.config, self.session, self.step, token, operation_id=self.oid, reason="reviewed", now=at(60))["state"]
            except a.AdminError:
                return "DENIED"
        with ThreadPoolExecutor(2) as pool:
            result = list(pool.map(attempt, (self.token, second)))
        self.assertEqual(["APPROVED", "DENIED"], sorted(result))
        self.assertEqual([(1,)], self.sql("SELECT SUM(used) FROM recognition_admin_confirmations", control=True))

    def test_concurrent_different_sessions(self):
        self.ready()
        second_session = m.open_admin_session(self.config, self.primary, independent_code(at(90)), now=at(90))
        second_step = m.create_step_up(self.config, second_session, independent_code(at(120)), action="approve", operation_id=self.oid, now=at(120))
        second_token = m.begin_operation_confirmation(self.config, second_session, second_step, operation_id=self.oid, now=at(120))
        barrier = threading.Barrier(2)
        def attempt(values):
            barrier.wait()
            try:
                return b.create_approval(self.config, *values, operation_id=self.oid, reason="reviewed", now=at(120))["state"]
            except a.AdminError:
                return "DENIED"
        with ThreadPoolExecutor(2) as pool:
            result = list(pool.map(attempt, ((self.session, self.step, self.token), (second_session, second_step, second_token))))
        self.assertEqual(["APPROVED", "DENIED"], sorted(result))
        self.assertEqual([(1,)], self.sql("SELECT SUM(used) FROM recognition_admin_confirmations", control=True))

    def test_target_writer_reservation_held_through_control_commit(self):
        self.ready()
        attempts = []
        def competing_writer(point):
            if point == "E":
                with closing(sqlite3.connect(self.path, timeout=0)) as conn:
                    with self.assertRaises(sqlite3.OperationalError):
                        conn.execute("BEGIN IMMEDIATE")
                    attempts.append("blocked")
        with patch.object(b, "_fault", side_effect=competing_writer):
            self.approve()
        self.assertEqual(["blocked"], attempts)

    def test_migration_idempotent_no_startup_implicit_install(self):
        self.session, self.step, self.token = self.confirmation()
        with self.assertRaises(a.AdminError):
            self.approve()
        for _ in range(2):
            b.install(self.config, operator="test-host", reason="explicit", now=at(60))
        self.approve()
        with a.connect(self.control, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            for table in ("recognition_approvals", "recognition_approval_history"):
                for verb in (f"DELETE FROM {table}", f"UPDATE {table} SET body_json=body_json"):
                    with self.assertRaises(sqlite3.IntegrityError):
                        conn.execute(verb)

    def test_migration_rollback(self):
        with a.connect(self.control, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            with patch.object(approval_schema, "check", side_effect=RuntimeError("migration failure")):
                with self.assertRaises(RuntimeError):
                    approval_schema.install(conn)
            self.assertIsNone(conn.execute("SELECT 1 FROM sqlite_master WHERE name='recognition_approvals'").fetchone())

    def test_web_approval_and_strict_server_derived_request(self):
        b.install(self.config, operator="test-host", reason="disposable migration", now=NOW)
        client = self.web_session()
        self.web_now = at(60)
        step = self.post(client, "step-up", code=independent_code(at(60)), action="approve", operation_id=self.oid).get_json()["step_up_token"]
        token = self.post(client, "confirmations", operation_id=self.oid, step_up_token=step).get_json()["confirmation_token"]
        suffix = "operations/" + self.oid + "/approve"
        values = dict(step_up_token=step, confirmation_token=token, reason="Reviewed")
        for extra in ({"actor_id": 1}, {"approved": True}, {"operation_sha256": self.op_sha}):
            with self.subTest(extra=extra):
                self.assertEqual(400, self.post(client, suffix, **values, **extra).status_code)
        self.assertEqual(400, client.post("/api/admin/recognition-control/" + suffix, json=values).status_code)
        response = self.post(client, suffix, **values)
        self.assertEqual(201, response.status_code, response.get_json())
        self.assertEqual("no-store", response.headers["Cache-Control"])
        approval_id = response.get_json()["approval"]["approval_id"]
        self.assertEqual(200, client.get("/api/admin/recognition-control/approvals/" + approval_id).status_code)
        listed = client.get("/api/admin/recognition-control/operations/" + self.oid + "/approvals")
        self.assertEqual(1, len(listed.get_json()))

    def test_web_anonymous_reviewer_lead_rejected(self):
        b.install(self.config, operator="test-host", reason="disposable migration", now=NOW)
        client = self.web()
        suffix = "operations/" + self.oid + "/approve"
        values = dict(step_up_token="x"*40, confirmation_token="y"*40, reason="attempt")
        with client.session_transaction() as browser:
            browser["auth_csrf"] = "test-csrf"
        self.assertEqual(403, self.post(client, suffix, **values).status_code)
        self.login(client, "reviewer@example.test")
        self.assertEqual(403, self.post(client, suffix, **values).status_code)
        self.sql("UPDATE community_reviewers SET role='review_lead' WHERE id=2")
        self.assertEqual(403, self.post(client, suffix, **values).status_code)
