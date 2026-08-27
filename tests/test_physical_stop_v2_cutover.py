import json
import sqlite3
import unittest
import uuid
from contextlib import ExitStack, closing
from pathlib import Path
from unittest.mock import patch

from scripts.active import migrate_physical_stops_v2 as orchestrator
from scripts.active import reset_v2_test_contributions as reset_module
from scripts.active.migrate_physical_stops_v2 import DEFAULT_PRODUCTION_DB, require_safe_target
from src.processing import physical_stop_v2_cutover as cutover
from src.processing.physical_stop_v2_proposal import manifest_sha256


def fixture(testcase):
    conn = sqlite3.connect(":memory:")
    testcase.addCleanup(conn.close)
    conn.executescript("""
      PRAGMA foreign_keys=ON;
      CREATE TABLE physical_stops(id INTEGER PRIMARY KEY,latitude REAL NOT NULL,
        longitude REAL NOT NULL,primary_name TEXT,member_count INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP);
      CREATE TABLE bus_stops(id INTEGER PRIMARY KEY,external_stop_id TEXT,
        latitude REAL,longitude REAL,stop_name TEXT);
      CREATE TABLE physical_stop_members(physical_stop_id INTEGER,bus_stop_id INTEGER UNIQUE,
        PRIMARY KEY(physical_stop_id,bus_stop_id));
      INSERT INTO physical_stops(id,latitude,longitude,primary_name,member_count) VALUES
        (1,38.9,-77,'parent',2),(406,1,1,'manual',0),(2231,1,1,'manual',0),
        (4468,1,1,'manual',0),(5196,1,1,'manual',0),(6080,1,1,'manual',0);
      INSERT INTO bus_stops VALUES(10,'A',38.9,-77,'A'),(11,'B',38.91,-77.01,'B');
      INSERT INTO physical_stop_members VALUES(1,10),(1,11);
    """)
    return conn


def manifest():
    return {
        "proposal_version": "physical-stop-v2-proposal-1",
        "generated_from": {}, "automatic_parent_count": 1, "child_group_count": 2,
        "manual_exceptions": [406, 2231, 4468, 5196, 6080],
        "parents": [{
            "predecessor_physical_stop_id": 1,
            "classification": "ordinary_curb_split", "reason_flags": ["fixture"],
            "old_name": "parent", "old_coordinates": [38.9, -77],
            "members": [{"bus_stop_id": 10}, {"bus_stop_id": 11}],
            "proposed_children": [
                {"member_bus_stop_ids": [10], "proposed_coordinates": [38.9, -77],
                 "proposed_name": "A"},
                {"member_bus_stop_ids": [11], "proposed_coordinates": [38.91, -77.01],
                 "proposed_name": "B"},
            ],
        }],
    }


class CutoverTests(unittest.TestCase):
    def patched_gate(self, value):
        return patch.multiple(cutover, EXPECTED_PARENT_COUNT=1, EXPECTED_CHILD_COUNT=2,
                              EXPECTED_SHA256=manifest_sha256(value))

    def test_default_production_database_is_refused(self):
        with self.assertRaises(ValueError):
            require_safe_target(DEFAULT_PRODUCTION_DB)

    def test_split_is_persistent_lineaged_and_second_run_is_noop(self):
        conn, proposal = fixture(self), manifest()
        with self.patched_gate(proposal):
            result = cutover.apply_reviewed_proposal(conn, proposal, confirm=True,
                                                     now="2026-01-01T00:00:00Z")
            self.assertEqual((1, 2), (result["retired_parents"], result["successors_created"]))
            self.assertEqual([6081, 6082], result["successor_ids"])
            self.assertEqual([(6081, 10), (6082, 11)], conn.execute(
                "SELECT physical_stop_id,bus_stop_id FROM physical_stop_members ORDER BY 1").fetchall())
            self.assertEqual("retired", conn.execute(
                "SELECT identity_status FROM physical_stop_identity_state WHERE physical_stop_id=1").fetchone()[0])
            self.assertEqual(2, conn.execute("SELECT COUNT(*) FROM physical_stop_identity_edges").fetchone()[0])
            second = cutover.apply_reviewed_proposal(conn, confirm=True)
            self.assertTrue(second["already_applied"])
            self.assertEqual((8, 6082), conn.execute(
                "SELECT COUNT(*),MAX(id) FROM physical_stops").fetchone())

    def test_failure_rolls_back_identity_mutation(self):
        conn, proposal = fixture(self), manifest()
        proposal["parents"][0]["proposed_children"][1]["member_bus_stop_ids"] = [999]
        with self.patched_gate(proposal), self.assertRaises(RuntimeError):
            cutover.apply_reviewed_proposal(conn, proposal, confirm=True)
        self.assertEqual([(1, 10), (1, 11)], conn.execute(
            "SELECT physical_stop_id,bus_stop_id FROM physical_stop_members ORDER BY 2").fetchall())
        self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM physical_stop_identity_events").fetchone()[0])

    def test_manual_exceptions_are_explicit(self):
        conn, proposal = fixture(self), manifest()
        with self.patched_gate(proposal):
            cutover.apply_reviewed_proposal(conn, proposal, confirm=True)
        self.assertEqual(5, conn.execute("""SELECT COUNT(*) FROM physical_stop_identity_state
            WHERE identity_status='manual_exception'""").fetchone()[0])


class ProductionSafetyTests(unittest.TestCase):
    def setUp(self):
        workspace_tmp = Path(__file__).resolve().parents[1] / ".tmp"
        workspace_tmp.mkdir(exist_ok=True)
        token = uuid.uuid4().hex
        self.database = workspace_tmp / f"protected-default-{token}.db"
        self.report = workspace_tmp / f"checkpoint-{token}.json"
        self.addCleanup(lambda: self.database.unlink(missing_ok=True))
        self.addCleanup(lambda: self.report.unlink(missing_ok=True))
        self.addCleanup(lambda: self.report.with_name(self.report.name + ".tmp").unlink(missing_ok=True))
        with closing(sqlite3.connect(self.database)) as conn, conn:
            conn.execute("CREATE TABLE community_reviewers(id INTEGER PRIMARY KEY)")
            conn.execute("INSERT INTO community_reviewers VALUES(1)")
            conn.execute("CREATE TABLE stop_gtfs_status(physical_stop_id INTEGER,current_gtfs INTEGER)")
            conn.execute("INSERT INTO stop_gtfs_status VALUES(1,1)")

    def patches(self, *, apply_side_effect=None, proposal_side_effect=None):
        proposal = manifest()
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(orchestrator, "DEFAULT_PRODUCTION_DB", self.database.resolve()))
        stack.enter_context(patch.object(reset_module, "DEFAULT_DATABASE", self.database.resolve()))
        stack.enter_context(patch.object(orchestrator, "cutover_state", return_value="pristine"))
        stack.enter_context(patch.object(
            orchestrator, "generate_manifest",
            side_effect=proposal_side_effect, return_value=proposal))
        stack.enter_context(patch.object(orchestrator, "validate_proposal_gate", return_value={}))
        stack.enter_context(patch.object(orchestrator, "preflight_manifest_attribution", return_value={}))
        stack.enter_context(patch.object(orchestrator, "preflight_manifest_geography", return_value={
            "coverage": {}, "parent_child_differences": [], "child_geography_crossings": []}))
        stack.enter_context(patch.object(orchestrator, "table_counts", return_value={"community_reviewers": 1}))
        stack.enter_context(patch.object(orchestrator, "heading_audit", return_value={}))
        stack.enter_context(patch.object(orchestrator, "migrate_review_schema"))
        stack.enter_context(patch.object(
            orchestrator, "apply_reviewed_proposal", side_effect=apply_side_effect,
            return_value={"already_applied": False, "retired_parents": 1,
                          "successors_created": 2, "successor_ids": [2, 3]}))
        stack.enter_context(patch.object(orchestrator, "recompute_geography", return_value={}))
        stack.enter_context(patch.object(orchestrator, "apply_manifest_attribution", return_value={}))
        stack.enter_context(patch.object(orchestrator, "validate_cutover", return_value={}))
        stack.enter_context(patch.object(orchestrator, "rebuild_products"))
        stack.enter_context(patch.object(orchestrator, "validate_database", return_value={
            "integrity_check": "ok", "foreign_key_violations": 0,
            "active_retired": 0, "retired_derived_rows": {}}))
        stack.enter_context(patch.object(orchestrator, "acceptance_results", return_value={}))
        return stack

    def reviewer_count(self):
        with closing(sqlite3.connect(self.database)) as conn:
            return conn.execute("SELECT COUNT(*) FROM community_reviewers").fetchone()[0]

    def test_exact_protected_path_authorizes_nested_reset_only_when_explicit(self):
        self.patches()
        with self.assertRaises(ValueError):
            orchestrator.run(self.database, apply=True)
        self.assertEqual(1, self.reviewer_count())

        result = orchestrator.run(
            self.database, apply=True, allow_production=True, report_path=self.report)
        self.assertEqual("complete", result["status"])
        self.assertEqual(0, self.reviewer_count())
        self.assertEqual("complete", result["phases"]["test_contributions_reset"])
        with patch.object(orchestrator, "cutover_state", return_value="applied"):
            second = orchestrator.run(
                self.database, apply=True, allow_production=True,
                report_path=self.report)
        self.assertEqual("already_complete", second["phases"]["identities_applied"])
        self.assertEqual("not_required", second["phases"]["test_contributions_reset"])
        with patch.object(orchestrator, "cutover_state", return_value="applied"), \
                patch.object(orchestrator, "rebuild_products",
                             side_effect=RuntimeError("later rebuild failed")):
            with self.assertRaisesRegex(RuntimeError, "later rebuild failed"):
                orchestrator.run(
                    self.database, apply=True, allow_production=True,
                    report_path=self.report)
        failed = json.loads(self.report.read_text(encoding="utf-8"))
        self.assertEqual("failed", failed["status"])
        self.assertEqual("derived_rebuild_completed", failed["failed_phase"])
        self.assertNotEqual("complete", failed["phases"]["derived_rebuild_completed"])

    def test_standalone_reset_keeps_independent_default_database_guard(self):
        with closing(sqlite3.connect(self.database)) as conn, conn:
            with patch.object(reset_module, "DEFAULT_DATABASE", self.database.resolve()):
                with self.assertRaises(ValueError):
                    reset_module.reset_test_contributions(
                        conn, confirmation=reset_module.CONFIRMATION,
                        database_path=self.database)
                reset_module.reset_test_contributions(
                    conn, confirmation=reset_module.CONFIRMATION,
                    database_path=self.database, allow_default=True,
                    _cutover_authorization=reset_module._CUTOVER_AUTHORIZATION)
        self.assertEqual(0, self.reviewer_count())

    def test_identity_checkpoint_survives_failure_and_requires_rollback(self):
        def commit_identity(conn, *_args, **_kwargs):
            conn.execute("CREATE TABLE committed_identity_marker(value INTEGER)")
            conn.execute("INSERT INTO committed_identity_marker VALUES(1)")
            conn.commit()
            return {"already_applied": False, "retired_parents": 1,
                    "successors_created": 2, "successor_ids": [2, 3]}

        self.patches(apply_side_effect=commit_identity)
        with self.assertRaisesRegex(RuntimeError, "injected failure"):
            orchestrator.run(
                self.database, apply=True, allow_production=True,
                report_path=self.report, failure_after_phase="identities_applied")
        report = json.loads(self.report.read_text(encoding="utf-8"))
        self.assertEqual("failed", report["status"])
        self.assertEqual("complete", report["phases"]["identities_applied"])
        self.assertEqual("test_contributions_reset", report["failed_phase"])
        self.assertIn("Restore", report["recovery"])
        with closing(sqlite3.connect(self.database)) as conn:
            self.assertEqual(1, conn.execute("SELECT value FROM committed_identity_marker").fetchone()[0])
        with self.assertRaisesRegex(RuntimeError, "incomplete V2 orchestration checkpoint"):
            orchestrator.run(
                self.database, apply=True, allow_production=True, report_path=self.report)

    def test_reset_checkpoint_survives_later_failure(self):
        self.patches()
        with self.assertRaisesRegex(RuntimeError, "injected failure"):
            orchestrator.run(
                self.database, apply=True, allow_production=True,
                report_path=self.report, failure_after_phase="test_contributions_reset")
        report = json.loads(self.report.read_text(encoding="utf-8"))
        self.assertEqual("complete", report["phases"]["test_contributions_reset"])
        self.assertEqual("geography_rebuilt", report["failed_phase"])
        self.assertEqual(0, self.reviewer_count())

    def test_proposal_and_rebuild_failures_never_claim_complete(self):
        self.patches(proposal_side_effect=ValueError("bad proposal"))
        with self.assertRaisesRegex(ValueError, "bad proposal"):
            orchestrator.run(
                self.database, apply=True, allow_production=True, report_path=self.report)
        report = json.loads(self.report.read_text(encoding="utf-8"))
        self.assertEqual(("failed", "proposal_validated"),
                         (report["status"], report["failed_phase"]))

        self.patches()
        with patch.object(orchestrator, "rebuild_products", side_effect=RuntimeError("rebuild failed")):
            with self.assertRaisesRegex(RuntimeError, "rebuild failed"):
                orchestrator.run(
                    self.database, apply=True, allow_production=True, report_path=self.report)
        report = json.loads(self.report.read_text(encoding="utf-8"))
        self.assertEqual(("failed", "derived_rebuild_completed"),
                         (report["status"], report["failed_phase"]))
        self.assertNotEqual("complete", report["phases"]["derived_rebuild_completed"])


if __name__ == "__main__":
    unittest.main()
