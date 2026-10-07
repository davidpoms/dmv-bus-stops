"""Real stop requests need neither road geometry nor scientific imports."""
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from src.api import app as api
from src.review import assignment_router


class StreetViewRequestTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        db = Path(folder.name) / 'stops.db'
        with sqlite3.connect(db) as conn:
            conn.executescript("""
                CREATE TABLE physical_stops(id,primary_name,latitude,longitude,state,
                    dc_ward,dc_anc,county,municipality);
                INSERT INTO physical_stops VALUES(1,'Test stop',38.912345,-77.023456,
                    'DC',NULL,NULL,NULL,NULL);
                CREATE TABLE physical_stop_members(physical_stop_id,bus_stop_id);
                INSERT INTO physical_stop_members VALUES(1,101);
                CREATE TABLE bus_stops(id,external_stop_id);
                INSERT INTO bus_stops VALUES(101,'W1');
                CREATE TABLE gtfs_stop_map(bus_stop_id,gtfs_stop_id,match_method);
                INSERT INTO gtfs_stop_map VALUES(101,'W1','wmata_stop_code');
                CREATE TABLE stop_wmata_evidence(id,physical_stop_id,wmata_stop_id,
                    wmata_heading,wmata_status,match_distance_m,match_confidence,created_at);
                INSERT INTO stop_wmata_evidence VALUES(1,1,'W1','119','PRS',2,'high','2026-01-01');
                CREATE TABLE improvement_opportunities(physical_stop_id,opportunity_score);
                INSERT INTO improvement_opportunities VALUES(1,50);
                CREATE TABLE stop_routes(stop_id,route_id);
                INSERT INTO stop_routes VALUES(101,10);
                CREATE TABLE routes(id,route_id,route_name);
                INSERT INTO routes VALUES(10,'R1','Route 1');
                CREATE TABLE improvement_recommendations(id,physical_stop_id,
                    recommendation_type,priority,confidence,evidence,reasons,created_at);
                CREATE TABLE stop_transit_evidence(stop_id);
                CREATE TABLE stop_osm_evidence(stop_id);
                CREATE TABLE stop_ddot_shelter_evidence(physical_stop_id,ddot_id,api_id,
                    lifecycle_status,route_ids,route_count,confidence,notes,created_at);
                CREATE TABLE stop_observations(id,physical_stop_id,observed_at,reviewer_id,
                    source,shelter_present,bench_present,notes,assignment_id,review_mode,
                    streetview_imagery_month,bench_feasible,concrete_pad_needed,
                    bench_condition,rider_comfort_category,accessibility_status,
                    weather_exposure,riders_avoid_facilities);
                CREATE TABLE stop_consensus(stop_id,has_shelter,has_bench,ada_accessible,
                    confidence,seating_type_consensus,rider_comfort_category,
                    rider_comfort_consensus,hostile_design_consensus,bench_feasible);
                CREATE TABLE stop_amenity_status(physical_stop_id,amenity_type,derived_status,
                    consensus_status,evidence_conflict,consensus_conflicts_with_other_evidence,
                    rationale,updated_at);
                INSERT INTO stop_amenity_status VALUES(1,'bench','unknown',NULL,0,0,NULL,NULL);
                CREATE TABLE stop_amenity_evidence(id,physical_stop_id,source,source_record_id,
                    amenity_type,present,confidence,match_distance_m,notes,jurisdiction,value,created_at);
                CREATE TABLE stop_improvement_impact(physical_stop_id,summary,impact_level,
                    recommendations,opportunity_score,daily_route_exposure);
                CREATE TABLE ridership_snapshots(route_id,weekday_boardings,period);
                CREATE TABLE opportunity_assessments(physical_stop_id,rider_exposure_percentile);
                CREATE TABLE community_reviewers(id,reviewer_key);
                INSERT INTO community_reviewers VALUES(1,'existing-reviewer');
            """)
        conn.close()
        self.enterContext(patch.object(api, 'DATABASE_PATH', db))
        self.enterContext(patch.object(assignment_router, 'DB', db))
        self.enterContext(patch.dict(api.app.config, TESTING=True, SECRET_KEY='streetview-test'))
        self.client = api.app.test_client()
        with self.client.session_transaction() as session:
            session['reviewer_key'] = 'existing-reviewer'

    def check_endpoint(self, path):
        expected = api.serving_direction_payload(1)
        self.assertEqual(['119'], expected['serving_headings'])
        statements = []
        connect = sqlite3.connect

        def traced_connect(*args, **kwargs):
            conn = connect(*args, **kwargs)
            conn.set_trace_callback(statements.append)
            return conn

        with patch.object(api, 'get_road_index', side_effect=AssertionError('road build')) as road, \
                patch.object(sqlite3, 'connect', side_effect=traced_connect):
            response = self.client.get(path)
        self.assertEqual(200, response.status_code)
        payload = response.get_json()
        road.assert_not_called()
        self.assertFalse(any('road_centerlines' in sql.lower() for sql in statements))
        self.assertEqual((38.912345, -77.023456), (payload['lat'], payload['lon']))
        self.assertIsNone(payload['streetview_camera_heading'])
        params = parse_qs(urlsplit(payload['streetview_url']).query)
        self.assertEqual(['38.912345,-77.023456'], params['viewpoint'])
        self.assertEqual(['pano'], params['map_action'])
        self.assertNotIn('heading', params)
        for key, value in expected.items():
            self.assertEqual(value, payload[key])

    def test_stop_detail_without_road_index(self):
        self.check_endpoint('/stops/1')

    def test_stop_detail_operational_jurisdiction(self):
        overlay = {
            'value': 'MD',
            'jurisdiction_basis': 'border_centerline_convention',
            'border_notice': True,
            'border_review_required': False,
            'border_notice_reasons': [],
        }
        with patch.object(api, 'operational_jurisdiction', return_value=overlay) as lookup:
            response = self.client.get('/stops/1')
        self.assertEqual(200, response.status_code)
        self.assertEqual(overlay, response.get_json()['operational_jurisdiction'])
        lookup.assert_called_once_with(1)

    def test_stop_detail_border_policy_unavailable(self):
        with patch.object(api, 'operational_jurisdiction',
                          side_effect=api.BorderPolicyUnavailable('unavailable')):
            response = self.client.get('/stops/1')
        self.assertEqual(503, response.status_code)
        self.assertEqual({
            'error': 'Operational jurisdiction policy is unavailable',
            'code': 'border_policy_unavailable',
        }, response.get_json())

    def test_review_info_without_road_index(self):
        self.check_endpoint('/review/1/info')

    def test_requests_without_scientific_imports(self):
        # A fresh interpreter avoids cached modules and global import mocking.
        source = """
import importlib.abc, sys, unittest
attempts = []
class BlockScientific(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('numpy', 'scipy') or fullname == 'src.spatial.nearest_road':
            attempts.append(fullname)
            raise ModuleNotFoundError(fullname)
sys.meta_path.insert(0, BlockScientific())
sys.path.insert(0, 'tests')
from test_streetview_requests import StreetViewRequestTests
suite = unittest.TestSuite(StreetViewRequestTests(name) for name in
    ('test_stop_detail_without_road_index', 'test_review_info_without_road_index'))
result = unittest.TextTestRunner().run(suite)
assert result.wasSuccessful()
assert not attempts, attempts
"""
        result = subprocess.run([sys.executable, '-B', '-c', source],
                                cwd=Path(__file__).resolve().parents[1],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
