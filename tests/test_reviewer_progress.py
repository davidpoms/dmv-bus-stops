"""Controlled file-backed fixtures for private, nonpersistent progress."""
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from src.api import app as api
from src.review import progress


class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "progress.db"
        self.db = sqlite3.connect(self.path)
        self.addCleanup(self.db.close)
        self.db.executescript("""
            CREATE TABLE community_reviewers(id INTEGER PRIMARY KEY,reviewer_key TEXT,display_name TEXT);
            INSERT INTO community_reviewers VALUES(1,'owner-key','<script>Owner</script>'),(2,'other-key','Other');
            CREATE TABLE physical_stops(id INTEGER PRIMARY KEY);
            CREATE TABLE stop_gtfs_status(physical_stop_id INTEGER PRIMARY KEY,current_gtfs INTEGER);
            CREATE TABLE stop_jurisdiction(stop_id INTEGER,state TEXT,county TEXT,municipality TEXT,dc_ward TEXT,dc_anc TEXT);
            CREATE TABLE stop_review_assignments(id INTEGER PRIMARY KEY,stop_id INTEGER,reviewer_id INTEGER,status TEXT,completed_at TEXT);
            CREATE TABLE stop_observations(id INTEGER PRIMARY KEY,assignment_id INTEGER,physical_stop_id INTEGER,reviewer_id INTEGER,source TEXT);
            CREATE INDEX assignment_stop ON stop_review_assignments(stop_id);
            CREATE INDEX observation_assignment ON stop_observations(assignment_id);
        """)
        self.db.commit()
        self.patch = patch.object(api, "DATABASE_PATH", self.path)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        old_config = {k: api.app.config[k] for k in ("TESTING", "SECRET_KEY")}
        self.addCleanup(api.app.config.update, old_config)
        api.app.config.update(TESTING=True, SECRET_KEY="progress-test")
        self.client = api.app.test_client()
        self.login()

    def login(self, identity=1, key="owner-key"):
        with self.client.session_transaction() as session:
            session.clear()
            if identity is not None:
                session["authenticated_reviewer_id"] = identity
            if key is not None:
                session["reviewer_key"] = key

    def stop(self, stop, active=1, geo=("DC", None, None, "1.0", "1D")):
        self.db.execute("INSERT INTO physical_stops VALUES(?)", (stop,))
        self.db.execute("INSERT INTO stop_gtfs_status VALUES(?,?)", (stop, active))
        self.db.execute("INSERT INTO stop_jurisdiction VALUES(?,?,?,?,?,?)", (stop, *geo))
        self.db.commit()

    def review(self, assignment, stop, reviewer=1, timestamp="2026-09-23 12:00:00", status="completed", source="community_review"):
        self.db.execute("INSERT INTO stop_review_assignments VALUES(?,?,?,?,?)",
                        (assignment, stop, reviewer, status, timestamp))
        self.db.execute("INSERT INTO stop_observations VALUES(?,?,?,?,?)",
                        (assignment, assignment, stop, reviewer, source))
        self.db.commit()

    def result(self):
        response = self.client.get("/api/reviewer/progress")
        self.assertEqual(200, response.status_code, response.get_json())
        return response.get_json()

    def test_unauthenticated_and_key_only_rejected(self):
        for identity, key in [(None, None), (None, "owner-key"), (1, None)]:
            with self.subTest(identity=identity, key=key):
                self.login(identity, key)
                response = self.client.get("/api/reviewer/progress")
                self.assertEqual(401, response.status_code)
                self.assertEqual("private, no-store", response.headers["Cache-Control"])

    def test_session_identity_must_match_key(self):
        for identity, key in [(1, "other-key"), (99, "owner-key")]:
            self.login(identity, key)
            self.assertEqual(403, self.client.get("/api/reviewer/progress").status_code)

    def test_selectors_rejected(self):
        for query in ["reviewer_id=2", "scope=Fairfax", "reviewer_key=other-key"]:
            self.assertEqual(400, self.client.get("/api/reviewer/progress?" + query).status_code)

    def test_private_response_shape_and_no_consent_dependency(self):
        response = self.client.get("/api/reviewer/progress")
        data = response.get_json()
        self.assertEqual({"as_of", "display_name", "distinct_stops_documented", "explorer",
                          "first_looks", "geographies", "featured_geography", "limitations"}, set(data))
        self.assertEqual("private, no-store", response.headers["Cache-Control"])
        self.assertEqual("<script>Owner</script>", data["display_name"])
        self.assertEqual("application/json", response.mimetype)
        for field in ['"email"', '"reviewer_key"', '"reviewer_id"', '"physical_stop_id"', '"coordinates"', '"consent"']:
            self.assertNotIn(field, response.get_data(as_text=True))
        self.assertNotIn("owner-key", response.get_data(as_text=True))
        self.assertIsNone(data["featured_geography"])

    def test_valid_history_deduplicates_and_preserves_inactive_explorer(self):
        for stop, active in enumerate([1, 0, 2, None], 1):
            self.stop(stop, active)
            self.review(stop, stop)
        self.review(10, 1)
        self.db.execute("INSERT INTO stop_jurisdiction SELECT * FROM stop_jurisdiction WHERE stop_id=1")
        self.db.commit()
        data = self.result()
        self.assertEqual(4, data["distinct_stops_documented"])
        self.assertEqual(4, data["first_looks"]["count"])
        self.assertEqual((1, 1), (data["geographies"][0]["numerator"], data["geographies"][0]["denominator"]))

    def test_invalid_evidence_excluded_before_deduplication(self):
        for i in range(1, 10):
            self.stop(i)
            self.review(i, i)
        self.db.execute("UPDATE stop_observations SET source='import' WHERE id=2")
        self.db.execute("UPDATE stop_review_assignments SET status='assigned' WHERE id=3")
        self.db.execute("UPDATE stop_observations SET reviewer_id=2 WHERE id=4")
        self.db.execute("UPDATE stop_observations SET physical_stop_id=999 WHERE id=5")
        self.db.execute("UPDATE stop_observations SET assignment_id=999 WHERE id=6")
        self.db.execute("INSERT INTO stop_observations VALUES(100,7,999,2,'community_review')")
        self.db.execute("UPDATE stop_review_assignments SET completed_at=NULL WHERE id=8")
        self.db.execute("UPDATE stop_review_assignments SET completed_at='not a date' WHERE id=9")
        self.db.commit()
        self.assertEqual(1, self.result()["distinct_stops_documented"])

    def test_noncommunity_extra_observation_does_not_invalidate(self):
        self.stop(1); self.review(1, 1)
        self.db.execute("INSERT INTO stop_observations VALUES(2,1,1,1,'import')")
        self.db.commit()
        self.assertEqual(1, self.result()["distinct_stops_documented"])

    def test_timestamp_formats_and_invalid_values(self):
        instant = progress.completion_instant("2026-09-23 12:00:00")
        for value in ["2026-09-23T12:00:00Z", "2026-09-23T08:00:00-04:00", "2026-09-23 12:00:00+00:00"]:
            self.assertEqual(instant, progress.completion_instant(value))
        for value in [None, "", "2026-09-23", "2026-09-23T12:00:00", "09/23/2026 12:00", "2026-02-30 12:00:00", "2026-09-23 24:00:00", "2026-09-23T12:00:00+00:99"]:
            self.assertIsNone(progress.completion_instant(value), value)

    def test_explorer_thresholds(self):
        for total, crossed, next_value in [(0, [], 5), (5, [5], 20), (42, [5, 20], 50),
                                            (100, [5, 20, 50, 100], None), (101, [5, 20, 50, 100], None)]:
            with self.subTest(total=total):
                value = progress.explorer_progress(total)
                self.assertEqual([5, 20, 50, 100], value["configured_thresholds"])
                self.assertEqual(crossed, value["crossed_thresholds"])
                self.assertEqual(next_value, value["next_threshold"])
                self.assertEqual(next_value is None, value["all_milestones_reached"])
                self.assertEqual(None if next_value is None else next_value-total, value["remaining"])

    def test_all_five_dynamic_denominators_and_scope_predicates(self):
        stop = 0
        for count, geo in [(26, ("DC", None, None, "Ward 01", "1D")),
                           (127, ("DC", None, None, "1", "1A")),
                           (38, ("DC", None, None, "6.0", "6D")),
                           (159, ("DC", None, None, "6", "6A")),
                           (473, ("VA", "Arlington", "Arlington", None, None))]:
            for _ in range(count):
                stop += 1
                self.stop(stop, geo=geo)
        for geo in [("VA", "Fairfax", "Fairfax", None, None),
                    ("MD", "Prince George's", "Woodlawn", None, None),
                    ("DC", None, "District of Columbia", "2", "2A"),
                    ("VA", "Arlington", "Other", None, None),
                    ("MD", None, None, "1", "1D"),
                    ("VA", "Other", "Arlington", None, None)]:
            stop += 1; self.stop(stop, geo=geo)
        data = self.result()
        self.assertEqual([s[0] for s in progress.SCOPES], [g["scope_key"] for g in data["geographies"]])
        self.assertEqual([26, 38, 153, 197, 473], [g["denominator"] for g in data["geographies"]])
        self.assertEqual([7, 10, 16, 20, 48], [g["required_count"] for g in data["geographies"]])
        self.db.execute("UPDATE stop_gtfs_status SET current_gtfs=0 WHERE physical_stop_id=1")
        self.db.commit()
        self.assertEqual(25, self.result()["geographies"][0]["denominator"])

    def test_rule_boundaries(self):
        for denominator, required in [(9, []), (10, [5,5,8,10]), (11, [5,6,9,11]),
                                       (99, [25,50,75,99]), (100, [10,25,50,75]), (101, [11,26,51,76])]:
            with self.subTest(denominator=denominator):
                data = progress.geography_progress(progress.SCOPES[0], 0, denominator)
                self.assertEqual(required, [t["required_count"] for t in data["configured_tiers"]])
                self.assertEqual(denominator >= 10, data["eligible"])

    def test_geography_crossings_and_completion(self):
        data = progress.geography_progress(progress.SCOPES[0], 5, 10)
        self.assertEqual([25, 50], data["crossed_tiers"])
        self.assertEqual((75, 8, 3), (data["next_tier_percentage"], data["required_count"], data["remaining"]))
        data = progress.geography_progress(progress.SCOPES[0], 10, 10)
        self.assertEqual("all_milestones_reached", data["state"])
        self.assertIsNone(data["remaining"])
        self.assertIsNone(progress.geography_progress(progress.SCOPES[0], 0, 0)["current_percentage"])

    def test_first_look_instant_order_and_numeric_tie(self):
        self.stop(1); self.stop(2)
        self.review(10, 1, timestamp="2026-09-23T08:00:00-04:00")
        self.review(2, 1, reviewer=2, timestamp="2026-09-23 12:00:00")
        self.review(3, 2, timestamp="2026-09-23 12:00:00")
        self.review(4, 2, reviewer=2, timestamp="2026-09-23T13:00:00Z")
        data = self.result()["first_looks"]
        self.assertEqual(1, data["count"])
        self.assertTrue(data["provisional"])
        self.review(5, 2, reviewer=2, timestamp="2026-09-22 12:00:00")
        self.assertEqual(0, self.result()["first_looks"]["count"])

    def test_invalid_competitors_do_not_win(self):
        self.stop(1); self.review(10, 1)
        self.review(2, 1, reviewer=2, timestamp="invalid")
        self.review(3, 1, reviewer=2, timestamp="2026-09-01 00:00:00")
        self.db.execute("INSERT INTO stop_observations VALUES(100,3,1,2,'community_review')")
        self.db.commit()
        self.assertEqual(1, self.result()["first_looks"]["count"])

    def test_authenticated_other_owner_gets_only_own_progress(self):
        self.stop(1); self.review(1, 1)
        self.login(2, "other-key")
        self.assertEqual(0, self.result()["distinct_stops_documented"])

    def test_featured_selection_zero_remaining_tie_and_completed(self):
        make = lambda index, n: progress.geography_progress(progress.SCOPES[index], n, 20)
        self.assertIsNone(progress.featured_geography([make(0,0), make(1,0)]))
        self.assertEqual("dc_anc:6D", progress.featured_geography([make(0,1), make(1,4)])["scope_key"])
        self.assertEqual("dc_anc:1D", progress.featured_geography([make(0,4), make(1,4)])["scope_key"])
        self.assertEqual("dc_anc:1D", progress.featured_geography([make(0,20), make(1,20)])["scope_key"])
        self.assertEqual("dc_anc:6D", progress.featured_geography([make(0,20), make(1,4)])["scope_key"])

    def test_get_never_writes_or_creates_accounts_or_schema(self):
        before = list(self.db.iterdump())
        with patch.object(api, "get_or_create_reviewer", side_effect=AssertionError("must not create")):
            self.result()
            self.login(None, None)
            self.assertEqual(401, self.client.get("/api/reviewer/progress").status_code)
        self.assertEqual(before, list(self.db.iterdump()))

    def test_missing_schema_is_sanitized_and_not_created(self):
        self.db.execute("DROP TABLE stop_observations"); self.db.commit()
        before = list(self.db.iterdump())
        response = self.client.get("/api/reviewer/progress")
        self.assertEqual(503, response.status_code)
        self.assertEqual("progress_unavailable", response.get_json()["code"])
        self.assertNotIn("stop_observations", response.get_data(as_text=True))
        self.assertEqual(before, list(self.db.iterdump()))

    def test_read_snapshot_query_only_and_connection_cleanup(self):
        real_connect = sqlite3.connect
        connections = []
        statements = []
        def connect(*args, **kwargs):
            conn = real_connect(*args, **kwargs)
            conn.set_trace_callback(statements.append)
            connections.append(conn)
            return conn
        for failure in (False, True):
            with self.subTest(failure=failure), patch.object(progress.sqlite3, "connect", side_effect=connect):
                if failure:
                    with patch.object(progress, "MEMBERSHIP_SQL", "SELECT * FROM nonexistent_table"):
                        with self.assertRaises(sqlite3.OperationalError):
                            progress.build_progress(self.path, 1, "owner-key")
                else:
                    progress.build_progress(self.path, 1, "owner-key")
            with self.assertRaises(sqlite3.ProgrammingError):
                connections[-1].execute("SELECT 1")
        self.assertIn("PRAGMA query_only=ON", statements)
        self.assertIn("BEGIN", statements)
        self.assertIn("ROLLBACK", statements)
        self.assertFalse(any(s.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE", "CREATE")) for s in statements))
        with closing(real_connect(self.path)) as conn:
            conn.execute("BEGIN EXCLUSIVE")  # No stranded reader blocks the writer.
            conn.rollback()

    def test_missing_file_not_created(self):
        missing = Path(self.temp.name) / "missing.db"
        with self.assertRaises(sqlite3.OperationalError):
            progress.build_progress(missing, 1, "owner-key")
        self.assertFalse(missing.exists())

    def test_setup_and_auth_failure_close_connections(self):
        real_connect = sqlite3.connect
        connections = []
        class SetupFailure(sqlite3.Connection):
            def execute(self, sql, *args):
                if sql == "PRAGMA query_only=ON":
                    raise sqlite3.OperationalError("injected setup failure")
                return super().execute(sql, *args)
        for setup_failure in (False, True):
            def connect(*args, **kwargs):
                if setup_failure:
                    kwargs["factory"] = SetupFailure
                conn = real_connect(*args, **kwargs)
                connections.append(conn)
                return conn
            with patch.object(progress.sqlite3, "connect", side_effect=connect):
                with self.assertRaises(sqlite3.OperationalError if setup_failure else PermissionError):
                    progress.build_progress(self.path, 1, "wrong-key")
            with self.assertRaises(sqlite3.ProgrammingError):
                connections[-1].execute("SELECT 1")

    def test_query_count_does_not_grow_with_scopes_or_reviews(self):
        real_connect = sqlite3.connect
        statements = []
        def connect(*args, **kwargs):
            conn = real_connect(*args, **kwargs)
            conn.set_trace_callback(statements.append)
            return conn
        for count in (0, 12):
            for i in range(1, count + 1):
                self.stop(i); self.review(i, i)
            statements.clear()
            with patch.object(progress.sqlite3, "connect", side_effect=connect):
                progress.build_progress(self.path, 1, "owner-key")
            reads = [s for s in statements if s.lstrip().upper().startswith(("SELECT", "WITH"))]
            self.assertEqual(3, len(reads))


if __name__ == "__main__":
    unittest.main()
