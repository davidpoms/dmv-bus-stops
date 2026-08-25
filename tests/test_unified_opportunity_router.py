import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.review import assignment_router
from src.review.context import build_review_context


class UnifiedOpportunityRouterTests(unittest.TestCase):
    def setUp(self):
        handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        handle.close()
        self.db = Path(handle.name)
        conn = sqlite3.connect(self.db)
        conn.executescript("""
        CREATE TABLE stop_gtfs_status(physical_stop_id INTEGER PRIMARY KEY,current_gtfs INTEGER);
        CREATE TABLE seating_improvement_opportunities(
          physical_stop_id INTEGER PRIMARY KEY,opportunity_rank INTEGER,
          workflow_state TEXT,bench_status TEXT,shelter_status TEXT,
          adequacy_status TEXT,clearance_status TEXT,rider_exposure_percentile REAL);
        CREATE TABLE stop_amenity_status(
          physical_stop_id INTEGER,amenity_type TEXT,derived_status TEXT,
          community_observation_count INTEGER,community_yes_count INTEGER,
          community_no_count INTEGER);
        CREATE TABLE stop_amenity_review_priority(
          physical_stop_id INTEGER,observations_needed_for_consensus INTEGER);
        CREATE TABLE stop_observations(
          physical_stop_id INTEGER,source TEXT,observed_at TEXT);
        CREATE TABLE stop_review_assignments(
          id INTEGER PRIMARY KEY,stop_id INTEGER,reviewer_id INTEGER,
          scenario TEXT,campaign TEXT,status TEXT);
        """)
        candidates = [
            (1, 70, "verify_presence", "unknown", "conflicting", "unknown", "unknown", 99),
            (2, 1, "verify_presence", "unknown", "unknown", "unknown", "unknown", 98),
            (3, 2, "assess_adequacy", "likely_yes", "likely_yes", "unknown", "unknown", 97),
            (4, 3, "collect_clearance_observation", "likely_no", "likely_no", "unknown", "unknown", 96),
            (5, 4, "verify_presence", "likely_yes", "likely_yes", "unknown", "unknown", 95),
            (6, 5, "verify_presence", "likely_yes", "likely_yes", "unknown", "unknown", 94),
            (7, 6, "planning_review", "likely_yes", "likely_yes", "limitation_observed", "observed_clear", 93),
            (8, 0, "verify_presence", "unknown", "unknown", "unknown", "unknown", 100),
        ]
        conn.executemany("INSERT INTO seating_improvement_opportunities VALUES (?,?,?,?,?,?,?,?)", candidates)
        conn.executemany("INSERT INTO stop_gtfs_status VALUES (?,?)", [(i, 0 if i == 8 else 1) for i in range(1, 9)])
        for row in candidates:
            stop, _, _, bench, shelter, *_ = row
            conn.execute("INSERT INTO stop_amenity_status VALUES (?,?,?,?,?,?)",
                         (stop, "bench", bench, 1 if stop == 5 else 3 if stop == 6 else 0, 1 if stop == 5 else 3 if stop == 6 else 0, 0))
            conn.execute("INSERT INTO stop_amenity_status VALUES (?,?,?,?,?,?)",
                         (stop, "shelter", shelter, 0, 0, 0))
            conn.execute("INSERT INTO stop_amenity_review_priority VALUES (?,?)", (stop, 2 if stop == 5 else 0))
        conn.execute("INSERT INTO stop_observations VALUES (5,'community_review','2026-01-01')")
        conn.execute("INSERT INTO stop_observations VALUES (6,'community_review','2025-01-01')")
        conn.commit(); conn.close()
        self.patch = patch.object(assignment_router, "DB", self.db)
        self.patch.start()

    def tearDown(self):
        self.patch.stop(); self.db.unlink(missing_ok=True)

    def complete(self, assignment_id):
        conn = sqlite3.connect(self.db)
        conn.execute("UPDATE stop_review_assignments SET status='completed' WHERE id=?", (assignment_id,))
        conn.commit(); conn.close()

    def test_rotation_is_deterministic_and_represents_core_cohorts(self):
        selected = []
        for _ in range(1, 8):
            assignment_id, stop_id = assignment_router.assign_stop(1, "opportunity")
            conn = sqlite3.connect(self.db)
            campaign = conn.execute("SELECT campaign FROM stop_review_assignments WHERE id=?", (assignment_id,)).fetchone()[0]
            conn.close()
            selected.append((stop_id, campaign)); self.complete(assignment_id)
        self.assertEqual([1, 2, 3, 4], [x[0] for x in selected[:4]])
        self.assertIn((5, "seating_adequacy"), selected)
        self.assertIn((6, "seating_adequacy"), selected)
        self.assertIn((7, "seating_adequacy"), selected)
        self.assertNotIn(8, [x[0] for x in selected])
        self.assertEqual(len(selected), len({x[0] for x in selected}))

    def test_empty_cohort_skips_and_active_assignment_is_excluded(self):
        conn = sqlite3.connect(self.db)
        conn.execute("UPDATE seating_improvement_opportunities SET shelter_status='unknown' WHERE physical_stop_id=1")
        conn.execute("UPDATE stop_amenity_status SET derived_status='unknown' WHERE physical_stop_id=1 AND amenity_type='shelter'")
        conn.execute("INSERT INTO stop_review_assignments VALUES (20,2,99,'opportunity',NULL,'assigned')")
        conn.commit(); conn.close()
        result = assignment_router.assign_stop(1, "opportunity")
        self.assertEqual(1, result[1])

    def test_reason_and_campaign_follow_evidence_need_without_a_score(self):
        context = build_review_context("map", {
            "bench_status": "conflicting", "shelter_status": "unknown",
            "adequacy_status": "unknown", "clearance_status": "unknown",
            "workflow_state": "verify_presence",
        })
        self.assertEqual("presence_verification", context["review_focus"])
        self.assertIn("sources disagree", context["evidence_explanation"])
        source = Path(assignment_router.__file__).read_text(encoding="utf-8")
        self.assertNotIn("volunteer_value_score", source)
        self.assertNotIn("evidence_gap_score", source)
        self.assertNotIn("review_value_score", source)


if __name__ == "__main__":
    unittest.main()
