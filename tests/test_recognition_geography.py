"""Geography reports: synthetic disposable fixtures, never production data."""

from contextlib import closing
from copy import deepcopy
import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.review.recognition import RecognitionGate
from src.review.recognition.geography import ACTIVE, DEFAULT_THRESHOLDS, build_geography_report
from src.review.recognition.qualification import capture, qualify
from src.review.recognition.rules import canonical, digest
from src.review.recognition.schema import connection, migrate


class GeographyReportTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / "offline.db"
        with closing(sqlite3.connect(self.path)) as conn:
            conn.executescript("""
                CREATE TABLE community_reviewers(id INTEGER PRIMARY KEY);
                INSERT INTO community_reviewers VALUES(1),(2);
                CREATE TABLE physical_stops(id INTEGER PRIMARY KEY);
                CREATE TABLE stop_gtfs_status(physical_stop_id INTEGER,current_gtfs INTEGER);
                CREATE TABLE stop_jurisdiction(stop_id INTEGER,state TEXT,county TEXT,
                    municipality TEXT,dc_ward TEXT,dc_anc TEXT);
                CREATE TABLE stop_review_assignments(id INTEGER PRIMARY KEY,stop_id INTEGER,
                    reviewer_id INTEGER,status TEXT,completed_at TEXT);
                CREATE TABLE stop_observations(id INTEGER PRIMARY KEY,assignment_id INTEGER,
                    reviewer_id INTEGER,physical_stop_id INTEGER,source TEXT);
                CREATE TABLE physical_stop_identity_events(id INTEGER PRIMARY KEY,event_type TEXT);
                CREATE TABLE physical_stop_identity_edges(event_id INTEGER,
                    predecessor_physical_stop_id INTEGER,successor_physical_stop_id INTEGER);
                CREATE TABLE physical_stop_identity_state(physical_stop_id INTEGER,identity_status TEXT);
            """)
            conn.executemany("INSERT INTO physical_stops VALUES(?)", [(n,) for n in range(1, 102)])
            conn.executemany("INSERT INTO stop_gtfs_status VALUES(?,1)", [(n,) for n in range(1, 102)])
            conn.execute("INSERT INTO stop_jurisdiction VALUES(1,'DC',NULL,'District of Columbia','Ward 1','1D')")
            conn.execute("INSERT INTO stop_jurisdiction VALUES(2,'VA','Arlington','Arlington',NULL,NULL)")
            conn.commit()

    def sql(self, sql, params=()):
        with closing(sqlite3.connect(self.path)) as conn:
            result = conn.execute(sql, params).fetchall()
            conn.commit()
            return result

    def review(self, n, *, stop=None, owner=1, captured=True, timestamp="2026-09-25T12:00:00Z"):
        self.sql("INSERT INTO stop_review_assignments VALUES(?,?,?,'completed',?)", (n, stop or n, owner, timestamp))
        self.sql("INSERT INTO stop_observations VALUES(?,?,?,?, 'community_review')", (n, n, owner, stop or n))
        if captured:
            migrate(self.path, apply=True)
            with connection(self.path, write=True) as conn:
                conn.execute("BEGIN IMMEDIATE")
                capture(conn, n, "explorer:v1", gate=RecognitionGate(capture=True), sqlite_utc_provenance="fixture-writer")
                conn.commit()

    def scope(self, count=10, dimension="dc_anc", key="dc_anc:1D"):
        members = [{"physical_stop_id": n, "current_gtfs": 1} for n in range(1, count + 1)]
        return {"dimension": dimension, "canonical_geography_id": key, "scope_key": key,
                "scope_version": "fixture-boundary-v1", "captured_at_utc": "2026-09-30T00:00:00Z",
                "effective_at_utc": "2026-09-30T00:00:00Z",
                "source_provenance": {"reference": "fixture-network", "sha256": "a" * 64},
                "boundary_provenance": {"reference": "fixture-boundary", "sha256": "b" * 64},
                "certification": {"approved": True, "reference": "fixture-reviewed-scope"},
                "active_membership_predicate": ACTIVE, "members": members, "membership_sha256": digest(members)}

    def envelope(self, scopes):
        body = {"format": "geography-scope-snapshot-v1", "scopes": scopes}
        return {**body, "snapshot_sha256": digest(body)}

    def report(self, scopes=None, *, reviewed=True, **kwargs):
        inputs = dict(scope_snapshot=self.envelope(scopes if scopes is not None else [self.scope()]),
                      cutoff_utc="2026-10-01T00:00:00Z", **kwargs)
        result = build_geography_report(self.path, **inputs)
        if reviewed:
            inputs["reconciliation"] = {"reference": "fixture-reviewed-inputs", "source_sha256": result["source_sha256"]}
            result = build_geography_report(self.path, **inputs)
        return result

    def row(self, report):
        return next(r for r in report["reviewer_scopes"] if r["reviewer_id"] == 1)

    def test_population_boundaries_and_ceiling_minimum_math(self):
        migrate(self.path, apply=True)
        for count, required in [(0, []), (9, []), (10, [5, 5, 8, 10]),
                                (13, [5, 7, 10, 13]), (99, [25, 50, 75, 99]), (100, [10, 25, 50, 75])]:
            with self.subTest(count=count):
                row = self.row(self.report([self.scope(count)]))
                self.assertEqual(count, row["D"])
                self.assertEqual(required, [t["required_count"] for t in row["required_counts"]])
                self.assertEqual(count >= 10, row["eligible"])

    def test_coverage_satisfied_is_never_issuance_ready(self):
        for n in range(1, 6):
            self.review(n)
        row = self.row(self.report())
        self.assertTrue(row["coverage_satisfied"])
        self.assertFalse(row["issuance_ready"])
        self.assertIn("trigger_and_earned_date_policy_unapproved", row["issuance_blockers"])
        self.assertFalse(row["unresolved"])

    def test_duplicate_members_and_repeated_reviews_count_once(self):
        self.review(1)
        self.review(20, stop=1)
        scope = self.scope()
        scope["members"].append(dict(scope["members"][0]))
        scope["membership_sha256"] = digest(scope["members"])
        row = self.row(self.report([scope]))
        self.assertEqual((10, 1), (row["D"], row["N"]))
        self.assertEqual(1, row["witnesses"][0]["assignment_id"])

    def test_independent_overlapping_dimensions(self):
        self.review(1)
        scopes = [self.scope(dimension=d, key=d + ":fixture")
                  for d in ("dc_anc", "dc_ward", "municipality", "county", "state")]
        report = self.report(scopes)
        self.assertEqual(5, len(report["scopes"]))
        self.assertEqual([(10, 1)] * 5, [(r["D"], r["N"]) for r in report["reviewer_scopes"] if r["reviewer_id"] == 1])

    def test_exact_active_predicate_snapshot_not_current_database(self):
        self.review(1)
        self.review(2)
        self.sql("UPDATE stop_gtfs_status SET current_gtfs=0")
        scope = self.scope()
        scope["members"][1]["current_gtfs"] = 0
        scope["members"][2]["current_gtfs"] = 2
        scope["membership_sha256"] = digest(scope["members"])
        row = self.row(self.report([scope]))
        self.assertEqual((8, 1), (row["D"], row["N"]))
        self.assertEqual([1], row["counted_physical_stop_ids"])

    def test_strings_booleans_and_alternate_active_predicates_rejected(self):
        self.review(1)
        for value in (True, "1", None):
            with self.subTest(value=value):
                scope = self.scope()
                scope["members"][0]["current_gtfs"] = value
                scope["membership_sha256"] = digest(scope["members"])
                self.assertIn("invalid_member", self.row(self.report([scope]))["quality_blockers"])
        scope = self.scope()
        scope["active_membership_predicate"] = "current_gtfs != 0"
        self.assertIn("invalid_active_membership_predicate", self.row(self.report([scope]))["quality_blockers"])

    def test_missing_scope_fields_and_uncertified_scope_are_unresolved(self):
        self.review(1)
        for field in ("dimension", "canonical_geography_id", "scope_key", "scope_version", "captured_at_utc",
                      "effective_at_utc", "source_provenance", "boundary_provenance", "members", "certification"):
            with self.subTest(field=field):
                scope = self.scope()
                del scope[field]
                row = self.row(self.report([scope]))
                self.assertTrue(row["unresolved"])
                self.assertIsNone(row["coverage_satisfied"])

    def test_ambiguous_snapshot_members_and_duplicate_scope_identity(self):
        self.review(1)
        scope = self.scope()
        scope["members"].append({"physical_stop_id": 1, "current_gtfs": 0})
        scope["membership_sha256"] = digest(scope["members"])
        self.assertIn("ambiguous_member_status", self.row(self.report([scope]))["quality_blockers"])
        report = self.report([self.scope(), self.scope()])
        self.assertTrue(all(r["unresolved"] for r in report["reviewer_scopes"]))

    def test_missing_ledger_and_uncaptured_evidence(self):
        self.review(1, captured=False)
        report = self.report()
        self.assertIn("recognition_completions_missing", report["quality_blockers"])
        row = self.row(report)
        self.assertEqual(0, row["N"])
        self.assertEqual(1, len(row["uncaptured_evidence"]))
        migrate(self.path, apply=True)
        report = self.report()
        self.assertNotIn("recognition_completions_missing", report["quality_blockers"])
        self.assertIn("uncaptured_qualifying_evidence", self.row(report)["quality_blockers"])

    def test_source_ledger_discrepancies_are_not_counted(self):
        self.review(1)
        self.sql("UPDATE stop_review_assignments SET completed_at='2026-09-24T12:00:00Z'")
        report = self.report()
        self.assertEqual(0, self.row(report)["N"])
        self.assertEqual("source_ledger_discrepancy", report["exclusions"][0]["reason"])

    def test_changed_source_owner_also_blocks_original_ledger_owner(self):
        self.review(1)
        self.sql("UPDATE stop_review_assignments SET reviewer_id=2")
        self.sql("UPDATE stop_observations SET reviewer_id=2")
        report = self.report()
        self.assertTrue(all(r["unresolved"] for r in report["reviewer_scopes"]))
        self.assertIn("source_ledger_discrepancies_present", self.row(report)["quality_blockers"])

    def test_qualification_identity_and_duplicate_observation_rejections(self):
        self.review(1)
        self.sql("INSERT INTO stop_observations VALUES(20,1,1,1,'community_review')")
        report = self.report()
        self.assertEqual("ambiguous_community_evidence", report["exclusions"][0]["reason"])
        self.assertEqual(0, self.row(report)["N"])

    def test_cutoff_and_permanent_timestamp_policy(self):
        for cutoff in ("2026-10-01 00:00:00", "2026-10-01T00:00:00.1Z", "2026-10-01T01:00:00+01:00", "invalid"):
            with self.subTest(cutoff=cutoff), self.assertRaises(ValueError):
                build_geography_report(self.path, scope_snapshot=self.envelope([self.scope()]), cutoff_utc=cutoff)
        for n, time in enumerate((None, "2026-09-25 12:00:00", "2026-09-25T12:00:00.1Z"), 1):
            self.review(n, captured=False, timestamp=time)
        report = self.report()
        self.assertEqual({"missing_completion_time", "unattested_naive_timestamp", "fractional_timestamp_policy_unresolved"},
                         {e["reason"] for e in report["exclusions"]})

    def test_ledger_timestamp_provenance_reused_without_invention(self):
        self.review(1, timestamp="2026-09-25 12:00:00")
        fact = self.row(self.report())["witnesses"][0]
        self.assertEqual("sqlite_current_timestamp_utc:fixture-writer", fact["timestamp_provenance"])

    def test_identity_split_merge_and_unattributed_events(self):
        self.review(1)
        self.sql("INSERT INTO physical_stop_identity_events VALUES(1,'split')")
        self.sql("INSERT INTO physical_stop_identity_edges VALUES(1,1,101)")
        report = self.report([self.scope(), self.scope(101, key="county:fixture", dimension="county")])
        self.assertTrue(all("physical_identity_changed" in s["quality_blockers"] for s in report["scopes"]))
        self.assertTrue(all(r["N"] == 1 for r in report["reviewer_scopes"] if r["reviewer_id"] == 1))
        self.sql("INSERT INTO physical_stop_identity_events VALUES(2,'movement')")
        self.assertIn("unattributed_identity_event", self.report()["quality_blockers"])

    def test_snapshot_membership_denominator_source_identity_changes(self):
        self.review(1)
        prior = self.report([self.scope(11)])
        report = self.report(previous_report=prior)
        issues = self.row(report)["quality_blockers"]
        for reason in ("scope_snapshot_changed", "membership_changed", "denominator_changed", "denominator_shrank"):
            self.assertIn(reason, issues)
        self.assertIn("prior_changes_require_review", self.report(previous_report=report)["changes"])
        self.sql("UPDATE stop_observations SET reviewer_id=2")
        self.sql("INSERT INTO physical_stop_identity_events VALUES(2,'merge')")
        report = self.report(previous_report=prior)
        self.assertIn("source_sha256_changed", report["changes"])
        self.assertIn("identity_sha256_changed", report["changes"])

    def test_hash_validation_and_snapshot_timestamp(self):
        self.review(1)
        scope = self.scope()
        scope["membership_sha256"] = "x" * 64
        self.assertIn("membership_hash_mismatch", self.row(self.report([scope]))["quality_blockers"])
        snapshot = self.envelope([self.scope()])
        snapshot["snapshot_sha256"] = "bad"
        report = build_geography_report(self.path, scope_snapshot=snapshot, cutoff_utc="2026-10-01T00:00:00Z")
        self.assertIn("snapshot_hash_mismatch", report["quality_blockers"])
        scope["captured_at_utc"] = "2026-10-02T00:00:00Z"
        self.assertIn("snapshot_after_evaluation_cutoff", self.row(self.report([scope]))["quality_blockers"])
        prior = self.report()
        prior["source_sha256"] = "bad"
        with self.assertRaises(ValueError):
            self.report(previous_report=prior)

    def test_discovery_is_not_certification_or_snapshot_substitution(self):
        self.review(1)
        report = self.report([])
        self.assertIn("no_explicit_scopes", report["quality_blockers"])
        self.assertEqual([], report["reviewer_scopes"])
        self.assertEqual(set(("dc_anc", "dc_ward", "municipality", "county", "state")),
                         {s["dimension"] for s in report["discovered_current_scopes"]})
        self.assertTrue(all(not s["certified"] for s in report["discovered_current_scopes"]))
        self.sql("INSERT INTO stop_jurisdiction VALUES(3,'VA','Fairfax','Fairfax',NULL,NULL)")
        report = self.report([])
        self.assertEqual(1, sum(s["dimension"] == "state" and s["label"] == "VA"
                                for s in report["discovered_current_scopes"]))

    def test_missing_geography_and_identity_sources_are_not_invented(self):
        self.review(1)
        self.sql("DROP TABLE stop_jurisdiction")
        self.sql("DROP TABLE physical_stop_identity_events")
        report = self.report()
        self.assertEqual([], report["discovered_current_scopes"])
        self.assertIn("identity_history_incomplete", report["quality_blockers"])

    def test_reconciliation_is_explicit_and_hash_bound(self):
        self.review(1)
        self.assertIn("historical_reconciliation_missing", self.report(reviewed=False)["quality_blockers"])
        report = build_geography_report(self.path, scope_snapshot=self.envelope([self.scope()]),
            cutoff_utc="2026-10-01T00:00:00Z", reconciliation={"reference": "fixture", "source_sha256": "a" * 64})
        self.assertIn("historical_reconciliation_mismatch", report["quality_blockers"])
        self.assertFalse(report["issuance_ready"])

    def test_orphan_evidence_and_missing_snapshot_identity(self):
        self.review(1)
        self.sql("INSERT INTO stop_observations VALUES(2,99,1,1,'community_review')")
        self.assertIn("orphan_community_evidence", self.report()["quality_blockers"])
        scope = self.scope()
        scope["members"].append({"physical_stop_id": 999, "current_gtfs": 1})
        scope["membership_sha256"] = digest(scope["members"])
        self.assertIn("missing_physical_identity", self.row(self.report([scope]))["quality_blockers"])

    def test_threshold_configuration_is_report_only(self):
        migrate(self.path, apply=True)
        config = deepcopy(DEFAULT_THRESHOLDS)
        config["small_percentages"] = [30, 60]
        row = self.row(self.report(thresholds=config))
        self.assertEqual([5, 6], [t["required_count"] for t in row["required_counts"]])
        with self.assertRaises(ValueError):
            self.report(thresholds={})

    def test_deterministic_read_only_and_no_other_recognition_changes(self):
        self.review(1)
        before = hashlib.sha256(self.path.read_bytes()).hexdigest()
        def check(conn, *args, **kwargs):
            self.assertTrue(conn.in_transaction)
            self.assertEqual(1, conn.execute("PRAGMA query_only").fetchone()[0])
            with self.assertRaises(sqlite3.OperationalError):
                conn.execute("DELETE FROM recognition_jobs")
            return qualify(conn, *args, **kwargs)
        with patch("src.review.recognition.geography.qualify", side_effect=check):
            first = self.report()
        self.assertEqual(canonical(first), canonical(self.report()))
        self.assertEqual(first["report_sha256"], digest({k: v for k, v in first.items() if k != "report_sha256"}))
        self.assertEqual(before, hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.assertEqual([(0,)], self.sql("SELECT count(*) FROM recognition_awards"))
        self.assertEqual([('pending', 0)], self.sql("SELECT state,attempts FROM recognition_jobs"))


if __name__ == "__main__":
    unittest.main()
