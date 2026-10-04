"""First Look reporting uses only synthetic disposable databases."""

import hashlib
from contextlib import closing
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.review.recognition.first_looks import build_report
from src.review.recognition.rules import canonical
from src.review.recognition.qualification import qualify


class FirstLookReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "historical.db"
        with closing(sqlite3.connect(self.path)) as conn:
            conn.executescript("""
                CREATE TABLE community_reviewers(id INTEGER PRIMARY KEY);
                INSERT INTO community_reviewers VALUES(1),(2);
                CREATE TABLE physical_stops(id INTEGER PRIMARY KEY);
                INSERT INTO physical_stops VALUES(1),(2);
                CREATE TABLE stop_gtfs_status(physical_stop_id INTEGER,current_gtfs INTEGER);
                INSERT INTO stop_gtfs_status VALUES(1,0),(2,1);
                CREATE TABLE stop_review_assignments(id INTEGER PRIMARY KEY,stop_id INTEGER,
                    reviewer_id INTEGER,status TEXT,completed_at TEXT);
                CREATE TABLE stop_observations(id INTEGER PRIMARY KEY,assignment_id INTEGER,
                    reviewer_id INTEGER,physical_stop_id INTEGER,source TEXT,observed_at TEXT);
                CREATE TABLE physical_stop_identity_edges(event_id INTEGER,
                    predecessor_physical_stop_id INTEGER,successor_physical_stop_id INTEGER);
            """)

    def sql(self, query, args=()):
        conn = sqlite3.connect(self.path)
        try:
            result = conn.execute(query, args).fetchall()
            conn.commit()
            return result
        finally:
            conn.close()

    def review(self, assignment, owner=1, stop=1, time="2026-09-25T12:00:00Z"):
        self.sql("INSERT INTO stop_review_assignments VALUES(?,?,?,'completed',?)", (assignment, stop, owner, time))
        self.sql("INSERT INTO stop_observations VALUES(?,?,?,?, 'community_review','1999-01-01')",
                 (assignment, assignment, owner, stop))

    def report(self, reviewed=True, **kwargs):
        reconciliation = {"reference": "synthetic-reviewed-cohort", "clock_review_reference": "synthetic-clock-audit",
                          "identity_review_reference": "synthetic-identity-audit",
                          "expected_assignment_ids": [r[0] for r in self.sql("SELECT id FROM stop_review_assignments ORDER BY id")]}
        return build_report(self.path, cutoff_utc="2026-10-01T00:00:00Z",
                            reconciliation=reconciliation if reviewed else None, **kwargs)

    def test_same_second_numeric_tie_across_reviewers_and_reversed_discovery(self):
        self.review(10, owner=1)
        self.review(9, owner=2, time="2026-09-25T08:00:00-04:00")
        report = self.report()
        winner = report["stops"][0]["provisional_winner"]
        self.assertEqual((9, 2), (winner["assignment_id"], winner["reviewer_id"]))
        self.sql("DELETE FROM stop_observations")
        self.sql("DELETE FROM stop_review_assignments")
        self.review(9, owner=2, time="2026-09-25T08:00:00-04:00")
        self.review(10, owner=1)
        self.assertEqual(report, self.report())

    def test_invalid_competitor_is_excluded_but_not_silently_ignored(self):
        self.review(1)
        self.review(2, owner=2, time="2026-09-24T12:00:00Z")
        self.sql("UPDATE stop_observations SET reviewer_id=1 WHERE id=2")
        stop = self.report()["stops"][0]
        self.assertEqual([1], [f["assignment_id"] for f in stop["qualifying_completions"]])
        self.assertEqual("evidence_identity_mismatch", stop["excluded"][0]["reason"])
        self.assertIsNone(stop["provisional_winner"])

    def test_missing_ambiguous_and_fractional_timestamps_require_review(self):
        for value in (None, "bad", "2026-09-24 12:00:00", "2026-09-24T12:00:00.1Z"):
            with self.subTest(value=value):
                self.sql("DELETE FROM stop_observations")
                self.sql("DELETE FROM stop_review_assignments")
                self.review(1)
                self.review(2, owner=2, time=value)
                report = self.report()
                self.assertEqual("requires_adjudication", report["status"])
                self.assertIsNone(report["stops"][0]["provisional_winner"])

    def test_reviewed_naive_provenance_is_preserved(self):
        self.review(1, time="2026-09-24 12:00:00")
        fact = self.report(sqlite_utc_provenance="synthetic-writer-audit")["stops"][0]["provisional_winner"]
        self.assertEqual("sqlite_current_timestamp_utc:synthetic-writer-audit", fact["timestamp_provenance"])
        with self.assertRaises(ValueError):
            self.report(sqlite_utc_provenance=" ")

    def test_late_earlier_completion_requires_adjudication(self):
        self.review(10)
        prior = self.report()
        self.review(20, owner=2, time="2026-09-24T12:00:00Z")
        report = self.report(previous_report=prior)
        stop = report["stops"][0]
        self.assertEqual(20, stop["earliest_candidate"]["assignment_id"])
        self.assertIsNone(stop["provisional_winner"])
        self.assertIn("late_discovered_earlier_completion", stop["reasons"])
        self.assertIsNone(self.report(previous_report=report)["stops"][0]["provisional_winner"])

    def test_corrected_backdated_and_removed_evidence_require_review(self):
        self.review(1)
        prior = self.report()
        self.sql("UPDATE stop_review_assignments SET completed_at='2026-09-20T12:00:00Z'")
        report = self.report(previous_report=prior)
        self.assertIn("corrected_or_removed_evidence", report["stops"][0]["reasons"])
        self.sql("DELETE FROM stop_observations")
        self.sql("DELETE FROM stop_review_assignments")
        self.assertEqual("requires_adjudication", self.report(previous_report=prior)["status"])

    def test_inactive_stops_retained_identity_changes_never_transfer_credit(self):
        self.review(1)
        self.assertEqual(1, self.report()["stops"][0]["provisional_winner"]["physical_stop_id"])
        self.sql("INSERT INTO physical_stop_identity_edges VALUES(1,1,2)")
        report = self.report()
        self.assertEqual([1], [s["physical_stop_id"] for s in report["stops"]])
        self.assertIn("physical_identity_changed", report["stops"][0]["reasons"])
        self.assertIsNone(report["stops"][0]["provisional_winner"])

    def test_unreviewed_coverage_clock_and_missing_competitors_block_winners(self):
        self.review(1)
        report = self.report(reviewed=False)
        self.assertIn("clock_regressions_unreviewed", report["reasons"])
        self.assertIn("historical_coverage_unreviewed", report["reasons"])
        self.assertIsNone(report["stops"][0]["provisional_winner"])
        self.sql("INSERT INTO stop_observations VALUES(99,99,2,1,'community_review','2026-01-01')")
        self.assertIn("missing_assignment_competitors", self.report()["reasons"])

    def test_expected_population_mismatch_and_cutoff(self):
        self.review(1, time="2026-10-01T00:00:00Z")
        self.assertEqual("at_or_after_cutoff", self.report()["excluded"][0]["reason"])
        report = build_report(self.path, cutoff_utc="2026-10-02T00:00:00Z", reconciliation={
            "reference": "fixture", "clock_review_reference": "fixture", "identity_review_reference": "fixture",
            "expected_assignment_ids": [1, 2]})
        self.assertIn("historical_population_mismatch", report["reasons"])

    def test_previous_report_tampering_rejected(self):
        self.review(1)
        prior = self.report()
        prior["source"] = []
        with self.assertRaisesRegex(ValueError, "incompatible_previous_report"):
            self.report(previous_report=prior)

    def test_existing_immutable_completion_conflict_and_awards_untouched(self):
        from src.review.recognition.schema import migrate
        self.review(1)
        migrate(self.path, apply=True)
        # Synthetic immutable fact conflicts with the current source timestamp.
        self.sql("""INSERT INTO recognition_completions VALUES(
            1,1,1,1,1,'2026-09-20T12:00:00Z','2026-09-20T12:00:00Z',
            'explicit_offset','explorer:v1','backfill','2026-10-01T00:00:00Z')""")
        before = hashlib.sha256(self.path.read_bytes()).hexdigest()
        report = self.report()
        self.assertIn("immutable_completion_conflict", report["stops"][0]["reasons"])
        self.assertIsNone(report["stops"][0]["provisional_winner"])
        self.assertEqual(before, hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.assertEqual([(0,)], self.sql("SELECT count(*) FROM recognition_awards"))

    def test_ambiguous_observations_block_ordering(self):
        self.review(1)
        self.sql("INSERT INTO stop_observations VALUES(2,1,1,1,'community_review','2000-01-01')")
        report = self.report()
        self.assertEqual([], report["qualified"])
        self.assertEqual("ambiguous_community_evidence", report["excluded"][0]["reason"])
        self.assertIsNone(report["stops"][0]["provisional_winner"])

    def test_deterministic_read_only_no_recognition_schema_needed(self):
        self.review(1)
        before = hashlib.sha256(self.path.read_bytes()).hexdigest()
        def read_only(conn, *args, **kwargs):
            self.assertEqual(1, conn.execute("PRAGMA query_only").fetchone()[0])
            with self.assertRaises(sqlite3.OperationalError):
                conn.execute("UPDATE stop_review_assignments SET status='assigned'")
            return qualify(conn, *args, **kwargs)
        with patch("src.review.recognition.first_looks.qualify", side_effect=read_only):
            first = self.report()
        self.assertEqual(canonical(first), canonical(self.report()))
        self.assertEqual(before, hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.assertFalse(first["permanent_claims_created"])
        self.assertFalse(self.sql("SELECT name FROM sqlite_master WHERE name LIKE 'recognition_%'"))


if __name__ == "__main__":
    unittest.main()
