import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.assessment import create_opportunity_assessments
from src.scoring.rider_exposure import percentile_by_stop
from src.api import app as api_app


class RiderExposureTests(unittest.TestCase):
    def test_cume_dist_percentiles_are_monotonic_and_preserve_ties(self):
        ranks = percentile_by_stop({1: 0, 2: None, 3: 10, 4: 10, 5: 20})
        self.assertEqual(ranks[1], ranks[2])
        self.assertEqual(ranks[3], ranks[4])
        self.assertLess(ranks[1], ranks[3])
        self.assertLess(ranks[3], ranks[5])
        self.assertEqual(100, ranks[5])

    def test_assessment_rebuild_uses_latest_period_distinct_routes_and_regenerates(self):
        handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        handle.close()
        path = Path(handle.name)
        conn = sqlite3.connect(path)
        conn.executescript("""
        CREATE TABLE physical_stops(id INTEGER PRIMARY KEY);
        INSERT INTO physical_stops VALUES (1),(2),(3);
        CREATE TABLE stop_gtfs_status(physical_stop_id INTEGER PRIMARY KEY,current_gtfs INTEGER);
        INSERT INTO stop_gtfs_status VALUES (1,1),(2,1),(3,0);
        CREATE TABLE physical_stop_members(physical_stop_id INTEGER,bus_stop_id INTEGER);
        INSERT INTO physical_stop_members VALUES (1,11),(1,12),(2,21),(3,31);
        CREATE TABLE stop_routes(stop_id INTEGER,route_id INTEGER);
        INSERT INTO stop_routes VALUES (11,101),(12,101),(21,102),(31,103);
        CREATE TABLE routes(id INTEGER PRIMARY KEY,route_id TEXT);
        INSERT INTO routes VALUES (101,'A'),(102,'B'),(103,'C');
        CREATE TABLE ridership_snapshots(route_id TEXT,weekday_boardings REAL,period TEXT);
        INSERT INTO ridership_snapshots VALUES
          ('A',999,'2026-06-30'),('A',100,'2026-07-31'),
          ('A',100,'2026-07-31'),('B',100,'2026-07-31'),
          ('C',1000,'2026-07-31');
        CREATE TABLE stop_priority_snapshots(stop_id INTEGER,factors TEXT,calculated_date TEXT);
        """)
        conn.close()
        try:
            with patch.object(create_opportunity_assessments, "DATABASE_PATH", path):
                create_opportunity_assessments.create_assessments()
                create_opportunity_assessments.create_assessments()
            conn = sqlite3.connect(path)
            rows = conn.execute("""SELECT physical_stop_id,combined_route_weekday_boardings,
                rider_exposure_percentile,assessment_json
                FROM opportunity_assessments ORDER BY physical_stop_id""").fetchall()
            self.assertEqual(2, len(rows))
            self.assertEqual(100, rows[0][1])  # duplicate route membership counted once
            self.assertEqual(rows[0][2], rows[1][2])
            self.assertEqual(100, rows[0][2])
            self.assertEqual(rows[0][2], json.loads(rows[0][3])["rider_exposure_percentile"])
        finally:
            conn.close()
            path.unlink(missing_ok=True)

    def test_average_weekday_uses_calendar_and_score_is_not_percentile(self):
        handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        handle.close()
        path = Path(handle.name)
        conn = sqlite3.connect(path)
        conn.execute("CREATE TABLE ridership_snapshots(period TEXT)")
        conn.execute("INSERT INTO ridership_snapshots VALUES ('2026-02-28')")
        conn.commit()
        conn.close()
        try:
            with patch.object(api_app, "DATABASE_PATH", path):
                self.assertEqual(20, api_app.latest_ridership_weekdays())
        finally:
            path.unlink(missing_ok=True)
        scoring_source = Path(create_opportunity_assessments.__file__).parents[1]
        scoring_source = scoring_source / "scoring" / "calculate_stop_priority.py"
        text = scoring_source.read_text(encoding="utf-8")
        self.assertIn('"route_exposure_score"', text)
        self.assertNotIn('"rider_exposure_percentile"', text)


if __name__ == "__main__":
    unittest.main()
