import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.api import app as public_api
from src.processing.heading_audit import (
    connected_component_chaining,
    maximum_heading_separation,
    strongly_contradictory,
)


ROOT = Path(__file__).resolve().parents[1]


class ServingDirectionTests(unittest.TestCase):
    def setUp(self):
        handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        handle.close()
        self.db = Path(handle.name)
        conn = sqlite3.connect(self.db)
        conn.executescript(
            """
            CREATE TABLE physical_stop_members(
                physical_stop_id INTEGER, bus_stop_id INTEGER
            );
            CREATE TABLE bus_stops(
                id INTEGER PRIMARY KEY, external_stop_id TEXT
            );
            CREATE TABLE gtfs_stop_map(
                gtfs_stop_id TEXT, bus_stop_id INTEGER, match_method TEXT
            );
            CREATE TABLE stop_wmata_evidence(
                id INTEGER PRIMARY KEY, physical_stop_id INTEGER,
                wmata_stop_id TEXT, wmata_status TEXT, wmata_heading TEXT,
                match_distance_m REAL, match_confidence TEXT, created_at TEXT
            );
            CREATE TABLE physical_stop_identity_state(
                physical_stop_id INTEGER PRIMARY KEY, identity_status TEXT,
                retired_at TEXT
            );
            CREATE TABLE physical_stop_identity_edges(
                predecessor_physical_stop_id INTEGER,
                successor_physical_stop_id INTEGER
            );

            INSERT INTO bus_stops VALUES
                (101,'source-101'),(102,'source-102'),(201,'source-201'),
                (301,'source-301'),(302,'source-302'),(401,'source-401');
            INSERT INTO bus_stops VALUES
                (959,'1002216'),(1185,'1002217');
            INSERT INTO physical_stop_members VALUES
                (1,101),(1,102),(2,201),(3,301),(3,302),(4,401);
            INSERT INTO physical_stop_members VALUES (7755,959),(7756,1185);
            INSERT INTO gtfs_stop_map VALUES
                ('W1',101,'wmata_stop_code'),
                ('W2',102,'wmata_stop_code'),
                ('W3',201,'wmata_stop_code'),
                ('I1',301,'wmata_stop_code'),
                ('I2',302,'wmata_stop_code'),
                ('BAD',401,'wmata_stop_code');
            INSERT INTO gtfs_stop_map VALUES
                ('7867',959,'wmata_stop_code'),('7868',1185,'wmata_stop_code');
            INSERT INTO gtfs_stop_map VALUES ('FALLBACK',101,'coordinate');

            -- The physical_stop_id on evidence is deliberately unreliable.
            INSERT INTO stop_wmata_evidence VALUES
                (1,99,'W1','UNEXPLAINED','119',500,'low','2026-01-01'),
                (2,1,'W2','OTHER','297',2,'high','2026-01-01'),
                (3,1,'UNRELATED','PRS','45',1,'high','2026-01-01'),
                (4,1,'W1','UNEXPLAINED','120',600,'low','2025-01-01'),
                (5,2,'W3','ABS','350',1,'high','2026-01-01'),
                (6,3,'I1','DUP','45',1,'high','2026-01-01'),
                (7,3,'I2','MOA','45',1,'high','2026-01-01'),
                (8,4,'BAD','PRS','not-a-heading',1,'high','2026-01-01');
            INSERT INTO stop_wmata_evidence VALUES
                (9,1,'FALLBACK','ABS','299',1,'high','2026-01-01');
            INSERT INTO stop_wmata_evidence VALUES
                (10,7755,'7867','PRS','119',5,'high','2026-08-26'),
                (11,7756,'7868','PRS','297',5,'high','2026-08-26');
            INSERT INTO physical_stop_identity_state VALUES
                (935,'retired','2026-08-26'),(7755,'current',NULL),(7756,'current',NULL);
            INSERT INTO physical_stop_identity_edges VALUES (935,7755),(935,7756);
            """
        )
        conn.commit()
        conn.close()
        self.patch = patch.object(public_api, "DATABASE_PATH", self.db)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def tearDown(self):
        self.db.unlink(missing_ok=True)

    def test_only_explicit_member_linked_headings_are_returned(self):
        directions = public_api.get_serving_directions(1)
        self.assertEqual(["119", "297"], [d["heading_degrees"] for d in directions])
        self.assertEqual(["W1", "W2"], [d["wmata_stop_id"] for d in directions])
        self.assertNotIn("UNRELATED", {d["wmata_stop_id"] for d in directions})
        self.assertNotIn("FALLBACK", {d["wmata_stop_id"] for d in directions})

    def test_status_and_spatial_distance_do_not_control_identity(self):
        directions = public_api.get_serving_directions(1)
        first = directions[0]
        self.assertEqual("UNEXPLAINED", first["evidence_status"])
        self.assertEqual(500, first["match_distance_m"])
        self.assertEqual("source-101", first["source_stop_id"])
        self.assertEqual("wmata_stop_code", first["linkage_method"])

    def test_contradictory_member_headings_and_provenance_are_preserved(self):
        directions = public_api.get_serving_directions(1)
        self.assertEqual(["Southeast", "Northwest"], [d["compass_label"] for d in directions])
        self.assertEqual([101, 102], [d["member_stop_id"] for d in directions])

    def test_missing_validated_heading_is_not_inferred(self):
        self.assertEqual([], public_api.get_serving_directions(999))
        self.assertEqual([], public_api.get_serving_headings(999))

    def test_malformed_heading_fails_closed(self):
        self.assertIsNone(public_api.compass_heading_label("not-a-heading"))
        self.assertIsNone(public_api.compass_heading_label("NaN"))
        self.assertEqual([], public_api.get_serving_directions(4))

    def test_identical_member_headings_keep_provenance_for_one_ui_label(self):
        directions = public_api.get_serving_directions(3)
        self.assertEqual(["45", "45"], [d["heading_degrees"] for d in directions])
        self.assertEqual({301, 302}, {d["member_stop_id"] for d in directions})
        review = (ROOT / "src/dashboard/static/review_info_loader.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("[...new Set(directions.map", review)

    def test_compass_labels_handle_wraparound(self):
        self.assertEqual("Northbound", public_api.compass_heading_label(350))
        self.assertEqual("Northbound", public_api.compass_heading_label(10))
        self.assertEqual(20, maximum_heading_separation([350, 10]))
        self.assertEqual(178, maximum_heading_separation([119, 297]))
        self.assertFalse(strongly_contradictory([350, 10]))
        self.assertTrue(strongly_contradictory([119, 297]))

    def test_connected_component_chaining_is_detected(self):
        # Consecutive points are below 20 m apart; the endpoints are not.
        coordinates = [(38.9, -77.0), (38.9001, -77.0), (38.9002, -77.0)]
        self.assertTrue(connected_component_chaining(coordinates))

    def test_review_and_stop_pages_use_shared_backend_representation(self):
        review = (ROOT / "src/dashboard/static/review_info_loader.js").read_text(
            encoding="utf-8"
        )
        detail = (ROOT / "src/dashboard/static/stop_detail.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("info.serving_directions", review)
        self.assertIn("review.serving_directions", detail)
        self.assertNotIn("review.serving_headings", detail)

    def test_post_v2_successors_keep_identity_specific_serving_directions(self):
        southeast = public_api.get_serving_directions(7755)
        northwest = public_api.get_serving_directions(7756)
        self.assertEqual(
            [("119", "Southeast", "1002216", "7867")],
            [(item["heading_degrees"], item["compass_label"],
              item["source_stop_id"], item["wmata_stop_id"])
             for item in southeast],
        )
        self.assertEqual(
            [("297", "Northwest", "1002217", "7868")],
            [(item["heading_degrees"], item["compass_label"],
              item["source_stop_id"], item["wmata_stop_id"])
             for item in northwest],
        )

    def test_retired_stop_api_and_page_link_every_successor(self):
        original_testing = public_api.app.testing
        public_api.app.testing = True
        self.addCleanup(setattr, public_api.app, "testing", original_testing)
        response = public_api.app.test_client().get("/stops/935")
        self.assertEqual(410, response.status_code)
        payload = response.get_json()
        self.assertEqual([7755, 7756], payload["successor_stop_ids"])
        self.assertEqual(
            [{"stop_id": 7755, "url": "/stop/7755"},
             {"stop_id": 7756, "url": "/stop/7756"}],
            payload["successors"],
        )
        detail = (ROOT / "src/dashboard/static/stop_detail.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("stopResponse.status === 410", detail)
        self.assertIn("(stop.successors || []).map", detail)
        self.assertIn("Current stop ${successor.stop_id}", detail)

    def test_streetview_orientation_is_not_transit_serving_direction(self):
        api_source = (ROOT / "src/api/app.py").read_text(encoding="utf-8")
        documentation = (ROOT / "docs/serving-directions.md").read_text(
            encoding="utf-8"
        )
        review = (ROOT / "src/dashboard/static/review_info_loader.js").read_text(
            encoding="utf-8"
        )
        self.assertIn('"streetview_display_heading": streetview_display_heading', api_source)
        self.assertNotIn('"heading": heading', api_source)
        self.assertNotIn('"serving_direction":', api_source)
        self.assertIn('"serving_directions": serving_directions', api_source)
        self.assertIn("nearest-road orientation", documentation)
        self.assertIn("must never be substituted", documentation)
        self.assertIn("info.serving_directions", review)
        self.assertNotIn("info.streetview_display_heading", review)


if __name__ == "__main__":
    unittest.main()
