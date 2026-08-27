import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.diagnostics.audit_osm_contribution_candidates import (
    audit,
    connect_read_only,
    write_output,
)


class OsmContributionAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "audit.db"
        conn = sqlite3.connect(self.db_path)
        conn.executescript(
            """
            CREATE TABLE physical_stops(
              id INTEGER PRIMARY KEY, primary_name TEXT, state TEXT, county TEXT,
              municipality TEXT, dc_ward TEXT);
            CREATE TABLE stop_gtfs_status(physical_stop_id INTEGER,current_gtfs INTEGER);
            CREATE TABLE physical_stop_identity_state(
              physical_stop_id INTEGER,identity_status TEXT);
            CREATE TABLE bus_stops(id INTEGER PRIMARY KEY,external_stop_id TEXT);
            CREATE TABLE physical_stop_members(physical_stop_id INTEGER,bus_stop_id INTEGER);
            CREATE TABLE stop_osm_evidence(
              id INTEGER PRIMARY KEY,stop_id INTEGER,osm_feature_id TEXT,
              osm_tags TEXT,osm_snapshot_date TEXT,osm_source_file TEXT);
            CREATE TABLE osm_features(
              id INTEGER PRIMARY KEY,osm_id INTEGER,osm_type TEXT);
            CREATE TABLE physical_stop_evidence_attribution(
              evidence_table TEXT,evidence_row_id INTEGER,physical_stop_id INTEGER,
              attribution_method TEXT,attribution_version TEXT,provenance_json TEXT,
              attributed_at TEXT);
            CREATE TABLE stop_observations(
              id INTEGER PRIMARY KEY,physical_stop_id INTEGER,shelter_present TEXT,
              bench_present TEXT,observed_at TEXT,source TEXT,review_mode TEXT,
              streetview_imagery_month TEXT);
            CREATE TABLE stop_consensus(
              stop_id INTEGER,has_bench INTEGER,has_shelter INTEGER,confidence REAL);
            CREATE TABLE gtfs_stop_map(
              gtfs_stop_id TEXT,bus_stop_id INTEGER,match_method TEXT);
            CREATE TABLE stop_wmata_evidence(
              id INTEGER,wmata_stop_id TEXT,wmata_heading TEXT,wmata_status TEXT,
              match_distance_m REAL,match_confidence REAL,created_at TEXT);
            """
        )
        for stop_id, status in ((1, "current"), (2, "current"), (3, "current"),
                                (4, "current"), (5, "current"),
                                (6, "manual_exception")):
            conn.execute("INSERT INTO physical_stops VALUES (?,?,?,?,?,?)",
                         (stop_id, f"Stop {stop_id}", "DC", None, None, "1"))
            conn.execute("INSERT INTO stop_gtfs_status VALUES (?,1)", (stop_id,))
            conn.execute("INSERT INTO physical_stop_identity_state VALUES (?,?)",
                         (stop_id, status))
            conn.execute("INSERT INTO bus_stops VALUES (?,?)",
                         (stop_id, f"REF{stop_id}"))
            conn.execute("INSERT INTO physical_stop_members VALUES (?,?)",
                         (stop_id, stop_id))
        evidence = [
            (1, 1, "101", {"ref": "REF1", "highway": "bus_stop",
                            "public_transport": "platform", "shelter": "no"}),
            (2, 2, "102", {"highway": "bus_stop"}),
            (3, 4, "103", {"ref": "REF4"}),
            (4, 5, "104", {"ref": "REF5"}),
            (5, 6, "105", {"ref": "REF6"}),
        ]
        for row_id, stop_id, feature_id, tags in evidence:
            conn.execute(
                "INSERT INTO stop_osm_evidence VALUES (?,?,?,?,?,?)",
                (row_id, stop_id, feature_id, json.dumps(tags), "2025-01-01",
                 "fixture.osm.pbf"),
            )
            conn.execute("INSERT INTO osm_features VALUES (?,?,?)",
                         (int(feature_id), 9000 + row_id, "node"))
        conn.execute(
            "INSERT INTO physical_stop_evidence_attribution VALUES "
            "('stop_osm_evidence',3,NULL,'unresolved',?,?,?)",
            ("physical-stop-v2-cutover-1", "{}", "2026-01-01"),
        )
        conn.execute(
            "INSERT INTO stop_observations VALUES "
            "(11,1,'yes','yes','2026-06-01','community_review','in_person',NULL)"
        )
        conn.execute(
            "INSERT INTO gtfs_stop_map VALUES ('REF1',1,'wmata_stop_code')"
        )
        conn.execute(
            "INSERT INTO stop_wmata_evidence VALUES "
            "(1,'REF1','90','PRS',1,1,'2026-01-01')"
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_exact_spatial_and_unresolved_coverage_and_candidate(self):
        conn = connect_read_only(self.db_path)
        try:
            result = audit(conn)
        finally:
            conn.close()
        self.assertEqual({
            "exact_identity_matched": 3,
            "spatial_only": 1,
            "unresolved_or_no_match": 2,
        }, result["coverage"])
        self.assertEqual(2, result["candidate_count"])
        by_change = {row["change_type"]: row for row in result["candidates"]}
        bench = by_change["osm_missing_bench_community_confirms_present"]
        self.assertEqual(("node", "9001"),
                         (bench["osm_object_type"], bench["osm_object_id"]))
        self.assertEqual([11], bench["supporting_observation_ids"])
        self.assertEqual([90.0], bench["serving_direction_degrees"])
        self.assertEqual("exact_member_ref",
                         bench["exact_match_provenance"]["method"])
        self.assertIn(
            "osm_says_shelter_no_community_confirms_present",
            by_change,
        )
        self.assertEqual(1, result["excluded_evidence"]["unresolved_v2_attribution"])
        self.assertGreater(
            result["classifications"]["bench:insufficient_confidence_no_action"], 0
        )

    def test_read_only_connection_and_json_csv_outputs(self):
        before = self.db_path.read_bytes()
        conn = connect_read_only(self.db_path)
        with self.assertRaises(sqlite3.OperationalError):
            conn.execute("CREATE TABLE forbidden_write(id INTEGER)")
        result = audit(conn)
        conn.close()
        json_path = Path(self.temp_dir.name) / "result.json"
        csv_path = Path(self.temp_dir.name) / "result.csv"
        write_output(json_path, result)
        write_output(csv_path, result)
        self.assertEqual(2, len(json.loads(json_path.read_text())["candidates"]))
        self.assertIn("osm_object_type", csv_path.read_text())
        self.assertEqual(before, self.db_path.read_bytes())

    def test_osm_newer_than_observation_and_manual_exception_fail_closed(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "UPDATE stop_osm_evidence SET osm_tags=? WHERE id=1",
            (json.dumps({"ref": "REF1", "check_date:bench": "2027-01-01"}),),
        )
        conn.commit()
        conn.close()
        conn = connect_read_only(self.db_path)
        try:
            result = audit(conn)
        finally:
            conn.close()
        self.assertEqual(1, result["candidate_count"])
        self.assertNotIn(
            "osm_missing_bench_community_confirms_present",
            {row["change_type"] for row in result["candidates"]},
        )
        self.assertGreaterEqual(
            result["classifications"]["bench:insufficient_confidence_no_action"], 1
        )

    def test_reached_consensus_is_eligible_without_likely_or_inventory_inputs(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("UPDATE stop_observations SET review_mode='remote' WHERE id=11")
        conn.executemany(
            "INSERT INTO stop_observations VALUES "
            "(?,1,'yes','yes',?,'community_review','remote',?)",
            [
                (12, "2026-06-02", "2026-05"),
                (13, "2026-06-03", "2026-06"),
            ],
        )
        conn.execute("INSERT INTO stop_consensus VALUES (1,1,1,0.9)")
        conn.commit()
        conn.close()
        conn = connect_read_only(self.db_path)
        try:
            result = audit(conn)
        finally:
            conn.close()
        self.assertEqual(2, result["candidate_count"])
        for candidate in result["candidates"]:
            self.assertEqual("confirmed_yes", candidate["consensus_status"])
            self.assertEqual([11, 12, 13], candidate["supporting_observation_ids"])
            self.assertEqual("reached community consensus",
                             candidate["reason_for_eligibility"])


if __name__ == "__main__":
    unittest.main()
