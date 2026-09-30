import inspect
import sqlite3
import unittest
from pathlib import Path
from unittest.mock import patch

from src.api import app as api
from src.review.attachments import SCHEMA, attach_photo, observation_attachments, validate_photo_url
from src.review.render_survey import render_survey
from src.spatial.camera_heading import bearing_to_stop


class ReviewerFieldAuditTests(unittest.TestCase):
    def test_exposure_distinct_completed_stops_including_history(self):
        conn = sqlite3.connect(':memory:')
        self.addCleanup(conn.close)
        conn.executescript("""
            CREATE TABLE stop_improvement_impact(physical_stop_id, average_weekday_boardings, daily_route_exposure);
            CREATE TABLE stop_review_assignments(stop_id, reviewer_id, status);
            INSERT INTO stop_improvement_impact VALUES (1,100.2,2304.6),(2,50.4,1159.2),(3,999,22977);
            INSERT INTO stop_review_assignments VALUES
                (1,7,'completed'),(1,7,'completed'),(2,7,'completed'),
                (3,7,'assigned'),(3,8,'completed'),(4,7,'completed');
        """)
        with patch.object(api, 'query_db', side_effect=lambda sql, args: conn.execute(sql, args).fetchall()):
            self.assertEqual(151, api.reviewer_weekday_exposure(7))
            self.assertEqual(0, api.reviewer_weekday_exposure(9))
        source = inspect.getsource(api.reviewer_weekday_exposure)
        self.assertNotIn('/', source)
        self.assertNotIn('current_gtfs', source)

    def test_direction_contract_single_multiple_and_unavailable(self):
        single = {'heading_degrees': '119', 'compass_label': 'Southeast'}
        other = {'heading_degrees': '297', 'compass_label': 'Northwest'}
        for directions, singular in [([], None), ([single], single),
                                     ([single, single], single), ([single, other], None)]:
            with patch.object(api, 'get_serving_directions', return_value=directions):
                payload = api.serving_direction_payload(1)
            self.assertEqual(singular, payload['serving_direction'])
            self.assertEqual(directions, payload['serving_directions'])

    def test_exposure_coverage_distinguishes_missing_zero_and_history(self):
        conn = sqlite3.connect(':memory:')
        self.addCleanup(conn.close)
        conn.executescript("""
            CREATE TABLE stop_improvement_impact(physical_stop_id,average_weekday_boardings);
            CREATE TABLE stop_review_assignments(stop_id,reviewer_id,status);
            CREATE TABLE stop_gtfs_status(physical_stop_id,current_gtfs);
            INSERT INTO stop_improvement_impact VALUES(1,10),(3,0),(4,20),(5,99),(6,99);
            INSERT INTO stop_gtfs_status VALUES(1,1),(2,1),(3,1),(4,0),(5,1),(6,1);
            INSERT INTO stop_review_assignments VALUES
                (1,7,'completed'),(1,7,'completed'),(2,7,'completed'),
                (3,7,'completed'),(4,7,'completed'),(5,7,'assigned'),(6,8,'completed');
        """)
        with patch.object(api, 'query_db', side_effect=lambda sql, args: conn.execute(sql, args).fetchall()):
            result = api.reviewer_exposure_summary(7)
            self.assertEqual(30, result['average_weekday_route_exposure_represented'])
            self.assertEqual({'reviewed_stops': 4, 'stops_with_exposure': 3,
                              'missing_stops': 1, 'complete': False}, result['route_exposure_coverage'])
            conn.execute('INSERT INTO stop_improvement_impact VALUES(2,0)')
            self.assertTrue(api.reviewer_exposure_summary(7)['route_exposure_coverage']['complete'])
            conn.execute('UPDATE stop_improvement_impact SET average_weekday_boardings=0')
            self.assertEqual(0, api.reviewer_weekday_exposure(7))
            conn.execute('UPDATE stop_improvement_impact SET average_weekday_boardings=NULL')
            self.assertIsNone(api.reviewer_weekday_exposure(7))
            self.assertEqual(0, api.reviewer_exposure_summary(7)['route_exposure_coverage']['stops_with_exposure'])

    def test_camera_bearing_and_coordinate_order(self):
        self.assertAlmostEqual(90, bearing_to_stop(0, 0, 0, 1))
        self.assertAlmostEqual(180, bearing_to_stop(1, 0, 0, 0))
        self.assertIsNone(bearing_to_stop(1, 2, 1, 2))
        with patch.object(api, 'get_road_index') as index:
            for lat, lon in [(0, 1), (38.912345, -77.023456)]:
                url, heading = api.streetview_for_stop(lat, lon)
                self.assertEqual(
                    'https://www.google.com/maps/@?api=1&map_action=pano'
                    f'&viewpoint={lat},{lon}', url)
                self.assertIsNone(heading)
                self.assertNotIn('heading=', url)
            index.assert_not_called()

    def test_photo_validation_and_evidence_identity(self):
        for value in ['javascript:alert(1)', 'file:///tmp/x', '//example.org',
                      'https://', 'https://user:password@example.org',
                      'https://example.org/\nfoo', 'https://example.org/' + 'a'*2048, 42]:
            with self.subTest(value=str(value)[:60]), self.assertRaises(ValueError):
                validate_photo_url(value)
        self.assertIsNone(validate_photo_url(''))
        conn = sqlite3.connect(':memory:')
        self.addCleanup(conn.close)
        conn.execute('CREATE TABLE stop_observations(id INTEGER PRIMARY KEY)')
        conn.execute(SCHEMA)
        conn.executemany('INSERT INTO stop_observations VALUES (?)', [(1,), (2,)])
        with conn:
            attach_photo(conn, 1, 'https://example.org/photos?a=1&b=2')
            attach_photo(conn, 2, None)
        self.assertEqual(1, len(observation_attachments(conn, 1)))
        self.assertEqual([], observation_attachments(conn, 2))
        with self.assertRaises(RuntimeError):
            with conn:
                attach_photo(conn, 2, 'https://example.org/other')
                raise RuntimeError('rollback')
        self.assertEqual([], observation_attachments(conn, 2))

    def test_public_templates_have_viewport(self):
        for path in Path('src/dashboard/templates').glob('*.html'):
            self.assertIn('name="viewport"', path.read_text(encoding='utf-8'), path.name)

    def test_photo_submission_rejects_invalid_url_before_any_write(self):
        with api.app.test_request_context('/review/submit', method='POST',
                                         json={'photo_url': 'javascript:alert(1)'}):
            with patch.object(api, 'query_db') as query:
                response, status = api.submit_review()
                self.assertEqual(400, status)
                self.assertIn('HTTP or HTTPS', response['error'])
                query.assert_not_called()
        html = render_survey()
        self.assertIn('name="photo_url"', html)
        self.assertIn('maxlength="2048"', html)
        self.assertIn('Photos (optional)', html)

    def test_attachment_write_never_creates_schema(self):
        conn = sqlite3.connect(':memory:')
        self.addCleanup(conn.close)
        conn.execute('CREATE TABLE stop_observations(id INTEGER PRIMARY KEY)')
        attach_photo(conn, 1, None)
        with self.assertRaises(sqlite3.OperationalError):
            attach_photo(conn, 1, 'https://example.org/photo')
        self.assertIsNone(conn.execute(
            "SELECT name FROM sqlite_master WHERE name='observation_attachments'"
        ).fetchone())
