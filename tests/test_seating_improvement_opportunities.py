import json
import inspect
import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.assessment.generate_seating_improvement_opportunities import (
    build_opportunities,
    classify_adequacy,
    documented_need,
    priority,
)
from src.api import app as api_app
from src.review.community_survey_v1 import SURVEY


class SeatingImprovementOpportunityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "test.db"
        self.conn = sqlite3.connect(self.db)
        self.conn.executescript("""
          CREATE TABLE physical_stops(id INTEGER PRIMARY KEY,primary_name TEXT);
          CREATE TABLE stop_gtfs_status(physical_stop_id INTEGER,current_gtfs INTEGER);
          CREATE TABLE stop_jurisdiction(stop_id INTEGER,state TEXT,county TEXT,municipality TEXT);
          CREATE TABLE stop_amenity_status(physical_stop_id INTEGER,amenity_type TEXT,
            derived_status TEXT,consensus_status TEXT);
          CREATE TABLE opportunity_assessments(physical_stop_id INTEGER,rider_exposure_percentile REAL);
          CREATE TABLE improvement_opportunities(physical_stop_id INTEGER,opportunity_score REAL);
          CREATE TABLE stop_observations(id INTEGER PRIMARY KEY,physical_stop_id INTEGER,
            source TEXT,bench_present TEXT,bench_type TEXT,bench_condition TEXT,rider_comfort_category TEXT,
            accessibility_status TEXT,bench_feasible TEXT,weather_exposure TEXT,
            riders_avoid_facilities TEXT);
        """)
        stops = [(1, "Present"), (2, "Absent"), (3, "Unknown"), (4, "Inactive")]
        self.conn.executemany("INSERT INTO physical_stops VALUES (?,?)", stops)
        self.conn.executemany("INSERT INTO stop_gtfs_status VALUES (?,?)",
                              [(1, 1), (2, 1), (3, 1), (4, 0)])
        self.conn.executemany("INSERT INTO stop_jurisdiction VALUES (?,?,?,?)",
                              [(i, "VA", "Test", "Town") for i in range(1, 5)])
        statuses = {1: ("confirmed_yes", "confirmed_yes"),
                    2: ("likely_no", "insufficient"),
                    3: ("conflicting", "insufficient"),
                    4: ("unknown", "insufficient")}
        for stop_id, (bench, consensus) in statuses.items():
            self.conn.execute("INSERT INTO stop_amenity_status VALUES (?,?,?,?)",
                              (stop_id, "bench", bench, consensus))
            self.conn.execute("INSERT INTO stop_amenity_status VALUES (?,?,?,?)",
                              (stop_id, "shelter", "confirmed_yes", "confirmed_yes"))
            self.conn.execute("INSERT INTO opportunity_assessments VALUES (?,?)",
                              (stop_id, 50 + stop_id))
            self.conn.execute("INSERT INTO improvement_opportunities VALUES (?,?)",
                              (stop_id, 10))
        self.conn.execute("INSERT INTO stop_observations VALUES (1,1,'community_review',"
                          "'yes','full_bench','dividers','good','good','unknown',NULL,NULL)")
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        self.temp.cleanup()

    def test_every_active_stop_is_included_without_score_or_presence_gate(self):
        self.assertEqual(3, build_opportunities(self.conn))
        rows = self.conn.execute("""SELECT physical_stop_id,bench_status,shelter_status,
          adequacy_status,workflow_state FROM seating_improvement_opportunities
          ORDER BY physical_stop_id""").fetchall()
        self.assertEqual([1, 2, 3], [row[0] for row in rows])
        self.assertEqual("limitation_observed", rows[0][3])
        self.assertEqual("collect_clearance_observation", rows[0][4])
        self.assertEqual("collect_clearance_observation", rows[1][4])
        self.assertEqual("verify_presence", rows[2][4])
        self.assertTrue(all(row[2] == "confirmed_yes" for row in rows))

    def test_priority_is_reproducible_and_rider_is_counted_once(self):
        build_opportunities(self.conn)
        row = self.conn.execute("""SELECT documented_need_index,
          documented_need_component,rider_benefit_component,priority_score,priority_factors
          FROM seating_improvement_opportunities WHERE physical_stop_id=1""").fetchone()
        self.assertEqual(90, row[0])
        self.assertAlmostEqual(row[1] + row[2], row[3])
        self.assertAlmostEqual(90 * .60 + 51 * .40, row[3])
        factors = json.loads(row[4])
        self.assertEqual(0.40, factors["rider_exposure"]["weight"])
        self.assertEqual(0.60, factors["documented_need"]["weight"])
        self.assertNotIn("legacy_opportunity_score", factors)
        self.assertNotIn("workflow", factors)
        self.assertNotIn("review_priority", factors)

    def test_adequacy_does_not_follow_presence(self):
        status, factors = classify_adequacy([])
        self.assertEqual("unknown", status)
        self.assertEqual(0, factors["observations"])

        no_presence = [(None, "", "none", "good", "good", None, None)]
        self.assertEqual("unknown", classify_adequacy(no_presence)[0])
        affirmative = [("yes", "full_bench", "none", "good", "good", None, None)]
        self.assertEqual("no_limitation_observed", classify_adequacy(affirmative)[0])

    def test_approved_need_values_use_max_and_never_reward_uncertainty(self):
        blank = [(None, "", "none", "good", "good", None, None)]
        self.assertEqual(0, documented_need("unknown", "unknown", blank)[0])
        self.assertEqual(0, documented_need("conflicting", "unknown", blank)[0])
        self.assertEqual(45, documented_need("likely_no", "unknown", blank)[0])
        self.assertEqual(55, documented_need("confirmed_no", "unknown", blank)[0])
        self.assertEqual(20, documented_need("likely_yes", "likely_no", blank)[0])
        limitation = [("yes", "full_bench", "dividers", "poor", "good", "exposed", "yes")]
        need, strongest, signals = documented_need("likely_no", "likely_no", limitation)
        self.assertEqual(90, need)
        self.assertEqual("observed_seating_limitation", strongest)
        self.assertGreater(sum(signals.values()), need)
        poor = [("yes", "full_bench", "none", "poor", "good", None, None)]
        fair = [("yes", "full_bench", "none", "fair", "good", None, None)]
        self.assertEqual(75, documented_need("likely_yes", "unknown", poor)[0])
        self.assertEqual(40, documented_need("likely_yes", "unknown", fair)[0])
        uncalibrated = [("yes", "full_bench", "none", "good", "blocked", "exposed", "yes")]
        self.assertEqual(0, documented_need("likely_yes", "unknown", uncalibrated)[0])

    def test_priority_has_only_need_and_rider_components(self):
        self.assertEqual((54.0, 20.0, 74.0), priority(90, 50))

    def test_present_limitation_can_outrank_absence(self):
        present = priority(90, 30)[2]
        absent = priority(45, 90)[2]
        self.assertGreater(present, absent)

    def test_targeted_refresh_changes_only_requested_stop(self):
        build_opportunities(self.conn)
        before = dict(self.conn.execute(
            "SELECT physical_stop_id,updated_at FROM seating_improvement_opportunities"
        ))
        self.conn.execute("UPDATE stop_amenity_status SET derived_status='likely_yes' "
                          "WHERE physical_stop_id=2 AND amenity_type='bench'")
        build_opportunities(self.conn, 2)
        after = dict(self.conn.execute(
            "SELECT physical_stop_id,updated_at FROM seating_improvement_opportunities"
        ))
        self.assertEqual(before[1], after[1])
        self.assertEqual(before[3], after[3])
        self.assertEqual("likely_yes", self.conn.execute(
            "SELECT bench_status FROM seating_improvement_opportunities WHERE physical_stop_id=2"
        ).fetchone()[0])

    def test_survey_provenance_and_prospective_fields_are_wired(self):
        modes = {value for value, _label in SURVEY["review_mode"]["options"]}
        self.assertTrue({"in_person", "street_view", "other_remote_visual", "remote"} <= modes)
        source = inspect.getsource(api_app.submit_review)
        self.assertIn('"assignment_id",', source)
        self.assertIn('"weather_exposure",', source)
        self.assertIn('"riders_avoid_facilities",', source)
        self.assertIn('"review_schema_migration_required"', source)
        self.assertNotIn("ALTER TABLE stop_observations", source)
        self.assertIn("WHERE assignment_id=?", source)
        self.assertNotIn("WHERE physical_stop_id=?\n        AND reviewer_id=?", source)


if __name__ == "__main__":
    unittest.main()
