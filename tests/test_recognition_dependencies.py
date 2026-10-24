"""Dependency validation against freshly created disposable fixtures only."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import sqlite3
import unittest
from unittest.mock import patch

from src.review.recognition import dependencies, events, permanent
from src.review.recognition.authorization import AuthorizationError
from src.review.recognition.qualification import Quarantined
from src.review.recognition.rules import canonical, digest
from src.review.recognition.schema import connection, TABLES as EXPLORER_TABLES
from tests import test_recognition_events as fixture
from tests.recognition_authorization_fixture import approval


class DependencyTests(unittest.TestCase):
    setUp = fixture.EventTests.setUp
    install = fixture.EventTests.install
    sql = fixture.EventTests.sql
    review = fixture.EventTests.review
    first = fixture.EventTests.first
    geo = fixture.EventTests.geo
    scope = fixture.EventTests.scope
    envelope = fixture.EventTests.envelope
    request = fixture.EventTests.request
    create = fixture.EventTests.create
    freeze = fixture.EventTests.freeze

    def frozen(self, geography=False, parent=None):
        return self.freeze(self.create(self.request(geography=geography, parent=parent))["preparation_id"])

    def check(self, frozen, **kwargs):
        with connection(self.path) as conn:
            conn.execute("BEGIN")
            return dependencies.recheck(conn, frozen["event"]["event_id"], **kwargs)

    def record(self, frozen, result, **kwargs):
        event_id = frozen["event"]["event_id"]
        subject = dependencies.recording_subject(event_id, result)
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            recorded = dependencies.record_validation(conn, event_id, result, **kwargs,
                **approval(self.path, **events.binding("record_event_state", subject)))
            conn.commit()
            return recorded

    def test_unchanged_both_families_and_exact_inventory(self):
        for geography in (False, True):
            with self.subTest(geography=geography):
                frozen = self.frozen(geography)
                self.assertEqual({"state": "READY", "reasons": []}, self.check(frozen))
                observed = frozen["preparation"]["dependencies"]["observations"]
                self.assertEqual([1], observed["assignment_inventory"])
                self.assertEqual([{"id": 1, "stop_id": 1, "reviewer_id": 1, "status": "completed",
                                   "completed_at": "2026-09-25T12:00:00Z"}], observed["review_evidence"]["assignments"])
                self.assertEqual("recognition-dependencies-v1", frozen["preparation"]["dependencies"]["format"])

    def test_new_competitor_and_population_boundary(self):
        frozen = self.frozen()
        self.review(2, stop=1, owner=2, captured=False, timestamp="2026-09-24T12:00:00Z")
        result = self.check(frozen)
        self.assertEqual("STALE", result["state"])
        self.assertIn("assignment_inventory_changed", result["reasons"])
        self.assertIn("review_evidence_changed", result["reasons"])

    def test_inventory_includes_new_excluded_assignments(self):
        frozen = self.frozen()
        self.sql("INSERT INTO stop_review_assignments VALUES(2,2,2,'pending',NULL)")
        self.assertEqual("STALE", self.check(frozen)["state"])

    def test_relevant_evidence_changed_both_families(self):
        first, geo = self.frozen(), self.frozen(True)
        self.sql("UPDATE stop_review_assignments SET completed_at='2026-09-24T12:00:00Z' WHERE id=1")
        for frozen in (first, geo):
            result = self.check(frozen)
            self.assertEqual("STALE", result["state"])
            self.assertIn("review_evidence_changed", result["reasons"])

    def test_identity_and_current_active_changes(self):
        first, geo = self.frozen(), self.frozen(True)
        self.sql("INSERT INTO physical_stop_identity_state VALUES(1,'retired')")
        for frozen in (first, geo):
            self.assertIn("identity_changed", self.check(frozen)["reasons"])
        self.sql("UPDATE stop_gtfs_status SET current_gtfs=0 WHERE physical_stop_id=1")
        self.assertIn("current_active_changed", self.check(geo)["reasons"])
        self.assertNotIn("current_active_changed", self.check(first)["reasons"])

    def test_policy_change_is_stale_not_archived_event_corruption(self):
        frozen = self.frozen()
        updated = deepcopy(permanent.DEFINITIONS)
        updated["first_look"]["rule_key"] = "first_look:v2"
        with patch.object(permanent, "DEFINITIONS", updated):
            self.assertEqual({"state": "STALE", "reasons": ["policy_changed"]}, self.check(frozen))
            result = self.record(frozen, self.check(frozen))
            self.assertEqual("STALE", result["state"])
        self.assertEqual("STALE", self.check(frozen)["state"])

    def test_valid_replacement_scope_is_stale_missing_certification_invalid(self):
        frozen = self.frozen(True)
        replacement = deepcopy(frozen["preparation"]["manifest"]["inputs"]["scope_snapshot"])
        scope = replacement["scopes"][0]
        scope["members"].append({"physical_stop_id": 11, "current_gtfs": 1})
        scope["membership_sha256"] = digest(scope["members"])
        replacement["snapshot_sha256"] = digest({k: v for k, v in replacement.items() if k != "snapshot_sha256"})
        result = self.check(frozen, current_scope_snapshot=replacement)
        self.assertEqual({"state": "STALE", "reasons": ["scope_snapshot_changed"]}, result)
        scope["certification"]["approved"] = False
        replacement["snapshot_sha256"] = digest({k: v for k, v in replacement.items() if k != "snapshot_sha256"})
        self.assertEqual("INVALID", self.check(frozen, current_scope_snapshot=replacement)["state"])
        scope["certification"]["approved"] = True
        scope["identity_review_reference"] = " "
        replacement["snapshot_sha256"] = digest({k: v for k, v in replacement.items() if k != "snapshot_sha256"})
        self.assertEqual({"state": "INVALID", "reasons": ["missing_scope_prerequisite"]},
                         self.check(frozen, current_scope_snapshot=replacement))

    def test_geography_policy_change_preserves_archive_and_marks_stale(self):
        frozen = self.frozen(True)
        from src.review.recognition import geography
        thresholds = deepcopy(geography.DEFAULT_THRESHOLDS)
        thresholds["small_minimum"] = 6
        with patch.object(geography, "DEFAULT_THRESHOLDS", thresholds):
            self.assertEqual({"state": "STALE", "reasons": ["policy_changed"]}, self.check(frozen))
        with patch.object(geography, "ACTIVE", "future-versioned-active-predicate"):
            self.assertEqual({"state": "STALE", "reasons": ["policy_changed"]}, self.check(frozen))

    def test_invalid_is_terminal_even_after_dependency_repair(self):
        frozen = self.frozen()
        self.sql("DELETE FROM stop_observations WHERE id=1")
        self.record(frozen, self.check(frozen))
        self.sql("INSERT INTO stop_observations VALUES(1,1,1,1,'community_review')")
        self.assertEqual({"state": "INVALID", "reasons": ["previously_invalid"]}, self.check(frozen))

    def test_unrelated_review_fields_and_noncommunity_evidence_are_ignored(self):
        first, geo = self.frozen(), self.frozen(True)
        self.sql("ALTER TABLE stop_review_assignments ADD COLUMN reviewer_notes TEXT")
        self.sql("UPDATE stop_review_assignments SET reviewer_notes='unrelated presentation metadata'")
        self.sql("INSERT INTO stop_observations VALUES(2,1,1,1,'other_source')")
        for frozen in (first, geo):
            self.assertEqual("READY", self.check(frozen)["state"])

    def test_unrelated_geography_discovery_and_nonmember_activity_are_ignored(self):
        frozen = self.frozen(True)
        self.sql("UPDATE stop_jurisdiction SET dc_anc='changed-discovery-label'")
        self.sql("UPDATE stop_gtfs_status SET current_gtfs=0 WHERE physical_stop_id=101")
        self.assertEqual("READY", self.check(frozen)["state"])

    def test_missing_required_evidence_is_invalid(self):
        frozen = self.frozen()
        self.sql("DELETE FROM stop_observations WHERE id=1")
        self.assertEqual({"state": "INVALID", "reasons": ["missing_required_community_evidence"]}, self.check(frozen))
        self.assertEqual("INVALID", self.record(frozen, self.check(frozen))["state"])

    def test_missing_schema_is_invalid_not_a_temporary_failure(self):
        frozen = self.frozen()
        self.sql("ALTER TABLE stop_observations RENAME TO removed_observations")
        self.assertEqual({"state": "INVALID", "reasons": ["missing_or_unsupported_schema:stop_observations"]},
                         self.check(frozen))

    def test_malformed_evidence_and_unsupported_rule_are_invalid(self):
        frozen = self.frozen()
        self.sql("UPDATE stop_review_assignments SET completed_at='invalid-time'")
        self.assertEqual({"state": "INVALID", "reasons": ["invalid_required_qualification:invalid_completion_time"]},
                         self.check(frozen))
        self.sql("UPDATE stop_review_assignments SET completed_at='2026-09-25T12:00:00Z'")
        with patch.object(permanent, "DEFINITIONS", {}):
            self.assertEqual({"state": "INVALID", "reasons": ["unsupported_rule"]}, self.check(frozen))

    def test_relevant_permanent_claim_changes_are_stale(self):
        from tests.recognition_authorization_fixture import migrate_private, finalize
        from src.review.recognition import RecognitionGate
        migrate_private(self.path, apply=True)
        frozen = self.frozen()
        manifest = frozen["preparation"]["manifest"]
        finalize(self.path, manifest, manifest_sha256=digest(manifest),
                 authorization_reference="synthetic-authorization", gate=RecognitionGate(issuance=True))
        self.assertEqual({"state": "STALE", "reasons": ["permanent_records_changed"]}, self.check(frozen))

    def test_target_mismatch_and_missing_transaction_fail_closed(self):
        frozen = self.frozen()
        from dataclasses import replace
        from src.review.recognition.authorization import target_identity
        actual = target_identity(self.path)
        with patch.object(dependencies, "target_identity", return_value=replace(actual, inode=actual.inode + 1)):
            self.assertEqual({"state": "INVALID", "reasons": ["target_observation_mismatch"]}, self.check(frozen))
        with connection(self.path) as conn:
            self.assertEqual({"state": "VERIFICATION_FAILURE", "reasons": ["transaction_required"]},
                             dependencies.recheck(conn, frozen["event"]["event_id"]))

    def test_read_snapshot_does_not_promise_future_readiness(self):
        self.sql("PRAGMA journal_mode=WAL")
        frozen = self.frozen()
        with connection(self.path) as conn:
            conn.execute("BEGIN")
            self.assertEqual("READY", dependencies.recheck(conn, frozen["event"]["event_id"])["state"])
            # A separate committed writer may change data while this WAL reader
            # legitimately continues to see its older snapshot.
            self.sql("UPDATE stop_review_assignments SET completed_at='2026-09-24T12:00:00Z'")
            self.assertEqual("READY", dependencies.recheck(conn, frozen["event"]["event_id"])["state"])
        self.assertEqual("STALE", self.check(frozen)["state"])

    def test_temporary_read_failure_does_not_record_a_decision(self):
        frozen = self.frozen()
        for error in (sqlite3.OperationalError("database is locked"), OSError("temporary target inspection")):
            with patch.object(dependencies, "_observe", side_effect=error):
                result = self.check(frozen)
                self.assertEqual("VERIFICATION_FAILURE", result["state"])
                with self.assertRaises(Quarantined):
                    self.record(frozen, result)
        self.assertEqual("READY", self.check(frozen)["state"])
        self.assertEqual(1, self.sql("SELECT COUNT(*) FROM recognition_event_history")[0][0])

    def test_immutable_dependency_binding_and_tampering(self):
        frozen = self.frozen()
        with self.assertRaises(sqlite3.IntegrityError):
            self.sql("UPDATE recognition_preparations SET body_json='{}'")
        trigger = "recognition_preparations_immutable_update"
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(f"DROP TRIGGER {trigger}")
            body = deepcopy(frozen["preparation"])
            body["dependencies"]["observations"]["assignment_inventory"] = []
            conn.execute("UPDATE recognition_preparations SET body_json=?,body_sha256=?", (canonical(body), digest(body)))
            from src.review.recognition.event_schema import definitions
            conn.execute(definitions()[trigger])
            result = dependencies.recheck(conn, frozen["event"]["event_id"])
            self.assertEqual("INVALID", result["state"])
            self.assertIn("corrupted_dependency_manifest", result["reasons"])
            conn.rollback()

    def test_stale_cannot_refresh_revision_gets_new_dependencies(self):
        frozen = self.frozen()
        original = deepcopy(frozen)
        self.review(2)
        result = self.check(frozen)
        recorded = self.record(frozen, result)
        self.assertEqual("STALE", recorded["state"])
        revised = self.frozen(parent=frozen["event"]["event_id"])
        self.assertEqual("READY", self.check(revised)["state"])
        self.assertNotEqual(original["event"]["event_id"], revised["event"]["event_id"])
        self.assertEqual(original["preparation"], recorded["preparation"])
        self.assertEqual(original["event"], recorded["event"])
        self.assertNotEqual(original["preparation"]["dependencies"], revised["preparation"]["dependencies"])
        self.assertEqual("STALE", self.freeze(original["preparation"]["preparation_id"])["state"])

    def test_concurrent_state_recording_and_changed_decision_fail_closed(self):
        frozen = self.frozen()
        self.sql("UPDATE stop_review_assignments SET completed_at='2026-09-24T12:00:00Z'")
        expected = self.check(frozen)
        def record_once(_):
            try:
                return self.record(frozen, expected)["state"]
            except Quarantined as error:
                return str(error)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(record_once, range(2)))
        self.assertEqual(["STALE", "validation_result_changed"], sorted(results))
        self.assertEqual(2, self.sql("SELECT COUNT(*) FROM recognition_event_history")[0][0])

    def test_changed_since_check_cannot_persist_old_result(self):
        frozen = self.frozen()
        self.sql("UPDATE stop_review_assignments SET completed_at='2026-09-24T12:00:00Z'")
        expected = self.check(frozen)
        self.sql("DELETE FROM stop_observations WHERE id=1")
        with self.assertRaisesRegex(Quarantined, "validation_result_changed"):
            self.record(frozen, expected)
        self.assertEqual(1, self.sql("SELECT COUNT(*) FROM recognition_event_history")[0][0])

    def test_existing_eligibility_explorer_and_read_only_validation_unchanged(self):
        expected_first, expected_geo = self.first(), self.geo()
        first, geo = self.frozen(), self.frozen(True)
        before = {table: self.sql(f"SELECT * FROM {table}") for table in EXPLORER_TABLES}
        self.assertEqual(expected_first, first["preparation"]["manifest"])
        self.assertEqual(expected_geo, geo["preparation"]["manifest"])
        self.check(first)
        self.check(geo)
        self.assertEqual(before, {table: self.sql(f"SELECT * FROM {table}") for table in EXPLORER_TABLES})
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            with self.assertRaises(AuthorizationError):
                dependencies.record_validation(conn, first["event"]["event_id"],
                    {"state": "STALE", "reasons": ["invented"]})


if __name__ == "__main__":
    unittest.main()
