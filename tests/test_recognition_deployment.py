"""Startup/target audit using synthetic files only, never a deployment DB."""

import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import textwrap
import unittest

from src.api.deployment import configured_database
from src.review.recognition import authority, authorization, permanent_schema
from src.review.recognition.schema import connection


ROOT = Path(__file__).resolve().parents[1]


class RecognitionDeploymentTests(unittest.TestCase):
    def test_database_selection_has_no_repository_or_relative_default(self):
        self.assertIsNone(configured_database({}))
        self.assertIsNone(configured_database({'DMV_BUS_STOPS_DB': ''}))
        self.assertIsNone(configured_database({'DMV_BUS_STOPS_DB': 'relative.db'}))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'explicit.db'
            self.assertEqual(path.resolve(), configured_database({'DMV_BUS_STOPS_DB': str(path)}))
            self.assertFalse(path.exists())

    def test_fresh_wsgi_and_cli_imports_never_connect_or_invoke_recognition_writers(self):
        code = textwrap.dedent('''
            import os
            import sqlite3
            from contextlib import ExitStack
            from pathlib import Path
            from unittest.mock import patch
            def forbidden(*args, **kwargs):
                raise AssertionError('unexpected startup write/provisioning/connection')
            with ExitStack() as stack:
                stack.enter_context(patch('dotenv.load_dotenv', return_value=False))
                stack.enter_context(patch.object(sqlite3, 'connect', side_effect=forbidden))
                from src.review.recognition import permanent, permanent_schema, live_first_look_schema
                from src.review.recognition import live_first_looks, authority, qualification, processing
                for module, names in (
                    (permanent, ('finalize', 'append_discrepancy')),
                    (permanent_schema, ('install', 'migrate')),
                    (live_first_look_schema, ('install', 'migrate')),
                    (live_first_looks, ('enqueue', 'seal_pending', 'record_retryable_failure')),
                    (authority, ('provision_production_authority', 'DisposableWorkspace')),
                    (qualification, ('capture', 'capture_completion')),
                    (processing, ('lease_jobs', 'finalize_job')),
                ):
                    for name in names:
                        stack.enter_context(patch.object(module, name, side_effect=forbidden))
                from src.api.app import app, DATABASE_PATH
                from src.review.assignment_router import DB
                from scripts.active import serve_pilot, process_live_recognition
                from scripts.active import rehearse_private_recognition, create_recognition_tables
                assert DATABASE_PATH == DB
                assert app.config['LIVE_FIRST_LOOK_GATE'].capture is False
                assert app.config['LIVE_FIRST_LOOK_GATE'].issuance is False
                assert app.config['LIVE_FIRST_LOOK_AUTHORITY'] is None
                assert app.config['LIVE_FIRST_LOOK_AUTHORIZATION'] is None
                assert app.config['LIVE_FIRST_LOOK_CONFIGURATION'].activation_at_utc is None
                assert app.config['LIVE_RECOGNITION_GATE'].issuance is False
                response = app.test_client().get('/test-route')
                expected = int(os.environ['EXPECTED_STATUS'])
                assert response.status_code == expected, response.status_code
                if expected == 200:
                    import types
                    stack.enter_context(patch.dict('sys.modules', {'waitress': types.SimpleNamespace(serve=lambda *a, **k: None)}))
                    serve_pilot.main()
            print('startup-safe')
        ''')
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / 'disposable.db'
            sqlite3.connect(database).close()
            before = database.read_bytes()
            for raw, status in (('', 503), ('relative.db', 503),
                                (str(database.with_name('absent.db')), 503), (str(database), 200)):
                env = {key: value for key, value in os.environ.items() if not key.startswith(
                    ('DMV_', 'FLASK_', 'REVIEWER_', 'SMTP_', 'RESEND_', 'LIVE_RECOGNITION_', 'PILOT_'))}
                env.update(DMV_BUS_STOPS_DB=raw, FLASK_SECRET_KEY='synthetic-startup-test-' * 3,
                           SESSION_COOKIE_SECURE='1', PILOT_SUPPORT_CONTACT='synthetic@example.org',
                           EXPECTED_STATUS=str(status), PYTHONDONTWRITEBYTECODE='1')
                with self.subTest(target=raw):
                    result = subprocess.run([sys.executable, '-B', '-c', code], cwd=ROOT,
                                            env=env, capture_output=True, text=True, timeout=45)
                    self.assertEqual(0, result.returncode, result.stderr)
                    self.assertIn('startup-safe', result.stdout)
            self.assertEqual(before, database.read_bytes())
            self.assertFalse(database.with_name('absent.db').exists())

    def test_production_shaped_target_outside_workspace_rejects_disposable_migration(self):
        # Both paths are synthetic. No real target's path, inode, or bytes are read.
        workspace = authority.DisposableWorkspace()
        self.addCleanup(workspace.cleanup)
        with tempfile.TemporaryDirectory() as directory:
            production = Path(directory) / 'dmv_bus_stops.db'
            conn = sqlite3.connect(production)
            try:
                conn.execute('CREATE TABLE synthetic_marker(value TEXT)')
                conn.commit()
            finally:
                conn.close()
            before = production.read_bytes()
            for label in ('production', 'disposable'):
                approval = authorization.Authorization(
                    target=authorization.target_identity(production), environment=label,
                    reference='synthetic-only', **authorization.migration_binding(
                        'private_recognition', permanent_schema.definitions()))
                workspace.approved.add(approval)
                with self.subTest(label=label), self.assertRaises(authorization.AuthorizationError):
                    permanent_schema.migrate(production, apply=True,
                        authorization=approval, authority=workspace.authority)
                with connection(production, write=True) as conn:
                    conn.execute('BEGIN IMMEDIATE')
                    with self.assertRaises(authorization.AuthorizationError):
                        permanent_schema.install(conn, authorization=approval, authority=workspace.authority)
                    conn.commit()
            self.assertEqual(before, production.read_bytes())

    def test_disposable_authority_is_not_based_on_database_filename(self):
        workspace = authority.DisposableWorkspace()
        self.addCleanup(workspace.cleanup)
        database = Path(workspace.name) / 'dmv_bus_stops.db'
        sqlite3.connect(database).close()
        binding = authorization.migration_binding('private_recognition', permanent_schema.definitions())
        approval = workspace.approve(database, **binding)
        authorization.verify(database, approval, workspace.authority, **binding)
        with self.assertRaisesRegex(authorization.AuthorizationError, 'production_authority_not_provisioned'):
            authority.provision_production_authority()


if __name__ == '__main__':
    unittest.main()
