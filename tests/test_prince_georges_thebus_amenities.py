import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "import_prince_georges_thebus_amenities.py"
SPEC = importlib.util.spec_from_file_location("thebus_import", SCRIPT)
thebus = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(thebus)


class TheBusAmenityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "test.db"
        conn = sqlite3.connect(self.db)
        conn.executescript(
            """
            CREATE TABLE physical_stops(id INTEGER PRIMARY KEY, latitude REAL, longitude REAL);
            CREATE TABLE stop_gtfs_status(physical_stop_id INTEGER PRIMARY KEY, current_gtfs INTEGER);
            CREATE TABLE stop_jurisdiction(stop_id INTEGER PRIMARY KEY, state TEXT, county TEXT);
            CREATE TABLE stop_amenity_evidence(
              id INTEGER PRIMARY KEY, physical_stop_id INTEGER, source TEXT,
              source_record_id TEXT, amenity_type TEXT, present INTEGER,
              confidence TEXT, match_distance_m REAL, notes TEXT,
              jurisdiction TEXT, value TEXT, raw_value TEXT,
              source_metadata TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE UNIQUE INDEX idx_stop_amenity_evidence_identity_unique
            ON stop_amenity_evidence(physical_stop_id,source,source_record_id,amenity_type);
            """
        )
        self.add_stop(conn, 1, 38.9, -76.9, 1, "MD", "Prince George's")
        self.add_stop(conn, 2, 38.901, -76.9, 1, "MD", "Prince George's")
        self.add_stop(conn, 3, 38.902, -76.9, 0, "MD", "Prince George's")
        self.add_stop(conn, 4, 38.903, -76.9, None, "MD", "Prince George's")
        self.add_stop(conn, 5, 38.9, -76.89995, 1, "DC", None)
        conn.commit(); conn.close()

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def add_stop(conn, stop_id, lat, lon, current, state, county):
        conn.execute("INSERT INTO physical_stops VALUES (?,?,?)", (stop_id, lat, lon))
        conn.execute("INSERT INTO stop_jurisdiction VALUES (?,?,?)", (stop_id, state, county))
        if current is not None:
            conn.execute("INSERT INTO stop_gtfs_status VALUES (?,?)", (stop_id, current))

    @staticmethod
    def feature(stop_id, lat=38.9, lon=-76.9, shelter="YES", receptacle="NO", ada="YES", route="10", objectid=1):
        return {
            "attributes": {
                "OBJECTID": objectid, "Stop_ID": stop_id, "ROUTE": route,
                "stop_lat": lat, "stop_lon": lon, "SHELTER": shelter,
                "RECEPTACLE": receptacle, "ADA": ada, "SHARED_RT": 0,
                "SHRD_STP": "WMATA F6", "COMMENTS": "raw",
            },
            "geometry": {"x": lon, "y": lat},
        }

    def classify(self, features):
        conn = sqlite3.connect(self.db); conn.row_factory = sqlite3.Row
        result = thebus.classify_groups(conn, features)
        conn.close(); return result

    def test_yes_no_case_and_semantic_mappings(self):
        result = self.classify([self.feature("100", shelter=" Yes ", receptacle="no")])
        rows = {r["amenity_type"]: r for r in result["evidence"]}
        self.assertEqual((rows["shelter"]["present"], rows["shelter"]["value"]), (1, "yes"))
        self.assertEqual((rows["trash_can"]["present"], rows["trash_can"]["value"]), (0, "no"))

    def test_inverse_yes_no_mappings(self):
        result = self.classify([self.feature("100", shelter="NO", receptacle="YES")])
        rows = {r["amenity_type"]: r for r in result["evidence"]}
        self.assertEqual(rows["shelter"]["present"], 0)
        self.assertEqual(rows["trash_can"]["present"], 1)

    def test_empty_unknown_and_ada_route_fields_never_emit(self):
        result = self.classify([self.feature("100", shelter="", receptacle="MAYBE")])
        self.assertEqual(result["evidence"], [])
        self.assertNotIn("ADA", thebus.SEMANTIC_FIELDS)
        self.assertNotIn("ROUTE", thebus.SEMANTIC_FIELDS)

    def test_conflicts_are_quarantined_per_amenity(self):
        rows = [
            self.feature("100", shelter="YES", receptacle="YES", objectid=1),
            self.feature("100", shelter="YES", receptacle="NO", objectid=2),
        ]
        result = self.classify(rows)
        self.assertEqual([r["amenity_type"] for r in result["evidence"]], ["shelter"])
        rows[1]["attributes"].update(SHELTER="NO", RECEPTACLE="YES")
        result = self.classify(rows)
        self.assertEqual([r["amenity_type"] for r in result["evidence"]], ["trash_can"])

    def test_same_stop_rows_consolidate_and_preserve_all_metadata(self):
        rows = [self.feature("100", objectid=1), self.feature("100", route="11", objectid=2)]
        result = self.classify(rows)
        self.assertEqual(len(result["evidence"]), 2)
        metadata = json.loads(result["evidence"][0]["source_metadata"])
        self.assertEqual(len(metadata["contributing_rows"]), 2)

    def test_rows_matching_different_stops_quarantine_all(self):
        rows = [self.feature("100", objectid=1), self.feature("100", lat=38.901, objectid=2)]
        result = self.classify(rows)
        self.assertEqual(result["evidence"], [])
        self.assertIn("100", result["matching_quarantine"])

    def test_current_pg_unique_matching_and_failure_closed(self):
        accepted = self.classify([self.feature("100")])
        self.assertEqual(accepted["evidence"][0]["physical_stop_id"], 1)
        for lat in (38.902, 38.903):
            self.assertEqual(self.classify([self.feature("100", lat=lat)])["evidence"], [])
        non_pg = self.classify([self.feature("100", lon=-76.89995)])
        self.assertEqual(non_pg["evidence"], [])

    def test_multiple_candidates_and_no_suffix_or_route_matching(self):
        conn = sqlite3.connect(self.db)
        self.add_stop(conn, 6, 38.9, -76.90001, 1, "MD", "Prince George's")
        conn.commit(); conn.close()
        result = self.classify([self.feature("3000001", route="1")])
        self.assertEqual(result["evidence"], [])

    def test_different_source_ids_can_share_physical_stop(self):
        result = self.classify([self.feature("100", objectid=1), self.feature("101", objectid=2)])
        self.assertEqual({r["source_record_id"] for r in result["evidence"]}, {"100", "101"})

    def test_reconciliation_is_idempotent_refreshes_moves_and_removes_stale(self):
        conn = sqlite3.connect(self.db); conn.row_factory = sqlite3.Row
        first = self.classify([self.feature("100", shelter="YES")])
        conn.execute("BEGIN"); thebus.apply_reconciliation(conn, first); conn.commit()
        for evidence in first["evidence"]:
            evidence["source_metadata"] = '{"refreshed":true}'
            evidence["physical_stop_id"] = 2
        conn.execute("BEGIN"); thebus.apply_reconciliation(conn, first); conn.commit()
        rows = list(conn.execute("SELECT physical_stop_id,source_metadata FROM stop_amenity_evidence WHERE source=?", (thebus.SOURCE,)))
        self.assertEqual(len(rows), 2)
        self.assertEqual({row[0] for row in rows}, {2})
        conflict = self.classify([
            self.feature("100", shelter="YES", receptacle="YES", objectid=1),
            self.feature("100", shelter="NO", receptacle="YES", objectid=2),
        ])
        conn.execute("BEGIN"); thebus.apply_reconciliation(conn, conflict); conn.commit()
        types = {r[0] for r in conn.execute("SELECT amenity_type FROM stop_amenity_evidence WHERE source=?", (thebus.SOURCE,))}
        self.assertEqual(types, {"trash_can"})
        conn.close()

    def test_rollback_restores_prior_rows(self):
        conn = sqlite3.connect(self.db, isolation_level=None); conn.row_factory = sqlite3.Row
        classified = self.classify([self.feature("100")])
        conn.execute("BEGIN IMMEDIATE")
        thebus.apply_reconciliation(conn, classified)
        conn.rollback()
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM stop_amenity_evidence").fetchone()[0], 0)
        conn.close()


if __name__ == "__main__":
    unittest.main()
