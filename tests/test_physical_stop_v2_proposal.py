import sqlite3
import unittest

from src.processing.physical_stop_v2_proposal import (
    canonical_json, generate_manifest, manifest_sha256, semantic_grouping,
)


def fixture(testcase, reverse=False):
    conn = sqlite3.connect(":memory:")
    testcase.addCleanup(conn.close)
    conn.executescript("""
      CREATE TABLE physical_stops(id INTEGER PRIMARY KEY,primary_name TEXT,
        latitude REAL,longitude REAL);
      CREATE TABLE physical_stop_members(physical_stop_id INTEGER,bus_stop_id INTEGER);
      CREATE TABLE bus_stops(id INTEGER PRIMARY KEY,external_stop_id TEXT,
        stop_name TEXT,latitude REAL,longitude REAL);
      CREATE TABLE gtfs_stop_map(gtfs_stop_id TEXT,bus_stop_id INTEGER,match_method TEXT);
      CREATE TABLE stop_wmata_evidence(id INTEGER PRIMARY KEY,physical_stop_id INTEGER,
        wmata_stop_id TEXT,wmata_heading TEXT,wmata_status TEXT,match_distance_m REAL,
        match_confidence TEXT,created_at TEXT);
      CREATE TABLE stop_routes(id INTEGER PRIMARY KEY,stop_id INTEGER,route_id INTEGER);
      CREATE TABLE routes(id INTEGER PRIMARY KEY,route_id TEXT);
      CREATE TABLE stop_gtfs_status(physical_stop_id INTEGER PRIMARY KEY,current_gtfs INTEGER);
      INSERT INTO routes VALUES(1,'R1');
    """)
    parents = [
        (935, "Porter", [(1,"1002216","Porter #2724",119,"7867","wmata_stop_code"),
                          (2,"1002217","Porter #2723",297,"7868","wmata_stop_code")]),
        (10, "Wrap", [(3,"A","Main",350,"A1","wmata_stop_code"),
                       (4,"B","Main",10,"B1","wmata_stop_code")]),
        (11, "Below threshold", [(5,"C","Oak",0,"C1","wmata_stop_code"),
                                   (6,"D","Oak",159,"D1","wmata_stop_code")]),
        (12, "Facility", [(7,"E","Terminal Bay A",None,None,None),
                           (8,"F","Terminal Bay B",None,None,None)]),
        (13, "Fallback conflict", [(9,"G","Pine",5,"G1","wmata_stop_code"),
                                     (10,"H","Pine",185,"HF","coordinate")]),
        (14, "Missing", [(11,"I","Elm",None,None,None),(12,"J","Elm",None,None,None)]),
        (15, "Shared boarding", [(15,"M","Shared",45,"SAME","wmata_stop_code"),
                                  (16,"N","Shared",45,"SAME","wmata_stop_code")]),
        (16, "Transitive geometry", [(17,"O","Chain",None,None,None),
                                      (18,"P","Chain",None,None,None),
                                      (19,"Q","Chain",None,None,None)]),
        (406, "Manual", [(13,"K","Manual",0,"K1","wmata_stop_code"),
                          (14,"L","Manual",180,"L1","wmata_stop_code")]),
    ]
    if reverse:
        parents.reverse()
    evidence_id = 1
    for parent_id, name, members in parents:
        conn.execute("INSERT INTO physical_stops VALUES(?,?,?,?)",
                     (parent_id, name, 38.9, -77.0))
        conn.execute("INSERT INTO stop_gtfs_status VALUES(?,1)", (parent_id,))
        iterable = list(reversed(members)) if reverse else members
        for member_id, external, stop_name, heading, gtfs, method in iterable:
            conn.execute("INSERT INTO bus_stops VALUES(?,?,?,?,?)",
                         (member_id, external, stop_name, 38.9+member_id/100000, -77.0))
            conn.execute("INSERT INTO physical_stop_members VALUES(?,?)", (parent_id, member_id))
            conn.execute("INSERT INTO stop_routes(stop_id,route_id) VALUES(?,1)", (member_id,))
            if gtfs:
                conn.execute("INSERT INTO gtfs_stop_map VALUES(?,?,?)", (gtfs, member_id, method))
                if not conn.execute(
                        "SELECT 1 FROM stop_wmata_evidence WHERE wmata_stop_id=?", (gtfs,)
                ).fetchone():
                    conn.execute("INSERT INTO stop_wmata_evidence VALUES(?,?,?,?,?,?,?,?)",
                                 (evidence_id, 999, gtfs, str(heading), 'UNKNOWN', 999, 'low',
                                  '2026-01-01'))
                    evidence_id += 1
        if parent_id == 13:
            conn.execute("INSERT INTO gtfs_stop_map VALUES('H1',10,'wmata_stop_code')")
            conn.execute("INSERT INTO stop_wmata_evidence VALUES(?,?,?,?,?,?,?,?)",
                         (evidence_id,999,'H1','7','UNKNOWN',999,'low','2026-01-01'))
            evidence_id += 1
    return conn


class ProposalTests(unittest.TestCase):
    def test_reference_classification_and_fail_closed_rules(self):
        manifest = generate_manifest(fixture(self))
        groups = semantic_grouping(manifest)
        self.assertEqual(((1,), (2,)), groups[935])
        self.assertEqual(((7,), (8,)), groups[12])
        for unchanged in (10, 11, 13, 14, 15, 16, 406):
            self.assertNotIn(unchanged, groups)
        stop = next(p for p in manifest["parents"]
                    if p["predecessor_physical_stop_id"] == 935)
        self.assertEqual(["7867"], stop["proposed_children"][0]["eligible_gtfs_stop_ids"])
        self.assertEqual([119.0], stop["proposed_children"][0]["serving_headings"])
        self.assertEqual(["7868"], stop["proposed_children"][1]["eligible_gtfs_stop_ids"])

    def test_equivalent_insertion_order_has_identical_canonical_output(self):
        first = generate_manifest(fixture(self, False))
        second = generate_manifest(fixture(self, True))
        self.assertEqual(canonical_json(first), canonical_json(second))
        self.assertEqual(manifest_sha256(first), manifest_sha256(second))

    def test_repeated_generation_is_byte_and_hash_stable(self):
        conn = fixture(self)
        outputs = [generate_manifest(conn) for _ in range(3)]
        self.assertEqual(1, len({canonical_json(value) for value in outputs}))
        self.assertEqual(1, len({manifest_sha256(value) for value in outputs}))


if __name__ == "__main__":
    unittest.main()
