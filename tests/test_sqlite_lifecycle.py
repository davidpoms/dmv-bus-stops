"""Failure cleanup, including separate-process rollback-journal contention."""
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.api import app as api
from src.review import assignment_router as router
from src.review import consensus


class SQLiteLifecycleTests(unittest.TestCase):
    def assert_failure_cleanup(self, call, conn):
        with patch.object(sqlite3, 'connect', return_value=conn):
            with self.assertRaises(sqlite3.OperationalError):
                call()
        conn.close.assert_called_once()
        conn.rollback.assert_called_once()

    def test_query_execute_failure(self):
        conn = MagicMock()
        conn.cursor.return_value.execute.side_effect = sqlite3.OperationalError('execute')
        self.assert_failure_cleanup(lambda: api.query_db('UPDATE t SET n=?', (1,)), conn)

    def test_query_commit_failure(self):
        conn = MagicMock()
        conn.commit.side_effect = sqlite3.OperationalError('commit')
        self.assert_failure_cleanup(lambda: api.query_db('UPDATE t SET n=1'), conn)

    def test_query_fetch_failure(self):
        conn = MagicMock()
        conn.cursor.return_value.fetchall.side_effect = sqlite3.OperationalError('fetch')
        self.assert_failure_cleanup(lambda: api.query_db('SELECT n FROM t'), conn)

    def test_query_success_preserves_order_and_parameters(self):
        conn = MagicMock()
        conn.cursor.return_value.fetchall.return_value = [(7,)]
        with patch.object(sqlite3, 'connect', return_value=conn):
            self.assertEqual([(7,)], api.query_db('SELECT ?', (7,)))
        conn.cursor.return_value.execute.assert_called_once_with('SELECT ?', (7,))
        names = [c[0] for c in conn.mock_calls]
        self.assertLess(names.index('commit'), names.index('cursor().fetchall'))
        conn.close.assert_called_once()
        conn.rollback.assert_not_called()

    def test_reviewer_failure_paths(self):
        for step in ('execute', 'commit'):
            with self.subTest(step=step):
                conn = MagicMock()
                target = conn.cursor.return_value.execute if step == 'execute' else conn.commit
                target.side_effect = sqlite3.OperationalError(step)
                self.assert_failure_cleanup(router.get_or_create_reviewer, conn)

    def test_assignment_failure_paths(self):
        for step in ('execute', 'commit'):
            with self.subTest(step=step):
                conn = MagicMock()
                cur = conn.cursor.return_value
                cur.execute.return_value.__iter__.return_value = iter([])
                cur.execute.return_value.fetchone.side_effect = [None, (1, 1)]
                target = cur.execute if step == 'execute' else conn.commit
                target.side_effect = sqlite3.OperationalError(step)
                with patch.object(router, 'stop_is_active', return_value=True):
                    self.assert_failure_cleanup(lambda: router.assign_stop(1, 'direct', stop_id=1), conn)

    def test_consensus_failure_paths(self):
        for step in ('execute', 'commit'):
            with self.subTest(step=step):
                conn = MagicMock()
                conn.execute.return_value.fetchall.return_value = []
                target = conn.execute if step == 'execute' else conn.commit
                target.side_effect = sqlite3.OperationalError(step)
                self.assert_failure_cleanup(lambda: consensus.calculate_stop_consensus(1), conn)

    def test_direct_api_writer_commit_failures(self):
        cases = [(api.create_observation, {'stop_id': 1}),
                 (api.save_reviewer_routes, {'routes': ['R1']})]
        for call, payload in cases:
            with self.subTest(call=call.__name__):
                conn = MagicMock()
                conn.commit.side_effect = sqlite3.OperationalError('commit')
                with patch.dict(api.app.config, SECRET_KEY='lifecycle-test-only'), \
                     api.app.test_request_context('/', method='POST', json=payload), \
                     patch.object(api, 'get_or_create_reviewer', return_value=(1, 'test')):
                    self.assert_failure_cleanup(call, conn)

    def test_early_returns_close_without_write(self):
        conn = MagicMock()
        conn.cursor.return_value.execute.return_value.fetchone.return_value = (1,)
        with patch.object(sqlite3, 'connect', return_value=conn):
            self.assertEqual((1, 'existing'), router.get_or_create_reviewer('existing'))
        conn.close.assert_called_once()
        conn.commit.assert_not_called()
        conn = MagicMock()
        with patch.object(sqlite3, 'connect', return_value=conn), \
             patch.object(router, 'stop_is_active', return_value=False):
            self.assertIsNone(router.assign_stop(1, 'direct', stop_id=1))
        conn.close.assert_called_once()
        conn.commit.assert_not_called()

    def test_auth_connection_setup_failure_closes(self):
        conn = MagicMock()
        conn.execute.side_effect = sqlite3.OperationalError('pragma')
        with patch.object(sqlite3, 'connect', return_value=conn):
            with self.assertRaises(sqlite3.OperationalError):
                api._auth_db()
        conn.close.assert_called_once()

    def test_sign_in_unexpected_failure_closes(self):
        conn = MagicMock()
        with patch.dict(api.app.config, TESTING=True), \
             api.app.test_request_context('/reviewer/sign-in', method='POST', json={'email': 'test@example.org'}), \
             patch.object(api, '_auth_db', return_value=conn), \
             patch.object(api, 'enforce_login_rate_limits', side_effect=TypeError('unexpected')):
            with self.assertRaises(TypeError):
                api.reviewer_sign_in()
        conn.close.assert_called_once()

    def test_read_connections_close_on_failure(self):
        for call in (lambda: api.get_wmata_history(1), lambda: api.get_wmata_evidence(1),
                     lambda: api.get_stop_evidence_summary(1), api.review_queue,
                     lambda: router.stop_is_active(1)):
            with self.subTest(call=call):
                conn = MagicMock()
                conn.execute.side_effect = sqlite3.OperationalError('read')
                with patch.object(sqlite3, 'connect', return_value=conn):
                    with self.assertRaises(sqlite3.OperationalError):
                        call()
                conn.close.assert_called_once()

    def test_rollback_failure_still_closes(self):
        conn = MagicMock()
        conn.commit.side_effect = sqlite3.OperationalError('commit')
        conn.rollback.side_effect = sqlite3.OperationalError('rollback')
        with patch.object(sqlite3, 'connect', return_value=conn):
            with self.assertRaises(sqlite3.OperationalError):
                api.query_db('UPDATE t SET n=1')
        conn.close.assert_called_once()

    def test_file_backed_commit_timeout_releases_lock_across_processes(self):
        # Child holds an explicit read transaction until told to release it.
        reader_code = """
import sqlite3, sys
c = sqlite3.connect(sys.argv[1])
c.execute('BEGIN')
c.execute('SELECT * FROM t').fetchall()
print('ready', flush=True)
sys.stdin.readline()
c.rollback()
c.close()
"""
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / 'contention.db')
            with closing(sqlite3.connect(path)) as setup:
                self.assertEqual('delete', setup.execute('PRAGMA journal_mode').fetchone()[0])
                setup.execute('CREATE TABLE t(n INTEGER)')
                setup.execute('INSERT INTO t VALUES(0)')
                setup.commit()
            blocker = subprocess.Popen([sys.executable, '-B', '-c', reader_code, path],
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, text=True)
            writer = None
            caught = None
            try:
                writer = sqlite3.connect(path, timeout=0.05)
                # communicate handshake is bounded by a reader thread timeout.
                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(blocker.stdout.readline)
                    try:
                        self.assertEqual('ready', future.result(timeout=10).strip())
                    except BaseException:
                        blocker.kill()
                        raise
                with patch.object(api, 'DATABASE_PATH', path), patch.object(sqlite3, 'connect', return_value=writer):
                    try:
                        api.query_db('UPDATE t SET n=1')
                    except sqlite3.OperationalError as exc:
                        caught = exc  # Retain traceback; do not rely on GC cleanup.
                self.assertIsNotNone(caught)
                self.assertIn('locked', str(caught))
                blocker.communicate('\n', timeout=10)
                self.assertEqual(0, blocker.returncode)
                independent = sqlite3.connect(path, timeout=0.1)
                try:
                    self.assertEqual([(0,)], independent.execute('SELECT * FROM t').fetchall())
                    independent.execute('UPDATE t SET n=2')
                    independent.commit()
                finally:
                    independent.close()
                with self.assertRaises(sqlite3.ProgrammingError):
                    writer.execute('SELECT 1')
                self.assertFalse(Path(path + '-journal').exists())
            finally:
                try:
                    if writer is not None:
                        writer.close()
                finally:
                    if blocker.poll() is None:
                        blocker.kill()
                    blocker.communicate(timeout=10)


if __name__ == '__main__':
    unittest.main()
