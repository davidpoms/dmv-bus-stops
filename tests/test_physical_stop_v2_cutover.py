import sqlite3
import unittest
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()
