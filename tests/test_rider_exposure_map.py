import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.api import app as api
from src.scoring.exposure_map import exposure_band, exposure_rows, map_payload, weekday_divisor, DAILY_LABEL
from src.assessment.generate_seating_improvement_opportunities import SCHEMA_SQL


class RiderExposureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "exposure.db"
        self.conn = sqlite3.connect(self.path)
        self.addCleanup(self.conn.close)
        self.conn.executescript("""
            CREATE TABLE physical_stops(id INTEGER PRIMARY KEY,primary_name TEXT,latitude REAL,longitude REAL);
            CREATE TABLE stop_gtfs_status(physical_stop_id INTEGER PRIMARY KEY,current_gtfs INTEGER,route_served INTEGER);
            CREATE TABLE physical_stop_members(physical_stop_id INTEGER,bus_stop_id INTEGER);
            CREATE TABLE stop_routes(stop_id INTEGER,route_id INTEGER);
            CREATE TABLE routes(id INTEGER PRIMARY KEY,route_id TEXT,route_name TEXT);
            CREATE TABLE opportunity_assessments(physical_stop_id INTEGER PRIMARY KEY,combined_route_weekday_boardings REAL);
            CREATE TABLE stop_amenity_status(physical_stop_id INTEGER,amenity_type TEXT,derived_status TEXT);
            CREATE TABLE ridership_snapshots(period TEXT);
            CREATE TABLE stop_jurisdiction(stop_id INTEGER PRIMARY KEY,state TEXT,county TEXT,municipality TEXT,dc_ward TEXT,dc_anc TEXT);
            INSERT INTO ridership_snapshots VALUES ('2026-07-31');
            INSERT INTO routes VALUES (1,'A','Route A'),(2,'B','Route B'),(3,'OLD','Historical only');
        """)
        self.conn.executescript(SCHEMA_SQL)
        for i in range(1, 108):
            self.conn.execute("INSERT INTO physical_stops VALUES (?,?,38,-77)", (i, f"Stop {i}"))
            # Route-served flag must never exclude an active stop.
            self.conn.execute("INSERT INTO stop_gtfs_status VALUES (?,?,0)", (i, int(i < 106)))
            self.conn.execute("INSERT INTO physical_stop_members VALUES (?,?)", (i, i))
            self.conn.execute("INSERT INTO stop_routes VALUES (?,?)", (i, 1 if i < 106 else 3))
            self.conn.execute("INSERT INTO opportunity_assessments VALUES (?,?)", (i, i * 100))
            self.conn.execute("INSERT INTO stop_jurisdiction VALUES (?,?,?,?,?,?)",
                              (i, 'VA' if i % 3 == 0 else 'MD', 'Example' if i <= 60 else 'Other',
                               'Tiny' if i <= 3 else None, '1.0' if i == 1 else '1' if i == 2 else None,
                               '1A' if i <= 25 else None))
        self.conn.executescript("""
            INSERT INTO stop_routes VALUES (1,1),(1,2),(2,2);
            INSERT INTO physical_stop_members VALUES (1,1001);
            INSERT INTO stop_routes VALUES (1001,1);
            UPDATE opportunity_assessments SET combined_route_weekday_boardings=200 WHERE physical_stop_id=1;
            UPDATE opportunity_assessments SET combined_route_weekday_boardings=NULL WHERE physical_stop_id=3;
            DELETE FROM stop_gtfs_status WHERE physical_stop_id=107;
            INSERT INTO stop_amenity_status VALUES (1,'bench','likely_no'),(2,'bench','unknown'),(4,'bench','conflicting');
        """)
        columns = [r[1] for r in self.conn.execute("PRAGMA table_info(seating_improvement_opportunities)")]
        for i, status, workflow in [(1, 'likely_no', 'collect_clearance_observation'),
                                    (2, 'unknown', 'verify_presence'), (106, 'likely_no', 'planning_review')]:
            values = {c: 0 for c in columns}
            values.update(physical_stop_id=i, opportunity_rank=i, primary_name=f"Stop {i}",
                          bench_status=status, shelter_status='unknown', workflow_state=workflow,
                          adequacy_factors='{}', need_signals='{}', priority_factors='{}', rationale='[]')
            self.conn.execute("INSERT INTO seating_improvement_opportunities VALUES (" +
                              ','.join('?' for _ in columns) + ")", [values[c] for c in columns])
        self.conn.commit()
        self.patch = patch.object(api, "DATABASE_PATH", self.path)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        api.app.config.update(TESTING=True, SECRET_KEY='exposure-test')
        self.client = api.app.test_client()

    def test_active_only_capped_deterministic_and_distinct_routes(self):
        data = map_payload(self.conn, 'highest')
        self.assertEqual(100, len(data['stops']))
        self.assertEqual(104, data['total_matching'])
        self.assertEqual(105, data['stops'][0]['physical_stop_id'])
        self.assertEqual(data, map_payload(self.conn, 'highest'))
        self.assertNotIn('OLD', [r['route_id'] for r in data['routes']])
        rows = {r['physical_stop_id']: r for r in exposure_rows(self.conn)}
        self.assertEqual(set(range(1, 106)), set(rows))
        self.assertEqual(2, rows[1]['active_route_count'])
        self.assertEqual('Unavailable', rows[3]['exposure_band'])
        self.assertEqual(rows[1]['exposure_percentile'], rows[2]['exposure_percentile'])

    def test_route_mode_and_limit_validation(self):
        data = self.client.get('/map/exposure?mode=route&route=B').get_json()
        self.assertEqual([1, 2], [r['physical_stop_id'] for r in data['stops']])
        self.assertEqual('Route B', data['selected_route']['route_name'])
        self.assertEqual([], map_payload(self.conn, 'route', 'OLD')['stops'])
        self.assertEqual(100, len(map_payload(self.conn, 'highest', limit=9999)['stops']))
        self.assertEqual(400, self.client.get('/map/exposure?limit=bad').status_code)
        self.assertEqual(400, self.client.get('/map/exposure?mode=bad').status_code)

    def test_existing_score_has_no_raw_route_count_bonus_and_bands_are_stable(self):
        before = exposure_rows(self.conn)
        self.conn.execute("INSERT INTO routes VALUES (4,'C','C')")
        self.conn.execute("INSERT INTO stop_routes VALUES (1,4)")
        after = exposure_rows(self.conn)
        self.assertEqual([r['exposure_score'] for r in before], [r['exposure_score'] for r in after])
        self.assertEqual(['Lower', 'Moderate', 'High', 'Very High'],
                         [exposure_band(p) for p in [39.99, 40, 75, 90]])
        self.assertGreater(after[0]['exposure_score'], after[-2]['exposure_score'])

    def test_seating_sort_preserves_states_and_excludes_stale_inactive_rows(self):
        data = self.client.get('/seating-opportunities?sort=rider_exposure').get_json()
        self.assertEqual(2, data['summary']['total_active_stops'])
        rows = data['opportunities']
        self.assertEqual([1, 2], [r['physical_stop_id'] for r in rows])
        self.assertEqual(['likely_no', 'unknown'], [r['bench_status'] for r in rows])
        self.assertEqual('verify_presence', rows[1]['workflow_state'])
        self.conn.execute('UPDATE opportunity_assessments SET combined_route_weekday_boardings=99999 WHERE physical_stop_id=2')
        self.conn.commit()
        rows = self.client.get('/seating-opportunities?sort=rider_exposure').get_json()['opportunities']
        self.assertEqual([2, 1], [r['physical_stop_id'] for r in rows])

    def test_read_only_and_public_allowlist(self):
        before = self.path.read_bytes()
        data = self.client.get('/map/exposure?mode=route&route=B').get_json()
        allowed = {'physical_stop_id', 'stop_name', 'latitude', 'longitude', 'exposure_score',
                   'exposure_percentile', 'exposure_band', 'ridership_value', 'ridership_label',
                   'active_route_count', 'active_routes', 'connection_class', 'bench_status',
                   'shelter_status', 'rank', 'weekday_divisor', 'geographies',
                   'regional_rank', 'regional_percentile', 'regional_band'}
        self.assertEqual(allowed, set(data['stops'][0]))
        self.assertEqual(['likely_no', 'unknown'], [r['bench_status'] for r in data['stops']])
        self.assertEqual(before, self.path.read_bytes())

    def test_daily_estimate_preserves_raw_score_and_uses_calendar_not_five_days(self):
        self.assertEqual(23, weekday_divisor('2026-07-31'))
        self.assertEqual(20, weekday_divisor('2026-02-28'))
        self.assertIsNone(weekday_divisor(None))
        self.assertIsNone(weekday_divisor('invalid'))
        row = map_payload(self.conn, 'highest')['stops'][0]
        self.assertEqual(10500, row['exposure_score'])
        self.assertAlmostEqual(10500 / 23, row['ridership_value'])
        self.assertEqual(DAILY_LABEL, row['ridership_label'])
        source = (Path(__file__).parents[1] / 'src/dashboard/static/exposure_map.js').read_text()
        self.assertIn('Not observed boarding activity at this stop', source)

    def test_all_independent_geography_dimensions_and_parameter_validation(self):
        for kind, value, expected in [('state','VA',set(range(3,106,3))-{3}),
                                      ('county','Example',set(range(1,61))-{3}),
                                      ('municipality','Tiny',{1,2}), ('dc_ward','1',{1,2}),
                                      ('dc_anc','1A',set(range(1,26))-{3})]:
            data = map_payload(self.conn, 'highest', geography_type=kind, geography_value=value)
            self.assertEqual(expected, {r['physical_stop_id'] for r in data['stops']})
        for params in ({'geography_type':'state'}, {'geography_value':'VA'},
                       {'geography_type':'county','geography_value':'   '},
                       {'geography_type':'state','geography_value':'absent'},
                       {'geography_type':'state; DROP TABLE routes','geography_value':'VA'}):
            self.assertEqual(400, self.client.get('/map/exposure', query_string=params).status_code)

    def test_local_percentile_population_raw_invariance_ties_and_tiny_groups(self):
        regional = {r['physical_stop_id']: r for r in exposure_rows(self.conn)}
        data = map_payload(self.conn, 'highest', geography_type='county', geography_value='Example')
        self.assertEqual(60, data['comparison']['population'])
        self.assertEqual(59, data['comparison']['usable_population'])
        rows = {r['physical_stop_id']: r for r in data['stops']}
        self.assertEqual('Very High', rows[55]['exposure_band'])
        self.assertEqual('Moderate', rows[55]['regional_band'])
        self.assertEqual(regional[55]['exposure_score'], rows[55]['exposure_score'])
        self.assertEqual(regional[55]['ridership_value'], rows[55]['ridership_value'])
        self.assertEqual(rows[1]['jurisdiction_percentile'], rows[2]['jurisdiction_percentile'])
        self.assertLess(rows[1]['rank'], rows[2]['rank'])
        tiny = map_payload(self.conn, 'route', 'A', geography_type='municipality', geography_value='Tiny')
        self.assertEqual(3, tiny['comparison']['population'])
        self.assertEqual(2, tiny['comparison']['usable_population'])
        self.assertTrue(tiny['comparison']['small_population'])
        self.assertEqual(['Small comparison group','Small comparison group','Unavailable'], [r['exposure_band'] for r in tiny['stops']])
        self.assertTrue(all(r['exposure_percentile'] is None for r in tiny['stops']))

    def test_route_and_seating_geography_do_not_redefine_exposure_population(self):
        data = map_payload(self.conn, 'route', 'B', geography_type='county', geography_value='Example')
        self.assertEqual([1,2], [r['physical_stop_id'] for r in data['stops']])
        self.assertEqual(59, data['comparison']['usable_population'])
        self.assertEqual([200,200], [r['exposure_score'] for r in data['stops']])
        data = self.client.get('/seating-opportunities', query_string={
            'geography_type':'county','geography_value':'Example', 'sort':'rider_exposure','bench_status':'unknown'}).get_json()
        self.assertEqual([2], [r['physical_stop_id'] for r in data['opportunities']])
        self.assertEqual('verify_presence', data['opportunities'][0]['workflow_state'])
        self.assertEqual(59, data['comparison']['usable_population'])
        self.assertEqual(400, self.client.get('/seating-opportunities?geography_type=bogus&geography_value=x').status_code)


if __name__ == '__main__':
    unittest.main()
