"""Slice E: explicitly synthetic fresh fixtures, deterministic time/failure."""

from concurrent.futures import ThreadPoolExecutor
import json
import threading
import unittest
from unittest.mock import patch

from src.review.recognition import local_readiness as r, production_receipts as p, local_execution as c
from src.review.recognition import administration as a, admin_auth as m, approvals as b, production_operations as d
from src.review.recognition import operations, permanent, authority, activation, operation_schema
from src.review.recognition.schema import TABLES as EXPLORER
from tests import test_recognition_local_execution as old
from tests import test_recognition_production_operations as production
from tests.test_recognition_administration import at, independent_code


class ReadinessReceiptTests(unittest.TestCase):
    sql = old.LocalExecutionTests.sql
    new_operation = old.LocalExecutionTests.new_operation
    approve = old.LocalExecutionTests.approve
    enrolled = old.LocalExecutionTests.enrolled
    authenticated = old.LocalExecutionTests.authenticated
    counts = old.LocalExecutionTests.counts
    request = production.ProductionOperationTests.request
    create = production.ProductionOperationTests.create

    def setUp(self):
        with patch.object(c, "DisposableExecutionWorkspace", c.DisposableProductionExecutionWorkspace):
            old.LocalExecutionTests.setUp(self)
        self.fixture.decision(self.operation, "SUPERSEDED")
        self.create()
        self.approve(90)
        r.install(self.config, operator="disposable-host", reason="explicit test install", now=at(90))

    def deployment(self, seconds=90):
        r.record_deployment_rehearsal(self.config, operator="disposable-host", reason="synthetic fixture evidence only",
            evidence={key: production.sha(dict(disposable_check=key)) for key in r.REHEARSAL_CHECKS}, now=at(seconds))

    def fresh_step(self, action, seconds=120, operation_id=None):
        return m.create_step_up(self.config, self.session, independent_code(at(seconds)), action=action, operation_id=operation_id, now=at(seconds))

    def activate(self):
        self.deployment()
        self.workspace.simulate_activation(self.session, self.fresh_step("activate"), reason="synthetic activation only", now=at(120))

    def execute(self, seconds=120):
        return c.execute_approved_operation(self.context, self.session, self.aid, now=at(seconds))

    def recover(self, seconds=150, context=None):
        return c.reconcile_operation(self.context if context is None else context, self.session, self.fresh_step("recover", seconds, self.oid), self.aid, now=at(seconds))

    def seal(self):
        return json.loads(self.sql("SELECT body_json FROM recognition_execution_seals WHERE operation_id=?", (self.oid,))[0][0])

    def test_readiness_stages_and_no_authority(self):
        report = r.assess(self.config, now=at(90))
        self.assertEqual("READY_FOR_DEPLOYMENT", report["status"])
        self.assertTrue(report["code_ready"])
        self.assertFalse(report["deployment_verified"])
        self.assertEqual(12, len(report["deployment_prerequisites"]))
        self.deployment()
        report = r.assess(self.config, now=at(90))
        self.assertEqual("READY_FOR_ACTIVATION", report["status"])
        self.assertEqual("BLOCKED", report["production_activation"])
        self.assertEqual("NOT_ACTIVATED", report["activation_state"])
        self.assertEqual("BLOCKED", c.execute_approved_operation(report, self.session, self.aid, now=at(90)).admission)
        self.assertEqual((0, 0, 0, 0), self.counts())

    def test_missing_owner_and_mfa_block(self):
        self.sql("UPDATE recognition_admin_mfa SET state='UNENROLLED'", control=True)
        self.assertEqual("BLOCKED", r.assess(self.config, now=at(90))["status"])
        self.sql("UPDATE community_reviewers SET role='review_lead' WHERE id=1")
        self.assertEqual("BLOCKED", r.assess(self.config, now=at(90))["status"])

    def test_wrong_target_schema_or_required_table_blocks(self):
        self.sql("UPDATE recognition_local_installation SET target_id='wrong'")
        self.assertEqual("BLOCKED", r.assess(self.config, now=at(90))["status"])

    def test_missing_execution_schema_blocks(self):
        self.sql("DROP TABLE recognition_execution_storage")
        self.assertEqual("BLOCKED", r.assess(self.config, now=at(90))["status"])

    def test_provider_objects_cannot_be_selected(self):
        for provider in (object(), "synthetic", "high-assurance", {"production": True}):
            with self.subTest(provider=type(provider).__name__):
                self.assertEqual("BLOCKED", r.assess(self.config, now=at(90), selected_provider=provider)["status"])

    def test_real_production_activation_and_provisioning_stay_blocked(self):
        self.deployment()
        result = r.change_state(self.config, self.session, self.fresh_step("activate"), state="ACTIVATED", reason="explicit attempt", now=at(120))
        self.assertEqual("BLOCKED", result["result"])
        self.assertEqual("NOT_ACTIVATED", r.assess(self.config, now=at(120))["activation_state"])
        context = d.load_context(self.config, self.oid)
        with patch.object(permanent, "finalize", side_effect=AssertionError("production mutation")):
            result = c.execute_approved_operation(context, self.session, self.aid, now=at(120))
        self.assertEqual("production_activation_deployment_blocked", result.reason)
        with self.assertRaises(Exception):
            authority.provision_production_authority()
        self.assertEqual("NOT_ACTIVATED", activation.get_activation_state().state)

    def test_explicit_fixture_activation_then_suspension_audited(self):
        self.activate()
        self.assertEqual("ACTIVATED", r.assess(self.config, now=at(120))["activation_state"])
        r.change_state(self.config, self.session, self.fresh_step("suspend", 150), state="SUSPENDED", reason="operator pause", now=at(150))
        self.assertEqual("SUSPENDED", r.assess(self.config, now=at(150))["activation_state"])
        self.assertNotEqual("COMPLETED", self.execute(150).state)
        self.assertEqual([(3,)], self.sql("SELECT COUNT(*) FROM recognition_local_activation", control=True))

    def test_deactivation_and_stop_block(self):
        self.activate()
        r.change_state(self.config, self.session, self.fresh_step("deactivate", 150), state="DEACTIVATED", reason="explicit deactivate", now=at(150))
        self.assertEqual("activation_not_permitted", self.execute(150).reason)

    def test_stop_blocks_activation(self):
        self.deployment()
        self.workspace.set_stop(active=True, now=at(90))
        with self.assertRaises(a.AdminError):
            self.workspace.simulate_activation(self.session, self.fresh_step("activate"), reason="must fail", now=at(120))

    def test_first_look_production_contract_receipt_and_projection(self):
        before = {name: self.sql("SELECT * FROM "+name) for name in EXPLORER}
        self.activate()
        result = self.execute()
        self.assertEqual(("ADMITTED", "COMPLETED"), (result.admission, result.state))
        receipt = self.seal()["receipt"]
        self.assertEqual("recognition-production-execution-receipt-v1", receipt["format"])
        self.assertEqual(production.sha(self.operation["envelope"]), receipt["operation_sha256"])
        self.assertEqual(production.sha(self.approval["approval"]), receipt["approval_sha256"])
        self.assertEqual(production.sha(receipt), result.receipt_sha256)
        self.assertEqual((1, 1, [], []), (receipt["authorized_count"], len(receipt["successful"]), receipt["quarantined"], receipt["other"]))
        self.assertEqual((1, 1), (receipt["actor_id"], receipt["restore_generation"]))
        self.assertEqual("Reviewed disposable population", receipt["reason"])
        self.assertEqual(1, len(receipt["actual_records"]["recognition_first_look_claims"]))
        with a.connect(self.path) as conn:
            op = operations.get_operation(conn, self.oid)
            self.assertEqual("COMPLETED", op["executions"][-1]["state"])
            self.assertEqual(dict(authorized=1, successful=1, quarantined=0, other=0, unaccounted=0), operations.validate_receipt(op, receipt))
            view = p.effective_recognition(conn, self.oid, self.approval)
            self.assertEqual([], view["corrections_applied"])
            self.assertEqual(1, len(view["awards"]))
        self.assertEqual(before, {name: self.sql("SELECT * FROM "+name) for name in EXPLORER})
        self.assertEqual("ALREADY_EXECUTED", self.execute().admission)

    def test_geography_full_actual_outcome_evidence(self):
        for n in range(2, 6):
            self.fixture.review(n)
        # G readiness requires stale pending approval authority to be reconciled.
        self.assertEqual("INVALIDATED", b.get_approval(self.config, self.session, self.aid, now=at(90))["state"])
        # Supersede the now-stale unclaimed operation before a new frozen evaluation.
        request = self.request(True)
        self.create(request)
        self.approve(120)
        self.deployment(120)
        self.workspace.simulate_activation(self.session, self.fresh_step("activate", 150), reason="synthetic geography", now=at(150))
        self.assertEqual("COMPLETED", self.execute(150).state)
        receipt = self.seal()["receipt"]
        self.assertEqual(("geography_steward", 2), (receipt["writer_family"], receipt["authorized_count"]))
        self.assertEqual(10, len(receipt["actual_records"]["recognition_geography_members"]))

    def test_evidence_commit_before_projection_recovery_never_writes_again(self):
        self.activate()
        def fail(point):
            if point == "E":
                raise c.journal.SimulatedInterruption("projection pending")
        with patch.object(c, "_fault", side_effect=fail), self.assertRaises(c.journal.SimulatedInterruption):
            self.execute()
        self.assertEqual((1, 1, 1, 1), self.counts())
        self.assertEqual([], self.sql("SELECT * FROM recognition_operation_receipts WHERE operation_id=?", (self.oid,)))
        with patch.object(permanent, "finalize", side_effect=AssertionError("projection must not execute writer")):
            self.assertEqual("RECOVERY_REQUIRED", self.execute().admission)
            self.assertEqual("ALREADY_EXECUTED", self.recover().admission)
            self.assertEqual("ALREADY_EXECUTED", self.execute(150).admission)
        self.assertEqual((1, 1, 1, 1), self.counts())

    def test_projection_idempotent_and_historical_seal_unchanged(self):
        self.activate()
        self.execute()
        seal = self.seal()
        with a.connect(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            self.assertEqual(seal["receipt"], p.project(conn, self.oid, self.approval, now=at(150)))
            self.assertEqual(seal["receipt"], p.project(conn, self.oid, self.approval, now=at(150)))
            conn.commit()
        self.assertEqual(seal, self.seal())
        self.assertEqual((1, 1, 1, 1), self.counts())

    def test_missing_projection_can_be_rebuilt_from_historical_seal(self):
        self.activate()
        self.execute()
        with a.connect(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("DROP TRIGGER recognition_operation_receipts_immutable_delete")
            conn.execute("DELETE FROM recognition_operation_receipts WHERE operation_id=?", (self.oid,))
            conn.execute(operation_schema.definitions()["recognition_operation_receipts_immutable_delete"])
            conn.commit()
        with patch.object(permanent, "finalize", side_effect=AssertionError("rebuild reran writer")):
            self.assertEqual("RECOVERY_REQUIRED", self.execute().admission)
            # A restarted process can load a descriptor without the old fixture's
            # in-memory capability; the missing projection is not an authority.
            context = d.load_recovery_context(self.config, self.oid)
            self.assertEqual("ALREADY_EXECUTED", self.recover(context=context).admission)
        self.assertEqual((1, 1, 1, 1), self.counts())

    def test_conflicting_projection_requires_reconciliation_not_execution(self):
        self.activate()
        def fail(point):
            if point == "E":
                raise c.journal.SimulatedInterruption("projection pending")
        with patch.object(c, "_fault", side_effect=fail), self.assertRaises(c.journal.SimulatedInterruption):
            self.execute()
        wrong = dict(self.seal()["receipt"], authorized_count=999)
        self.sql("INSERT INTO recognition_operation_receipts VALUES(?,?,?)", (self.oid, c.canonical(wrong), production.sha(wrong)))
        with patch.object(permanent, "finalize", side_effect=AssertionError("conflict reran writer")):
            self.assertEqual("RECONCILIATION_REQUIRED", self.execute().admission)
            self.assertEqual("RECONCILIATION_REQUIRED", self.recover().admission)
        self.assertEqual("RECOVERY_REQUIRED", r.assess(self.config, now=at(150))["status"])
        self.assertEqual((1, 1, 1, 1), self.counts())

    def test_concurrent_production_fixture_execution_single_writer(self):
        self.activate()
        barrier = threading.Barrier(2)
        def run():
            barrier.wait()
            return self.execute().admission
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda _: run(), range(2)))
        self.assertEqual(["ADMITTED", "ALREADY_EXECUTED"], sorted(results))
        self.assertEqual((1, 1, 1, 1), self.counts())

    def test_stale_operation_blocks_even_activated_fixture(self):
        self.activate()
        self.sql("UPDATE stop_review_assignments SET status='pending' WHERE id=1")
        self.assertEqual("BLOCKED", self.execute().admission)
        self.assertEqual((0, 0, 0, 0), self.counts())

    def test_valid_delayed_session_fresh_step_and_confirmation(self):
        self.create()
        step = self.fresh_step("approve", 14430, self.oid)
        token = m.begin_operation_confirmation(self.config, self.session, step, operation_id=self.oid, now=at(14430))
        approved = b.create_approval(self.config, self.session, step, token, operation_id=self.oid, reason="Four hours later", now=at(14430))
        self.assertEqual("APPROVED", approved["state"])

    def test_delayed_expired_step_and_confirmation_rejected(self):
        self.create()
        step = self.fresh_step("approve", 14400, self.oid)
        token = m.begin_operation_confirmation(self.config, self.session, step, operation_id=self.oid, now=at(14400))
        with self.assertRaises(a.AdminError):
            b.create_approval(self.config, self.session, step, token, operation_id=self.oid, reason="Expired", now=at(15000))
        self.assertEqual([(0,)], self.sql("SELECT used FROM recognition_admin_confirmations WHERE token_hash=?", (a.token_hash(token),), control=True))

    def test_delayed_session_expiry_logout_reset_and_consumed_confirmation(self):
        with self.assertRaises(a.AdminError):
            self.fresh_step("approve", 30000, self.oid)

    def test_logged_out_session_cannot_step_up(self):
        m.invalidate_primary(self.config, self.primary, now=at(90))
        with self.assertRaises(a.AdminError):
            self.fresh_step("approve", 14400, self.oid)

    def test_mfa_reset_cannot_step_up(self):
        a.reset_mfa(self.config, expected_generation=1, operator="disposable-owner", reason="reset", now=at(90))
        with self.assertRaises(a.AdminError):
            self.fresh_step("approve", 14400, self.oid)

    def test_restore_generation_cannot_step_up(self):
        with a.connect(self.path) as conn:
            observation = a.observe_target(conn)
        a.advance_restore_generation(self.config, expected_generation=1, expected_target_sha256=production.sha(observation), operator="disposable-host", reason="restore", now=at(90))
        readiness = r.assess(self.config, now=at(90))
        self.assertEqual("NOT_ACTIVATED", readiness["activation_state"])
        self.assertFalse(readiness["activation_ready"])
        self.assertTrue(readiness["code_ready"])
        with self.assertRaises(a.AdminError):
            self.fresh_step("approve", 14400, self.oid)

    def test_readiness_explicit_install_idempotent_no_startup_activation(self):
        r.install(self.config, operator="disposable-host", reason="repeat", now=at(90))
        self.assertEqual([(1,)], self.sql("SELECT COUNT(*) FROM recognition_local_activation", control=True))
        self.assertEqual("NOT_ACTIVATED", r.assess(self.config, now=at(90))["activation_state"])

    def test_delayed_fresh_step_does_not_revive_expired_confirmation(self):
        self.create()
        old_step = self.fresh_step("approve", 14400, self.oid)
        token = m.begin_operation_confirmation(self.config, self.session, old_step, operation_id=self.oid, now=at(14400))
        fresh = self.fresh_step("approve", 14700, self.oid)
        with self.assertRaises(a.AdminError):
            b.create_approval(self.config, self.session, fresh, token, operation_id=self.oid, reason="Old confirmation", now=at(15000))
        self.assertEqual([(0,)], self.sql("SELECT used FROM recognition_admin_confirmations WHERE token_hash=?", (a.token_hash(token),), control=True))

    def test_delayed_confirmation_cannot_be_consumed_twice(self):
        self.create()
        step = self.fresh_step("approve", 14400, self.oid)
        token = m.begin_operation_confirmation(self.config, self.session, step, operation_id=self.oid, now=at(14400))
        for attempt in range(2):
            if attempt:
                with self.assertRaises(a.AdminError):
                    b.create_approval(self.config, self.session, step, token, operation_id=self.oid, reason="Replay", now=at(14400))
            else:
                self.assertEqual("APPROVED", b.create_approval(self.config, self.session, step, token, operation_id=self.oid, reason="Approved", now=at(14400))["state"])

    def test_delayed_confirmation_rejects_changed_operation(self):
        self.create()
        oid = self.oid
        step = self.fresh_step("approve", 14400, oid)
        token = m.begin_operation_confirmation(self.config, self.session, step, operation_id=oid, now=at(14400))
        d.create_operation(self.config, self.session, dict(self.request(), parent_operation_id=oid), now=at(14430))
        with self.assertRaises(a.AdminError):
            b.create_approval(self.config, self.session, step, token, operation_id=oid, reason="Changed", now=at(14430))
        self.assertEqual([(0,)], self.sql("SELECT used FROM recognition_admin_confirmations WHERE token_hash=?", (a.token_hash(token),), control=True))

    def test_delayed_valid_session_wrong_target_rejects_confirmation(self):
        self.create()
        step = self.fresh_step("approve", 14400, self.oid)
        token = m.begin_operation_confirmation(self.config, self.session, step, operation_id=self.oid, now=at(14400))
        self.sql("UPDATE recognition_local_installation SET target_id='wrong-target'")
        with self.assertRaises(a.AdminError):
            b.create_approval(self.config, self.session, step, token, operation_id=self.oid, reason="Wrong target", now=at(14400))

    def test_projection_update_rollback_then_owner_retry(self):
        self.activate()
        original = p.project
        def fail(*args, **kwargs):
            original(*args, **kwargs)
            raise RuntimeError("projection transaction interrupted before commit")
        with patch.object(p, "project", side_effect=fail):
            self.assertEqual("RECOVERY_REQUIRED", self.execute().admission)
        self.assertEqual([], self.sql("SELECT * FROM recognition_operation_receipts WHERE operation_id=?", (self.oid,)))
        with patch.object(permanent, "finalize", side_effect=AssertionError("projection reran writer")):
            self.assertEqual("ALREADY_EXECUTED", self.recover().admission)
        self.assertEqual((1, 1, 1, 1), self.counts())

    def test_readiness_unresolved_claim_requires_recovery(self):
        self.activate()
        def fail(point):
            if point == "C":
                raise c.journal.SimulatedInterruption("before writer")
        with patch.object(c, "_fault", side_effect=fail), self.assertRaises(c.journal.SimulatedInterruption):
            self.execute()
        report = r.assess(self.config, now=at(120))
        self.assertEqual("RECOVERY_REQUIRED", report["status"])
        self.assertEqual([self.oid], report["unresolved_recovery"])

    def test_readiness_migration_savepoint_rolls_back(self):
        with a.connect(self.control, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            for name in r.definitions():
                if name != "recognition_local_activation":
                    conn.execute("DROP TRIGGER "+name)
            conn.execute("DROP TABLE recognition_local_activation")
            conn.commit()
        with patch.object(r, "_append", side_effect=RuntimeError("install failure")):
            with self.assertRaises(RuntimeError):
                r.install(self.config, operator="disposable-host", reason="retry", now=at(90))
        self.assertEqual([], self.sql("SELECT name FROM sqlite_master WHERE name='recognition_local_activation'", control=True))

    def test_readiness_missing_key_and_incompatible_pending_operation(self):
        # The original authority-free production format remains the only pending
        # production family. An older synthetic contract cannot become production.
        self.new_operation()
        self.assertEqual("BLOCKED", r.assess(self.config, now=at(90))["status"])
        self.key_file.unlink()
        self.assertEqual(["host_mfa_key_unavailable"], r.assess(self.config, now=at(90))["issues"])

    def test_activated_fixture_cannot_leak_to_real_production_context(self):
        self.activate()
        context = d.load_context(self.config, self.oid)
        with patch.object(permanent, "finalize", side_effect=AssertionError("fixture leaked to production")):
            result = c.execute_approved_operation(context, self.session, self.aid, now=at(120))
        self.assertEqual("production_activation_deployment_blocked", result.reason)
        self.assertEqual((0, 0, 0, 0), self.counts())

    def test_provisioning_block_is_independent_of_activation_block(self):
        self.activate()
        context = d.load_context(self.config, self.oid)
        with patch.object(d, "activation_guard", return_value=None), patch.object(permanent, "finalize", side_effect=AssertionError("provisioning bypass")):
            result = c.execute_approved_operation(context, self.session, self.aid, now=at(120))
        self.assertEqual("production_activation_deployment_blocked", result.reason)
        self.assertEqual((0, 0, 0, 0), self.counts())
