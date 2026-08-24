import json
import sqlite3
import unittest
from pathlib import Path

from src.amenities.status_synthesis import (
    DERIVED_STATUSES,
    geography_status_rows,
    rebuild_stop_amenity_status,
)


ROOT = Path(__file__).resolve().parents[1]


class AmenityStatusSynthesisTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript(
            """
            CREATE TABLE physical_stops(id INTEGER PRIMARY KEY);
            CREATE TABLE stop_gtfs_status(
                physical_stop_id INTEGER PRIMARY KEY, current_gtfs INTEGER NOT NULL
            );
            CREATE TABLE bus_stops(id INTEGER PRIMARY KEY, external_stop_id TEXT);
            CREATE TABLE physical_stop_members(
                physical_stop_id INTEGER, bus_stop_id INTEGER
            );
            CREATE TABLE stop_amenity_evidence(
                physical_stop_id INTEGER, source TEXT, amenity_type TEXT,
                present INTEGER, value TEXT
            );
            CREATE TABLE stop_osm_evidence(stop_id INTEGER, osm_tags TEXT);
            CREATE TABLE stop_observations(
                physical_stop_id INTEGER, shelter_present TEXT,
                bench_present TEXT, source TEXT
            );
            CREATE TABLE stop_consensus(
                stop_id INTEGER, has_shelter INTEGER, has_bench INTEGER,
                confidence REAL
            );
            CREATE TABLE stop_jurisdiction(
                stop_id INTEGER, state TEXT, county TEXT, municipality TEXT,
                dc_ward TEXT, dc_anc TEXT
            );
            CREATE TABLE stop_wmata_evidence(
                physical_stop_id INTEGER, wmata_shelter INTEGER, wmata_bench INTEGER
            );
            CREATE TABLE jurisdiction_source_evidence(
                physical_stop_id INTEGER, source_metadata TEXT
            );
            """
        )

    def add_stop(self, stop_id, current=1, external=None, geography=None):
        self.db.execute("INSERT INTO physical_stops VALUES (?)", (stop_id,))
        if current is not None:
            self.db.execute(
                "INSERT INTO stop_gtfs_status VALUES (?,?)", (stop_id, current)
            )
        external = external or f"ext-{stop_id}"
        self.db.execute("INSERT INTO bus_stops VALUES (?,?)", (stop_id, external))
        self.db.execute(
            "INSERT INTO physical_stop_members VALUES (?,?)", (stop_id, stop_id)
        )
        if geography:
            self.db.execute(
                "INSERT INTO stop_jurisdiction VALUES (?,?,?,?,?,?)",
                (stop_id, *geography),
            )

    def local(self, stop_id, amenity, present, source="ALEXANDRIA"):
        self.db.execute(
            "INSERT INTO stop_amenity_evidence VALUES (?,?,?,?,?)",
            (stop_id, source, amenity, present, "yes" if present else "no"),
        )

    def observe(self, stop_id, shelter, bench, count=1):
        self.db.executemany(
            "INSERT INTO stop_observations VALUES (?,?,?,'community_review')",
            [(stop_id, shelter, bench)] * count,
        )

    def status(self, stop_id, amenity):
        return self.db.execute(
            "SELECT * FROM stop_amenity_status WHERE physical_stop_id=? AND amenity_type=?",
            (stop_id, amenity),
        ).fetchone()

    def test_current_scope_two_rows_and_missing_status_fail_closed(self):
        self.add_stop(1, 1)
        self.add_stop(2, 0)
        self.add_stop(3, None)
        rebuild_stop_amenity_status(self.db)
        self.assertEqual(2, self.db.execute("SELECT COUNT(*) FROM stop_amenity_status").fetchone()[0])
        self.assertEqual({"shelter", "bench"}, {
            row[0] for row in self.db.execute("SELECT amenity_type FROM stop_amenity_status")
        })
        self.assertEqual({1}, {
            row[0] for row in self.db.execute("SELECT DISTINCT physical_stop_id FROM stop_amenity_status")
        })

    def test_local_yes_no_and_explicit_conflict(self):
        self.add_stop(1); self.add_stop(2); self.add_stop(3)
        self.local(1, "shelter", 1)
        self.local(2, "shelter", 0)
        self.local(3, "shelter", 1, "ALEXANDRIA")
        self.local(3, "shelter", 0, "MONTGOMERY_COUNTY_WMATA")
        rebuild_stop_amenity_status(self.db)
        self.assertEqual("likely_yes", self.status(1, "shelter")["derived_status"])
        self.assertEqual("likely_no", self.status(2, "shelter")["derived_status"])
        self.assertEqual("conflicting", self.status(3, "shelter")["derived_status"])
        self.assertEqual(1, self.status(3, "shelter")["evidence_conflict"])

    def test_safe_osm_yes_and_no_require_explicit_identity_matched_tags(self):
        self.add_stop(1, external="A"); self.add_stop(2, external="B")
        self.add_stop(3, external="C"); self.add_stop(4, external="D")
        rows = [
            (1, {"ref": "A", "shelter": "yes"}),
            (2, {"ref:wmata": "B", "bench": "yes"}),
            (3, {"ref": "C", "shelter": "no"}),
            (4, {"ref": "wrong", "bench": "no"}),
        ]
        self.db.executemany(
            "INSERT INTO stop_osm_evidence VALUES (?,?)",
            [(stop, json.dumps(tags)) for stop, tags in rows],
        )
        rebuild_stop_amenity_status(self.db)
        self.assertEqual("likely_yes", self.status(1, "shelter")["derived_status"])
        self.assertEqual("likely_yes", self.status(2, "bench")["derived_status"])
        self.assertEqual("likely_no", self.status(3, "shelter")["derived_status"])
        self.assertEqual("unknown", self.status(4, "bench")["derived_status"])

    def test_missing_and_bare_zero_osm_do_not_imply_no(self):
        self.add_stop(1); self.add_stop(2)
        self.db.execute(
            "INSERT INTO stop_osm_evidence VALUES (?,?)",
            (2, json.dumps({"ref": "ext-2", "highway": "bus_stop"})),
        )
        rebuild_stop_amenity_status(self.db)
        for stop_id in (1, 2):
            for amenity in ("shelter", "bench"):
                self.assertEqual("unknown", self.status(stop_id, amenity)["derived_status"])

    def test_full_consensus_is_authoritative_and_preserves_disagreement(self):
        self.add_stop(1); self.add_stop(2)
        self.local(1, "shelter", 0)
        self.local(2, "bench", 1)
        self.observe(1, "yes", "unknown", 3)
        self.observe(2, "unknown", "no", 3)
        self.db.executemany(
            "INSERT INTO stop_consensus VALUES (?,?,?,?)",
            [(1, 1, None, 1.0), (2, None, 0, 1.0)],
        )
        rebuild_stop_amenity_status(self.db)
        shelter = self.status(1, "shelter")
        bench = self.status(2, "bench")
        self.assertEqual("confirmed_yes", shelter["derived_status"])
        self.assertEqual("confirmed_no", bench["derived_status"])
        self.assertEqual(1, shelter["consensus_conflicts_with_other_evidence"])
        self.assertEqual(1, bench["consensus_conflicts_with_other_evidence"])

    def test_preconsensus_community_is_likely_or_conflicting(self):
        self.add_stop(1); self.add_stop(2); self.add_stop(3)
        self.observe(1, "yes", "unknown")
        self.observe(2, "no", "unknown")
        self.observe(3, "yes", "unknown")
        self.observe(3, "no", "unknown")
        rebuild_stop_amenity_status(self.db)
        self.assertEqual("likely_yes", self.status(1, "shelter")["derived_status"])
        self.assertEqual("likely_no", self.status(2, "shelter")["derived_status"])
        self.assertEqual("conflicting", self.status(3, "shelter")["derived_status"])

    def test_quarantined_and_raw_sources_and_wmata_fields_are_ignored(self):
        self.add_stop(1)
        self.local(1, "shelter", 1, "DDOT")
        self.db.execute("INSERT INTO stop_wmata_evidence VALUES (1,1,1)")
        self.db.execute("INSERT INTO jurisdiction_source_evidence VALUES (1,'raw')")
        rebuild_stop_amenity_status(self.db)
        self.assertEqual("unknown", self.status(1, "shelter")["derived_status"])
        self.assertEqual("unknown", self.status(1, "bench")["derived_status"])

    def test_geographies_partition_statuses_and_overlap_intentionally(self):
        geographies = [
            ("DC", "District of Columbia", "Washington", "5", "5F"),
            ("MD", "Prince George's County", "Greenbelt", None, None),
            ("VA", "Arlington County", "Arlington", None, None),
        ]
        for stop_id, geography in enumerate(geographies, 1):
            self.add_stop(stop_id, geography=geography)
        self.local(1, "shelter", 1)
        self.local(2, "shelter", 0)
        rebuild_stop_amenity_status(self.db)
        rows = geography_status_rows(self.db)
        types = {row["type"] for row in rows}
        self.assertTrue({"State", "County", "Municipality", "DC Ward", "ANC"} <= types)
        self.assertTrue(any(row["geography"] == "Maryland" for row in rows))
        for row in rows:
            for amenity in ("shelter", "bench"):
                self.assertEqual(
                    row["total_stops"],
                    sum(row[f"{amenity}_{status}"] for status in DERIVED_STATUSES),
                )
        state_total = sum(row["total_stops"] for row in rows if row["type"] == "State")
        all_total = sum(row["total_stops"] for row in rows)
        self.assertEqual(3, state_total)
        self.assertGreater(all_total, state_total)

    def test_rebuild_is_idempotent_removes_stale_and_preserves_evidence(self):
        self.add_stop(1); self.add_stop(2)
        self.local(1, "shelter", 1)
        before = self.db.execute("SELECT COUNT(*) FROM stop_amenity_evidence").fetchone()[0]
        rebuild_stop_amenity_status(self.db)
        first = [tuple(row)[:-1] for row in self.db.execute(
            "SELECT * FROM stop_amenity_status ORDER BY physical_stop_id,amenity_type"
        )]
        rebuild_stop_amenity_status(self.db)
        second = [tuple(row)[:-1] for row in self.db.execute(
            "SELECT * FROM stop_amenity_status ORDER BY physical_stop_id,amenity_type"
        )]
        self.assertEqual(first, second)
        self.db.execute("UPDATE stop_gtfs_status SET current_gtfs=0 WHERE physical_stop_id=2")
        rebuild_stop_amenity_status(self.db)
        self.assertEqual(0, self.db.execute(
            "SELECT COUNT(*) FROM stop_amenity_status WHERE physical_stop_id=2"
        ).fetchone()[0])
        self.assertEqual(before, self.db.execute("SELECT COUNT(*) FROM stop_amenity_evidence").fetchone()[0])

    def test_frontend_keeps_generic_searchable_geography_table(self):
        javascript = (ROOT / "src/dashboard/static/dashboard.js").read_text(
            encoding="utf-8"
        )
        template = (ROOT / "src/dashboard/templates/dashboard.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("`${x.type} ${x.geography}`", javascript)
        self.assertIn("filterPipeline('State')", template)
        for label in (
            "Shelter Yes", "Shelter No", "Shelter Conflict", "Shelter Unknown",
            "Bench Yes", "Bench No", "Bench Conflict", "Bench Unknown",
        ):
            self.assertIn(label, template)
        self.assertNotIn("wmata_shelter", javascript)
        self.assertNotIn("wmata_bench", javascript)


if __name__ == "__main__":
    unittest.main()
