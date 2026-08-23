import json
import sqlite3
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
            CREATE TABLE stop_wmata_evidence (
                id INTEGER PRIMARY KEY, physical_stop_id INTEGER, wmata_status TEXT
            );
            INSERT INTO stop_wmata_evidence VALUES (1,1,'PRS'),(2,2,'PRS'),(3,3,'PRS');
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
            CREATE TABLE community_reviewers (
                id INTEGER PRIMARY KEY, reviewer_key TEXT,
                display_name TEXT, profile_created_at TEXT
            );
            INSERT INTO community_reviewers VALUES (1,'reviewer',NULL,NULL);
            CREATE TABLE community_reviewer_routes (reviewer_id INTEGER, route_id INTEGER);
            INSERT INTO community_reviewer_routes VALUES (1,10);
            CREATE TABLE stop_review_assignments (
                id INTEGER PRIMARY KEY, stop_id INTEGER, reviewer_id INTEGER,
                scenario TEXT, status TEXT, completed_at TEXT
            );
            INSERT INTO stop_review_assignments VALUES
                (20,2,1,'opportunity','completed','2026-01-01');
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
        create_review_queue.create_review_queue()
        self.assertEqual({1}, self.queue_ids())

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


if __name__ == "__main__":
    unittest.main()
