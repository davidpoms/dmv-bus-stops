import importlib.util
import json
import sqlite3
import unittest
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "import_falls_church_amenities.py"
SPEC = importlib.util.spec_from_file_location("falls_church_importer", SCRIPT)
importer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(importer)


class FallsChurchAmenityImporterTests(unittest.TestCase):
    def setUp(self):
        self.db = ROOT / f".falls_church_test_{uuid.uuid4().hex}.db"
        conn = sqlite3.connect(self.db)
        conn.executescript(
            """
            CREATE TABLE physical_stops(id INTEGER PRIMARY KEY, primary_name TEXT);
            CREATE TABLE stop_gtfs_status(
              physical_stop_id INTEGER PRIMARY KEY, current_gtfs INTEGER);
            CREATE TABLE stop_jurisdiction(
              stop_id INTEGER PRIMARY KEY, state TEXT, county TEXT,
              municipality TEXT);
            CREATE TABLE stop_amenity_evidence(
              id INTEGER PRIMARY KEY, physical_stop_id INTEGER, source TEXT,
              source_record_id TEXT, amenity_type TEXT, present INTEGER,
              confidence TEXT, match_distance_m REAL, notes TEXT,
              jurisdiction TEXT, value TEXT, raw_value TEXT,
              source_metadata TEXT);
            CREATE UNIQUE INDEX idx_evidence_identity ON stop_amenity_evidence
              (physical_stop_id,source,source_record_id,amenity_type);
            """
        )
        for _, _, stop_id, name in importer.CURATED_CROSSWALKS:
            conn.execute("INSERT INTO physical_stops VALUES (?,?)", (stop_id, name))
            conn.execute("INSERT INTO stop_gtfs_status VALUES (?,1)", (stop_id,))
            conn.execute(
                "INSERT INTO stop_jurisdiction VALUES (?,?,?,?)",
                (stop_id, "VA", "Falls Church", "Falls Church"),
            )
        conn.commit()
        conn.close()

    def tearDown(self):
        for suffix in ("", "-shm", "-wal", "-journal"):
            path = Path(str(self.db) + suffix)
            if path.exists():
                path.unlink()

    def connect(self):
        return sqlite3.connect(self.db)

    def test_all_records_validate_and_identities_are_stable(self):
        conn = self.connect()
        rows = importer.validate_crosswalks(conn)
        conn.close()
        self.assertEqual(len(rows), 8)
        identities = [r["source_record_id"] for r in rows]
        self.assertEqual(len(identities), len(set(identities)))
        self.assertTrue(all(identities))
        self.assertEqual(identities, [r[0] for r in importer.CURATED_CROSSWALKS])

    def assert_validation_fails(self, statement, parameters):
        conn = self.connect()
        conn.execute(statement, parameters)
        conn.commit()
        with self.assertRaises(RuntimeError):
            importer.validate_crosswalks(conn)
        conn.close()

    def test_inactive_stop_aborts(self):
        self.assert_validation_fails(
            "UPDATE stop_gtfs_status SET current_gtfs=0 WHERE physical_stop_id=?",
            (4324,),
        )

    def test_missing_status_aborts(self):
        self.assert_validation_fails(
            "DELETE FROM stop_gtfs_status WHERE physical_stop_id=?", (4324,)
        )

    def test_non_falls_church_stop_aborts(self):
        self.assert_validation_fails(
            "UPDATE stop_jurisdiction SET county='Fairfax' WHERE stop_id=?", (4324,)
        )

    def test_changed_target_aborts_without_fallback(self):
        self.assert_validation_fails(
            "UPDATE physical_stops SET primary_name='W Broad St+Birch St Bay 2' WHERE id=?",
            (4324,),
        )
        self.assertFalse(hasattr(importer, "spatial_match"))
        self.assertFalse(hasattr(importer, "suffix_match"))

    def test_emits_exact_positive_semantics(self):
        conn = self.connect()
        rows = importer.evidence_rows(importer.validate_crosswalks(conn))
        conn.close()
        self.assertEqual(len(rows), 32)
        for amenity in importer.AMENITY_TYPES:
            selected = [r for r in rows if r["amenity_type"] == amenity]
            self.assertEqual(len(selected), 8)
            self.assertTrue(all(r["present"] == 1 and r["value"] == "yes" for r in selected))
        self.assertFalse(
            {"sign", "recycling", "real_time_sign", "ada", "accessible"}
            & {r["amenity_type"] for r in rows}
        )
        self.assertEqual({r["present"] for r in rows}, {1})
        self.assertEqual(
            {r["source_record_id"] for r in rows},
            {r[0] for r in importer.CURATED_CROSSWALKS},
        )

    def test_metadata_preserves_required_provenance(self):
        conn = self.connect()
        row = importer.evidence_rows(importer.validate_crosswalks(conn))[0]
        conn.close()
        metadata = json.loads(row["source_metadata"])
        self.assertEqual(metadata["official_city_source_url"], importer.SOURCE_URL)
        self.assertTrue(metadata["curated_match"])
        self.assertEqual(
            metadata["matching_method"],
            "directional_intersection_manual_crosswalk",
        )

    def test_apply_is_idempotent_and_ambiguous_locations_are_excluded(self):
        first = importer.run(self.db, apply=True)
        second = importer.run(self.db, apply=True)
        conn = self.connect()
        rows = list(
            conn.execute(
                "SELECT source_record_id,amenity_type,present FROM stop_amenity_evidence"
            )
        )
        conn.close()
        self.assertEqual(len(rows), 32)
        self.assertEqual(first["expected_inserts"], 32)
        self.assertEqual(second["expected_inserts"], 0)
        self.assertEqual(second["expected_updates"], 32)
        emitted = {row[0] for row in rows}
        self.assertTrue(all("roosevelt" not in identity for identity in emitted))
        self.assertEqual(second["quarantined_count"], 7)

    def test_failure_rolls_back_and_preserves_prior_state(self):
        importer.run(self.db, apply=True)
        conn = self.connect()
        conn.execute(
            "UPDATE physical_stops SET primary_name='Changed' WHERE id=4324"
        )
        conn.commit()
        before = list(
            conn.execute(
                "SELECT physical_stop_id,source_record_id,amenity_type,present "
                "FROM stop_amenity_evidence ORDER BY 1,2,3"
            )
        )
        conn.close()
        with self.assertRaises(RuntimeError):
            importer.run(self.db, apply=True)
        conn = self.connect()
        after = list(
            conn.execute(
                "SELECT physical_stop_id,source_record_id,amenity_type,present "
                "FROM stop_amenity_evidence ORDER BY 1,2,3"
            )
        )
        conn.close()
        self.assertEqual(before, after)

    def test_invalid_existing_source_row_rolls_back(self):
        conn = self.connect()
        conn.execute(
            """INSERT INTO stop_amenity_evidence
               (physical_stop_id,source,source_record_id,amenity_type,present,value)
               VALUES (4324,?,?,?,?,?)""",
            (importer.SOURCE, "legacy", "sign", 0, "no"),
        )
        conn.commit()
        conn.close()
        with self.assertRaises(RuntimeError):
            importer.run(self.db, apply=True)
        conn = self.connect()
        self.assertEqual(
            conn.execute("SELECT COUNT(*) FROM stop_amenity_evidence").fetchone()[0],
            1,
        )
        conn.close()


if __name__ == "__main__":
    unittest.main()
