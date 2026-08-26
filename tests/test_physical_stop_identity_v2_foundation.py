import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from shapely.geometry import Polygon

from scripts.active.reset_v2_test_contributions import (
    CONFIRMATION, reset_test_contributions,
)
from src.processing.evidence_attribution_v2 import attribute
from src.processing.build_physical_stops import build_physical_stops
from src.processing.physical_stop_geography import assign_geography, recompute_geography
from src.processing.physical_stop_identity_v2 import (
    IncomingMember, allocate_successor_ids, apply_plan, ensure_identity_schema,
    plan_reconciliation, propose_partition,
    propose_merge,
)


def database(testcase):
    conn = sqlite3.connect(":memory:")
    testcase.addCleanup(conn.close)
    conn.executescript("""
      PRAGMA foreign_keys=ON;
      CREATE TABLE bus_stops(id INTEGER PRIMARY KEY,external_stop_id TEXT,
        latitude REAL,longitude REAL,stop_name TEXT);
      CREATE TABLE physical_stops(id INTEGER PRIMARY KEY,latitude REAL,
        longitude REAL,primary_name TEXT,member_count INTEGER,state TEXT,
        dc_ward TEXT,dc_anc TEXT,county TEXT,municipality TEXT);
      CREATE TABLE physical_stop_members(physical_stop_id INTEGER,bus_stop_id INTEGER UNIQUE,
        PRIMARY KEY(physical_stop_id,bus_stop_id));
      INSERT INTO bus_stops VALUES(10,'A',38.9,-77.0,'A'),(11,'B',38.9,-77.0,'B'),
        (12,'C',38.91,-77.01,'C');
      INSERT INTO physical_stops(id,latitude,longitude,primary_name,member_count)
        VALUES(1,38.9,-77.0,'A',2);
      INSERT INTO physical_stop_members VALUES(1,10),(1,11);
    """)
    return conn


class IdentityFoundationTests(unittest.TestCase):
    def test_schema_is_idempotent_and_initializes_existing_ids(self):
        conn = database(self)
        ensure_identity_schema(conn)
        ensure_identity_schema(conn)
        self.assertEqual([(1, "current")], conn.execute(
            "SELECT physical_stop_id,identity_status FROM physical_stop_identity_state"
        ).fetchall())

    def test_same_exact_snapshot_is_stable_on_repeated_plans(self):
        conn = database(self)
        members = [IncomingMember(str(i), i, 38.9, -77, exact_physical_stop_id=1)
                   for i in (10, 11)]
        for _ in range(3):
            plan = plan_reconciliation(conn, members)
            self.assertTrue(plan.is_noop)
            self.assertTrue(all(value == 0 for value in plan.counts().values()))

    def test_member_change_and_retirement_are_explicit(self):
        conn = database(self)
        plan = plan_reconciliation(conn, [
            IncomingMember("A", 10, 38.9, -77, exact_physical_stop_id=1),
            IncomingMember("C", 12, 38.9, -77, exact_physical_stop_id=1),
        ], version="fixture-1")
        self.assertEqual(1, plan.counts()["member_added"])
        self.assertEqual(1, plan.counts()["member_removed"])
        apply_plan(conn, plan, confirm=True, now="2026-08-26T00:00:00Z")
        self.assertEqual([(10,), (12,)], conn.execute(
            "SELECT bus_stop_id FROM physical_stop_members ORDER BY bus_stop_id"
        ).fetchall())

    def test_geometry_only_and_manual_exceptions_fail_closed(self):
        conn = database(self)
        plan = plan_reconciliation(conn, [IncomingMember("X", 12, 0, 0)])
        self.assertEqual(1, len(plan.ambiguous))
        with self.assertRaises(ValueError):
            apply_plan(conn, plan, confirm=True)
        self.assertTrue(propose_partition(406, [(10,), (11,)], reason="opposed").ambiguous)
        self.assertEqual("split", propose_partition(
            1, [(10,), (11,)], reason="strongly opposed headings"
        ).actions[0].action)
        self.assertEqual("merge", propose_merge(
            [1, 2], [10, 11], reason="reviewed shared boarding identity"
        ).actions[0].action)

    def test_moved_exact_identity_is_planned_but_not_silently_applied(self):
        conn = database(self)
        plan = plan_reconciliation(conn, [
            IncomingMember("A", 10, 39.0, -77, exact_physical_stop_id=1),
            IncomingMember("B", 11, 39.0, -77, exact_physical_stop_id=1),
        ])
        self.assertEqual(1, plan.counts()["movement"])
        with self.assertRaises(ValueError):
            apply_plan(conn, plan, confirm=True)

    def test_successor_allocation_is_stable_and_above_maximum(self):
        conn = database(self)
        groups = [(2, [12, 11]), (1, [10]), (1, [9])]
        first = allocate_successor_ids(conn, groups)
        second = allocate_successor_ids(conn, reversed(groups))
        self.assertEqual(first, second)
        self.assertEqual([2, 3, 4], sorted(first.values()))

    def test_geography_is_offline_deterministic_and_updates_one_stop(self):
        square = Polygon([(-78, 38), (-76, 38), (-76, 40), (-78, 40)])
        boundaries = {"dc_ward": [], "dc_anc": [], "md_place": [(square, "Town")],
                      "va_place": [], "county": [], "state_fips": [(square, "24")]}
        expected = {"state": "MD", "county": None, "municipality": "Town",
                    "dc_ward": None, "dc_anc": None}
        self.assertEqual(expected, assign_geography(38.9, -77, boundaries))
        conn = database(self)
        self.assertEqual(1, recompute_geography(conn, [1], boundaries=boundaries))
        self.assertEqual(("MD", None, "Town"), conn.execute(
            "SELECT state,county,municipality FROM stop_jurisdiction WHERE stop_id=1"
        ).fetchone())

    def test_evidence_exact_precedence_and_spatial_ambiguity(self):
        conn = database(self)
        self.assertEqual(("exact_member", 1), attribute(
            conn, evidence_table="raw", evidence_row_id=1, version="v1",
            exact_member_stop_id=1, spatial_stop_id=99, spatial_is_unambiguous=True))
        self.assertEqual(("unresolved", None), attribute(
            conn, evidence_table="raw", evidence_row_id=2, version="v1",
            spatial_stop_id=1, spatial_is_unambiguous=False))


class ResetGuardTests(unittest.TestCase):
    def test_old_builder_refuses_populated_identity_registry(self):
        temporary_root = Path(__file__).resolve().parents[1] / ".tmp"
        temporary_root.mkdir(exist_ok=True)
        descriptor, raw_path = tempfile.mkstemp(suffix=".db", dir=temporary_root)
        os.close(descriptor)
        path = Path(raw_path)
        self.addCleanup(path.unlink, missing_ok=True)
        try:
            conn = sqlite3.connect(path)
            conn.executescript("""CREATE TABLE physical_stops(id INTEGER PRIMARY KEY,
                latitude REAL,longitude REAL,primary_name TEXT,member_count INTEGER,
                created_at TEXT); INSERT INTO physical_stops VALUES(7,1,2,'keep',1,NULL);
                CREATE TABLE physical_stop_members(physical_stop_id INTEGER,bus_stop_id INTEGER);
                CREATE TABLE bus_stops(id INTEGER PRIMARY KEY,latitude REAL,longitude REAL,
                    stop_name TEXT);""")
            conn.close()
            with self.assertRaises(RuntimeError):
                build_physical_stops(path, bootstrap_empty=True)
            conn = sqlite3.connect(path)
            self.assertEqual([(7,)], conn.execute("SELECT id FROM physical_stops").fetchall())
            conn.close()
        finally:
            path.unlink(missing_ok=True)

    def test_reset_is_narrow_transactional_and_requires_confirmation(self):
        conn = sqlite3.connect(":memory:")
        self.addCleanup(conn.close)
        human = ("community_reviewers", "community_reviewer_routes",
                 "stop_review_assignments", "stop_observations",
                 "stop_consensus", "community_stewardships", "review_feedback",
                 "community_requests")
        for table in human:
            conn.execute(f"CREATE TABLE {table}(id INTEGER PRIMARY KEY)")
            conn.execute(f"INSERT INTO {table} VALUES(1)")
        for table in ("bus_stops", "physical_stops", "stop_amenity_evidence"):
            conn.execute(f"CREATE TABLE {table}(id INTEGER PRIMARY KEY)")
            conn.execute(f"INSERT INTO {table} VALUES(1)")
        with self.assertRaises(ValueError):
            reset_test_contributions(conn, confirmation="wrong")
        counts = reset_test_contributions(conn, confirmation=CONFIRMATION)
        self.assertEqual(set(human), set(counts))
        for table in human:
            self.assertEqual(0, conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        for table in ("bus_stops", "physical_stops", "stop_amenity_evidence"):
            self.assertEqual(1, conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


if __name__ == "__main__":
    unittest.main()
