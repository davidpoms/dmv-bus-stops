"""New disposable targets, explicit synthetic approvals, no production execution."""

import base64
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from src.review.recognition import (RecognitionGate, dependencies, enrollment, execution as x,
    execution_schema, operations, permanent, permanent_schema, status, trust, writer_boundary, live_first_looks)
from src.review.recognition.authorization import AuthorizationError, migration_binding, manifest_binding
from src.review.recognition.rules import canonical
from src.review.recognition.schema import connection, TABLES as EXPLORER_TABLES
from tests import recognition_trust_fixture as f
from tests.recognition_authorization_fixture import approval
from tests.recognition_authorization_fixture import workspace_for


NOW = "2099-01-01T00:00:00Z"
EXPIRY = "2099-01-04T00:00:00Z"


def independent_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.base = f.TrustFixture()
        self.base.setUp()
        self.addCleanup(self.base.doCleanups)
        self.fixture = self.base.fixture
        self.enrollment_key = Ed25519PrivateKey.generate()
        config = dict(registry_id="synthetic-enrollment-registry", issuer_id="synthetic-storage-admin",
            key_id="synthetic-enrollment-key", public_key=base64.b64encode(
                self.enrollment_key.public_key().public_bytes_raw()).decode(), host_id="synthetic-host", deployment_id="synthetic-deployment")
        with patch.object(tempfile, "tempdir", str(self.fixture.path.parent)):
            self.workspace = enrollment.SyntheticEnrollmentWorkspace(canonical(config))
        self.addCleanup(self.workspace.cleanup)
        self.path = self.workspace.directory / "execution-target.sqlite"
        shutil.copyfile(self.fixture.path, self.path)
        self.fixture.path = self.path
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            permanent_schema.install(conn, **approval(self.path, **migration_binding("private_recognition", permanent_schema.definitions())))
            execution_schema.install(conn, **approval(self.path, **migration_binding("recognition_execution", execution_schema.definitions())))
            conn.commit()
        self.checkpoint = self.workspace.directory / "status.sqlite"
        self.control = self.workspace.directory / "control.sqlite"
        for path, install in ((self.checkpoint, status.install_checkpoint), (self.control, execution_schema.install_control)):
            with closing(sqlite3.connect(path)) as conn:
                conn.execute("BEGIN IMMEDIATE")
                install(conn)
                conn.commit()
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            subject = execution_schema.storage_subject(conn, self.control, self.checkpoint)
            execution_schema.bind_stores(conn, self.control, self.checkpoint,
                **approval(self.path, **execution_schema.storage_binding(subject)))
            conn.commit()
        self.workspace.establish_incarnation(self.path)
        self.record = self.enroll()
        self.ref = self.workspace.register(self.record, trusted_now_utc=NOW)
        self.prepare()

    def enroll(self, supersedes=None):
        p = trust.load(self.workspace.payload(self.path, enrollment_id=str(uuid4()), issued_at_utc=NOW,
            provenance="synthetic-storage-ceremony", supersedes=supersedes))
        raw = b"DMV-recognition-target-enrollment-v1\x00" + json.dumps(p, sort_keys=True,
            separators=(",", ":"), ensure_ascii=True).encode()
        return canonical(dict(format=enrollment.FORMAT, algorithm="Ed25519", payload=p,
            signature=base64.b64encode(self.enrollment_key.sign(raw)).decode()))

    def prepare(self, *, geography=False, policy=None):
        request = self.fixture.request(geography=geography)
        event = self.fixture.freeze(self.fixture.create(request)["preparation_id"])["event"]["event_id"]
        policy = deepcopy(x.POLICY if policy is None else policy)
        subject = dict(event_id=event, accounting_policy=policy, enrollment=self.ref)
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            op = operations.create_operation(conn, event, policy, enrollment_reference=self.ref,
                enrollment_provider=self.workspace, trusted_now_utc=NOW,
                **approval(self.path, **operations.binding("create", subject)))
            conn.commit()
        e = op["envelope"]
        p = trust.load(trust.authorization_payload(canonical(e), artifact_id=str(uuid4()), authority_id="authority-A",
            key_id="key-A", registry_id="synthetic-registry", issued_at_utc=NOW, expires_at_utc=EXPIRY))
        self.artifact = f.signed(p, self.base.keys["A"])
        self.authref = dict(authorization_id=p["artifact_id"], artifact_sha256=independent_digest(json.loads(self.artifact)))
        self.operation = self.fixture.decision(op, "AUTHORIZED", evidence=self.authref)
        self.e = self.operation["envelope"]
        self.oid = self.e["operation_id"]
        self.manifest = self.fixture.first() if not geography else self.fixture.geo()
        self.writer_permission = approval(self.path, **manifest_binding(self.manifest))
        self.execution_permission = approval(self.path, **x.execution_binding(self.e))
        self.context = x.SyntheticExecutionContext(self.path, self.oid, enrollment_provider=self.workspace,
            trust_provider=self.base.provider, checkpoint_path=self.checkpoint, control_path=self.control,
            execution_authorization=self.execution_permission["authorization"],
            writer_authorization=self.writer_permission["authorization"], authority=self.writer_permission["authority"])
        self.status_payload = deepcopy(self.base.status_payload)
        self.status_payload.update(issued_at_utc=NOW, expires_at_utc=EXPIRY)
        self.snapshot = f.signed(self.status_payload, self.base.keys["status"], "status")

    def execute(self, **overrides):
        return x.execute_operation(self.context, **{**dict(artifact_json=self.artifact, snapshot_json=self.snapshot,
            trusted_now_utc=NOW), **overrides})

    def recovery_permission(self):
        return approval(self.path, **x.execution_binding(self.e, "reconcile"))["authorization"]

    def recover(self, **overrides):
        return x.reconcile_operation(self.context, **{**dict(recovery_authorization=self.recovery_permission(), trusted_now_utc=NOW), **overrides})

    def sql(self, query, params=()):
        return self.fixture.sql(query, params)

    def test_success_receipt_accounting_independent_hash_and_duplicate(self):
        before = {t: self.sql("SELECT * FROM " + t) for t in EXPLORER_TABLES}
        result = self.execute()
        self.assertEqual(("ADMITTED", "COMPLETED"), (result.admission, result.state))
        self.assertEqual([(1, 1, 1)], self.sql("SELECT physical_stop_id,reviewer_id,assignment_id FROM recognition_first_look_claims"))
        with connection(self.path) as conn:
            op = operations.get_operation(conn, self.oid)
        self.assertEqual(dict(authorized=1, successful=1, quarantined=0, other=0, unaccounted=0), operations.validate_receipt(op, op["receipt"]))
        self.assertEqual(self.authref, op["receipt"]["authorization"])
        self.assertEqual(self.ref, op["receipt"]["enrollment"])
        self.assertEqual(independent_digest(op["receipt"]), result.receipt_sha256)
        self.assertEqual("ALREADY_EXECUTED", self.execute().admission)
        self.assertEqual(1, self.sql("SELECT COUNT(*) FROM recognition_private_operations")[0][0])
        self.assertEqual(before, {t: self.sql("SELECT * FROM " + t) for t in EXPLORER_TABLES})

    def test_admit_automatically_executes(self):
        result = x.admit_operation(self.context, artifact_json=self.artifact, snapshot_json=self.snapshot, trusted_now_utc=NOW)
        self.assertEqual("COMPLETED", result.state)

    def test_concurrent_invocations_do_not_double_apply(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.execute(), range(2)))
        self.assertEqual({"ADMITTED", "ALREADY_EXECUTED"}, {r.admission for r in results})
        self.assertEqual(1, self.sql("SELECT COUNT(*) FROM recognition_first_look_claims")[0][0])

    def test_geography_dispatch_uses_existing_writer(self):
        for n in range(2, 6):
            self.fixture.review(n)
        self.prepare(geography=True)
        result = self.execute()
        self.assertEqual("COMPLETED", result.state)
        self.assertEqual(2, self.sql("SELECT COUNT(*) FROM recognition_geography_awards")[0][0])
        self.assertEqual(10, self.sql("SELECT COUNT(*) FROM recognition_geography_members")[0][0])

    def test_before_claim_interruption_has_no_durable_execution_and_can_submit(self):
        with self.assertRaises(x.SimulatedInterruption):
            self.execute(fault_point="BEFORE_CLAIM")
        self.assertEqual(0, self.sql("SELECT COUNT(*) FROM recognition_execution_claims")[0][0])
        self.assertEqual("COMPLETED", self.execute().state)

    def test_after_claim_interruption_requires_separate_recovery_and_new_operation(self):
        with self.assertRaises(x.SimulatedInterruption):
            self.execute(fault_point="AFTER_CLAIM")
        self.assertEqual("RECOVERY_REQUIRED", self.execute().admission)
        self.assertEqual(0, self.sql("SELECT COUNT(*) FROM recognition_first_look_claims")[0][0])
        self.assertEqual("FAILED_BEFORE_COMMIT", self.recover().state)
        self.assertEqual("BLOCKED", self.execute().admission)
        self.prepare()
        self.assertEqual("COMPLETED", self.execute().state)

    def test_after_mutation_before_commit_rolls_back_and_never_blind_retries(self):
        with self.assertRaises(x.SimulatedInterruption):
            self.execute(fault_point="AFTER_MUTATION")
        self.assertEqual(0, self.sql("SELECT COUNT(*) FROM recognition_first_look_claims")[0][0])
        self.assertEqual(0, self.sql("SELECT COUNT(*) FROM recognition_execution_seals")[0][0])
        self.assertEqual("RECOVERY_REQUIRED", self.execute().admission)
        self.assertEqual("FAILED_BEFORE_COMMIT", self.recover().state)

    def test_after_commit_before_projection_recovers_durable_receipt(self):
        with self.assertRaises(x.SimulatedInterruption):
            self.execute(fault_point="AFTER_COMMIT")
        self.assertEqual(1, self.sql("SELECT COUNT(*) FROM recognition_first_look_claims")[0][0])
        self.assertEqual(0, self.sql("SELECT COUNT(*) FROM recognition_operation_receipts")[0][0])
        self.assertEqual("RECOVERY_REQUIRED", self.execute().admission)
        result = self.recover()
        self.assertEqual(("ALREADY_EXECUTED", "COMPLETED"), (result.admission, result.state))
        self.assertEqual("ALREADY_EXECUTED", self.execute().admission)

    def test_after_finalization_interruption_returns_already_executed(self):
        with self.assertRaises(x.SimulatedInterruption):
            self.execute(fault_point="AFTER_FINALIZATION")
        self.assertEqual("ALREADY_EXECUTED", self.execute().admission)

    def test_uncertain_commit_error_after_actual_commit_requires_reconciliation(self):
        def commit_then_error(conn):
            conn.commit()
            raise sqlite3.OperationalError("synthetic lost acknowledgement")
        with patch.object(x, "_commit_target", side_effect=commit_then_error):
            self.assertEqual("RECOVERY_REQUIRED", self.execute().admission)
        self.assertEqual("RECOVERY_REQUIRED", self.execute().admission)
        self.assertEqual("COMPLETED", self.recover().state)

    def test_recovery_authority_is_separate_from_ordinary_authorization_or_role(self):
        with self.assertRaises(x.SimulatedInterruption):
            self.execute(fault_point="AFTER_CLAIM")
        for permission in (self.execution_permission["authorization"], self.writer_permission["authorization"], {"role": "owner"}):
            with self.subTest(permission=type(permission)), self.assertRaises((trust.TrustError, AuthorizationError)):
                self.recover(recovery_authorization=permission)
        self.assertEqual("FAILED_BEFORE_COMMIT", self.recover().state)

    def test_recovery_fences_original_delayed_worker(self):
        with self.assertRaises(x.SimulatedInterruption):
            self.execute(fault_point="AFTER_CLAIM")
        self.recover()
        result = x._execute_claim(x._context(self.context), NOW, None)
        self.assertEqual("FAILED_BEFORE_COMMIT", result.state)
        self.assertEqual(0, self.sql("SELECT COUNT(*) FROM recognition_first_look_claims")[0][0])

    def test_invalid_signature_permanently_blocks_operation(self):
        value = json.loads(self.artifact)
        value["payload"]["artifact_id"] = str(uuid4())
        self.assertEqual("BLOCKED", self.execute(artifact_json=canonical(value)).admission)
        self.assertEqual("BLOCKED", self.execute().admission)

    def test_missing_status_waits_without_losing_authorization(self):
        result = self.execute(snapshot_json=None)
        self.assertEqual(("WAITING_FOR_VERIFICATION", "WAITING"), (result.admission, result.state))
        self.assertEqual("COMPLETED", self.execute().state)

    def test_invalid_status_and_revoked_authority_cannot_quarantine(self):
        p = deepcopy(self.status_payload)
        p["authorities"][0]["state"] = "REVOKED"
        snapshot = f.signed(p, self.base.keys["status"], "status")
        self.assertEqual("BLOCKED", self.execute(snapshot_json=snapshot).admission)
        self.assertEqual(0, self.sql("SELECT COUNT(*) FROM recognition_execution_seals")[0][0])

    def test_relevant_population_change_permanently_blocks(self):
        self.fixture.review(2)
        self.assertEqual("BLOCKED", self.execute().admission)
        self.assertEqual(0, self.sql("SELECT COUNT(*) FROM recognition_first_look_claims")[0][0])

    def test_dependency_temporary_failure_waits(self):
        with patch.object(dependencies, "recheck", return_value={"state": "VERIFICATION_FAILURE", "reasons": ["read_failed"]}):
            self.assertEqual("WAITING_FOR_VERIFICATION", self.execute().admission)
        self.assertEqual("COMPLETED", self.execute().state)

    def test_target_replacement_records_block_outside_target(self):
        replacement = self.path.with_name("replacement.sqlite")
        shutil.copyfile(self.path, replacement)
        replacement.replace(self.path)
        result = self.execute()
        self.assertEqual(("BLOCKED", "target_identity_mismatch"), (result.admission, result.reason))
        with closing(sqlite3.connect(self.control)) as conn:
            self.assertEqual(1, conn.execute("SELECT COUNT(*) FROM recognition_execution_blocks").fetchone()[0])

    def test_new_enrollment_cannot_satisfy_old_operation(self):
        self.workspace.register(self.enroll(self.ref), trusted_now_utc=NOW)
        self.assertEqual("BLOCKED", self.execute().admission)

    def test_different_operation_cannot_reuse_authorization_or_receipt(self):
        self.execute()
        old_artifact = self.artifact
        self.prepare()
        self.assertEqual("BLOCKED", self.execute(artifact_json=old_artifact).admission)
        self.assertEqual(1, self.sql("SELECT COUNT(*) FROM recognition_execution_seals")[0][0])

    def test_committed_execution_remains_completed_after_authority_revocation(self):
        self.execute()
        p = deepcopy(self.status_payload)
        p.update(sequence=2, snapshot_id=str(uuid4()))
        p["authorities"][0]["state"] = "REVOKED"
        self.assertEqual("ALREADY_EXECUTED", self.execute(snapshot_json=f.signed(p, self.base.keys["status"], "status")).admission)

    def test_separate_recovery_context_does_not_require_writer_or_execute_permission(self):
        with self.assertRaises(x.SimulatedInterruption):
            self.execute(fault_point="AFTER_COMMIT")
        permissions = workspace_for(self.path).approved
        permissions.discard(self.execution_permission["authorization"])
        permissions.discard(self.writer_permission["authorization"])
        recovery = self.recovery_permission()
        context = x.SyntheticRecoveryContext(self.path, self.oid, enrollment_provider=self.workspace,
            trust_provider=self.base.provider, recovery_authorization=recovery, authority=self.writer_permission["authority"])
        self.assertEqual("COMPLETED", x.reconcile_operation(context, recovery_authorization=recovery, trusted_now_utc=NOW).state)
        self.assertEqual("BLOCKED", x.execute_operation(context, artifact_json=self.artifact,
            snapshot_json=self.snapshot, trusted_now_utc=NOW).admission)

    def test_dependency_change_between_claim_and_mutation_is_not_quarantine(self):
        original = x._interrupt
        def changed(point, fault):
            if point == "AFTER_CLAIM":
                self.fixture.review(2)
            return original(point, fault)
        with patch.object(x, "_interrupt", side_effect=changed):
            self.assertEqual("FAILED_BEFORE_COMMIT", self.execute().state)
        self.assertEqual(0, self.sql("SELECT COUNT(*) FROM recognition_first_look_claims")[0][0])

    def test_stale_dependencies_after_durable_commit_do_not_erase_completion(self):
        with self.assertRaises(x.SimulatedInterruption):
            self.execute(fault_point="AFTER_COMMIT")
        self.fixture.state(self.e["event_id"], "STALE")
        self.assertEqual("COMPLETED", self.recover().state)

    def test_writer_system_or_authorization_failure_is_never_quarantined(self):
        for error in (AuthorizationError("rejected"), sqlite3.OperationalError("synthetic I/O"), RuntimeError("synthetic system failure")):
            if self.sql("SELECT COUNT(*) FROM recognition_execution_claims")[0][0]:
                self.prepare()
            with self.subTest(error=type(error)), patch.object(permanent, "finalize", side_effect=error):
                self.assertEqual("FAILED_BEFORE_COMMIT", self.execute().state)
        self.assertEqual(0, self.sql("SELECT COUNT(*) FROM recognition_execution_seals")[0][0])

    def test_no_successful_receipt_can_be_fabricated_for_wrong_operation(self):
        self.execute()
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT body_json FROM recognition_execution_seals WHERE operation_id=?", (self.oid,)).fetchone()
            value = json.loads(row[0])
            value["receipt"]["operation_id"] = str(uuid4())
            conn.execute("DROP TRIGGER recognition_execution_seals_immutable_update")
            conn.execute("UPDATE recognition_execution_seals SET body_json=?,body_sha256=? WHERE operation_id=?",
                         (canonical(value), independent_digest(value), self.oid))
            conn.execute(execution_schema.definitions()["recognition_execution_seals_immutable_update"])
            conn.commit()
        self.assertEqual("RECOVERY_REQUIRED", self.execute().admission)
        self.assertEqual("RECOVERY_REQUIRED", self.recover().admission)

    def test_legacy_writer_outcomes_without_seal_are_not_adopted_by_recovery(self):
        with self.assertRaises(x.SimulatedInterruption):
            self.execute(fault_point="AFTER_CLAIM")
        permanent.finalize(self.path, self.manifest, manifest_sha256=self.e["writer_manifest_sha256"],
            authorization_reference=self.manifest["authorization_reference"], gate=RecognitionGate(issuance=True), **self.writer_permission)
        result = self.recover()
        self.assertEqual(("RECOVERY_REQUIRED", "PARTIALLY_EXECUTED_RECONCILIATION_REQUIRED"), (result.admission, result.state))
        self.assertEqual("RECOVERY_REQUIRED", self.execute().admission)

    def test_control_install_rollback_and_immutable_stop_and_block_records(self):
        permission = approval(self.control, **x.stop_binding(True, "stop", 0))["authorization"]
        x.set_emergency_stop(self.context, reason="stop", expected_sequence=0, authorization=permission, trusted_now_utc=NOW)
        with closing(sqlite3.connect(self.control)) as conn:
            conn.execute("PRAGMA recursive_triggers=OFF")
            for sql in ("UPDATE recognition_execution_stops SET body_json='{}'", "DELETE FROM recognition_execution_stops",
                        "INSERT OR REPLACE INTO recognition_execution_stops SELECT * FROM recognition_execution_stops"):
                with self.assertRaises(sqlite3.IntegrityError):
                    conn.execute(sql)
            conn.rollback()
        fresh = self.workspace.directory / "control-rollback.sqlite"
        with closing(sqlite3.connect(fresh)) as conn:
            conn.execute("BEGIN IMMEDIATE")
            execution_schema.install_control(conn)
            conn.rollback()
            self.assertFalse(conn.execute("SELECT name FROM sqlite_master WHERE name='recognition_execution_stops'").fetchall())

    def test_control_or_status_store_cannot_be_substituted_to_bypass_existing_state(self):
        for name, source in (("control", self.control), ("checkpoint", self.checkpoint)):
            other = source.with_name("substituted-" + source.name)
            shutil.copyfile(source, other)
            with self.subTest(name=name), self.assertRaisesRegex(trust.TrustError, "storage_binding_mismatch"):
                x.SyntheticExecutionContext(self.path, self.oid, enrollment_provider=self.workspace,
                    trust_provider=self.base.provider, checkpoint_path=other if name == "checkpoint" else self.checkpoint,
                    control_path=other if name == "control" else self.control,
                    execution_authorization=self.execution_permission["authorization"],
                    writer_authorization=self.writer_permission["authorization"], authority=self.writer_permission["authority"])

    def test_emergency_stop_can_be_activated_when_target_is_missing(self):
        self.path.unlink()
        permission = approval(self.control, **x.stop_binding(True, "target missing", 0))["authorization"]
        result = x.set_emergency_stop(self.context, reason="target missing", expected_sequence=0,
            authorization=permission, trusted_now_utc=NOW)
        self.assertTrue(result["active"])

    def test_checkpoint_commit_failure_after_claim_retains_target_status_floor(self):
        original = status._verified_status_transaction
        @contextmanager
        def interrupted(*args, **kwargs):
            with original(*args, **kwargs) as facts:
                yield facts
                raise sqlite3.OperationalError("synthetic checkpoint commit failure")
        p = {**self.status_payload, "sequence": 5, "snapshot_id": str(uuid4())}
        snapshot = f.signed(p, self.base.keys["status"], "status")
        with patch.object(status, "_verified_status_transaction", interrupted):
            self.assertEqual("RECOVERY_REQUIRED", self.execute(snapshot_json=snapshot).admission)
        self.assertEqual("RECOVERY_REQUIRED", self.execute().admission)
        self.assertEqual("FAILED_BEFORE_COMMIT", self.recover().state)
        self.prepare()
        result = self.execute()
        self.assertEqual(("BLOCKED", "target_status_sequence_rollback"), (result.admission, result.reason))

    def test_invalid_status_signature_permanently_blocks_without_quarantine(self):
        value = json.loads(self.snapshot)
        value["payload"]["sequence"] = 2
        self.assertEqual("BLOCKED", self.execute(snapshot_json=canonical(value)).admission)
        self.assertEqual(0, self.sql("SELECT COUNT(*) FROM recognition_execution_seals")[0][0])

    def test_valid_revocation_floor_survives_denial_and_blocks_old_status_for_new_operation(self):
        p = deepcopy(self.status_payload)
        p.update(sequence=2, snapshot_id=str(uuid4()))
        p["authorities"][0]["state"] = "REVOKED"
        snapshot = f.signed(p, self.base.keys["status"], "status")
        self.assertEqual("BLOCKED", self.execute(snapshot_json=snapshot).admission)
        with closing(sqlite3.connect(self.checkpoint)) as conn:
            self.assertEqual(2, conn.execute("SELECT sequence FROM recognition_status_checkpoint").fetchone()[0])
        self.prepare()
        result = self.execute()
        self.assertEqual(("BLOCKED", "status_sequence_rollback"), (result.admission, result.reason))

    def test_terminal_journal_cannot_transition_back_to_executing(self):
        self.execute()
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            with self.assertRaisesRegex(sqlite3.IntegrityError, "invalid_execution_transition"):
                x._append(conn, self.oid, "EXECUTING", "forbidden replay", NOW)

    def test_substantive_block_survives_context_reconstruction(self):
        self.execute(artifact_json="{}")
        context = x.SyntheticExecutionContext(self.path, self.oid, enrollment_provider=self.workspace,
            trust_provider=self.base.provider, checkpoint_path=self.checkpoint, control_path=self.control,
            execution_authorization=self.execution_permission["authorization"],
            writer_authorization=self.writer_permission["authorization"], authority=self.writer_permission["authority"])
        result = x.execute_operation(context, artifact_json=self.artifact, snapshot_json=self.snapshot, trusted_now_utc=NOW)
        self.assertEqual("BLOCKED", result.admission)

    def test_storage_binding_cannot_be_rewritten_even_with_new_disposable_approval(self):
        other = self.control.with_name("other-control.sqlite")
        shutil.copyfile(self.control, other)
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            subject = execution_schema.storage_subject(conn, other, self.checkpoint)
            with self.assertRaisesRegex(ValueError, "already_bound"):
                execution_schema.bind_stores(conn, other, self.checkpoint,
                    **approval(self.path, **execution_schema.storage_binding(subject)))

    def test_caught_installer_failure_cannot_commit_partial_execution_schema(self):
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            for table in reversed(list(execution_schema.TABLES)):
                conn.execute("DROP TABLE " + table)
            conn.execute("CREATE TABLE recognition_execution_seals(bad TEXT)")
            conn.commit()
            conn.execute("BEGIN IMMEDIATE")
            with self.assertRaises(ValueError):
                execution_schema.install(conn, **approval(self.path, **migration_binding("recognition_execution", execution_schema.definitions())))
            conn.commit()
        self.assertFalse(self.sql("SELECT name FROM sqlite_master WHERE name='recognition_execution_claims'"))

    def test_stop_is_durable_auditable_and_requires_explicit_clear(self):
        reason = "synthetic stop"
        permission = approval(self.control, **x.stop_binding(True, reason, 0))["authorization"]
        stopped = x.set_emergency_stop(self.context, reason=reason, expected_sequence=0, authorization=permission, trusted_now_utc=NOW)
        self.assertEqual("BLOCKED", self.execute().admission)
        self.assertEqual(0, self.sql("SELECT COUNT(*) FROM recognition_execution_claims")[0][0])
        with self.assertRaises(AuthorizationError):
            x.clear_emergency_stop(self.context, reason=reason, activation_sequence=1, authorization=permission, trusted_now_utc=NOW)
        clear = approval(self.control, **x.stop_binding(False, "reviewed restart", stopped["sequence"]))["authorization"]
        x.clear_emergency_stop(self.context, reason="reviewed restart", activation_sequence=1, authorization=clear, trusted_now_utc=NOW)
        self.assertEqual("COMPLETED", self.execute().state)
        with closing(sqlite3.connect(self.control)) as conn:
            self.assertEqual(2, conn.execute("SELECT COUNT(*) FROM recognition_execution_stops").fetchone()[0])

    def test_stop_after_entry_does_not_interrupt_commit_protocol(self):
        original = x._interrupt
        def stop(point, fault):
            if point == "AFTER_CLAIM":
                permission = approval(self.control, **x.stop_binding(True, "stop after entry", 0))["authorization"]
                x.set_emergency_stop(self.context, reason="stop after entry", expected_sequence=0,
                    authorization=permission, trusted_now_utc=NOW)
            return original(point, fault)
        with patch.object(x, "_interrupt", side_effect=stop):
            self.assertEqual("COMPLETED", self.execute().state)

    def test_direct_production_writer_and_fake_context_bypasses_fail(self):
        prod = replace(self.writer_permission["authorization"], environment="production")
        with patch.object(permanent, "verify", return_value=None):
            with self.assertRaisesRegex(AuthorizationError, "production_execution_context_unavailable"):
                permanent.finalize(self.path, self.manifest, manifest_sha256=self.e["writer_manifest_sha256"],
                    authorization_reference=self.manifest["authorization_reference"], gate=RecognitionGate(issuance=True),
                    authorization=prod, authority=self.writer_permission["authority"])
        with self.assertRaisesRegex(AuthorizationError, "coordinator_execution_capability_required"):
            permanent.finalize(self.path, self.manifest, manifest_sha256=self.e["writer_manifest_sha256"],
                authorization_reference=self.manifest["authorization_reference"], gate=RecognitionGate(issuance=True),
                execution_context=object(), **self.writer_permission)
        with self.assertRaises(TypeError):
            writer_boundary.ExecutionCapability()
        with self.assertRaisesRegex(AuthorizationError, "production_execution_context_unavailable"):
            live_first_looks.seal_pending(None, 1, gate=RecognitionGate(issuance=True), authorization=prod)

    def test_no_generic_callback_or_production_context(self):
        with self.assertRaises(trust.TrustError):
            self.execute(fault_point=lambda: True)
        self.assertEqual("BLOCKED", x.execute_operation({"role": "owner"}, artifact_json=self.artifact,
            snapshot_json=self.snapshot, trusted_now_utc=NOW).admission)

    def test_unapproved_quarantine_policy_is_not_used_to_skip_claims(self):
        self.prepare(policy={"reference": "invented", "quarantine_categories": ["authorization_failure"], "other_categories": []})
        self.assertEqual("BLOCKED", self.execute().admission)
        self.assertEqual(0, self.sql("SELECT COUNT(*) FROM recognition_first_look_claims")[0][0])

    def test_incomplete_accounting_prevents_completion_and_rolls_back_writer(self):
        original = x._receipt
        calls = 0
        def incomplete(*args):
            nonlocal calls
            calls += 1
            receipt = original(*args)
            if calls > 1:
                receipt["successful"] = []
                operations.validate_receipt(args[0], receipt)
            return receipt
        with patch.object(x, "_receipt", side_effect=incomplete):
            result = self.execute()
        self.assertEqual("FAILED_BEFORE_COMMIT", result.state)
        self.assertEqual(0, self.sql("SELECT COUNT(*) FROM recognition_first_look_claims")[0][0])

    def test_journal_and_seal_immutable_even_with_recursive_triggers_off(self):
        self.execute()
        for table in execution_schema.TABLES:
            with connection(self.path, write=True) as conn:
                conn.execute("PRAGMA recursive_triggers=OFF")
                for sql in (f"UPDATE {table} SET body_json='{{}}'", f"DELETE FROM {table}",
                            f"INSERT OR REPLACE INTO {table} SELECT * FROM {table}"):
                    with self.subTest(table=table, sql=sql), self.assertRaises(sqlite3.IntegrityError):
                        conn.execute(sql)

    def test_installer_idempotent_explicit_and_rollback_safe(self):
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            execution_schema.install(conn, **approval(self.path, **migration_binding("recognition_execution", execution_schema.definitions())))
            conn.rollback()
            conn.execute("BEGIN IMMEDIATE")
            for table in reversed(list(execution_schema.TABLES)):
                conn.execute("DROP TABLE " + table)
            conn.commit()
            conn.execute("BEGIN IMMEDIATE")
            execution_schema.install(conn, **approval(self.path, **migration_binding("recognition_execution", execution_schema.definitions())))
            conn.rollback()
        self.assertFalse(self.sql("SELECT name FROM sqlite_master WHERE name='recognition_execution_claims'"))


if __name__ == "__main__":
    unittest.main()
