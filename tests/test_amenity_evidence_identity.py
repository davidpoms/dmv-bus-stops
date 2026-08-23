import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.migrate_amenity_evidence_identity import migrate
from src.amenities.importer import insert_amenity_evidence


class AmenityEvidenceIdentityTests(unittest.TestCase):
    def setUp(self):
        handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        handle.close()
        self.db = Path(handle.name)
        conn = sqlite3.connect(self.db)
        conn.executescript(
            """
            CREATE TABLE stop_amenity_evidence (
                id INTEGER PRIMARY KEY,
                physical_stop_id INTEGER,
                source TEXT,
                source_record_id TEXT,
                amenity_type TEXT,
                present INTEGER,
                confidence TEXT,
                match_distance_m REAL,
                notes TEXT,
                jurisdiction TEXT,
                value TEXT,
                raw_value TEXT,
                source_metadata TEXT
            );
            CREATE UNIQUE INDEX idx_stop_amenity_evidence_unique
            ON stop_amenity_evidence (physical_stop_id, source, amenity_type);
            """
        )
        conn.close()

    def tearDown(self):
        self.db.unlink(missing_ok=True)

    def test_migration_allows_multiple_source_assets_at_one_stop(self):
        conn = sqlite3.connect(self.db)
        migrate(conn)
        conn.close()
        for identity in ("6000477", "6000483"):
            for amenity in ("ada_bus_pad", "ada_path"):
                insert_amenity_evidence(
                    self.db, 733, "ARLINGTON_COUNTY", identity,
                    amenity, 1,
                )
        conn = sqlite3.connect(self.db)
        self.assertEqual(
            4,
            conn.execute("SELECT COUNT(*) FROM stop_amenity_evidence").fetchone()[0],
        )
        conn.close()

    def test_upsert_is_idempotent_and_refreshes_values(self):
        conn = sqlite3.connect(self.db)
        migrate(conn)
        conn.close()
        insert_amenity_evidence(
            self.db, 1, "ALEXANDRIA", "stop-1", "bench", 0,
        )
        insert_amenity_evidence(
            self.db, 1, "ALEXANDRIA", "stop-1", "bench", 1,
        )
        conn = sqlite3.connect(self.db)
        self.assertEqual(
            (1, 1),
            conn.execute(
                "SELECT COUNT(*), MAX(present) FROM stop_amenity_evidence"
            ).fetchone(),
        )
        conn.close()

    def test_missing_or_placeholder_identity_is_rejected(self):
        conn = sqlite3.connect(self.db)
        migrate(conn)
        conn.close()
        for identity in (None, "", "None", "null", "nan"):
            with self.subTest(identity=identity), self.assertRaises(ValueError):
                insert_amenity_evidence(
                    self.db, 1, "ALEXANDRIA", identity, "bench", 1,
                )

    def test_quarantined_legacy_source_cannot_write(self):
        conn = sqlite3.connect(self.db)
        migrate(conn)
        conn.close()
        with self.assertRaises(ValueError):
            insert_amenity_evidence(
                self.db, 1, "DDOT", "1000087", "shelter", 1,
            )

    def test_migration_aborts_on_supported_full_key_collision(self):
        conn = sqlite3.connect(self.db)
        conn.execute("DROP INDEX idx_stop_amenity_evidence_unique")
        conn.executemany(
            """INSERT INTO stop_amenity_evidence
               (physical_stop_id,source,source_record_id,amenity_type,present)
               VALUES (1,'ALEXANDRIA','stop-1','bench',1)""",
            [(), ()],
        )
        with self.assertRaises(RuntimeError):
            migrate(conn)
        conn.close()


if __name__ == "__main__":
    unittest.main()
