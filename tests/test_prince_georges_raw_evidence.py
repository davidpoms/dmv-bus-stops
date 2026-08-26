import importlib.util
import json
import sqlite3
import tempfile
import unittest
import uuid
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "active" / "import_prince_georges_raw_evidence.py"
SPEC = importlib.util.spec_from_file_location("pg_import", SCRIPT)
pg = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pg)


class PrinceGeorgesRawEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "test.db"
        conn = sqlite3.connect(self.db)
        conn.executescript(
            """
            CREATE TABLE physical_stops(id INTEGER PRIMARY KEY, latitude REAL, longitude REAL);
            CREATE TABLE stop_gtfs_status(physical_stop_id INTEGER PRIMARY KEY, current_gtfs INTEGER);
            CREATE TABLE stop_jurisdiction(stop_id INTEGER PRIMARY KEY, state TEXT, county TEXT);
            CREATE TABLE bus_stops(id INTEGER PRIMARY KEY, external_stop_id TEXT);
            CREATE TABLE physical_stop_members(physical_stop_id INTEGER, bus_stop_id INTEGER);
            CREATE TABLE stop_amenity_evidence(id INTEGER PRIMARY KEY, amenity_type TEXT);
            """
        )
        self.add_stop(conn, 1, 38.90000, -76.90000, 1, "MD", "Prince George's", "3000001")
        self.add_stop(conn, 2, 38.90100, -76.90000, 1, "MD", "Prince George's", "3000002")
        self.add_stop(conn, 3, 38.90200, -76.90000, 0, "MD", "Prince George's", "3000003")
        self.add_stop(conn, 4, 38.90300, -76.90000, None, "MD", "Prince George's", "3000004")
        self.add_stop(conn, 5, 38.90000, -76.89995, 1, "DC", None, "3000005")
        conn.commit()
        conn.close()

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def add_stop(conn, stop_id, lat, lon, current, state, county, external):
        conn.execute("INSERT INTO physical_stops VALUES (?,?,?)", (stop_id, lat, lon))
        conn.execute("INSERT INTO stop_jurisdiction VALUES (?,?,?)", (stop_id, state, county))
        conn.execute("INSERT INTO bus_stops VALUES (?,?)", (stop_id, external))
        conn.execute("INSERT INTO physical_stop_members VALUES (?,?)", (stop_id, stop_id))
        if current is not None:
            conn.execute("INSERT INTO stop_gtfs_status VALUES (?,?)", (stop_id, current))

    @staticmethod
    def feature(reg_id, lat, lon, globalid=None, **extra):
        attrs = {
            "GLOBALID": globalid or str(uuid.uuid4()), "REG_ID": reg_id,
            "BSTP_LAT": lat, "BSTP_LON": lon, "BSTP_HAS_B": "Y",
        }
        attrs.update(extra)
        return {"attributes": attrs, "geometry": {"x": lon, "y": lat}}

    def classify(self, features):
        conn = sqlite3.connect(self.db)
        conn.row_factory = sqlite3.Row
        result = pg.classify_features(conn, features)
        conn.close()
        return result

    def test_globalid_normalization_and_rejection(self):
        value = "{" + str(uuid.uuid4()).upper() + "}"
        self.assertEqual(pg.normalize_globalid(value), value[1:-1].lower())
        for bad in (None, "", "None", "not-a-guid"):
            with self.assertRaises(ValueError):
                pg.normalize_globalid(bad)

    def test_exact_full_id_and_no_suffix_match(self):
        accepted = self.classify([self.feature("3000001", 38.9, -76.9)])
        self.assertEqual(accepted["accepted"][0]["match_method"], "exact_reg_id")
        suffix = self.classify([self.feature("1", 39.5, -77.5)])
        self.assertEqual(len(suffix["accepted"]), 0)

    def test_exact_over_50m_is_review(self):
        result = self.classify([self.feature("3000001", 38.91, -76.9)])
        self.assertEqual(result["review"][0]["reason"], "exact_id_over_50m")

    def test_unique_spatial_fallback_and_ambiguous_review(self):
        result = self.classify([self.feature("unknown", 38.901, -76.9)])
        self.assertEqual(result["accepted"][0]["match_method"], "unique_spatial_10m")
        conn = sqlite3.connect(self.db)
        self.add_stop(conn, 6, 38.90100, -76.89999, 1, "MD", "Prince George's", "3000006")
        conn.commit(); conn.close()
        result = self.classify([self.feature("unknown", 38.901, -76.9)])
        self.assertEqual(result["review"][0]["reason"], "spatial_review")

    def test_inactive_missing_and_non_pg_exact_ids_are_rejected(self):
        for reg_id, lat in (("3000003", 38.902), ("3000004", 38.903), ("3000005", 38.9)):
            result = self.classify([self.feature(reg_id, lat, -76.9)])
            self.assertEqual(len(result["accepted"]), 0)
        non_pg = self.classify([self.feature("3000005", 38.9, -76.89995)])
        self.assertEqual(non_pg["unmatched"][0]["reason"], "exact_id_non_pg")

    def test_schema_identity_is_source_centric_and_record_can_move(self):
        conn = sqlite3.connect(self.db)
        pg.setup_schema(conn)
        indexes = list(conn.execute("PRAGMA index_info(idx_jurisdiction_source_evidence_identity)"))
        self.assertEqual([row[2] for row in indexes], ["source", "source_record_id"])
        gid = str(uuid.uuid4())
        first = self.feature("3000001", 38.9, -76.9, gid)
        result = self.classify([first])["accepted"]
        pg.upsert_rows(conn, result)
        result[0]["physical_stop_id"] = 2
        pg.upsert_rows(conn, result)
        self.assertEqual(conn.execute("SELECT COUNT(*), physical_stop_id FROM jurisdiction_source_evidence").fetchone(), (1, 2))
        conn.close()

    def test_idempotence_metadata_refresh_multiple_records_and_no_amenities(self):
        gid1, gid2 = str(uuid.uuid4()), str(uuid.uuid4())
        features = [
            self.feature("3000001", 38.9, -76.9, gid1, marker="old"),
            self.feature("another", 38.9, -76.9, gid2),
        ]
        conn = sqlite3.connect(self.db)
        conn.row_factory = sqlite3.Row
        classified = pg.classify_features(conn, features)
        conn.execute("BEGIN")
        pg.setup_schema(conn); pg.upsert_rows(conn, classified["accepted"]); conn.commit()
        features[0]["attributes"]["marker"] = "new"
        classified = pg.classify_features(conn, features)
        conn.execute("BEGIN"); pg.upsert_rows(conn, classified["accepted"]); conn.commit()
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM jurisdiction_source_evidence").fetchone()[0], 2)
        metadata = json.loads(conn.execute("SELECT source_metadata FROM jurisdiction_source_evidence WHERE source_record_id=?", (gid1,)).fetchone()[0])
        self.assertEqual(metadata["marker"], "new")
        self.assertEqual(metadata["BSTP_HAS_B"], "Y")
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM stop_amenity_evidence").fetchone()[0], 0)
        conn.close()

    def test_transaction_rolls_back_on_validation_failure(self):
        feature = self.feature("3000001", 38.9, -76.9)
        conn = sqlite3.connect(self.db, isolation_level=None)
        conn.row_factory = sqlite3.Row
        accepted = pg.classify_features(conn, [feature])["accepted"]
        conn.execute("BEGIN IMMEDIATE")
        pg.setup_schema(conn); pg.upsert_rows(conn, accepted)
        with self.assertRaises(RuntimeError):
            pg.validate_applied(conn, [])
        conn.rollback()
        exists = conn.execute("SELECT 1 FROM sqlite_master WHERE name='jurisdiction_source_evidence'").fetchone()
        self.assertIsNone(exists)
        conn.close()


if __name__ == "__main__":
    unittest.main()
