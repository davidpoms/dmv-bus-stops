import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.replace_ddot_shelter_evidence import (
    apply_replacement,
    preflight,
    validate_source_report,
)


class DdotReplacementTests(unittest.TestCase):
    def setUp(self):
        handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        handle.close()
        self.db = Path(handle.name)
        conn = sqlite3.connect(self.db)
        conn.executescript(
            """
            CREATE TABLE physical_stops (
                id INTEGER PRIMARY KEY, latitude REAL, longitude REAL,
                primary_name TEXT, state TEXT
            );
            INSERT INTO physical_stops VALUES
                (11,38.83544555,-76.9921875,'Wheeler','DC'),
                (5136,38.83544555,-76.9921875,'Tantallon','MD');
            CREATE TABLE stop_amenity_evidence (
                id INTEGER PRIMARY KEY, physical_stop_id INTEGER, source TEXT,
                source_record_id TEXT, amenity_type TEXT, present INTEGER,
                confidence TEXT, match_distance_m REAL, notes TEXT,
                jurisdiction TEXT, value TEXT, raw_value TEXT,
                source_metadata TEXT, created_at TEXT
            );
            CREATE UNIQUE INDEX idx_stop_amenity_evidence_identity_unique
            ON stop_amenity_evidence
              (physical_stop_id,source,source_record_id,amenity_type);
            CREATE TABLE stop_ddot_shelter_evidence (
                id INTEGER PRIMARY KEY, physical_stop_id INTEGER, ddot_id TEXT,
                lifecycle_status TEXT
            );
            INSERT INTO stop_ddot_shelter_evidence VALUES
                (1,11,'1000087','CONFIRMED_ACTIVE'),
                (2,5136,'1000087','CONFIRMED_ACTIVE');
            INSERT INTO stop_amenity_evidence
              (physical_stop_id,source,source_record_id,amenity_type,present,raw_value)
            VALUES
              (11,'DDOT','1000087','shelter',1,'CONFIRMED_ACTIVE'),
              (5136,'DDOT','1000087','shelter',1,'CONFIRMED_ACTIVE'),
              (11,'DDOT','older-direct','shelter',1,'1');
            """
        )
        conn.commit()
        conn.close()
        self.features = [{
            "attributes": {
                "OBJECTID": 299, "DDOT_ID": 1000087,
                "DDOT_SHELTER_ID": "1000087", "Barcode": "DC-000617",
                "Panel_No": 910981, "Site_Code": 210981,
                "Sales_Address": "Wheeler Rd SE + Varney St SE",
            },
            "geometry": {"x": -76.9921875, "y": 38.83544555},
        }]

    def tearDown(self):
        self.db.unlink(missing_ok=True)

    def counts(self):
        conn = sqlite3.connect(self.db)
        values = (
            conn.execute("SELECT COUNT(*) FROM stop_amenity_evidence WHERE source='DDOT_ARCGIS'").fetchone()[0],
            conn.execute("SELECT COUNT(*) FROM stop_amenity_evidence WHERE source='DDOT'").fetchone()[0],
            conn.execute("SELECT COUNT(*) FROM stop_ddot_shelter_evidence").fetchone()[0],
        )
        conn.close()
        return values

    def report(self):
        return preflight(self.db, self.features)

    def apply(self, report, **kwargs):
        return apply_replacement(
            self.db, report,
            acknowledge_feed_change=True,
            acknowledge_deletion_change=True,
            **kwargs,
        )

    def test_default_preflight_performs_no_writes_and_regression_passes(self):
        before = self.counts()
        report = self.report()
        self.assertEqual(before, self.counts())
        self.assertTrue(report["regression_1000087"]["stop_11"])
        self.assertFalse(report["regression_1000087"]["stop_5136"])

    def test_success_is_atomic_preserves_history_and_is_idempotent(self):
        report = self.report()
        self.assertEqual("committed", self.apply(report))
        self.assertEqual((1, 1, 2), self.counts())
        second = self.report()
        self.assertEqual("committed", self.apply(second))
        self.assertEqual((1, 1, 2), self.counts())

    def test_failures_at_each_stage_roll_back_everything(self):
        for stage in ("during_insertion", "after_insertion", "after_cleanup"):
            with self.subTest(stage=stage):
                before = self.counts()
                with self.assertRaises(RuntimeError):
                    self.apply(self.report(), failure_stage=stage)
                self.assertEqual(before, self.counts())

    def test_deletion_set_mismatch_aborts(self):
        report = self.report()
        report["deletion_candidate_count"] += 1
        with self.assertRaises(RuntimeError):
            self.apply(report)
        self.assertEqual((0, 3, 2), self.counts())

    def test_material_feed_delta_requires_acknowledgement(self):
        report = self.report()
        with self.assertRaises(RuntimeError):
            apply_replacement(self.db, report, acknowledge_deletion_change=True)
        self.assertEqual((0, 3, 2), self.counts())

    def test_non_dc_accepted_record_aborts(self):
        report = self.report()
        report["results"][0]["physical_stop_id"] = 5136
        report["results"][0]["state"] = "MD"
        with self.assertRaises(RuntimeError):
            self.apply(report)
        self.assertEqual((0, 3, 2), self.counts())

    def test_empty_identity_preflight_aborts(self):
        report = {
            "source_feature_count": 1,
            "distinct_source_identity_count": 0,
            "duplicate_generated_identities": {},
            "accepted_non_dc_count": 0,
            "results": [{
                "status": "accepted",
                "source_record_id": "1000087",
                "physical_stop_id": 11,
            }],
        }
        with self.assertRaises(RuntimeError):
            validate_source_report(report)

    def test_duplicate_identity_preflight_aborts(self):
        with self.assertRaises(RuntimeError):
            preflight(self.db, self.features + self.features)


if __name__ == "__main__":
    unittest.main()
