"""Synthetic caller-owned live transactions; no production configuration."""

from dataclasses import replace
import unittest
from unittest.mock import patch

from src.review.recognition import RecognitionGate
from src.review.recognition import permanent
from src.review.recognition.live_first_looks import Configuration, enqueue, seal_pending
from src.review.recognition.live_first_look_schema import migrate
from src.review.recognition.permanent_schema import migrate as migrate_permanent
from src.review.recognition.rules import canonical, digest
from src.review.recognition.schema import connection, migrate as migrate_explorer
from tests import test_recognition_geography as fixture


CAPTURE = RecognitionGate(capture=True)
ISSUE = RecognitionGate(issuance=True)
CONFIG = Configuration(activation_at_utc="2026-10-01T00:00:00Z",
                       historical_cutoff_utc="2026-09-30T00:00:00Z",
                       policy_reference="synthetic-finality-test-only", policy_sha256="a" * 64)


class LiveFirstLookTests(unittest.TestCase):
    sql = fixture.GeographyReportTests.sql
    review = fixture.GeographyReportTests.review

    def setUp(self):
        fixture.GeographyReportTests.setUp(self)
        self.review(1)
        migrate_permanent(self.path, apply=True)
        self.baseline = permanent.prepare(self.path, family="first_look", inputs={
            "cutoff_utc": CONFIG.historical_cutoff_utc, "reconciliation": {
                "reference": "synthetic-historical", "clock_review_reference": "synthetic-clock",
                "identity_review_reference": "synthetic-identity", "expected_assignment_ids": [1]}},
            evaluation_at_utc=CONFIG.historical_cutoff_utc, authorization_reference="synthetic-historical")
        self.baseline_id = digest(self.baseline)
        migrate(self.path, apply=True)

    def seal_baseline(self):
        permanent.finalize(self.path, self.baseline, manifest_sha256=self.baseline_id,
                           authorization_reference="synthetic-historical", gate=ISSUE)

    def add_live(self, number=2, *, stop=2, owner=1, time="2026-10-01T12:00:00Z"):
        self.review(number, stop=stop, owner=owner, captured=False, timestamp=time)
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            result = enqueue(conn, number, configuration=CONFIG, gate=CAPTURE)
            conn.commit()
        return result

    def guard(self, conn, context):
        self.assertTrue(conn.in_transaction)
        self.assertEqual(context["configuration"], CONFIG.__dict__)
        return {"historical_operation_id": self.baseline_id,
                "evaluation_at_utc": "2026-10-03T00:00:00Z", "reference": "synthetic-finality-decision",
                "inputs": {"cutoff_utc": "2026-10-03T00:00:00Z", "reconciliation": {
                    "reference": "synthetic-full-population", "clock_review_reference": "synthetic-clock",
                    "identity_review_reference": "synthetic-identity",
                    "expected_assignment_ids": [r[0] for r in conn.execute("SELECT id FROM stop_review_assignments ORDER BY id")]}}}

    def process(self, number=2, **kwargs):
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            result = seal_pending(conn, number, gate=ISSUE, **{"finality_guard": self.guard, **kwargs})
            conn.commit()
        return result

    def pending(self, number=2):
        return self.sql("SELECT state,attempts,last_error_code,outcome FROM recognition_first_look_pending WHERE assignment_id=?", (number,))[0]

    def test_disabled_defaults_do_not_touch_connection(self):
        self.assertIsNone(enqueue(None, 2))
        self.assertEqual({"state": "disabled"}, seal_pending(None, 2))
        self.assertIsNone(Configuration().activation_at_utc)
        self.review(2, captured=False)
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            with self.assertRaises(ValueError):
                enqueue(conn, 2, gate=CAPTURE)
        self.assertEqual([], self.sql("SELECT * FROM recognition_first_look_pending"))

    def test_migration_dry_run_repeat_and_rollback(self):
        before = self.path.read_bytes()
        self.assertFalse(migrate(self.path)["applied"])
        self.assertEqual(before, self.path.read_bytes())
        migrate(self.path, apply=True)
        migrate_explorer(self.path, apply=True)
        self.assertEqual([(1,)], self.sql("SELECT assignment_id FROM recognition_jobs"))

    def test_capture_pending_idempotency_and_explorer_separation(self):
        old_jobs = self.sql("SELECT * FROM recognition_jobs")
        self.add_live()
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            enqueue(conn, 2, configuration=CONFIG, gate=CAPTURE)
            conn.commit()
        self.assertEqual(("pending", 0, None, None), self.pending())
        self.assertEqual([(2,)], self.sql("SELECT COUNT(*) FROM recognition_completions"))
        self.assertEqual(old_jobs, self.sql("SELECT * FROM recognition_jobs"))
        self.assertEqual([(0,)], self.sql("SELECT COUNT(*) FROM recognition_awards"))

    def test_before_activation_and_missing_community_evidence(self):
        self.assertFalse(self.add_live(time="2026-09-30T12:00:00Z")["enqueued"])
        self.assertEqual([], self.sql("SELECT * FROM recognition_first_look_pending"))
        self.review(3, captured=False, timestamp="2026-10-01T12:00:00Z")
        self.sql("DELETE FROM stop_observations WHERE assignment_id=3")
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            with self.assertRaisesRegex(ValueError, "missing_community_evidence"):
                enqueue(conn, 3, configuration=CONFIG, gate=CAPTURE)
        self.assertEqual([(1,)], self.sql("SELECT COUNT(*) FROM recognition_completions"))

    def test_unsealed_baseline_blocks_claim_and_explicit_retry(self):
        self.add_live()
        result = self.process()
        self.assertEqual("quarantined", result["state"])
        self.assertEqual("missing_operation", result["reason"])
        self.assertEqual([], self.sql("SELECT * FROM recognition_first_look_claims"))
        # Existing historical manifest is frozen; seal on an otherwise identical
        # fixture before adding live work in successful tests below.
        self.assertEqual(result, self.process())
        self.assertEqual(1, self.pending()[1])

    def test_finality_guard_absent_or_not_ready_durably_defers(self):
        self.seal_baseline()
        self.add_live()
        self.assertEqual("pending", self.process(finality_guard=None)["state"])
        self.assertEqual("pending", self.process(finality_guard=lambda conn, context: None)["state"])
        self.assertEqual(2, self.pending()[1])
        self.assertEqual([(1,)], self.sql("SELECT physical_stop_id FROM recognition_first_look_claims"))

    def test_numeric_tie_not_delivery_order_and_duplicate_claim(self):
        self.seal_baseline()
        self.add_live(10, owner=1)
        self.add_live(2, owner=2)
        old_jobs = self.sql("SELECT * FROM recognition_jobs")
        self.assertEqual("claim_sealed", self.process(10)["outcome"])
        self.assertEqual([(2, 2)], self.sql("SELECT assignment_id,reviewer_id FROM recognition_first_look_claims WHERE physical_stop_id=2"))
        self.assertEqual("existing_claim", self.process(2)["outcome"])
        before = self.path.read_bytes()
        self.assertTrue(self.process(10)["idempotent"])
        self.assertEqual(before, self.path.read_bytes())
        self.assertEqual(old_jobs, self.sql("SELECT * FROM recognition_jobs"))
        with connection(self.path) as conn:
            self.assertEqual(2, permanent.check_claim_integrity(conn, 2)["assignment_id"])

    def test_earlier_completion_wins_even_with_larger_assignment_id(self):
        self.seal_baseline()
        self.add_live(2)
        self.add_live(10, owner=2, time="2026-10-01T11:00:00Z")
        self.assertEqual("done", self.process(2)["state"])
        self.assertEqual([(10,)], self.sql("SELECT assignment_id FROM recognition_first_look_claims WHERE physical_stop_id=2"))

    def test_late_earlier_completion_quarantines_without_reassignment(self):
        self.seal_baseline()
        self.add_live(2)
        self.process(2)
        self.add_live(10, owner=2, time="2026-10-01T11:00:00Z")
        result = self.process(10)
        self.assertEqual({"state": "quarantined", "reason": "existing_claim_requires_discrepancy"}, result)
        self.assertEqual([(2,)], self.sql("SELECT assignment_id FROM recognition_first_look_claims WHERE physical_stop_id=2"))
        self.assertEqual("quarantined", self.process(10, retry_quarantined=True)["state"])
        self.assertEqual(2, self.pending(10)[1])

    def test_finality_cutoff_excludes_completion(self):
        self.seal_baseline()
        self.add_live()
        def guard(conn, context):
            result = self.guard(conn, context)
            result["inputs"]["cutoff_utc"] = "2026-10-01T12:00:00Z"
            return result
        self.assertEqual("quarantined", self.process(finality_guard=guard)["state"])
        self.assertEqual([(1,)], self.sql("SELECT physical_stop_id FROM recognition_first_look_claims"))

    def test_caller_rollback_includes_completion_and_pending(self):
        self.review(2, captured=False, timestamp="2026-10-01T12:00:00Z")
        self.sql("UPDATE stop_review_assignments SET status='pending',completed_at=NULL WHERE id=2")
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("UPDATE stop_review_assignments SET status='completed',completed_at='2026-10-01T12:00:00Z' WHERE id=2")
            enqueue(conn, 2, configuration=CONFIG, gate=CAPTURE)
            self.assertTrue(conn.in_transaction)
        self.assertEqual([("pending", None)], self.sql("SELECT status,completed_at FROM stop_review_assignments WHERE id=2"))
        self.assertEqual([], self.sql("SELECT * FROM recognition_first_look_pending"))
        self.assertEqual([(1,)], self.sql("SELECT COUNT(*) FROM recognition_completions"))

    def test_sealing_failure_and_caller_rollback_are_atomic(self):
        self.seal_baseline()
        self.add_live()
        original = permanent.check_claim_integrity
        def fail_after_insert(conn, stop):
            if stop == 2:
                self.assertIsNotNone(conn.execute("SELECT 1 FROM recognition_first_look_claims WHERE physical_stop_id=2").fetchone())
                raise RuntimeError("synthetic-failure-after-insert")
            return original(conn, stop)
        with patch.object(permanent, "check_claim_integrity", side_effect=fail_after_insert):
            with self.assertRaises(RuntimeError):
                self.process()
        self.assertEqual(("pending", 0, None, None), self.pending())
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            self.assertEqual("done", seal_pending(conn, 2, gate=ISSUE, finality_guard=self.guard)["state"])
            self.assertTrue(conn.in_transaction)
        self.assertEqual(("pending", 0, None, None), self.pending())
        self.assertEqual([(1,)], self.sql("SELECT COUNT(*) FROM recognition_private_operations"))
        self.assertEqual("done", self.process()["state"])

    def test_immutable_configuration_and_changed_source(self):
        self.seal_baseline()
        self.add_live()
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            with self.assertRaisesRegex(ValueError, "live_configuration_conflict"):
                enqueue(conn, 2, gate=CAPTURE, configuration=replace(CONFIG, policy_reference="different"))
        self.sql("UPDATE stop_observations SET reviewer_id=2 WHERE assignment_id=2")
        self.assertEqual("quarantined", self.process()["state"])
        self.assertEqual([(1,)], self.sql("SELECT physical_stop_id FROM recognition_first_look_claims"))

    def test_guard_cannot_write_or_commit_and_identity_exceptions_withhold(self):
        import sqlite3
        self.seal_baseline()
        self.add_live()
        def bad_guard(conn, context):
            conn.execute("COMMIT")
        with self.assertRaises(sqlite3.DatabaseError):
            self.process(finality_guard=bad_guard)
        self.assertEqual(("pending", 0, None, None), self.pending())
        self.sql("INSERT INTO physical_stop_identity_events VALUES(1,'merge')")
        self.sql("INSERT INTO physical_stop_identity_edges VALUES(1,2,3)")
        self.assertEqual("quarantined", self.process()["state"])
        self.assertEqual([(1,)], self.sql("SELECT physical_stop_id FROM recognition_first_look_claims"))

    def test_undeclared_competitor_and_tampered_pending_schema_rejected(self):
        self.seal_baseline()
        self.add_live()
        self.review(3, stop=2, owner=2, captured=False, timestamp="2026-10-01T11:00:00Z")
        self.assertEqual("competitor_completion_not_captured", self.process()["reason"])
        self.sql("DROP TRIGGER recognition_first_look_pending_context")
        with self.assertRaisesRegex(ValueError, "live_first_look_schema_mismatch"):
            self.process()

    def test_concurrent_deliveries_create_one_claim(self):
        from concurrent.futures import ThreadPoolExecutor
        self.seal_baseline()
        self.add_live(10, owner=1)
        self.add_live(2, owner=2)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(self.process, [10, 2]))
        self.assertEqual(["claim_sealed", "existing_claim"], sorted(r["outcome"] for r in results))
        self.assertEqual([(2,)], self.sql("SELECT assignment_id FROM recognition_first_look_claims WHERE physical_stop_id=2"))
        self.assertEqual([(2,)], self.sql("SELECT COUNT(*) FROM recognition_private_operations"))

    def test_primitives_never_open_a_connection_and_live_claim_read_integrity(self):
        from src.review.recognition.achievements import build_achievements
        self.seal_baseline()
        self.review(2, captured=False, timestamp="2026-10-01T12:00:00Z")
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            with patch("sqlite3.connect", side_effect=AssertionError("independent connection")):
                enqueue(conn, 2, configuration=CONFIG, gate=CAPTURE)
                self.assertEqual("done", seal_pending(conn, 2, gate=ISSUE, finality_guard=self.guard)["state"])
            conn.commit()
        self.sql("ALTER TABLE community_reviewers ADD COLUMN reviewer_key TEXT")
        self.sql("UPDATE community_reviewers SET reviewer_key='synthetic' WHERE id=1")
        before = self.path.read_bytes()
        results = build_achievements(self.path, 1, "synthetic")["achievements"]
        self.assertEqual(2, len(results))
        self.assertTrue(all(set(r) == {"family", "recognition_kind", "earned_at_utc"} for r in results))
        self.assertEqual(before, self.path.read_bytes())


if __name__ == "__main__":
    unittest.main()
