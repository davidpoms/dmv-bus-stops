import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import unittest

from src.amenities.review_priority import rebuild_review_priority


REPO_ROOT = Path(__file__).resolve().parents[1]


class AmenityReviewPriorityTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
        CREATE TABLE stop_gtfs_status(physical_stop_id INTEGER PRIMARY KEY,current_gtfs INTEGER);
        INSERT INTO stop_gtfs_status VALUES (1,1),(2,1),(3,0);
        CREATE TABLE opportunity_assessments(
          physical_stop_id INTEGER,rider_exposure_percentile REAL);
        INSERT INTO opportunity_assessments VALUES (1,10),(2,99),(3,100);
        CREATE TABLE stop_amenity_status(
          physical_stop_id INTEGER,amenity_type TEXT,derived_status TEXT,
          consensus_status TEXT,evidence_conflict INTEGER,
          community_observation_count INTEGER,
          community_yes_count INTEGER,community_no_count INTEGER,
          consensus_conflicts_with_other_evidence INTEGER);
        """)

    def tearDown(self):
        self.db.close()

    def add_pair(self, stop, shelter, bench, observations=0, consensus="not_reached"):
        self.db.executemany("INSERT INTO stop_amenity_status VALUES (?,?,?,?,?,?,?,?,?)", [
            (stop,"shelter",shelter,consensus,int(shelter=="conflicting"),observations,observations,0,0),
            (stop,"bench",bench,consensus,int(bench=="conflicting"),observations,observations,0,0),
        ])

    def test_rebuild_scope_uniqueness_and_workflow_dominance(self):
        self.add_pair(1,"conflicting","unknown")
        self.add_pair(2,"unknown","likely_no")
        self.add_pair(3,"conflicting","conflicting")
        first = rebuild_review_priority(self.db)
        second = rebuild_review_priority(self.db)
        self.assertEqual(4, len(first))
        self.assertEqual(4, len(second))
        self.assertEqual(4, self.db.execute(
            "SELECT COUNT(*) FROM stop_amenity_review_priority").fetchone()[0])
        conflict = self.db.execute("""SELECT review_priority_score FROM
          stop_amenity_review_priority WHERE physical_stop_id=1 AND amenity_type='shelter'""").fetchone()[0]
        unknown_high = self.db.execute("""SELECT review_priority_score FROM
          stop_amenity_review_priority WHERE physical_stop_id=2 AND amenity_type='shelter'""").fetchone()[0]
        self.assertGreater(conflict, unknown_high)

    def test_near_consensus_and_resolved(self):
        self.add_pair(1,"likely_yes","likely_yes",observations=2)
        self.add_pair(2,"confirmed_yes","confirmed_no",observations=3,consensus="yes")
        rebuild_review_priority(self.db)
        self.assertEqual("one_observation_short", self.db.execute("""SELECT workflow_state
          FROM stop_amenity_review_priority WHERE physical_stop_id=1 LIMIT 1""").fetchone()[0])
        resolved = self.db.execute("""SELECT DISTINCT workflow_state,review_priority_score
          FROM stop_amenity_review_priority WHERE physical_stop_id=2""").fetchone()
        self.assertEqual(("consensus_reached",0), tuple(resolved))

    def test_exposure_orders_within_state_and_targeted_rebuild_leaves_other_stop(self):
        self.add_pair(1,"unknown","unknown")
        self.add_pair(2,"unknown","unknown")
        rebuild_review_priority(self.db)
        low = self.db.execute("SELECT review_priority_score FROM stop_amenity_review_priority "
                              "WHERE physical_stop_id=1 LIMIT 1").fetchone()[0]
        high = self.db.execute("SELECT review_priority_score FROM stop_amenity_review_priority "
                               "WHERE physical_stop_id=2 LIMIT 1").fetchone()[0]
        self.assertGreater(high, low)
        before = [tuple(row) for row in self.db.execute(
            "SELECT * FROM stop_amenity_review_priority WHERE physical_stop_id=2"
        )]
        self.db.execute("UPDATE stop_amenity_status SET derived_status='likely_yes' "
                        "WHERE physical_stop_id=1")
        rebuild_review_priority(self.db, 1)
        after = [tuple(row) for row in self.db.execute(
            "SELECT * FROM stop_amenity_review_priority WHERE physical_stop_id=2"
        )]
        self.assertEqual(before, after)

    def test_rationale_uses_canonical_rider_exposure_name(self):
        self.add_pair(1, "unknown", "unknown")
        self.add_pair(2, "unknown", "unknown")
        rebuild_review_priority(self.db)
        rationale = json.loads(self.db.execute(
            "SELECT rationale FROM stop_amenity_review_priority LIMIT 1"
        ).fetchone()[0])
        self.assertEqual(10, rationale["rider_exposure_percentile"])
        self.assertNotIn("route_exposure_percentile", rationale)


class AmenityReviewPriorityScriptTests(unittest.TestCase):
    def test_direct_and_module_invocations_import_successfully(self):
        scripts = (
            ("scripts/active/rebuild_amenity_review_priority.py",
             "scripts.active.rebuild_amenity_review_priority"),
            ("scripts/diagnostics/preflight_amenity_review_priority.py",
             "scripts.diagnostics.preflight_amenity_review_priority"),
        )
        for script, module in scripts:
            with self.subTest(invocation="direct", script=script):
                result = subprocess.run(
                    [sys.executable, str(REPO_ROOT / script), "--help"],
                    cwd=REPO_ROOT, capture_output=True, text=True,
                )
                self.assertEqual(0, result.returncode, result.stderr)
            with self.subTest(invocation="module", module=module):
                result = subprocess.run(
                    [sys.executable, "-m", module, "--help"],
                    cwd=REPO_ROOT, capture_output=True, text=True,
                )
                self.assertEqual(0, result.returncode, result.stderr)


if __name__ == "__main__":
    unittest.main()
