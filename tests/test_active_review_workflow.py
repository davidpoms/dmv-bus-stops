import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.api import app as review_api
from src.review import assignment_router
from src.review import create_review_queue
from src.review import create_stop_review_assignments
from src.review import export_review_tasks


class ActiveReviewWorkflowTests(unittest.TestCase):
    def setUp(self):
        handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        handle.close()
        self.db = Path(handle.name)
        self.export = self.db.with_suffix(".json")
        conn = sqlite3.connect(self.db)
        conn.executescript(
            """
            CREATE TABLE physical_stops (
                id INTEGER PRIMARY KEY, primary_name TEXT,
                latitude REAL, longitude REAL, state TEXT
            );
            INSERT INTO physical_stops VALUES
                (1,'Current',0,0,'DC'),
                (2,'Inactive',0.001,0.001,'DC'),
                (3,'Missing status',0.002,0.002,'DC');
            CREATE TABLE stop_gtfs_status (
                physical_stop_id INTEGER PRIMARY KEY, current_gtfs INTEGER
            );
            INSERT INTO stop_gtfs_status VALUES (1,1),(2,0);
            CREATE TABLE improvement_opportunities (
                physical_stop_id INTEGER, priority_rank INTEGER,
                opportunity_score REAL
            );
            INSERT INTO improvement_opportunities VALUES
                (1,3,10),(2,1,100),(3,2,90);
            CREATE TABLE opportunity_assessments (
                physical_stop_id INTEGER, combined_route_weekday_boardings REAL
            );
            INSERT INTO opportunity_assessments VALUES (1,10),(2,100),(3,90);
            CREATE TABLE seating_improvement_opportunities (
                physical_stop_id INTEGER PRIMARY KEY, opportunity_rank INTEGER,
                priority_score REAL, workflow_state TEXT
            );
            INSERT INTO seating_improvement_opportunities VALUES
                (1,1,0,'verify_presence'),
                (2,2,100,'planning_review'),
                (3,3,90,'assess_adequacy');
            CREATE TABLE stop_wmata_evidence (
                id INTEGER PRIMARY KEY, physical_stop_id INTEGER,
                wmata_status TEXT, wmata_shelter INTEGER, wmata_bench INTEGER
            );
            INSERT INTO stop_wmata_evidence VALUES
                (1,1,'PRS',1,1),(2,2,'PRS',1,1),(3,3,'PRS',1,1);
            CREATE TABLE review_queue (
                id INTEGER PRIMARY KEY, physical_stop_id INTEGER,
                priority_rank INTEGER, opportunity_score REAL,
                location_name TEXT, review_status TEXT DEFAULT 'pending',
                review_questions TEXT, consensus_status TEXT DEFAULT 'pending',
                resolution_reason TEXT, verification_needed INTEGER DEFAULT 1,
                community_review_available INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO review_queue
                (id,physical_stop_id,priority_rank,opportunity_score,location_name)
                VALUES (1,1,3,10,'Current'),(2,2,1,100,'Inactive'),
                       (3,3,2,90,'Missing status');
            CREATE TABLE physical_stop_members (
                physical_stop_id INTEGER, bus_stop_id INTEGER
            );
            INSERT INTO physical_stop_members VALUES (1,101),(2,102),(3,103);
            CREATE TABLE stop_routes (stop_id INTEGER, route_id INTEGER);
            INSERT INTO stop_routes VALUES (101,10),(102,10),(103,10);
            CREATE TABLE routes (
                id INTEGER PRIMARY KEY, route_id TEXT, route_name TEXT
            );
            INSERT INTO routes VALUES (10,'C61','Route C61');
            CREATE TABLE community_reviewers (
                id INTEGER PRIMARY KEY, reviewer_key TEXT,
                display_name TEXT, profile_created_at TEXT
            );
            INSERT INTO community_reviewers VALUES (1,'reviewer',NULL,NULL);
            CREATE TABLE community_reviewer_routes (reviewer_id INTEGER, route_id TEXT);
            INSERT INTO community_reviewer_routes VALUES (1,'C61');
            CREATE TABLE stop_review_assignments (
                id INTEGER PRIMARY KEY, stop_id INTEGER, reviewer_id INTEGER,
                scenario TEXT, campaign TEXT, status TEXT, completed_at TEXT
            );
            INSERT INTO stop_review_assignments VALUES
                (20,2,1,'opportunity',NULL,'completed','2026-01-01');
            CREATE TABLE stop_observations (
                id INTEGER PRIMARY KEY, physical_stop_id INTEGER,
                observed_at TEXT, shelter_present TEXT, bench_present TEXT,
                notes TEXT, reviewer_id INTEGER, source TEXT
            );
            INSERT INTO stop_observations VALUES
                (30,2,'2026-01-01','no','no','historical',1,'community_review');
            CREATE TABLE stop_consensus (stop_id INTEGER, confidence TEXT);
            """
        )
        conn.commit()
        conn.close()
        self.patches = (
            patch.object(create_review_queue, "DATABASE_PATH", self.db),
            patch.object(create_stop_review_assignments, "DATABASE_PATH", self.db),
            patch.object(assignment_router, "DB", self.db),
            patch.object(review_api, "DATABASE_PATH", self.db),
        )
        for context in self.patches:
            context.start()
            self.addCleanup(context.stop)
        review_api.app.config.update(TESTING=True, SECRET_KEY="test")
        self.client = review_api.app.test_client()

    def tearDown(self):
        self.export.unlink(missing_ok=True)
        self.db.unlink(missing_ok=True)

    def queue_ids(self):
        conn = sqlite3.connect(self.db)
        ids = {row[0] for row in conn.execute("SELECT physical_stop_id FROM review_queue")}
        conn.close()
        return ids

    def reset_assignments(self):
        conn = sqlite3.connect(self.db)
        conn.execute("DELETE FROM stop_review_assignments WHERE id<>20")
        conn.commit()
        conn.close()

    def test_queue_rebuild_uses_only_canonical_current_status(self):
        conn = sqlite3.connect(self.db)
        conn.executescript(
            """
            INSERT INTO physical_stops VALUES
                (4,'Current ABS',0.003,0.003,'DC'),
                (5,'Current zero amenities',0.004,0.004,'DC'),
                (6,'Current no WMATA',0.005,0.005,'DC'),
                (7,'Inactive PRS',0.006,0.006,'DC');
            INSERT INTO stop_gtfs_status VALUES (4,1),(5,1),(6,1),(7,0);
            INSERT INTO improvement_opportunities VALUES
                (4,4,50),(5,5,40),(6,6,30),(7,7,100);
            INSERT INTO stop_wmata_evidence VALUES
                (4,4,'ABS',0,0),
                (5,5,'PRS',0,0),
                (7,7,'PRS',1,1);
            """
        )
        conn.commit()
        conn.close()

        create_review_queue.create_review_queue()
        self.assertEqual({1, 4, 5, 6}, self.queue_ids())

        source = Path(create_review_queue.__file__).read_text(encoding="utf-8")
        self.assertNotIn("stop_wmata_evidence", source)
        self.assertNotIn("wmata_shelter", source)
        self.assertNotIn("wmata_bench", source)
        self.assertNotIn("'PRS'", source)
        self.assertNotIn("'ABS'", source)

    def test_assignment_modes_and_specific_requests_fail_closed(self):
        self.assertIsNone(assignment_router.assign_stop(1, "opportunity", stop_id=2))
        self.assertIsNone(assignment_router.assign_stop(1, "opportunity", stop_id=3))

        specific = assignment_router.assign_stop(1, "opportunity", stop_id=1)
        self.assertIsNotNone(specific)
        self.assertEqual(1, specific[1])

        for scenario, kwargs in (
            ("route", {}),
            ("nearby", {"latitude": 0.001, "longitude": 0.001}),
            ("opportunity", {}),
        ):
            with self.subTest(scenario=scenario):
                self.reset_assignments()
                result = assignment_router.assign_stop(1, scenario, **kwargs)
                self.assertIsNotNone(result)
                self.assertEqual(1, result[1])

    def test_opportunity_campaigns_use_seating_workflow_and_rank(self):
        conn = sqlite3.connect(self.db)
        conn.executescript("""
            INSERT INTO physical_stops VALUES (4,'Same name',0.1,0.1,'MD'),
                                              (5,'Same name',0.2,0.2,'VA'),
                                              (6,'No action',0.3,0.3,'DC'),
                                              (7,'Planning',0.4,0.4,'DC'),
                                              (8,'Constrained',0.5,0.5,'DC');
            INSERT INTO stop_gtfs_status VALUES (4,1),(5,1),(6,1),(7,1),(8,1);
            INSERT INTO seating_improvement_opportunities VALUES
                (4,2,1,'assess_adequacy'),
                (5,3,99,'collect_clearance_observation'),
                (6,4,100,'no_current_action'),
                (7,5,2,'planning_review'),
                (8,6,3,'constrained_or_special_review');
        """)
        conn.commit()
        conn.close()

        self.reset_assignments()
        assignment_id, stop_id = assignment_router.assign_stop(
            1, "opportunity", campaign="presence_verification")
        self.assertEqual(1, stop_id)
        conn = sqlite3.connect(self.db)
        self.assertEqual("presence_verification", conn.execute(
            "SELECT campaign FROM stop_review_assignments WHERE id=?", (assignment_id,)
        ).fetchone()[0])
        conn.execute("UPDATE stop_review_assignments SET status='completed' WHERE id=?",
                     (assignment_id,))
        conn.commit()
        conn.close()

        self.assertEqual(4, assignment_router.assign_stop(
            2, "opportunity", campaign="seating_adequacy")[1])
        self.assertEqual(5, assignment_router.assign_stop(
            3, "opportunity", campaign="bench_clearance")[1])
        self.assertEqual(7, assignment_router.assign_stop(
            4, "opportunity", campaign="planning_review")[1])
        self.assertEqual(8, assignment_router.assign_stop(
            5, "opportunity", campaign="constrained_review")[1])
        with self.assertRaises(ValueError):
            assignment_router.assign_stop(6, "opportunity", campaign="bogus")

    def test_opportunity_has_no_score_gate_and_no_action_is_excluded(self):
        self.reset_assignments()
        result = assignment_router.assign_stop(2, "opportunity")
        self.assertEqual(1, result[1])
        conn = sqlite3.connect(self.db)
        self.assertEqual(0, conn.execute(
            "SELECT COUNT(*) FROM stop_review_assignments WHERE stop_id=6"
        ).fetchone()[0])
        conn.close()

    def test_opportunity_start_validates_and_preserves_campaign(self):
        self.assertEqual(400, self.client.get(
            "/review/start?mode=opportunity&campaign=unknown"
        ).status_code)
        response = self.client.get(
            "/review/start?mode=opportunity&campaign=presence_verification",
            follow_redirects=False,
        )
        self.assertEqual(302, response.status_code)
        self.assertIn("campaign=presence_verification", response.location)
        conn = sqlite3.connect(self.db)
        self.assertEqual("presence_verification", conn.execute(
            "SELECT campaign FROM stop_review_assignments WHERE status='assigned' "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()[0])
        before = conn.execute(
            "SELECT COUNT(*) FROM stop_review_assignments"
        ).fetchone()[0]
        conn.execute("ALTER TABLE stop_review_assignments DROP COLUMN campaign")
        conn.commit()
        conn.close()
        response = self.client.get("/review/start?mode=opportunity")
        self.assertEqual(503, response.status_code)
        self.assertEqual("review_schema_migration_required", response.get_json()["code"])
        conn = sqlite3.connect(self.db)
        self.assertEqual(before, conn.execute(
            "SELECT COUNT(*) FROM stop_review_assignments"
        ).fetchone()[0])
        conn.close()

    def test_bulk_assignment_and_export_exclude_inactive_rows(self):
        create_stop_review_assignments.create_assignments()
        conn = sqlite3.connect(self.db)
        assigned = {row[0] for row in conn.execute(
            "SELECT stop_id FROM stop_review_assignments WHERE status='assigned'"
        )}
        conn.close()
        self.assertEqual({1}, assigned)

        export_review_tasks.export_review_tasks(self.db, self.export)
        tasks = json.loads(self.export.read_text(encoding="utf-8"))
        self.assertEqual([1], [task["physical_stop_id"] for task in tasks])

    def test_active_candidate_apis_filter_and_mutations_reject(self):
        queue = self.client.get("/api/review-queue")
        self.assertEqual(200, queue.status_code)
        self.assertEqual([1], [item["stop_id"] for item in queue.get_json()["queue"]])

        validation = self.client.get("/validation/queue")
        self.assertEqual(200, validation.status_code)
        self.assertEqual([1], [item["stop_id"] for item in validation.get_json()])

        for url in (
            "/review/start?stop_id=2",
            "/review/start?stop_id=3",
            "/review/2",
            "/review/3",
            "/review/2/assignment",
            "/review/3/assignment",
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(409, response.status_code)
                self.assertEqual("stop_not_current", response.get_json()["code"])

    def test_submission_rejects_old_assignment_but_history_remains_readable(self):
        with self.client.session_transaction() as session:
            session["reviewer_key"] = "reviewer"
        conn = sqlite3.connect(self.db)
        before = conn.execute(
            "SELECT COUNT(*) FROM stop_observations"
        ).fetchone()[0]
        conn.close()
        migration_required = self.client.post(
            "/review/submit", json={"stop_id": 1, "assignment_id": 999}
        )
        self.assertEqual(503, migration_required.status_code)
        self.assertEqual(
            "review_schema_migration_required",
            migration_required.get_json()["code"],
        )
        conn = sqlite3.connect(self.db)
        self.assertEqual(before, conn.execute(
            "SELECT COUNT(*) FROM stop_observations"
        ).fetchone()[0])
        conn.close()
        response = self.client.post(
            "/review/submit",
            json={"stop_id": 2, "assignment_id": 20},
        )
        self.assertEqual(409, response.status_code)
        self.assertEqual("stop_not_current", response.get_json()["code"])

        conn = sqlite3.connect(self.db)
        self.assertEqual(before, conn.execute("SELECT COUNT(*) FROM stop_observations").fetchone()[0])
        self.assertEqual("completed", conn.execute(
            "SELECT status FROM stop_review_assignments WHERE id=20"
        ).fetchone()[0])
        conn.close()

        history = self.client.get("/stops/2/community-reviews")
        self.assertEqual(200, history.status_code)
        self.assertEqual(1, len(history.get_json()["reviews"]))

    def test_submission_persists_prospective_comfort_fields_and_assignment_history(self):
        conn = sqlite3.connect(self.db)
        for name, declaration in (
            ("observer", "TEXT"), ("trash_present", "TEXT"),
            ("bench_feasible", "TEXT"), ("concrete_pad_needed", "TEXT"),
            ("ada_clearance_possible", "TEXT"), ("bench_type", "TEXT"),
            ("bench_condition", "TEXT"), ("shelter_type", "TEXT"),
            ("rider_comfort_category", "TEXT"), ("accessibility_status", "TEXT"),
            ("hostile_design", "TEXT"), ("confidence", "TEXT"),
            ("review_mode", "TEXT"), ("reviewer_relationship", "TEXT"),
            ("rider_activity", "TEXT"), ("usage_times", "TEXT"),
            ("property_owner_outreach", "TEXT"), ("steward_email", "TEXT"),
            ("steward_candidate", "INTEGER"), ("streetview_imagery_month", "TEXT"),
        ):
            conn.execute(f"ALTER TABLE stop_observations ADD COLUMN {name} {declaration}")
        conn.execute("""CREATE TABLE stop_improvement_impact(
            physical_stop_id INTEGER,daily_route_exposure REAL,
            average_weekday_boardings REAL)""")
        conn.execute("CREATE TABLE community_stewardships("
                     "stop_id INTEGER,reviewer_id INTEGER,created_at TEXT)")
        conn.execute("INSERT INTO stop_improvement_impact VALUES (1,10,5)")
        conn.execute("INSERT INTO stop_review_assignments VALUES "
                     "(21,1,1,'opportunity',NULL,'assigned',NULL)")
        conn.execute("""INSERT INTO stop_observations
            (id,physical_stop_id,observed_at,shelter_present,bench_present,
             notes,reviewer_id,source,review_mode,streetview_imagery_month)
            VALUES (31,1,'2024-01-02','unknown','unknown','older review',1,
                    'community_review','remote',NULL)""")
        conn.commit()
        conn.close()
        env = os.environ.copy()
        env["DMV_BUS_STOPS_DB"] = str(self.db)
        subprocess.check_call(
            [sys.executable, "scripts/active/create_review_tables.py"],
            cwd=Path(__file__).resolve().parents[1], env=env,
        )
        conn = sqlite3.connect(self.db)
        before = conn.execute("SELECT COUNT(*) FROM stop_observations").fetchone()[0]
        conn.close()
        with self.client.session_transaction() as session:
            session["reviewer_key"] = "reviewer"
        with patch.object(review_api, "calculate_stop_consensus", return_value={}), \
             patch.object(review_api, "refresh_after_community_mutation"):
            response = self.client.post("/review/submit", json={
                "stop_id": 1, "assignment_id": 21,
                "review_mode": "street_view",
                "streetview_imagery_month": "2025-05",
                "weather_exposure": "exposed",
                "riders_avoid_facilities": "yes",
                "seating_type": ["full_bench"],
                "seating_limitations": "dividers",
                "waiting_environment_rating": "poor",
            })
        self.assertEqual(200, response.status_code, response.get_json())
        conn = sqlite3.connect(self.db)
        self.assertEqual(before + 1, conn.execute(
            "SELECT COUNT(*) FROM stop_observations"
        ).fetchone()[0])
        row = conn.execute("""SELECT assignment_id,weather_exposure,
          riders_avoid_facilities,review_mode,streetview_imagery_month,observed_at
          FROM stop_observations WHERE assignment_id=21""").fetchone()
        older = conn.execute("""SELECT id,notes,assignment_id,review_mode,
          streetview_imagery_month FROM stop_observations WHERE id=31""").fetchone()
        conn.close()
        self.assertEqual((21, "exposed", "yes", "street_view", "2025-05"), row[:5])
        self.assertNotEqual(row[4], row[5])
        self.assertEqual((31, "older review", None, "remote", None), older)


if __name__ == "__main__":
    unittest.main()
