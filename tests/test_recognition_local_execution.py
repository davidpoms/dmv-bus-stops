"""Fresh disposable local bridge tests. No production factory or providers."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from copy import deepcopy
import hashlib
import json
import sqlite3
import socket
import tempfile
import threading
import unittest
from unittest.mock import patch

from cryptography.fernet import Fernet

from src.review.recognition import local_execution as c, administration as a, admin_auth as m, approvals as b
from src.review.recognition import permanent, execution, activation, authority, writer_boundary, dependencies, live_first_looks
from src.review.recognition import RecognitionGate, operation_schema
from src.review.recognition.schema import TABLES as EXPLORER
from tests import test_recognition_operations as operation_fixture
from tests import test_recognition_administration as slice_a
from tests.test_recognition_administration import NOW, at, independent_code, INSTALLATION


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


class LocalExecutionTests(unittest.TestCase):
    enrolled = slice_a.AdministrationTests.enrolled
    authenticated = slice_a.AdministrationTests.authenticated

    def setUp(self):
        self.fixture = operation_fixture.OperationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        # Place the NEW local workspace inside the fixture's disposable source
        # root so original preparation fixtures can still issue test-only records.
        with patch.object(tempfile, "tempdir", str(self.fixture.path.parent)):
            self.workspace = c.DisposableExecutionWorkspace()
        self.addCleanup(self.workspace.cleanup)
        self.path, self.control = self.workspace.target, self.workspace.control
        with closing(sqlite3.connect(self.fixture.path)) as source, closing(sqlite3.connect(self.path)) as target:
            source.backup(target)
        self.fixture.path = self.path
        with closing(sqlite3.connect(self.path)) as conn, conn:
            for definition in ("reviewer_key TEXT", "email TEXT", "email_verified_at TEXT", "role TEXT"):
                conn.execute("ALTER TABLE community_reviewers ADD COLUMN " + definition)
            conn.execute("UPDATE community_reviewers SET reviewer_key='owner-key',email='owner@example.test',email_verified_at='2026-01-01',role='owner' WHERE id=1")
            conn.execute("UPDATE community_reviewers SET reviewer_key='other-key',role='reviewer' WHERE id=2")
        self.workspace.install_target_storage()
        self.workspace.install_target_storage()
        self.new_operation()
        self.key_file = self.workspace.directory / "test-mfa.key"
        self.key_file.write_bytes(Fernet.generate_key())
        self.key_file.chmod(0o600)
        self.config = a.LocalAdministration(self.path, self.control, self.key_file)
        a.install(self.config, installation_id=INSTALLATION, owner_id=1, operator="disposable-host", reason="test", now=NOW)
        b.install(self.config, operator="disposable-host", reason="test", now=NOW)
        self.primary = m.record_primary_authentication(self.config, actor_id=1, reviewer_key="owner-key", now=NOW)
        self.session = self.authenticated()
        self.approve()
        self.context = self.workspace.bind(self.config)
        self.workspace.set_readiness(permitted=True, now=at(60))

    def sql(self, statement, values=(), *, control=False):
        with closing(sqlite3.connect(self.control if control else self.path)) as conn, conn:
            return conn.execute(statement, values).fetchall()

    def new_operation(self, *, geography=False, policy=None):
        request = self.fixture.request(geography=geography)
        event = self.fixture.freeze(self.fixture.create(request)["preparation_id"])["event"]["event_id"]
        self.operation = self.fixture.make(event=event, policy=deepcopy(c.POLICY if policy is None else policy))
        self.oid = self.operation["envelope"]["operation_id"]

    def approve(self, seconds=60):
        self.step = m.create_step_up(self.config, self.session, independent_code(at(seconds)), action="approve", operation_id=self.oid, now=at(seconds))
        self.token = m.begin_operation_confirmation(self.config, self.session, self.step, operation_id=self.oid, now=at(seconds))
        self.approval = b.create_approval(self.config, self.session, self.step, self.token, operation_id=self.oid, reason="Reviewed disposable population", now=at(seconds))
        self.aid = self.approval["approval"]["approval_id"]

    def execute(self, seconds=60):
        return c.execute_approved_operation(self.context, self.session, self.aid, now=at(seconds))

    def recover(self, seconds=90):
        step = m.create_step_up(self.config, self.session, independent_code(at(seconds)), action="recover", operation_id=self.oid, now=at(seconds))
        return c.reconcile_operation(self.context, self.session, step, self.aid, now=at(seconds))

    def counts(self):
        return tuple(self.sql("SELECT COUNT(*) FROM " + table)[0][0] for table in
            ("recognition_execution_claims", "recognition_execution_seals", "recognition_private_operations", "recognition_first_look_claims"))

    def test_success_exact_actual_writer_receipt_and_explorer(self):
        before = {table: self.sql("SELECT * FROM " + table) for table in EXPLORER}
        with patch.object(authority, "DisposableWorkspace", side_effect=AssertionError("synthetic authority")), \
             patch.object(execution, "execute_operation", side_effect=AssertionError("signed execution")), \
             patch.object(activation, "activate_production", side_effect=AssertionError("activation")), \
             patch.object(live_first_looks, "seal_pending", side_effect=AssertionError("live writer")):
            result = self.execute()
        self.assertEqual(("ADMITTED", "COMPLETED"), (result.admission, result.state))
        self.assertEqual([(1, 1, 1)], self.sql("SELECT physical_stop_id,reviewer_id,assignment_id FROM recognition_first_look_claims"))
        self.assertEqual((1, 1, 1, 1), self.counts())
        seal = json.loads(self.sql("SELECT body_json FROM recognition_execution_seals")[0][0])
        receipt = seal["receipt"]
        self.assertEqual(sha(self.operation["envelope"]), receipt["operation_sha256"])
        self.assertEqual(sha(receipt), result.receipt_sha256)
        self.assertEqual(self.aid, receipt["approval_id"])
        self.assertEqual(sha(self.approval["approval"]), receipt["approval_sha256"])
        self.assertEqual((1, 1, [], []), (receipt["authorized_count"], len(receipt["successful"]), receipt["quarantined"], receipt["other"]))
        self.assertEqual((INSTALLATION, 1, 1), (receipt["installation_id"], receipt["restore_generation"], receipt["actor_id"]))
        stat = self.path.stat()
        self.assertEqual(dict(hostname=socket.gethostname(), database=str(self.path.resolve()), device=stat.st_dev, inode=stat.st_ino), receipt["target_observation"]["observation"])
        self.assertEqual(before, {table: self.sql("SELECT * FROM " + table) for table in EXPLORER})
        self.assertEqual("ALREADY_EXECUTED", self.execute().admission)
        historical = b.get_approval(self.config, self.session, self.aid, now=at(60))
        self.assertEqual("APPROVED", historical["state"])
        self.assertFalse(historical["execution_pending"])
        self.assertEqual("NOT_ACTIVATED", activation.get_activation_state().state)

    def test_geography_actual_writer(self):
        for n in range(2, 6):
            self.fixture.review(n)
        self.new_operation(geography=True)
        self.approve(90)
        result = self.execute(90)
        self.assertEqual("COMPLETED", result.state)
        self.assertEqual([(1, 5, 10), (1, 5, 10)], self.sql("SELECT reviewer_id,numerator,denominator FROM recognition_geography_awards"))
        self.assertEqual([(10,)], self.sql("SELECT COUNT(*) FROM recognition_geography_members"))

    def test_no_production_context_or_direct_writer(self):
        for context in (None, object(), self.config):
            self.assertEqual("BLOCKED", c.execute_approved_operation(context, self.session, self.aid, now=at(60)).admission)
        with self.assertRaises(TypeError):
            c.DisposableExecutionContext()
        with self.assertRaises(Exception):
            authority.provision_production_authority()
        manifest = self.fixture.first()
        with self.assertRaises(Exception):
            permanent.finalize(self.path, manifest, manifest_sha256=sha(manifest), authorization_reference=manifest["authorization_reference"], gate=RecognitionGate(issuance=True))
        self.assertEqual((0, 0, 0, 0), self.counts())

    def _crash(self, stage):
        def interrupt(point):
            if point == stage:
                raise execution.SimulatedInterruption(stage)
        with patch.object(c, "_fault", side_effect=interrupt), self.assertRaises(execution.SimulatedInterruption):
            self.execute()
        expected = (0, 0, 0, 0) if stage in "AB" else ((1, 0, 0, 0) if stage in "CD" else (1, 1, 1, 1))
        self.assertEqual(expected, self.counts())
        if stage in "AB":
            self.assertEqual("COMPLETED", self.execute().state)
        elif stage in "CD":
            self.assertEqual("RECOVERY_REQUIRED", self.execute().admission)
            self.assertEqual("FAILED_BEFORE_COMMIT", self.recover().state)
            self.assertEqual("FAILED_BEFORE_COMMIT", self.execute(90).state)
        elif stage == "E":
            self.assertEqual("RECOVERY_REQUIRED", self.execute().admission)
            self.assertEqual("ALREADY_EXECUTED", self.recover().admission)
            self.assertEqual("ALREADY_EXECUTED", self.execute(90).admission)
        else:
            self.assertEqual("ALREADY_EXECUTED", self.execute().admission)

    def test_crash_a(self): self._crash("A")
    def test_crash_b(self): self._crash("B")
    def test_crash_c(self): self._crash("C")
    def test_crash_d(self): self._crash("D")
    def test_crash_e(self): self._crash("E")
    def test_crash_f(self): self._crash("F")
    def test_crash_g(self): self._crash("G")

    def test_stale_dependency_blocks(self):
        self.sql("UPDATE stop_review_assignments SET status='pending' WHERE id=1")
        result = self.execute()
        self.assertEqual("BLOCKED", result.admission)
        self.assertEqual((0, 0, 0, 0), self.counts())

    def test_invalid_dependency_blocks(self):
        self.sql("DELETE FROM stop_observations WHERE assignment_id=1")
        self.assertNotEqual("COMPLETED", self.execute().state)
        self.assertEqual((0, 0, 0, 0), self.counts())

    def test_temporary_verification_waits_and_rechecks(self):
        with patch.object(dependencies, "recheck", return_value={"state": "VERIFICATION_FAILURE"}):
            result = self.execute()
        self.assertEqual(("WAITING_FOR_VERIFICATION", "WAITING"), (result.admission, result.state))
        self.assertEqual((0, 0, 0, 0), self.counts())
        self.assertEqual("COMPLETED", self.execute().state)

    def test_superseded_operation_blocks(self):
        self.fixture.decision(self.operation, "SUPERSEDED")
        self.assertEqual("BLOCKED", self.execute().admission)
        self.assertEqual((0, 0, 0, 0), self.counts())

    def test_invalidated_approval_blocks(self):
        b.invalidate_approval(self.config, self.session, self.step, self.aid, reason="changed review", now=at(60))
        self.assertEqual("BLOCKED", self.execute().admission)
        self.assertEqual((0, 0, 0, 0), self.counts())

    def test_target_generation_advance_blocks(self):
        with a.connect(self.path) as conn:
            observation = a.observe_target(conn)
        a.advance_restore_generation(self.config, expected_generation=1, expected_target_sha256=sha(observation), operator="disposable-host", reason="restore test", now=at(60))
        self.assertNotEqual("COMPLETED", self.execute().state)
        self.assertEqual((0, 0, 0, 0), self.counts())

    def test_schema_change_blocks(self):
        self.sql("CREATE TABLE unexpected_schema(id INTEGER)")
        self.assertNotEqual("COMPLETED", self.execute().state)
        self.assertEqual((0, 0, 0, 0), self.counts())

    def test_target_installation_mismatch_blocks(self):
        self.sql("UPDATE recognition_local_installation SET installation_id='wrong-installation'")
        self.assertNotEqual("COMPLETED", self.execute().state)
        self.assertEqual((0, 0, 0, 0), self.counts())

    def test_deactivation_blocks(self):
        self.workspace.set_readiness(permitted=False, now=at(60))
        self.assertEqual("activation_not_permitted", self.execute().reason)
        self.assertEqual((0, 0, 0, 0), self.counts())

    def test_stop_before_entry_blocks(self):
        self.workspace.set_stop(active=True, now=at(60))
        self.assertEqual("emergency_stop", self.execute().reason)
        self.assertEqual((0, 0, 0, 0), self.counts())

    def test_concurrent_executors(self):
        barrier = threading.Barrier(2)
        def run():
            barrier.wait()
            return self.execute().admission
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda _: run(), range(2)))
        self.assertEqual(["ADMITTED", "ALREADY_EXECUTED"], sorted(results))
        self.assertEqual((1, 1, 1, 1), self.counts())

    def test_different_operations_same_writer_cannot_duplicate(self):
        first_aid = self.aid
        self.new_operation()
        self.approve(90)
        second_aid = self.aid
        first = c.execute_approved_operation(self.context, self.session, first_aid, now=at(90))
        second = c.execute_approved_operation(self.context, self.session, second_aid, now=at(90))
        self.assertEqual("COMPLETED", first.state)
        self.assertEqual("BLOCKED", second.admission)
        self.assertEqual((1, 1, 1, 1), self.counts())

    def test_recovery_requires_owner_session_and_step(self):
        result = c.reconcile_operation(self.context, None, None, self.aid, now=at(60))
        self.assertEqual("RECOVERY_REQUIRED", result.admission)
        self.assertEqual((0, 0, 0, 0), self.counts())

    def test_quarantine_policy_rejected(self):
        policy = deepcopy(c.POLICY)
        policy["quarantine_categories"] = ["bad_evidence"]
        self.new_operation(policy=policy)
        self.approve(90)
        self.assertEqual("unsupported_accounting_or_quarantine", self.execute(90).reason)
        self.assertEqual((0, 0, 0, 0), self.counts())

    def test_preview_never_is_admission(self):
        preview = c.verify_approved_operation(self.context, self.session, self.aid, now=at(60))
        self.assertEqual("VERIFIED", preview.admission)
        self.workspace.set_stop(active=True, now=at(60))
        self.assertEqual("BLOCKED", self.execute().admission)

    def test_commit_lost_ack_never_retries_writer(self):
        commits = []
        def commit(conn):
            conn.commit()
            commits.append(1)
            if len(commits) == 2:
                raise sqlite3.OperationalError("simulated lost writer commit acknowledgement")
        with patch.object(c, "_commit_target", side_effect=commit):
            self.assertEqual("RECOVERY_REQUIRED", self.execute().admission)
        self.assertEqual((1, 1, 1, 1), self.counts())
        with patch.object(permanent, "finalize", side_effect=AssertionError("blind retry")):
            self.assertEqual("RECOVERY_REQUIRED", self.execute().admission)
            self.assertEqual("ALREADY_EXECUTED", self.recover().admission)

    def test_dependency_changes_in_claim_commit_gap(self):
        def change(point):
            if point == "C":
                self.sql("UPDATE stop_review_assignments SET status='pending' WHERE id=1")
        with patch.object(c, "_fault", side_effect=change):
            self.assertEqual("RECOVERY_REQUIRED", self.execute().admission)
        self.assertEqual((1, 0, 0, 0), self.counts())
        self.assertEqual("FAILED_BEFORE_COMMIT", self.recover().state)

    def test_policy_changes_after_approval(self):
        modified = deepcopy(permanent.DEFINITIONS)
        modified["first_look"]["ordering"] = "unsupported-policy"
        with patch.dict(permanent.DEFINITIONS, modified):
            self.assertEqual("BLOCKED", self.execute().admission)
        self.assertEqual((0, 0, 0, 0), self.counts())

    def test_owner_demotion_blocks(self):
        self.sql("UPDATE community_reviewers SET role='review_lead' WHERE id=1")
        self.assertEqual("BLOCKED", self.execute().admission)
        self.assertEqual((0, 0, 0, 0), self.counts())

    def test_operation_digest_change_blocks(self):
        table = "recognition_operation_contracts"
        triggers = [(name, sql) for name, sql in operation_schema.definitions().items() if name.startswith(table + "_immutable_")]
        with closing(sqlite3.connect(self.path)) as conn, conn:
            for name, _ in triggers:
                conn.execute("DROP TRIGGER " + name)
            row = conn.execute("SELECT body_json FROM recognition_operation_contracts WHERE operation_id=?", (self.oid,)).fetchone()
            body = json.loads(row[0])
            body["population_sha256"] = "0"*64
            conn.execute("UPDATE recognition_operation_contracts SET body_json=?,body_sha256=? WHERE operation_id=?", (c.canonical(body), sha(body), self.oid))
            for _, sql in triggers:
                conn.execute(sql)
        self.assertEqual("BLOCKED", self.execute().admission)
        self.assertEqual((0, 0, 0, 0), self.counts())

    def test_target_file_replacement_blocks(self):
        replacement = self.workspace.directory / "replacement.sqlite"
        with closing(sqlite3.connect(self.path)) as source, closing(sqlite3.connect(replacement)) as dest:
            source.backup(dest)
        replacement.replace(self.path)
        self.assertEqual("BLOCKED", self.execute().admission)
        self.assertEqual((0, 0, 0, 0), self.counts())

    def test_stop_request_after_entry_serializes_without_interrupting(self):
        blocked = []
        def stop_request(point):
            if point == "C":
                with closing(sqlite3.connect(self.control, timeout=0)) as conn:
                    with self.assertRaises(sqlite3.OperationalError):
                        conn.execute("BEGIN IMMEDIATE")
                blocked.append(True)
        with patch.object(c, "_fault", side_effect=stop_request):
            self.assertEqual("COMPLETED", self.execute().state)
        self.workspace.set_stop(active=True, now=at(90))
        self.assertEqual([True], blocked)
        self.assertEqual("ALREADY_EXECUTED", self.execute(90).admission)

    def test_writer_capability_is_exact_and_one_use(self):
        original = permanent.finalize
        saved = []
        def inspect(database, manifest, **kwargs):
            token = kwargs["execution_context"]
            saved.append(token)
            wrong = deepcopy(manifest)
            wrong["authorization_reference"] = "another-operation"
            with self.assertRaises(Exception):
                original(database, wrong, **{**kwargs, "manifest_sha256": sha(wrong), "authorization_reference": "another-operation"})
            result = original(database, manifest, **kwargs)
            with self.assertRaises(Exception):
                original(database, manifest, **kwargs)
            return result
        with patch.object(permanent, "finalize", side_effect=inspect):
            self.assertEqual("COMPLETED", self.execute().state)
        with self.assertRaises(Exception):
            writer_boundary.acquire(saved[0], self.path, self.fixture.first())

    def test_receipt_integrity_not_just_completed_flag(self):
        self.assertEqual("COMPLETED", self.execute().state)
        with patch.object(execution, "_writer_evidence", return_value="0"*64):
            self.assertNotEqual("ALREADY_EXECUTED", self.execute().admission)
        self.assertEqual((1, 1, 1, 1), self.counts())

    def test_install_savepoint_rolls_back(self):
        fresh = c.DisposableExecutionWorkspace()
        self.addCleanup(fresh.cleanup)
        # Existing explicit schemas are installed first in setUp; verify failure
        # rolls back the entire caller-owned DDL using a fresh disposable copy.
        with closing(sqlite3.connect(self.path)) as source, closing(sqlite3.connect(fresh.target)) as dest:
            source.backup(dest)
        with closing(sqlite3.connect(fresh.target)) as conn, conn:
            for name in c.execution_schema.definitions():
                if name not in c.execution_schema.TABLES:
                    conn.execute("DROP TRIGGER " + name)
            for table in ("recognition_execution_seals", "recognition_execution_claims", "recognition_execution_audit", "recognition_execution_storage"):
                conn.execute("DROP TABLE " + table)
        before = None
        with a.connect(fresh.target) as conn:
            before = list(conn.iterdump())
        with patch.object(c.execution_schema, "check_schema", side_effect=RuntimeError("DDL check failed")):
            with self.assertRaises(RuntimeError):
                fresh.install_target_storage()
        with a.connect(fresh.target) as conn:
            self.assertEqual(before, list(conn.iterdump()))

    def test_approval_automatically_verifies_and_executes(self):
        self.new_operation()
        step = m.create_step_up(self.config, self.session, independent_code(at(90)), action="approve", operation_id=self.oid, now=at(90))
        token = m.begin_operation_confirmation(self.config, self.session, step, operation_id=self.oid, now=at(90))
        result = c.approve_and_execute(self.config, self.session, step, token, operation_id=self.oid, reason="Reviewed", now=at(90), context=self.context)
        self.assertEqual("COMPLETED", result["execution"]["state"])
        self.assertFalse(result["execution_pending"])
        self.assertEqual((1, 1, 1, 1), self.counts())

    def test_two_http_approval_requests_cannot_enable_production_execution(self):
        from src.api import app as api
        from src.review.recognition import admin_routes
        self.new_operation()
        step = m.create_step_up(self.config, self.session, independent_code(at(90)), action="approve", operation_id=self.oid, now=at(90))
        token = m.begin_operation_confirmation(self.config, self.session, step, operation_id=self.oid, now=at(90))
        barrier = threading.Barrier(2)
        def request():
            client = api.app.test_client()
            with client.session_transaction() as browser:
                browser.update(authenticated_reviewer_id=1, reviewer_key="owner-key", recognition_primary=self.primary,
                               recognition_admin=self.session, auth_csrf="test-csrf")
            barrier.wait()
            response = client.post("/api/admin/recognition-control/operations/" + self.oid + "/approve", json=dict(
                step_up_token=step, confirmation_token=token, reason="Reviewed", csrf_token="test-csrf"))
            return response.status_code, response.get_json()
        with patch.object(api, "DATABASE_PATH", self.path), patch.dict(api.app.config, dict(TESTING=True, SECRET_KEY="slice-c-disposable-only",
                RECOGNITION_ADMIN_CONTROL=str(self.control), RECOGNITION_ADMIN_KEY_FILE=str(self.key_file))), \
             patch.object(admin_routes, "now_utc", return_value=at(90)):
            with ThreadPoolExecutor(2) as pool:
                results = list(pool.map(lambda _: request(), range(2)))
        self.assertEqual([201, 403], sorted(status for status, _ in results))
        successful = next(body for status, body in results if status == 201)
        self.assertEqual("BLOCKED", successful["execution"]["admission"])
        self.assertEqual((0, 0, 0, 0), self.counts())

    def test_unsupported_family_blocks(self):
        with patch.object(c, "SUPPORTED", frozenset()):
            self.assertEqual("UNSUPPORTED_OPERATION", self.execute().reason)
        self.assertEqual((0, 0, 0, 0), self.counts())

    def test_context_and_claim_alone_cannot_mint_writer_lease(self):
        def fail(point):
            if point == "C":
                raise execution.SimulatedInterruption("claim only")
        with patch.object(c, "_fault", side_effect=fail), self.assertRaises(execution.SimulatedInterruption):
            self.execute()
        manifest = self.fixture.first()
        with a.connect(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            claim = c._read(conn, "recognition_execution_claims", self.oid)
            with self.assertRaisesRegex(Exception, "protected_final_verification"):
                with writer_boundary._local_lease(self.context, conn, manifest, claim):
                    self.fail("unverified context issued a lease")
        self.assertEqual((1, 0, 0, 0), self.counts())

    def test_outcomes_without_seal_require_reconciliation(self):
        def fail(point):
            if point == "C":
                raise execution.SimulatedInterruption("claim only")
        with patch.object(c, "_fault", side_effect=fail), self.assertRaises(execution.SimulatedInterruption):
            self.execute()
        from tests.recognition_authorization_fixture import finalize
        manifest = self.fixture.first()
        finalize(self.path, manifest, manifest_sha256=sha(manifest), authorization_reference=manifest["authorization_reference"], gate=RecognitionGate(issuance=True))
        with patch.object(permanent, "finalize", side_effect=AssertionError("recovery must never write awards")):
            self.assertEqual("PARTIALLY_EXECUTED_RECONCILIATION_REQUIRED", self.recover().state)
            self.assertEqual("RECOVERY_REQUIRED", self.execute(90).admission)
