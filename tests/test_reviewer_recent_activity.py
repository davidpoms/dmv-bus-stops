"""Private recent activity against disposable SQLite fixtures."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.api import app as api
from src.review import recent_activity


class RecentActivityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "activity.db"
        self.db = sqlite3.connect(self.path)
        self.addCleanup(self.db.close)
        self.db.executescript("""
            CREATE TABLE community_reviewers(id INTEGER PRIMARY KEY, reviewer_key TEXT);
            INSERT INTO community_reviewers VALUES(1,'owner'),(2,'other');
            CREATE TABLE physical_stops(id INTEGER PRIMARY KEY, primary_name TEXT);
            INSERT INTO physical_stops VALUES(1,'<img src=x onerror=alert(1)>'),(2,NULL),(3,'');
            CREATE TABLE stop_gtfs_status(physical_stop_id INTEGER,current_gtfs INTEGER);
            INSERT INTO stop_gtfs_status VALUES(1,0),(2,1),(3,1);
            CREATE TABLE stop_review_assignments(id INTEGER PRIMARY KEY,stop_id INTEGER,
                reviewer_id INTEGER,status TEXT,completed_at TEXT);
            CREATE TABLE stop_observations(id INTEGER PRIMARY KEY,assignment_id INTEGER,
                physical_stop_id INTEGER,reviewer_id INTEGER,source TEXT,observed_at TEXT);
        """)
        self.db.commit()
        database_patch = patch.object(api, "DATABASE_PATH", self.path)
        database_patch.start()
        self.addCleanup(database_patch.stop)
        config = {k: api.app.config[k] for k in ("TESTING", "SECRET_KEY")}
        self.addCleanup(api.app.config.update, config)
        api.app.config.update(TESTING=True, SECRET_KEY="activity-test")
        self.client = api.app.test_client()
        self.login()

    def login(self, identity=1, key="owner"):
        with self.client.session_transaction() as session:
            session.clear()
            if identity is not None:
                session["authenticated_reviewer_id"] = identity
            if key is not None:
                session["reviewer_key"] = key

    def review(self, assignment, timestamp="2026-10-01 12:00:00", stop=1,
               reviewer=1, status="completed", source="community_review"):
        self.db.execute("INSERT INTO stop_review_assignments VALUES(?,?,?,?,?)",
                        (assignment, stop, reviewer, status, timestamp))
        self.db.execute("INSERT INTO stop_observations VALUES(?,?,?,?,?,?)",
                        (assignment, assignment, stop, reviewer, source, "2026-12-31 23:59:59"))
        self.db.commit()

    def result(self):
        response = self.client.get("/api/reviewer/recent-activity")
        self.assertEqual(200, response.status_code)
        self.assertEqual("private, no-store", response.headers["Cache-Control"])
        return response.get_json()

    def test_owner_only_authorization(self):
        self.review(1)
        self.review(2, reviewer=2, stop=2)
        for identity, key, status in [(None,None,401),(None,"owner",401),
                                      (1,None,401),(1,"other",403),(99,"owner",403)]:
            with self.subTest(identity=identity, key=key):
                self.login(identity, key)
                response = self.client.get("/api/reviewer/recent-activity")
                self.assertEqual(status, response.status_code)
                self.assertEqual("private, no-store", response.headers["Cache-Control"])
                self.assertNotIn("activities", response.get_json())
        for identity, key, stop in [(1,"owner",1),(2,"other",2)]:
            self.login(identity, key)
            self.assertEqual([stop], [r["stop_id"] for r in self.result()["activities"]])

    def test_query_and_body_parameters_rejected(self):
        for options in [{"query_string": {"reviewer_id": 2}},
                        {"query_string": {"reviewer_key": "other"}},
                        {"json": {"reviewer_id": 2}},
                        {"data": {"reviewer_key": "other"}},
                        {"query_string": {"limit": 99}}]:
            response = self.client.get("/api/reviewer/recent-activity", **options)
            self.assertEqual(400, response.status_code)
            self.assertEqual("private, no-store", response.headers["Cache-Control"])

    def test_five_newest_after_qualification_and_repeated_inactive_stops(self):
        for number in range(1, 9):
            self.review(number, f"2026-10-01 12:00:0{number}")
        for number in range(10, 17):
            self.review(number, "2026-10-02 12:00:00", status="assigned")
        self.review(17, "not a timestamp")
        rows = self.result()["activities"]
        self.assertEqual([f"2026-10-01T12:00:0{n}Z" for n in [8,7,6,5,4]],
                         [r["completed_at"] for r in rows])
        self.assertEqual([1] * 5, [r["stop_id"] for r in rows])

    def test_offsets_fractional_seconds_and_numeric_ties(self):
        self.review(9, "2026-10-01T13:00:00+01:00", stop=1)
        self.review(10, "2026-10-01T07:00:00-05:00", stop=2)
        self.review(11, "2026-10-01T12:00:00.123456Z", stop=3)
        self.review(12, "2026-10-01T14:00:00+03:00", stop=1)
        rows = self.result()["activities"]
        self.assertEqual([3,2,1,1], [r["stop_id"] for r in rows])
        self.assertEqual(["2026-10-01T12:00:00.123456Z", "2026-10-01T12:00:00Z",
                          "2026-10-01T12:00:00Z", "2026-10-01T11:00:00Z"],
                         [r["completed_at"] for r in rows])

    def test_invalid_timestamps_do_not_use_observed_at(self):
        for number, value in enumerate([None,"","invalid","2026-10-01T12:00:00",
                                         "2026-02-30 12:00:00"], 1):
            self.review(number, value)
        self.assertEqual([], self.result()["activities"])

    def test_ambiguous_mismatched_missing_and_noncommunity_evidence_excluded(self):
        for number in range(1, 7):
            self.review(number)
        self.db.execute("INSERT INTO stop_observations VALUES(101,1,1,1,'community_review',NULL)")
        # A conflicting duplicate must not disappear during identity matching.
        self.db.execute("INSERT INTO stop_observations VALUES(102,2,2,2,'community_review',NULL)")
        self.db.execute("UPDATE stop_observations SET reviewer_id=2 WHERE id=3")
        self.db.execute("UPDATE stop_observations SET physical_stop_id=2 WHERE id=4")
        self.db.execute("DELETE FROM stop_observations WHERE id=5")
        self.db.execute("UPDATE stop_observations SET source='other' WHERE id=6")
        self.db.commit()
        self.assertEqual([], self.result()["activities"])

    def test_noncommunity_extra_evidence_does_not_duplicate_completion(self):
        self.review(1)
        self.db.execute("INSERT INTO stop_observations VALUES(101,1,1,1,'other',NULL)")
        self.db.commit()
        self.assertEqual(1, len(self.result()["activities"]))

    def test_minimal_payload_and_missing_names(self):
        self.assertEqual([], self.result()["activities"])
        for stop in (1,2,3):
            self.review(stop, stop=stop)
        data = self.result()
        self.assertEqual({"available","activities","limitations"}, set(data))
        self.assertIs(data["available"], True)
        for row in data["activities"]:
            self.assertEqual({"stop_id","stop_name","completed_at"}, set(row))
        self.assertEqual(["Bus Stop","Bus Stop","<img src=x onerror=alert(1)>"],
                         [r["stop_name"] for r in data["activities"]])

    def test_read_only_snapshot_and_cleanup(self):
        self.review(1)
        before = self.path.read_bytes()
        original = sqlite3.connect
        traces, opened = [], []
        def connect(*args, **kwargs):
            self.assertIn("mode=ro", args[0])
            self.assertTrue(kwargs["uri"])
            conn = original(*args, **kwargs)
            conn.set_trace_callback(traces.append)
            opened.append(conn)
            return conn
        with patch.object(recent_activity.sqlite3, "connect", side_effect=connect), \
             patch.object(api, "get_or_create_reviewer", side_effect=AssertionError("Account write")):
            self.result()
        self.assertEqual(before, self.path.read_bytes())
        self.assertEqual(1, len(opened))
        self.assertEqual("PRAGMA query_only=ON", traces[0])
        self.assertEqual("BEGIN", traces[1])
        self.assertEqual("ROLLBACK", traces[-1])
        self.assertFalse(any(s.lstrip().upper().startswith(("INSERT","UPDATE","DELETE","CREATE","ALTER")) for s in traces))
        with self.assertRaises(sqlite3.ProgrammingError):
            opened[0].execute("SELECT 1")

    def test_missing_database_and_schema_fail_without_creation(self):
        missing = self.path.parent / "missing.db"
        empty = self.path.parent / "empty.db"
        sqlite3.connect(empty).close()
        for path in (missing, empty):
            with patch.object(api, "DATABASE_PATH", path):
                response = self.client.get("/api/reviewer/recent-activity")
            self.assertEqual(503, response.status_code)
            self.assertFalse(response.get_json()["available"])
            self.assertEqual("private, no-store", response.headers["Cache-Control"])
            self.assertNotIn(str(path), response.get_data(as_text=True))
        self.assertFalse(missing.exists())
        self.assertEqual(b"", empty.read_bytes())


if __name__ == "__main__":
    unittest.main()
