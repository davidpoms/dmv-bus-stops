"""Independent approval is synthetic here; no production artifacts are opened."""

from copy import deepcopy
import sqlite3
import unittest
from unittest.mock import patch

from src.review.recognition import RecognitionGate, permanent
from src.review.recognition.first_look_launch import (
    CANDIDATE_ARTIFACT_SHA256, FINALITY, HISTORICAL_CUTOFF, build_guard, configuration_for,
)
from src.review.recognition.live_first_looks import enqueue, seal_pending, delivery_status, record_retryable_failure
from src.review.recognition.live_first_look_schema import migrate
from src.review.recognition.permanent_schema import migrate as migrate_permanent
from src.review.recognition.qualification import capture_completion
from src.review.recognition.report_connection import report_connection
from src.review.recognition.rules import RULE_KEY, digest
from src.review.recognition.schema import connection, migrate as migrate_explorer
from tests import test_recognition_geography as fixture


CAPTURE = RecognitionGate(capture=True)
ISSUE = RecognitionGate(issuance=True)


class LaunchPolicyTests(unittest.TestCase):
    sql = fixture.GeographyReportTests.sql

    def setUp(self):
        fixture.GeographyReportTests.setUp(self)
        migrate_explorer(self.path, apply=True)
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            for n in range(1, 56):
                conn.execute("INSERT INTO stop_review_assignments VALUES(?,?,1,'completed','2026-09-25T12:00:00Z')", (n, n))
                conn.execute("INSERT INTO stop_observations VALUES(?,?,1,?,'community_review')", (n, n, n))
                capture_completion(conn, n, RULE_KEY, gate=CAPTURE)
            conn.commit()
        migrate_permanent(self.path, apply=True)
        migrate(self.path, apply=True)
        self.baseline = self.population(HISTORICAL_CUTOFF)
        self.policy = {"format": "first-look-launch-policy-v1", "reference": "synthetic-policy-review",
                       "activation_at_utc": "2026-10-01T00:00:00Z", "historical_cutoff_utc": HISTORICAL_CUTOFF,
                       "historical_qualified_count": 55, "candidate_artifact_sha256": CANDIDATE_ARTIFACT_SHA256,
                       "historical_operation_id": digest(self.baseline),
                       "historical_qualified_sha256": digest(self.baseline["report"]["qualified"]),
                       "sqlite_utc_provenance": None, "gap_assignment_ids": [],
                       "gap_review_reference": "synthetic-empty-gap-review", "finality": dict(FINALITY)}

    def population(self, cutoff="2026-10-03T00:00:00Z"):
        inputs = {"cutoff_utc": cutoff, "reconciliation": {
            "reference": "synthetic-population-review", "clock_review_reference": "synthetic-clock-review",
            "identity_review_reference": "synthetic-identity-review",
            "expected_assignment_ids": [r[0] for r in self.sql("SELECT id FROM stop_review_assignments ORDER BY id")]}}
        return permanent.prepare(self.path, family="first_look", inputs=inputs, evaluation_at_utc=cutoff,
                                 authorization_reference="synthetic-inspection-reference")

    def seal_baseline(self):
        permanent.finalize(self.path, self.baseline, manifest_sha256=digest(self.baseline),
                           authorization_reference="synthetic-inspection-reference", gate=ISSUE)

    def add(self, number=60, *, stop=60, timestamp="2026-10-01T12:00:00Z"):
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("INSERT INTO stop_review_assignments VALUES(?,?,2,'completed',?)", (number, stop, timestamp))
            conn.execute("INSERT INTO stop_observations VALUES(?,?,2,?,'community_review')", (number, number, stop))
            result = enqueue(conn, number, configuration=configuration_for(self.policy), gate=CAPTURE)
            conn.commit()
        return result

    def approval(self, population):
        return {"format": "first-look-launch-authorization-v1", "reference": "synthetic-independent-approval",
                "policy_sha256": digest(self.policy), "population_sha256": digest(population),
                "baseline_link_review_reference": "synthetic-candidate-to-sealed-baseline-review"}

    def guard(self, population=None):
        population = population or self.population()
        auth = self.approval(population)
        def verifier(candidate, policy_hash, population_hash):
            return candidate == auth and policy_hash == auth["policy_sha256"] and population_hash == auth["population_sha256"]
        return build_guard(self.policy, population, auth, authorization_verifier=verifier)

    def process(self, guard, number=60, **kwargs):
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            result = seal_pending(conn, number, finality_guard=guard, gate=ISSUE, **kwargs)
            conn.commit()
        return result

    def test_default_and_missing_authorization_are_disabled(self):
        self.assertIsNone(build_guard())
        population = self.population()
        self.assertIsNone(build_guard(self.policy, population))
        self.assertIsNone(build_guard(self.policy, population, self.approval(population)))
        self.assertEqual({"state": "disabled"}, seal_pending(None, 60))
        with self.assertRaisesRegex(ValueError, "launch_not_independently_authorized"):
            build_guard(self.policy, population, self.approval(population), authorization_verifier=lambda *args: False)

    def test_missing_activation_finality_baseline_and_review_refs_rejected(self):
        for key in ("activation_at_utc", "finality", "historical_operation_id", "gap_review_reference"):
            policy = deepcopy(self.policy)
            policy[key] = None
            with self.subTest(field=key), self.assertRaises(ValueError):
                configuration_for(policy)
        self.add()
        self.assertEqual("missing_operation", self.process(self.guard())["reason"])

    def test_exact_55_baseline_and_candidate_reference_pinned(self):
        self.seal_baseline()
        for key, value in (("historical_qualified_count", 54), ("candidate_artifact_sha256", "0" * 64)):
            policy = {**self.policy, key: value}
            with self.assertRaisesRegex(ValueError, "historical_launch_context_mismatch"):
                configuration_for(policy)
        self.policy["historical_qualified_sha256"] = "0" * 64
        self.add()
        self.assertEqual("historical_population_mismatch", self.process(self.guard())["reason"])

    def test_before_activation_not_enqueued(self):
        self.assertEqual({"enqueued": False, "reason": "before_activation"}, self.add(timestamp="2026-09-30T12:00:00Z"))
        self.assertEqual([], self.sql("SELECT * FROM recognition_first_look_pending"))

    def test_after_activation_seals_and_retry_is_idempotent(self):
        self.seal_baseline()
        self.add()
        guard = self.guard()
        self.assertEqual("claim_sealed", self.process(guard)["outcome"])
        before = self.path.read_bytes()
        self.assertTrue(self.process(guard)["idempotent"])
        self.assertEqual(before, self.path.read_bytes())
        with connection(self.path) as conn:
            self.assertEqual(60, permanent.check_claim_integrity(conn, 60)["assignment_id"])

    def test_after_exclusive_frontier_defers(self):
        self.seal_baseline()
        self.add(timestamp="2026-10-03T00:00:00Z")
        self.assertEqual("pending", self.process(self.guard())["state"])
        self.assertEqual([(55,)], self.sql("SELECT COUNT(*) FROM recognition_first_look_claims"))

    def test_late_arrival_invalidates_approval(self):
        self.seal_baseline()
        self.add()
        guard = self.guard()
        self.add(61, stop=60, timestamp="2026-10-01T11:00:00Z")
        # The full-population reconciliation rejects the new competitor before
        # the subsequent canonical-manifest comparison can run.
        self.assertEqual("historical_population_unreviewed", self.process(guard, 61)["reason"])
        self.assertEqual([], self.sql("SELECT * FROM recognition_first_look_claims WHERE physical_stop_id=60"))

    def test_existing_claim_acknowledged_conflict_never_reassigned(self):
        self.seal_baseline()
        self.add()
        self.process(self.guard())
        self.add(61, stop=60, timestamp="2026-10-02T12:00:00Z")
        self.assertEqual("existing_claim", self.process(self.guard(), 61)["outcome"])
        self.add(62, stop=60, timestamp="2026-10-01T11:00:00Z")
        self.assertEqual("existing_claim_requires_discrepancy", self.process(self.guard(), 62)["reason"])
        self.assertEqual([(60,)], self.sql("SELECT assignment_id FROM recognition_first_look_claims WHERE physical_stop_id=60"))
        with connection(self.path) as conn:
            self.assertEqual("quarantined/conflict", delivery_status(conn, 62)["phase"])

    def test_caller_rollback(self):
        self.seal_baseline()
        self.add()
        guard = self.guard()
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            self.assertEqual("done", seal_pending(conn, 60, gate=ISSUE, finality_guard=guard)["state"])
        self.assertEqual([("pending", 0)], self.sql("SELECT state,attempts FROM recognition_first_look_pending"))
        self.assertEqual([(55,)], self.sql("SELECT COUNT(*) FROM recognition_first_look_claims"))

    def test_55_historical_and_nine_later_with_incomplete_pairs_remain_separate(self):
        self.seal_baseline()
        before = self.sql("SELECT * FROM recognition_first_look_claims ORDER BY physical_stop_id")
        for n in range(60, 69):
            self.add(n, stop=n)
        # Nine synthetic completions, with three later incomplete assignments
        # for already reviewed stops. No real assignment/stop/reviewer IDs.
        for number, stop in ((80, 60), (81, 61), (82, 68)):
            self.sql("INSERT INTO stop_review_assignments VALUES(?,?,2,'pending',NULL)", (number, stop))
        guard = self.guard()
        self.assertEqual([(9,)], self.sql("SELECT COUNT(*) FROM recognition_first_look_pending"))
        for number in reversed(range(60, 69)):
            self.assertEqual("claim_sealed", self.process(guard, number)["outcome"])
        self.assertEqual([(n,) for n in range(60, 69)], self.sql(
            "SELECT assignment_id FROM recognition_first_look_claims WHERE physical_stop_id>55 ORDER BY assignment_id"))
        self.assertEqual([(80,), (81,), (82,)], self.sql(
            "SELECT id FROM stop_review_assignments WHERE status='pending' ORDER BY id"))
        self.assertEqual(before, self.sql("SELECT * FROM recognition_first_look_claims WHERE physical_stop_id<=55 ORDER BY physical_stop_id"))
        self.assertEqual([(0,)], self.sql("SELECT COUNT(*) FROM recognition_jobs"))
        self.assertEqual(55, len(self.baseline["report"]["qualified"]))

    def test_reviewed_population_uses_time_then_numeric_id_not_delivery(self):
        self.seal_baseline()
        self.add(70, stop=60)
        self.add(60, stop=60)
        self.add(90, stop=60, timestamp="2026-10-01T11:00:00Z")
        guard = self.guard()
        self.assertEqual("claim_sealed", self.process(guard, 70)["outcome"])
        self.assertEqual("existing_claim", self.process(guard, 60)["outcome"])
        self.assertEqual([(90,)], self.sql("SELECT assignment_id FROM recognition_first_look_claims WHERE physical_stop_id=60"))
        self.add(71, stop=61)
        self.add(69, stop=61)
        guard = self.guard()
        self.process(guard, 71)
        self.assertEqual([(69,)], self.sql("SELECT assignment_id FROM recognition_first_look_claims WHERE physical_stop_id=61"))

    def test_incomplete_competitor_completing_earlier_invalidates_closure(self):
        self.seal_baseline()
        self.add()
        self.sql("INSERT INTO stop_review_assignments VALUES(61,60,2,'pending',NULL)")
        guard = self.guard()
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("UPDATE stop_review_assignments SET status='completed',completed_at='2026-10-01T11:00:00Z' WHERE id=61")
            conn.execute("INSERT INTO stop_observations VALUES(61,61,2,60,'community_review')")
            enqueue(conn, 61, configuration=configuration_for(self.policy), gate=CAPTURE)
            conn.commit()
        self.assertEqual("closed_population_changed", self.process(guard)["reason"])
        self.assertEqual([], self.sql("SELECT * FROM recognition_first_look_claims WHERE physical_stop_id=60"))
        self.assertEqual("claim_sealed", self.process(self.guard(), 61)["outcome"])
        self.assertEqual([(61,)], self.sql("SELECT assignment_id FROM recognition_first_look_claims WHERE physical_stop_id=60"))

    def test_delivery_states_and_explicit_transient_retry_record(self):
        self.seal_baseline()
        self.add()
        def status():
            with connection(self.path) as conn:
                return delivery_status(conn, 60)
        self.assertEqual("pending", status()["phase"])
        self.process(None)
        self.assertEqual("eligible_awaiting_finality", status()["phase"])
        error = sqlite3.OperationalError("synthetic lock")
        error.sqlite_errorcode = sqlite3.SQLITE_BUSY
        self.assertEqual({"state": "disabled"}, record_retryable_failure(None, 60, error))
        before = status()
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            self.assertEqual("retryable_failure", record_retryable_failure(conn, 60, error, gate=ISSUE)["phase"])
        self.assertEqual(before, status())  # Caller rollback includes retry metadata.
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            record_retryable_failure(conn, 60, error, gate=ISSUE)
            conn.commit()
        self.assertEqual("retryable_failure", status()["phase"])
        self.process(self.guard())
        self.assertEqual("sealed", status()["phase"])
        before = status()
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            record_retryable_failure(conn, 60, error, gate=ISSUE)
            with self.assertRaisesRegex(ValueError, "failure_not_retryable"):
                record_retryable_failure(conn, 60, RuntimeError("unknown"), gate=ISSUE)
            conn.commit()
        self.assertEqual(before, status())

    def test_gap_population_requires_explicit_review_without_live_credit(self):
        self.seal_baseline()
        self.add(58, stop=58, timestamp="2026-09-30T12:00:00Z")
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            capture_completion(conn, 58, RULE_KEY, gate=CAPTURE)
            conn.commit()
        self.add()
        self.assertEqual("preactivation_population_unreconciled", self.process(self.guard())["reason"])

    def test_authorization_revocation_and_hash_mismatch(self):
        self.seal_baseline()
        self.add()
        population = self.population()
        auth = self.approval(population)
        with self.assertRaisesRegex(ValueError, "authorization_hash_mismatch"):
            build_guard(self.policy, population, {**auth, "population_sha256": "0" * 64}, authorization_verifier=lambda *args: True)
        allowed = [True]
        guard = build_guard(self.policy, population, auth, authorization_verifier=lambda *args: allowed[0])
        allowed[0] = False
        self.assertEqual("launch_not_independently_authorized", self.process(guard)["reason"])

    def test_nested_report_validation_preserves_outer_sql_authorizer(self):
        self.seal_baseline()
        self.add()
        guard = self.guard()
        original = permanent._prepare
        def inspected(conn, *args):
            result = original(conn, *args)
            with self.assertRaises(sqlite3.DatabaseError):
                conn.execute("UPDATE stop_review_assignments SET status='pending'")
            return result
        # Exercise the real nested report path while the guard's outer read-only
        # authorizer remains active, not a mocked simplified population reader.
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            from dataclasses import asdict
            fact = dict(conn.execute("SELECT * FROM recognition_completions WHERE assignment_id=60").fetchone())
            fact = {k: fact[k] for k in self.population()["report"]["qualified"][-1]}
            with report_connection(conn), patch.object(permanent, "_prepare", side_effect=inspected):
                self.assertIsNotNone(guard(conn, {"configuration": asdict(guard.configuration), "completion": fact}))
                with self.assertRaises(sqlite3.DatabaseError):
                    conn.execute("COMMIT")


if __name__ == "__main__":
    unittest.main()
