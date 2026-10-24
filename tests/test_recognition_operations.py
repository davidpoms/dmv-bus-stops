"""Operation contract tests: fresh disposable targets, no real approval/execution."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib
import json
import sqlite3
import unittest
from unittest.mock import patch
from uuid import UUID

from src.review.recognition import events, operations as op, operation_schema as schema
from src.review.recognition import authority, permanent
from src.review.recognition.authorization import migration_binding, AuthorizationError
from src.review.recognition.qualification import Quarantined
from src.review.recognition.rules import canonical
from src.review.recognition.schema import connection, TABLES as EXPLORER_TABLES
from tests import test_recognition_events as event_fixture
from tests.recognition_authorization_fixture import approval


POLICY = {"reference": "synthetic-accounting-v1", "quarantine_categories": ["bad_evidence"],
          "other_categories": ["already_present"]}
AUTH = {"authorization_id": "synthetic-approval-1", "artifact_sha256": "a" * 64}


class OperationTests(unittest.TestCase):
    sql = event_fixture.EventTests.sql
    review = event_fixture.EventTests.review
    first = event_fixture.EventTests.first
    geo = event_fixture.EventTests.geo
    scope = event_fixture.EventTests.scope
    envelope = event_fixture.EventTests.envelope
    request = event_fixture.EventTests.request
    create = event_fixture.EventTests.create
    freeze = event_fixture.EventTests.freeze
    state = event_fixture.EventTests.state
    install = event_fixture.EventTests.install

    def setUp(self):
        event_fixture.EventTests.setUp(self)
        self.install_operations()
        self.event = self.freeze(self.create()["preparation_id"])["event"]["event_id"]

    def install_operations(self):
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            schema.install(conn, **approval(self.path, **migration_binding(
                "recognition_operations", schema.definitions())))
            conn.commit()

    def make(self, event=None, policy=None):
        event = event or self.event
        policy = POLICY if policy is None else policy
        subject = dict(event_id=event, accounting_policy=policy)
        return self.write("create", subject, lambda c, kw: op.create_operation(c, event, policy, **kw))

    def write(self, action, subject, call):
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            result = call(conn, approval(self.path, **op.binding(action, subject)))
            conn.commit()
            return result

    def decision(self, operation, state, reason="synthetic-decision", evidence=None):
        oid = operation["envelope"]["operation_id"]
        subject = dict(operation_id=oid, state=state, reason=reason, evidence=evidence)
        extra = {}
        if state == "SENT_BACK":
            subject_event = dict(event_id=operation["envelope"]["event_id"], state="INVALID", reason=reason)
            permission = approval(self.path, **events.binding("record_event_state", subject_event))
            extra = dict(event_authorization=permission["authorization"], event_authority=permission["authority"])
        return self.write("decision", subject, lambda c, kw: op.record_decision(c, **subject, **extra, **kw))

    def execution(self, operation, state, receipt=None, reason="synthetic-execution"):
        subject = dict(operation_id=operation["envelope"]["operation_id"], state=state, reason=reason, receipt=receipt)
        return self.write("execution", subject, lambda c, kw: op.record_execution(c, **subject, **kw))

    def authorized(self):
        return self.decision(self.make(), "AUTHORIZED", evidence=AUTH)

    def receipt(self, operation, outcome="COMPLETED", group="successful"):
        e = operation["envelope"]
        item = {"member_id": e["member_ids"][0], "outcome_reference": "synthetic-result-1"}
        if group != "successful":
            item.update(category="bad_evidence" if group == "quarantined" else "already_present",
                        reason="synthetic explanation")
        return dict(format="recognition-operation-receipt-v1", synthetic_assertion_only=True,
                    operation_id=e["operation_id"], event_id=e["event_id"], authorization=AUTH,
                    enrollment={"enrollment_id": None, "generation": None},
                    target_identity=e["target_observation"], outcome=outcome, authorized_count=1,
                    successful=[item] if group == "successful" else [],
                    quarantined=[item] if group == "quarantined" else [],
                    other=[item] if group == "other" else [],
                    started_at_utc=e["created_at_utc"], finished_at_utc=e["created_at_utc"])

    def get(self, oid):
        with connection(self.path) as conn:
            return op.get_operation(conn, oid)

    def test_creation_bindings_and_independent_digest(self):
        result = self.make()
        e = result["envelope"]
        UUID(e["operation_id"])
        with connection(self.path) as conn:
            frozen = events.get_event(conn, self.event)
        p = frozen["preparation"]
        independent_hash = lambda x: hashlib.sha256(json.dumps(
            x, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
        self.assertEqual(self.event, e["event_id"])
        self.assertEqual(p["preparation_id"], e["preparation_id"])
        self.assertEqual(independent_hash(p), e["preparation_sha256"])
        self.assertEqual(independent_hash(p["dependencies"]), e["dependencies_sha256"])
        self.assertEqual(independent_hash(p["manifest"]), e["writer_manifest_sha256"])
        self.assertEqual(independent_hash(p["manifest"]["candidates"]), e["population_sha256"])
        self.assertEqual([independent_hash(p["manifest"]["candidates"][0])], e["member_ids"])
        self.assertEqual("first_look", e["family"])
        self.assertEqual("finalize", e["action"])
        self.assertEqual(p["manifest"]["rule"], e["rule"])
        self.assertEqual({"enrollment_id": None, "generation": None}, e["enrollment"])
        self.assertNotIn(e["operation_id"], (self.event, p["preparation_id"], p["manifest_sha256"]))
        self.assertEqual("PREPARED", result["decisions"][-1]["state"])
        self.assertEqual("NOT_STARTED", result["executions"][-1]["state"])
        self.assertIsNone(result["receipt"])

    def test_duplicate_create_and_freeze_deterministic(self):
        first = self.make()
        self.assertEqual(first, self.make())
        self.freeze(first["envelope"]["preparation_id"])
        self.assertEqual(first, self.make())
        altered = {**POLICY, "reference": "different-policy"}
        with self.assertRaisesRegex(Quarantined, "create_conflict"):
            self.make(policy=altered)
        self.assertEqual(1, self.sql("SELECT COUNT(*) FROM recognition_operation_contracts")[0][0])

    def test_concurrent_create_returns_one_identity(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.make()["envelope"]["operation_id"], range(2)))
        self.assertEqual(results[0], results[1])

    def test_revision_new_identity_no_inheritance_and_old_unchanged(self):
        old = self.authorized()
        self.decision(old, "SUPERSEDED")
        historical = self.get(old["envelope"]["operation_id"])
        preparation = self.create(self.request(parent=self.event))
        event = self.freeze(preparation["preparation_id"])["event"]["event_id"]
        revised = self.make(event)
        self.assertNotEqual(old["envelope"]["operation_id"], revised["envelope"]["operation_id"])
        self.assertEqual(old["envelope"]["writer_manifest_sha256"], revised["envelope"]["writer_manifest_sha256"])
        self.assertEqual("PREPARED", revised["decisions"][-1]["state"])
        self.assertIsNone(revised["decisions"][-1]["evidence"])
        self.assertEqual(historical, self.get(old["envelope"]["operation_id"]))

    def test_send_back_invalidates_event_and_requires_new_identity(self):
        old = self.make()
        self.decision(old, "SENT_BACK", reason="fix reconciliation")
        with connection(self.path) as conn:
            self.assertEqual("INVALID", events.get_event(conn, self.event)["state"])
        with self.assertRaises(Quarantined):
            self.decision(old, "AUTHORIZED", evidence=AUTH)
        revision = self.freeze(self.create(self.request(parent=self.event))["preparation_id"])
        self.assertNotEqual(old["envelope"]["operation_id"],
                            self.make(revision["event"]["event_id"])["envelope"]["operation_id"])

    def test_terminal_decisions_and_authorization_identity_cannot_change(self):
        for state in ("REJECTED", "SUPERSEDED", "INVALIDATED"):
            event = self.freeze(self.create()["preparation_id"])["event"]["event_id"]
            operation = self.make(event)
            terminal = self.decision(operation, state)
            with self.assertRaisesRegex(Quarantined, "invalid_decision_transition"):
                self.decision(terminal, "AUTHORIZED", evidence=AUTH)
            with self.assertRaisesRegex(Quarantined, "authorized_assertion_required"):
                self.execution(terminal, "EXECUTING")
        authorized = self.authorized()
        self.assertEqual(authorized, self.decision(authorized, "AUTHORIZED", evidence=AUTH))
        with self.assertRaises(Quarantined):
            self.decision(authorized, "AUTHORIZED", evidence={**AUTH, "authorization_id": "replacement"})

    def test_legal_execution_and_terminal_conflicts(self):
        authorized = self.authorized()
        waiting = self.execution(authorized, "WAITING")
        running = self.execution(waiting, "EXECUTING")
        receipt = self.receipt(running)
        done = self.execution(running, "COMPLETED", receipt)
        self.assertEqual(done, self.execution(done, "COMPLETED", receipt))
        for state in ("EXECUTING", "FAILED_BEFORE_COMMIT", "UNKNOWN_RECOVERY_REQUIRED"):
            with self.assertRaisesRegex(Quarantined, "invalid_execution_transition"):
                self.execution(done, state)
        superseded = self.decision(done, "SUPERSEDED")
        self.assertEqual("COMPLETED", superseded["executions"][-1]["state"])
        self.assertEqual(done["receipt"], superseded["receipt"])

    def test_failure_unknown_and_partial_are_distinct_terminal_histories(self):
        for state in ("FAILED_BEFORE_COMMIT", "UNKNOWN_RECOVERY_REQUIRED",
                      "PARTIALLY_EXECUTED_RECONCILIATION_REQUIRED"):
            event = self.freeze(self.create()["preparation_id"])["event"]["event_id"]
            operation = self.decision(self.make(event), "AUTHORIZED", evidence=AUTH)
            if state != "FAILED_BEFORE_COMMIT":
                operation = self.execution(operation, "EXECUTING")
            result = self.execution(operation, state)
            self.assertEqual(state, result["executions"][-1]["state"])
            with self.assertRaises(Quarantined):
                self.execution(result, "EXECUTING")

    def test_accounting_success_quarantine_and_other(self):
        operation = self.authorized()
        self.assertEqual(dict(authorized=1, successful=1, quarantined=0, other=0, unaccounted=0),
                         op.validate_receipt(operation, self.receipt(operation)))
        self.assertEqual(dict(authorized=1, successful=0, quarantined=1, other=0, unaccounted=0),
                         op.validate_receipt(operation, self.receipt(
                             operation, "COMPLETED_WITH_QUARANTINE", "quarantined")))
        self.assertEqual(1, op.validate_receipt(operation, self.receipt(operation, group="other"))["other"])
        running = self.execution(operation, "EXECUTING")
        done = self.execution(running, "COMPLETED_WITH_QUARANTINE",
                              self.receipt(running, "COMPLETED_WITH_QUARANTINE", "quarantined"))
        self.assertEqual(1, len(done["receipt"]["quarantined"]))

    def test_incomplete_unknown_and_duplicate_receipt_accounting(self):
        operation = self.authorized()
        receipt = self.receipt(operation)
        receipt["successful"] = []
        with self.assertRaisesRegex(Quarantined, "incomplete_receipt_accounting"):
            op.validate_receipt(operation, receipt)
        receipt["outcome"] = "UNKNOWN_RECOVERY_REQUIRED"
        self.assertEqual(1, op.validate_receipt(operation, receipt)["unaccounted"])
        receipt = self.receipt(operation)
        receipt["successful"] *= 2
        with self.assertRaisesRegex(Quarantined, "duplicate_receipt_member"):
            op.validate_receipt(operation, receipt)
        receipt["successful"] = [{"member_id": "b"*64, "outcome_reference": "unknown"}]
        with self.assertRaises(Quarantined):
            op.validate_receipt(operation, receipt)

    def test_receipt_all_bindings_categories_and_timestamps(self):
        operation = self.authorized()
        for field, value in (("operation_id", "other"), ("event_id", "other"),
                             ("authorization", {**AUTH, "artifact_sha256": "b"*64}),
                             ("enrollment", {"enrollment_id": "invented", "generation": 1}),
                             ("target_identity", {}), ("authorized_count", True),
                             ("started_at_utc", "2000-01-01T00:00:00Z")):
            receipt = self.receipt(operation)
            receipt[field] = value
            with self.subTest(field=field), self.assertRaises(Quarantined):
                op.validate_receipt(operation, receipt)
        receipt = self.receipt(operation, "COMPLETED_WITH_QUARANTINE", "quarantined")
        receipt["quarantined"][0]["category"] = "authorization_failure"
        with self.assertRaisesRegex(Quarantined, "unapproved_accounting_category"):
            op.validate_receipt(operation, receipt)
        receipt = self.receipt(operation, group="quarantined")
        with self.assertRaisesRegex(Quarantined, "quarantine_outcome_mismatch"):
            op.validate_receipt(operation, receipt)

    def test_completion_requires_receipt_and_rolls_back_if_accounting_fails(self):
        operation = self.execution(self.authorized(), "EXECUTING")
        for receipt in (None, {**self.receipt(operation), "successful": []}):
            with self.assertRaises(Quarantined):
                self.execution(operation, "COMPLETED", receipt)
        self.assertEqual("EXECUTING", self.get(operation["envelope"]["operation_id"])["executions"][-1]["state"])
        self.assertEqual(0, self.sql("SELECT COUNT(*) FROM recognition_operation_receipts")[0][0])

    def test_immutable_envelope_histories_receipts_with_recursive_triggers_off(self):
        running = self.execution(self.authorized(), "EXECUTING")
        self.execution(running, "COMPLETED", self.receipt(running))
        for table in schema.TABLES:
            for statement in (f"UPDATE {table} SET body_json='{{}}'", f"DELETE FROM {table}",
                              f"INSERT OR REPLACE INTO {table} SELECT * FROM {table}"):
                with connection(self.path, write=True) as conn:
                    conn.execute("PRAGMA recursive_triggers=OFF")
                    with self.subTest(statement=statement), self.assertRaises(sqlite3.IntegrityError):
                        conn.execute(statement)

    def test_database_transition_trigger_rejects_invalid_insert(self):
        operation = self.make()
        oid = operation["envelope"]["operation_id"]
        self.decision(operation, "REJECTED")
        with connection(self.path, write=True) as conn:
            with self.assertRaisesRegex(sqlite3.IntegrityError, "invalid_operation_transition"):
                conn.execute("INSERT INTO recognition_operation_decisions VALUES(?,3,'AUTHORIZED','{}',?)", (oid, "c"*64))
            with self.assertRaisesRegex(sqlite3.IntegrityError, "authorized_assertion_required"):
                conn.execute("INSERT INTO recognition_operation_executions VALUES(?,2,'EXECUTING','{}',?)", (oid, "c"*64))

    def test_invalid_event_blocks_authorized_execution_assertion(self):
        operation = self.authorized()
        self.state(self.event, "STALE")
        with self.assertRaisesRegex(Quarantined, "event_not_ready"):
            self.execution(operation, "EXECUTING")
        self.assertEqual("NOT_STARTED", self.get(operation["envelope"]["operation_id"])["executions"][-1]["state"])

    def test_waiting_operation_can_be_invalidated_without_rewriting_execution(self):
        waiting = self.execution(self.authorized(), "WAITING")
        invalidated = self.decision(waiting, "INVALIDATED")
        self.assertEqual(waiting["executions"], invalidated["executions"])
        with self.assertRaisesRegex(Quarantined, "authorized_assertion_required"):
            self.execution(invalidated, "EXECUTING")

    def test_forged_envelope_bindings_fail_even_with_recomputed_hash(self):
        operation = self.make()
        for field, value in (("event_id", "different-event"), ("dependencies_sha256", "f"*64),
                             ("population_sha256", "f"*64), ("member_ids", []),
                             ("target_observation", {}), ("rule_sha256", "f"*64),
                             ("enrollment", {"enrollment_id": "fake", "generation": 1})):
            e = {**operation["envelope"], field: value}
            with connection(self.path, write=True) as conn:
                conn.execute("BEGIN IMMEDIATE")
                conn.execute("DROP TRIGGER recognition_operation_contracts_immutable_update")
                conn.execute("UPDATE recognition_operation_contracts SET body_json=?,body_sha256=?",
                             (canonical(e), hashlib.sha256(canonical(e).encode()).hexdigest()))
                trigger = schema.definitions()["recognition_operation_contracts_immutable_update"]
                conn.execute(trigger)
                with self.subTest(field=field), self.assertRaisesRegex(Quarantined, "operation_binding_mismatch"):
                    op.get_operation(conn, operation["envelope"]["operation_id"])

    def test_send_back_failure_rolls_back_decision_and_event(self):
        operation = self.make()
        subject = dict(operation_id=operation["envelope"]["operation_id"], state="SENT_BACK",
                       reason="revise", evidence=None)
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            with self.assertRaises(AuthorizationError):
                op.record_decision(conn, **subject, **approval(self.path, **op.binding("decision", subject)))
            conn.commit()
        self.assertEqual(operation, self.get(operation["envelope"]["operation_id"]))
        with connection(self.path) as conn:
            self.assertEqual("READY", events.get_event(conn, self.event)["state"])

    def test_authority_recheck_failure_rolls_back_create_even_if_caller_commits(self):
        real_verify = op.verify
        calls = 0

        def fail_after_write(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise AuthorizationError("synthetic_revocation")
            return real_verify(*args, **kwargs)

        subject = dict(event_id=self.event, accounting_policy=POLICY)
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            with patch.object(op, "verify", side_effect=fail_after_write):
                with self.assertRaisesRegex(AuthorizationError, "synthetic_revocation"):
                    op.create_operation(conn, self.event, POLICY,
                                        **approval(self.path, **op.binding("create", subject)))
            conn.commit()
        self.assertEqual(0, self.sql("SELECT COUNT(*) FROM recognition_operation_contracts")[0][0])
        self.assertEqual(0, self.sql("SELECT COUNT(*) FROM recognition_operation_decisions")[0][0])

    def test_second_disposable_target_cannot_reuse_observed_event_or_approval(self):
        other = self.path.with_name("second-disposable.sqlite")
        with connection(self.path) as source:
            target = sqlite3.connect(other)
            try:
                source.backup(target)
            finally:
                target.close()
        subject = dict(event_id=self.event, accounting_policy=POLICY)
        with connection(other, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            with self.assertRaisesRegex(AuthorizationError, "authorization_target_mismatch"):
                op.create_operation(conn, self.event, POLICY,
                                    **approval(self.path, **op.binding("create", subject)))
            with self.assertRaisesRegex(Quarantined, "operation_target_changed"):
                op.create_operation(conn, self.event, POLICY,
                                    **approval(other, **op.binding("create", subject)))

    def test_geography_contract_uses_exact_candidate_population(self):
        for n in range(2, 6):
            self.review(n)
        prepared = self.create(self.request(geography=True))
        event = self.freeze(prepared["preparation_id"])["event"]["event_id"]
        operation = self.make(event)
        self.assertEqual("geography_steward", operation["envelope"]["family"])
        self.assertEqual(len(prepared["manifest"]["candidates"]), len(operation["envelope"]["member_ids"]))
        self.assertTrue(operation["envelope"]["member_ids"])

    def test_tamper_detection_even_when_envelope_hash_recomputed(self):
        operation = self.make()
        e = deepcopy(operation["envelope"])
        e["action"] = "seal_pending"
        with connection(self.path, write=True) as conn:
            conn.execute("DROP TRIGGER recognition_operation_contracts_immutable_update")
            conn.execute("UPDATE recognition_operation_contracts SET body_json=?,body_sha256=?",
                         (canonical(e), hashlib.sha256(canonical(e).encode()).hexdigest()))
            conn.commit()
        # First fail closed on schema replacement, then verify independent binding comparison.
        with self.assertRaisesRegex(Quarantined, "schema_mismatch"):
            self.get(e["operation_id"])
        self.install_operations()
        with self.assertRaisesRegex(Quarantined, "operation_binding_mismatch"):
            self.get(e["operation_id"])

    def test_install_repeat_and_transaction_rollback(self):
        self.install_operations()
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            for table in reversed(list(schema.TABLES)):
                conn.execute(f"DROP TABLE {table}")
            conn.commit()
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            schema.install(conn, **approval(self.path, **migration_binding("recognition_operations", schema.definitions())))
        self.assertFalse(self.sql("SELECT name FROM sqlite_master WHERE name='recognition_operation_contracts'"))

    def test_install_failure_savepoint_rollback_even_when_caught(self):
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            for table in reversed(list(schema.TABLES)):
                conn.execute(f"DROP TABLE {table}")
            conn.execute("CREATE TABLE recognition_operation_executions(bad TEXT)")
            conn.commit()
            conn.execute("BEGIN IMMEDIATE")
            with self.assertRaises(Quarantined):
                schema.install(conn, **approval(self.path, **migration_binding("recognition_operations", schema.definitions())))
            conn.commit()
        self.assertFalse(self.sql("SELECT name FROM sqlite_master WHERE name='recognition_operation_contracts'"))

    def test_no_authority_role_or_production_bypass(self):
        subject = dict(event_id=self.event, accounting_policy=POLICY)
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            for kw in ({}, {"authorization": {"role": "owner"}}, {"authority": object()}):
                with self.assertRaises(Quarantined):
                    op.create_operation(conn, self.event, POLICY, **kw)
            kw = approval(self.path, **op.binding("create", subject))
            kw["authorization"] = replace(kw["authorization"], environment="production")
            with self.assertRaisesRegex(Quarantined, "synthetic_operation_persistence_only"):
                op.create_operation(conn, self.event, POLICY, **kw)
        with self.assertRaisesRegex(AuthorizationError, "production_authority_not_provisioned"):
            authority.provision_production_authority()

    def test_no_production_execution_or_writer_authority(self):
        operation = self.authorized()
        with patch.object(permanent, "finalize", side_effect=AssertionError("writer invoked")), \
                patch("sqlite3.connect", side_effect=AssertionError("import opened target")):
            importlib.reload(op)
        self.assertNotIn("execute", vars(op))
        with connection(self.path) as conn:
            from src.review.recognition.authorization import verify
            with self.assertRaisesRegex(AuthorizationError, "authorization_required"):
                verify(conn, operation, None)

    def test_no_transaction_and_no_install_authority(self):
        with connection(self.path, write=True) as conn:
            with self.assertRaises(ValueError):
                op.create_operation(conn, self.event, POLICY)
            conn.execute("BEGIN IMMEDIATE")
            with self.assertRaises(Quarantined):
                schema.install(conn)

    def test_explorer_and_existing_writer_tables_unchanged(self):
        before = {table: self.sql(f"SELECT * FROM {table}") for table in EXPLORER_TABLES}
        operation = self.execution(self.authorized(), "EXECUTING")
        self.execution(operation, "COMPLETED", self.receipt(operation))
        self.assertEqual(before, {table: self.sql(f"SELECT * FROM {table}") for table in EXPLORER_TABLES})
        self.assertFalse(self.sql("SELECT name FROM sqlite_master WHERE name='recognition_private_operations'"))


if __name__ == "__main__":
    unittest.main()
