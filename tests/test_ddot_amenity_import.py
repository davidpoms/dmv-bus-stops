import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.amenities.ddot import build_source_record_id
from src.amenities.matcher import find_nearest_physical_stop


class DdotMatcherTests(unittest.TestCase):
    def setUp(self):
        handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        handle.close()
        self.db = Path(handle.name)
        conn = sqlite3.connect(self.db)
        conn.executescript(
            """
            CREATE TABLE physical_stops (
                id INTEGER PRIMARY KEY,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                primary_name TEXT,
                state TEXT
            );
            CREATE TABLE bus_stops (
                id INTEGER PRIMARY KEY,
                external_stop_id TEXT
            );
            CREATE TABLE physical_stop_members (
                physical_stop_id INTEGER,
                bus_stop_id INTEGER
            );
            """
        )
        conn.executemany(
            "INSERT INTO physical_stops VALUES (?, ?, ?, ?, ?)",
            [
                (11, 38.83544555, -76.9921875,
                 "Wheeler Rd SE+Varney St SE", "DC"),
                (5136, 38.83544555, -76.9921875,
                 "Tantallon Dr+Asbury Dr", "MD"),
            ],
        )
        conn.executemany(
            "INSERT INTO bus_stops VALUES (?, ?)",
            [(1, "1000087"), (2, "3000087")],
        )
        conn.executemany(
            "INSERT INTO physical_stop_members VALUES (?, ?)",
            [(11, 1), (5136, 2)],
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        self.db.unlink(missing_ok=True)

    def test_ddot_1000087_matches_dc_stop_not_suffix_similar_md_stop(self):
        match = find_nearest_physical_stop(
            self.db,
            38.83544555,
            -76.9921875,
            jurisdiction_state="DC",
            maximum_distance_m=100,
        )
        self.assertEqual(11, match["physical_stop_id"])
        self.assertEqual("DC", match["state"])
        self.assertNotEqual(5136, match["physical_stop_id"])

    def test_no_dc_candidate_never_falls_back_to_suffix_similar_md_stop(self):
        conn = sqlite3.connect(self.db)
        conn.execute("DELETE FROM physical_stops WHERE id = 11")
        conn.commit()
        conn.close()

        match = find_nearest_physical_stop(
            self.db,
            38.83544555,
            -76.9921875,
            jurisdiction_state="DC",
            maximum_distance_m=100,
        )
        self.assertIsNone(match)


class DdotIdentityTests(unittest.TestCase):
    def test_repeated_ddot_id_with_distinct_barcodes_stays_distinct(self):
        first = build_source_record_id(
            {"DDOT_ID": 1001126, "Barcode": "DC-000527", "Panel_No": 911013},
            38.900022,
            -76.985613,
        )
        second = build_source_record_id(
            {"DDOT_ID": 1001126, "Barcode": "DC-000558", "Panel_No": 911292},
            38.899885,
            -76.985581,
        )
        self.assertNotEqual(first, second)
        self.assertTrue(first.startswith("barcode:"))

    def test_panel_is_used_when_barcode_is_missing(self):
        identity = build_source_record_id(
            {"DDOT_ID": 1003655, "Panel_No": 911280},
            38.935868,
            -77.024342,
        )
        self.assertEqual("panel:911280", identity)

    def test_ddot_id_alone_is_never_source_identity(self):
        identity = build_source_record_id(
            {"DDOT_ID": 1000087, "Site_Code": 210981},
            38.83544555,
            -76.9921875,
        )
        self.assertNotEqual("1000087", identity)
        self.assertTrue(identity.startswith("site-location:"))

    def test_hash_fallback_is_deterministic(self):
        attrs_a = {"Sales_Address": "Example", "DDOT_ID": 123}
        attrs_b = {"DDOT_ID": 123, "Sales_Address": "Example"}
        first = build_source_record_id(attrs_a, 38.9, -77.0)
        second = build_source_record_id(attrs_b, 38.9, -77.0)
        self.assertEqual(first, second)
        self.assertTrue(first.startswith("feature-sha256:"))


if __name__ == "__main__":
    unittest.main()
