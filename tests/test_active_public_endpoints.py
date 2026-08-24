import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import generate_priority_levels
from src.api import app as public_api
from src.amenities.status_synthesis import SCHEMA_SQL


class ActivePublicEndpointTests(unittest.TestCase):
    def setUp(self):
        handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        handle.close()
        self.db = Path(handle.name)
        conn = sqlite3.connect(self.db)
        conn.executescript(
            """
            CREATE TABLE physical_stops (
                id INTEGER PRIMARY KEY, primary_name TEXT,
                latitude REAL, longitude REAL
            );
            INSERT INTO physical_stops VALUES
                (1,'Current PRS',1,1),(2,'Current ABS',2,2),
                (3,'Current no WMATA',3,3),(4,'Inactive favorable',4,4),
                (5,'Missing favorable',5,5);
            CREATE TABLE stop_gtfs_status (
                physical_stop_id INTEGER PRIMARY KEY, current_gtfs INTEGER
            );
            INSERT INTO stop_gtfs_status VALUES (1,1),(2,1),(3,1),(4,0);
            CREATE TABLE improvement_opportunities (
                physical_stop_id INTEGER, opportunity_score REAL
            );
            INSERT INTO improvement_opportunities VALUES
                (1,50),(2,40),(3,30),(4,100),(5,90);
            CREATE TABLE stop_wmata_evidence (
                id INTEGER PRIMARY KEY, physical_stop_id INTEGER,
                wmata_stop_id TEXT, wmata_status TEXT, wmata_heading TEXT,
                wmata_bench INTEGER, wmata_shelter INTEGER,
                wmata_accessible TEXT, match_distance_m REAL,
                match_confidence TEXT, created_at TEXT
            );
            INSERT INTO stop_wmata_evidence VALUES
                (1,1,'W1','PRS',NULL,1,1,'Y',1,'high','2026-01-01'),
                (2,2,'W2','ABS',NULL,0,0,'N',1,'high','2026-01-01'),
                (4,4,'W4','PRS',NULL,1,1,'Y',1,'high','2026-01-01'),
                (5,5,'W5','PRS',NULL,1,1,'Y',1,'high','2026-01-01');
            CREATE TABLE stop_consensus (
                stop_id INTEGER PRIMARY KEY, confidence TEXT,
                has_shelter INTEGER, has_bench INTEGER,
                notes TEXT, updated_at TEXT
            );
            INSERT INTO stop_consensus
                (stop_id,confidence,has_shelter,has_bench)
                VALUES (2,'validated',0,1);
            CREATE TABLE stop_jurisdiction (
                stop_id INTEGER, state TEXT, county TEXT,
                municipality TEXT, dc_ward TEXT, dc_anc TEXT
            );
            INSERT INTO stop_jurisdiction VALUES
                (1,'DC','Test',NULL,NULL,NULL),(2,'DC','Test',NULL,NULL,NULL),
                (3,'DC','Test',NULL,NULL,NULL),(4,'DC','Test',NULL,NULL,NULL),
                (5,'DC','Test',NULL,NULL,NULL);
            CREATE TABLE stop_amenity_evidence (
                id INTEGER PRIMARY KEY, physical_stop_id INTEGER, source TEXT,
                source_record_id TEXT, amenity_type TEXT, present INTEGER,
                confidence TEXT, match_distance_m REAL, notes TEXT,
                jurisdiction TEXT, value TEXT, raw_value TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO stop_amenity_evidence VALUES
                (1,1,'DDOT','legacy-1','shelter',1,'low',1,'legacy',
                 'DISTRICT_OF_COLUMBIA','yes','1','2026-01-01'),
                (2,1,'DDOT_ARCGIS','arcgis-1','shelter',1,'high',1,'clean',
                 'DISTRICT_OF_COLUMBIA','yes','1','2026-01-02'),
                (3,2,'ALEXANDRIA','alex-1','bench',1,'high',1,'local',
                 'ALEXANDRIA','yes','1','2026-01-01'),
                (4,4,'DDOT_ARCGIS','arcgis-4','shelter',1,'high',1,'inactive',
                 'DISTRICT_OF_COLUMBIA','yes','1','2026-01-01'),
                (5,5,'DDOT_ARCGIS','arcgis-5','bench',1,'high',1,'missing',
                 'DISTRICT_OF_COLUMBIA','yes','1','2026-01-01');
            CREATE TABLE stop_improvement_impact (
                physical_stop_id INTEGER, opportunity_score REAL,
                impact_level TEXT
            );
            INSERT INTO stop_improvement_impact VALUES
                (1,50,'high'),(2,40,'medium'),(3,30,'low'),
                (4,100,'very_high'),(5,90,'very_high');
            CREATE TABLE physical_stop_members (
                physical_stop_id INTEGER, bus_stop_id INTEGER
            );
            INSERT INTO physical_stop_members VALUES
                (1,101),(2,102),(3,103),(4,104),(5,105);
            CREATE TABLE bus_stops (id INTEGER PRIMARY KEY);
            INSERT INTO bus_stops VALUES (101),(102),(103),(104),(105);
            CREATE TABLE stop_routes (stop_id INTEGER, route_id INTEGER);
            INSERT INTO stop_routes VALUES
                (101,10),(102,10),(103,10),(104,10),(105,10);
            CREATE TABLE routes (id INTEGER PRIMARY KEY, route_id TEXT, route_name TEXT);
            INSERT INTO routes VALUES (10,'C61','Route C61');
            """
        )
        conn.executescript(SCHEMA_SQL)
        conn.executemany(
            """
            INSERT INTO stop_amenity_status(
                physical_stop_id,amenity_type,derived_status,consensus_status,updated_at
            ) VALUES (?,?,?,'not_reached','test')
            """,
            [
                (1,"shelter","likely_yes"),(1,"bench","unknown"),
                (2,"shelter","unknown"),(2,"bench","likely_yes"),
                (3,"shelter","unknown"),(3,"bench","unknown"),
            ],
        )
        conn.commit()
        conn.close()
        self.db_patch = patch.object(public_api, "DATABASE_PATH", self.db)
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        public_api.app.config.update(TESTING=True, SECRET_KEY="test")
        self.client = public_api.app.test_client()

    def tearDown(self):
        self.db.unlink(missing_ok=True)

    def test_active_population_endpoints_ignore_wmata_values(self):
        features = self.client.get("/map/stops").get_json()["features"]
        self.assertEqual({1, 2, 3}, {
            feature["properties"]["stop_id"] for feature in features
        })

        top = self.client.get("/priorities/top").get_json()
        self.assertEqual(
            {"Current PRS", "Current ABS", "Current no WMATA"},
            {item["location"] for item in top},
        )

        routes = self.client.get("/routes").get_json()
        self.assertEqual("C61", routes[0]["route_id"])
        self.assertEqual(3, routes[0]["stop_count"])

    def test_priority_summary_is_safe_before_and_populated_after_rebuild(self):
        response = self.client.get("/priority-summary")
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {"P1": 0, "P2": 0, "P3": 0, "monitor": 0},
            response.get_json(),
        )

        generate_priority_levels.generate_priority_levels(self.db)
        self.assertEqual(
            {"P1": 0, "P2": 0, "P3": 1, "monitor": 2},
            self.client.get("/priority-summary").get_json(),
        )

    def test_current_amenity_boundary_quarantines_legacy_ddot(self):
        evidence = public_api.get_current_amenity_evidence(1)
        self.assertEqual({"DDOT_ARCGIS"}, {row[1] for row in evidence})

        supported = public_api.get_current_amenity_evidence(2)
        self.assertEqual({"ALEXANDRIA"}, {row[1] for row in supported})

        conn = sqlite3.connect(self.db)
        legacy_rows = conn.execute(
            "SELECT COUNT(*) FROM stop_amenity_evidence WHERE source='DDOT'"
        ).fetchone()[0]
        conn.close()
        self.assertEqual(1, legacy_rows)

    def test_validation_update_uses_configured_database_path(self):
        response = self.client.post(
            "/validation/update",
            json={"stop_id": 1, "confidence": "validated", "notes": "test"},
        )
        self.assertEqual(200, response.status_code)
        conn = sqlite3.connect(self.db)
        row = conn.execute(
            "SELECT confidence,notes FROM stop_consensus WHERE stop_id=1"
        ).fetchone()
        conn.close()
        self.assertEqual(("validated", "test"), row)

    def test_public_amenity_counts_use_local_and_community_evidence(self):
        summary = self.client.get("/api/evidence-summary").get_json()
        self.assertEqual(
            {
                "total": 3,
                "likely_shelter": 1,
                "likely_bench": 1,
                "no_shelter_evidence": 2,
            },
            summary,
        )

        geography = self.client.get("/pipeline/geography").get_json()
        county = next(row for row in geography if row["type"] == "County")
        self.assertEqual(3, county["total_stops"])
        self.assertEqual(1, county["shelter_known_or_likely_present"])
        self.assertEqual(1, county["bench_known_or_likely_present"])
        self.assertEqual(2, county["shelter_unknown"])
        self.assertEqual(2, county["bench_unknown"])

    def test_public_payload_and_frontends_do_not_claim_wmata_amenities(self):
        metadata = public_api.get_wmata_evidence(1)
        self.assertNotIn("wmata_shelter", metadata)
        self.assertNotIn("wmata_bench", metadata)
        self.assertNotIn("wmata_status", metadata)

        root = Path(__file__).resolve().parents[1]
        dashboard = (root / "src/dashboard/static/dashboard.js").read_text(
            encoding="utf-8"
        )
        review = (root / "src/dashboard/static/review_stop.js").read_text(
            encoding="utf-8"
        )
        for source in (dashboard, review):
            self.assertNotIn("wmata_shelter", source)
            self.assertNotIn("wmata_bench", source)
            self.assertNotIn("WMATA-reported stop amenities", source)
            self.assertNotIn("likely has a shelter", source)


if __name__ == "__main__":
    unittest.main()
