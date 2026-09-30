"""Single-stop selection preserves batch identity and latest-heading semantics."""
import sqlite3
import unittest
from unittest.mock import patch

from src.processing import serving_directions as directions


class TargetedDirectionTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        self.addCleanup(self.conn.close)
        self.conn.executescript("""
            CREATE TABLE physical_stop_members(physical_stop_id, bus_stop_id);
            CREATE TABLE bus_stops(id, external_stop_id);
            CREATE TABLE gtfs_stop_map(gtfs_stop_id, bus_stop_id, match_method);
            CREATE TABLE stop_wmata_evidence(id INTEGER PRIMARY KEY, physical_stop_id,
                wmata_stop_id, wmata_heading, wmata_status, match_distance_m,
                match_confidence, created_at);
            CREATE TABLE stop_gtfs_status(physical_stop_id, current_gtfs);
            INSERT INTO physical_stop_members VALUES(1,101),(2,201);
            INSERT INTO bus_stops VALUES(101,'source-101'),(201,'source-201');
            INSERT INTO stop_gtfs_status VALUES(1,0),(2,1);
        """)

    def mapping(self, identity='A', method='wmata_stop_code', member=101):
        self.conn.execute('INSERT INTO gtfs_stop_map VALUES(?,?,?)',
                          (identity, member, method))

    def evidence(self, identity='A', heading='119', date='2026-01-01'):
        # Deliberately unrelated physical_stop_id and low-confidence provenance.
        self.conn.execute('INSERT INTO stop_wmata_evidence VALUES(NULL,999,?,?,?,?,?,?)',
                          (identity, heading, 'UNEXPLAINED', 500, 'low', date))

    def result(self, stop=1):
        expected = directions.load_member_directions(self.conn).get(stop, {})
        actual = directions.serving_directions_for_stop(self.conn, stop)
        self.assertEqual(expected, actual)
        raw = [row for row in self.conn.execute(directions.LATEST_DIRECTIONS_SQL)
               if row[0] == stop]
        self.assertEqual(raw, self.conn.execute(directions.STOP_DIRECTIONS_SQL,
                                               (stop,)).fetchall())
        return actual

    def test_exact_methods_and_provenance(self):
        for method in ('wmata_stop_code', 'exact_stop_code', 'explicit_crosswalk'):
            with self.subTest(method=method):
                self.conn.execute('DELETE FROM gtfs_stop_map')
                self.mapping(method=method)
                self.evidence()
                self.assertEqual([{
                    'gtfs_stop_id': 'A', 'heading_degrees': 119.0,
                    'linkage_method': method, 'evidence_status': 'UNEXPLAINED',
                    'match_distance_m': 500, 'confidence': 'low',
                }], self.result()[101])

    def test_conflicting_exact_identity_without_heading_still_blocks(self):
        self.mapping('A')
        self.mapping('B', 'explicit_crosswalk')
        self.evidence('A')
        self.assertEqual({}, self.result())

    def test_coordinate_fallback_without_exact_identity(self):
        self.mapping(method='coordinate')
        self.evidence()
        self.assertEqual('coordinate', self.result()[101][0]['linkage_method'])

    def test_coordinate_rejected_even_when_exact_has_no_heading(self):
        self.mapping('A', 'coordinate')
        self.mapping('B', 'exact_stop_code')
        self.evidence('A')
        self.assertEqual({}, self.result())
        self.evidence('B', '297')
        self.assertEqual(['B'], [d['gtfs_stop_id'] for d in self.result()[101]])

    def test_latest_nonblank_and_id_tiebreak(self):
        self.mapping()
        self.evidence(heading='90')
        self.evidence(heading='180', date='2026-02-01')
        self.evidence(heading='270', date='2026-02-01')
        self.evidence(heading=None, date='2026-03-01')
        self.evidence(heading='   ', date='2026-04-01')
        self.evidence(heading='', date='2026-05-01')
        self.assertEqual(270, self.result()[101][0]['heading_degrees'])

    def test_invalid_latest_does_not_fall_back(self):
        self.mapping()
        for heading in ('bad', 'NaN', 'inf', '\t'):
            with self.subTest(heading=heading):
                self.conn.execute('DELETE FROM stop_wmata_evidence')
                self.evidence(heading='90')
                self.evidence(heading=heading, date='2026-02-01')
                self.assertEqual({}, self.result())

    def test_multiple_members_headings_duplicates_and_order(self):
        self.conn.execute('INSERT INTO physical_stop_members VALUES(1,102)')
        self.conn.execute("INSERT INTO bus_stops VALUES(102,'source-102')")
        self.mapping('B', member=102)
        self.mapping('A')
        self.mapping('A')
        self.evidence('B', '-63')
        self.evidence('A', '479')
        result = self.result()
        self.assertEqual([101, 102], list(result))
        self.assertEqual([119, 119], [d['heading_degrees'] for d in result[101]])
        self.assertEqual([297], [d['heading_degrees'] for d in result[102]])

    def test_text_identity_matching(self):
        self.mapping(123)
        self.evidence('123', '360')
        self.assertEqual('123', self.result()[101][0]['gtfs_stop_id'])
        self.assertEqual(0, self.result()[101][0]['heading_degrees'])

    def test_noncurrent_stop_is_not_filtered(self):
        self.mapping()
        self.evidence()
        self.assertTrue(self.result())
        self.conn.execute('DELETE FROM stop_gtfs_status')
        self.assertTrue(self.result())

    def test_missing_and_untrusted_directions(self):
        self.mapping(method='unknown')
        self.evidence()
        self.assertEqual({}, self.result())
        self.assertEqual({}, self.result(999))

    def test_targeted_path_does_not_call_batch_or_process_unrelated_rows(self):
        self.mapping()
        self.evidence()
        self.mapping('OTHER', member=201)
        self.evidence('OTHER')
        with patch.object(directions, 'load_member_directions',
                          side_effect=AssertionError('batch loader called')):
            result = directions.serving_directions_for_stop(self.conn, 1)
        self.assertEqual([101], list(result))
        rows = self.conn.execute(directions.STOP_DIRECTIONS_SQL, (1,)).fetchall()
        self.assertEqual(1, len(rows))
        self.assertEqual(1, rows[0][0])
        self.assertEqual(2, len(directions.load_member_directions(self.conn)))


if __name__ == '__main__':
    unittest.main()
