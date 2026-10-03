"""Private permanent awards API, using only disposable SQLite fixtures."""

from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from src.api import app as api
from src.review.recognition import RecognitionGate
from src.review.recognition import achievements
from src.review.recognition.integrity import check_award_integrity
from src.review.recognition.processing import lease_jobs, prepare_evaluation, finalize_job
from src.review.recognition.qualification import capture, Quarantined
from src.review.recognition.rules import RULE_KEY
from src.review.recognition.schema import connection, migrate


class AchievementsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'achievements.db'
        with closing(sqlite3.connect(self.path)) as conn:
            conn.executescript("""
                CREATE TABLE community_reviewers(id INTEGER PRIMARY KEY,reviewer_key TEXT,email TEXT);
                INSERT INTO community_reviewers VALUES(1,'owner-key','private@example.test'),
                    (2,'other-key','other@example.test'),(3,'empty-key','empty@example.test');
                CREATE TABLE physical_stops(id INTEGER PRIMARY KEY);
                CREATE TABLE stop_review_assignments(id INTEGER PRIMARY KEY,stop_id INTEGER,
                    reviewer_id INTEGER,status TEXT,completed_at TEXT);
                CREATE TABLE stop_observations(id INTEGER PRIMARY KEY,assignment_id INTEGER,
                    physical_stop_id INTEGER,reviewer_id INTEGER,source TEXT);
            """)
        migrate(self.path, apply=True)  # Fixture setup only; API never installs schema.
        config = {key: api.app.config[key] for key in ('TESTING', 'SECRET_KEY')}
        self.addCleanup(api.app.config.update, config)
        api.app.config.update(TESTING=True, SECRET_KEY='achievements-test')
        database_patch = patch.object(api, 'DATABASE_PATH', self.path)
        database_patch.start()
        self.addCleanup(database_patch.stop)
        self.client = api.app.test_client()
        self.login()

    def login(self, identity=1, key='owner-key'):
        with self.client.session_transaction() as session:
            session.clear()
            if identity is not None:
                session['authenticated_reviewer_id'] = identity
            if key is not None:
                session['reviewer_key'] = key

    def populate(self, *, tied=False):
        gate = RecognitionGate(capture=True, issuance=True)
        with connection(self.path, write=True) as conn:
            conn.execute('BEGIN IMMEDIATE')
            for assignment in range(1, 26):
                owner = 1 if assignment <= 20 else 2
                timestamp = '2026-09-23T12:00:00Z' if tied else f'2026-09-23T12:00:{assignment:02d}Z'
                conn.execute('INSERT INTO physical_stops VALUES(?)', (assignment,))
                conn.execute("INSERT INTO stop_review_assignments VALUES(?,?,?,'completed',?)",
                             (assignment, assignment, owner, timestamp))
                conn.execute("INSERT INTO stop_observations VALUES(?,?,?,?,'community_review')",
                             (assignment, assignment, assignment, owner))
                capture(conn, assignment, RULE_KEY, gate=gate)
            jobs = lease_jobs(conn, RULE_KEY, gate=gate, limit=25)
            conn.commit()
        prepared = {owner: prepare_evaluation(self.path, owner, RULE_KEY) for owner in (1, 2)}
        with connection(self.path, write=True) as conn:
            conn.execute('BEGIN IMMEDIATE')
            for job in jobs:
                owner = 1 if job['assignment_id'] <= 20 else 2
                finalize_job(conn, job['assignment_id'], job['lease_token'], RULE_KEY, prepared[owner], gate=gate)
            conn.commit()

    def get(self, status=200, **kwargs):
        response = self.client.get('/api/reviewer/achievements', **kwargs)
        self.assertEqual(status, response.status_code, response.get_json())
        self.assertEqual('private, no-store', response.headers['Cache-Control'])
        return response

    def test_unauthenticated_or_incomplete_session(self):
        for identity, key in ((None, None), (None, 'owner-key'), (1, None)):
            with self.subTest(identity=identity, key=key):
                self.login(identity, key)
                with patch.object(api, 'build_achievements', side_effect=AssertionError('database access')):
                    self.get(401)

    def test_mismatched_session_is_forbidden(self):
        for identity, key in ((1, 'other-key'), (99, 'owner-key')):
            self.login(identity, key)
            self.get(403)

    def test_query_parameters_are_rejected(self):
        for query in ('reviewer_id=2', 'reviewer_key=other-key', 'scope=global', 'x='):
            with self.subTest(query=query), patch.object(api, 'build_achievements', side_effect=AssertionError('database access')):
                self.get(400, query_string=query)

    def test_request_bodies_are_rejected(self):
        for body in (b'{}', b' ', b'reviewer_id=2'):
            with self.subTest(body=body), patch.object(api, 'build_achievements', side_effect=AssertionError('database access')):
                self.get(400, data=body)

    def test_only_owner_awards_and_only_display_fields(self):
        self.populate()
        data = self.get().get_json()
        self.assertEqual({'available', 'achievements'}, set(data))
        self.assertTrue(data['available'])
        self.assertEqual(['5', '20'], [a['tier_key'] for a in data['achievements']])
        for award in data['achievements']:
            self.assertEqual({'family', 'scope_key', 'tier_key', 'numerator', 'earned_at_utc'}, set(award))
            self.assertEqual('explorer', award['family'])
            self.assertEqual('global', award['scope_key'])
        self.assertEqual('2026-09-23T12:00:05Z', data['achievements'][0]['earned_at_utc'])
        self.login(2, 'other-key')
        other = self.get().get_json()['achievements']
        self.assertEqual(1, len(other))
        self.assertEqual('2026-09-23T12:00:25Z', other[0]['earned_at_utc'])

    def test_deterministic_order_uses_award_id_for_ties(self):
        self.populate(tied=True)
        with connection(self.path) as conn:
            expected = [dict(r) for r in conn.execute('''SELECT family,scope_key,tier_key,numerator,earned_at_utc
                FROM recognition_awards WHERE reviewer_id=1 ORDER BY earned_at_utc,award_id''')]
        self.assertEqual(2, len(expected))
        self.assertEqual(expected, self.get().get_json()['achievements'])
        self.assertEqual(expected, self.get().get_json()['achievements'])

    def test_each_returned_award_is_verified_in_same_read_snapshot(self):
        self.populate()
        with connection(self.path) as conn:
            ids = [r[0] for r in conn.execute('SELECT award_id FROM recognition_awards WHERE reviewer_id=1 ORDER BY earned_at_utc,award_id')]
        seen = []
        def verify(conn, award_id):
            self.assertTrue(conn.in_transaction)
            self.assertEqual(1, conn.execute('PRAGMA query_only').fetchone()[0])
            with self.assertRaises(sqlite3.OperationalError):
                conn.execute("UPDATE community_reviewers SET email='forbidden'")
            seen.append(award_id)
            return check_award_integrity(conn, award_id)
        with patch.object(achievements, 'check_award_integrity', side_effect=verify):
            self.get()
        self.assertEqual(ids, seen)

    def test_integrity_failure_propagates_and_api_exposes_no_partial_awards(self):
        self.populate()
        with connection(self.path, write=True) as conn:
            conn.execute('DROP TRIGGER recognition_award_witnesses_immutable_delete')
            conn.execute("DELETE FROM recognition_award_witnesses WHERE award_id IN "
                         "(SELECT award_id FROM recognition_awards WHERE reviewer_id=1 AND tier_key='20')")
            conn.commit()
        with self.assertRaises(Quarantined):
            achievements.build_achievements(self.path, 1, 'owner-key')
        with self.assertLogs(api.app.logger, level='ERROR'):
            data = self.get(503).get_json()
        self.assertFalse(data['available'])
        self.assertNotIn('achievements', data)
        self.assertNotIn('evidence', str(data))

    def test_read_only_connection_no_writes_and_no_progress_recomputation(self):
        self.populate()
        before = self.path.read_bytes()
        real_connect = sqlite3.connect
        opened = []
        def connect(database_uri, **kwargs):
            self.assertTrue(database_uri.endswith('?mode=ro'))
            conn = real_connect(database_uri, **kwargs)
            opened.append(conn)
            return conn
        with patch('src.review.recognition.schema.sqlite3.connect', side_effect=connect), \
             patch.object(api, 'build_progress', side_effect=AssertionError('progress recomputed')):
            self.get()
        self.assertEqual(before, self.path.read_bytes())
        self.assertEqual(1, len(opened))
        with self.assertRaises(sqlite3.ProgrammingError):
            opened[0].execute('SELECT 1')

    def test_empty_award_set(self):
        self.assertEqual({'available': True, 'achievements': []}, self.get().get_json())

    def test_awards_are_not_reearned_from_current_assignment_state(self):
        self.populate()
        expected = self.get().get_json()
        with connection(self.path, write=True) as conn:
            conn.execute("UPDATE stop_review_assignments SET status='assigned',completed_at=NULL")
            conn.commit()
        self.assertEqual(expected, self.get().get_json())

    def test_missing_recognition_schema_is_unavailable_not_empty(self):
        legacy = self.path.parent / 'legacy.db'
        with closing(sqlite3.connect(legacy)) as conn:
            conn.executescript("CREATE TABLE community_reviewers(id INTEGER,reviewer_key TEXT);"
                               "INSERT INTO community_reviewers VALUES(1,'owner-key');")
        before = legacy.read_bytes()
        with patch.object(api, 'DATABASE_PATH', legacy), self.assertLogs(api.app.logger, level='ERROR'):
            self.assertFalse(self.get(503).get_json()['available'])
        self.assertEqual(before, legacy.read_bytes())

    def test_missing_database_is_unavailable_and_not_created(self):
        missing = self.path.parent / 'missing.db'
        with patch.object(api, 'DATABASE_PATH', missing), self.assertLogs(api.app.logger, level='ERROR'):
            self.assertFalse(self.get(503).get_json()['available'])
        self.assertFalse(missing.exists())


if __name__ == '__main__':
    unittest.main()
