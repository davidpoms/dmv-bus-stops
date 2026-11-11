"""Local manifest projection reuse only; no runtime/security observation cache."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import sqlite3
import subprocess
import sys
import time
import unittest

from src.review.recognition import administration as a
from src.review.recognition import runtime_enrollment_transition_schema as s
from src.review.recognition.trust import fields, identity, load, require


def _previous_manifest(conn, *, exclude=()):
    """Pre-ZR reader kept only as a timing/equivalence oracle in this test."""
    if not s.present(conn):
        return s.claims.manifest(conn, exclude=exclude)
    expected = s.definitions()
    actual = dict(conn.execute("SELECT name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"))
    require(all(n in actual and ' '.join(actual[n].split()) == ' '.join(sql.split()) for n, sql in expected.items()), 'transition_partial_schema')
    rows = s.authority._rows(conn, s.ACTION)
    require(len(rows) == 1, 'transition_migration_audit')
    audit = s.authority._record(rows[0]); subject = audit['subject']
    fields(subject, ('migration_id','previous_schema_sha256','installed_schema_sha256','installation_id','generation','reason'))
    from src.review.recognition import runtime_execution_attempt_schema as attempts
    prior = s.authority._rows(conn, attempts.ACTION)
    require(len(prior) == 1 and prior[0]['sequence'] < rows[0]['sequence'] and subject['migration_id'] == s.MIGRATION
            and subject['installed_schema_sha256'] == s.claims.manifest(conn)
            and subject['previous_schema_sha256'] == s.claims.manifest(conn, exclude=expected)
            and s.authority._record(prior[0])['subject']['installed_schema_sha256'] == subject['previous_schema_sha256'], 'transition_migration_manifest')
    identity(subject['installation_id']); s.operation._positive(subject['generation'])
    s.authority._reason(subject['reason']); s.authority._reason(audit['actor'])
    binding = conn.execute('SELECT body_json FROM recognition_admin_bindings WHERE generation=?', (subject['generation'],)).fetchone()
    require(binding and load(binding[0])['installation_id'] == subject['installation_id'], 'transition_migration_scope')
    return s.claims.manifest(conn, exclude=set(exclude) | set(expected))
from tests import test_recognition_runtime_enrollment_transition as fixtures
from tests.test_recognition_runtime_execution_attempt_creation import _cleanup_fixture_tree


class ValidationEfficiencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = fixtures.EnrollmentTransitionTests()
        cls.addClassCleanup(_cleanup_fixture_tree, cls.fixture)
        cls.fixture.setUp()
        cls.fixture.migrate()

    @contextmanager
    def connection(self):
        with a.connect(self.fixture.config.control) as source:
            conn = sqlite3.connect(':memory:')
            conn.row_factory = sqlite3.Row
            source.backup(conn)
        try:
            conn.execute('BEGIN IMMEDIATE')
            yield conn
        finally:
            conn.close()

    def observe(self, conn, reader=None, **options):
        reads = []
        conn.set_trace_callback(lambda sql: reads.append(sql) if sql.startswith('SELECT name,sql FROM sqlite_master') else None)
        try:
            result = (reader or s.historical_manifest)(conn, **options)
        finally:
            conn.set_trace_callback(None)
        return result, len(reads)

    def test_one_definition_read_per_call_and_exact_projection(self):
        with self.connection() as conn:
            for excluded in ((), tuple(s.authority.definitions())):
                expected = s.claims.manifest(conn, exclude=set(excluded) | set(s.definitions()))
                for _ in range(2):
                    result, count = self.observe(conn, exclude=excluded)
                    self.assertEqual(expected, result)
                    self.assertEqual(1, count)

    def test_connection_and_transaction_changes_always_read_again(self):
        with self.connection() as first, self.connection() as second:
            expected = self.observe(first)[0]
            self.assertEqual((expected, 1), self.observe(second))
            first.rollback()
            first.execute('BEGIN IMMEDIATE')
            self.assertEqual((expected, 1), self.observe(first))

    def test_unreserved_and_adapted_connections_keep_all_original_reads(self):
        with self.connection() as conn:
            expected = self.observe(conn)[0]
            conn.rollback()
            self.assertEqual((expected, 4), self.observe(conn))
            conn.execute('BEGIN IMMEDIATE')
            class Adapter:
                def execute(self, *args):
                    return conn.execute(*args)
                def set_trace_callback(self, callback):
                    conn.set_trace_callback(callback)
            self.assertEqual((expected, 4), self.observe(Adapter()))

    def test_mutation_and_final_validation_cannot_reuse_prior_schema(self):
        with self.connection() as conn:
            self.observe(conn)
            conn.execute('CREATE TABLE unexpected_schema_change(value TEXT)')
            with self.assertRaisesRegex(ValueError, 'transition_migration_manifest'):
                self.observe(conn)

    def test_history_is_revalidated_not_just_definition_digest(self):
        with self.connection() as conn:
            self.observe(conn)
            # Disposable corruption: changing an audit must not be hidden by a
            # previous successful schema observation. Drop guards only in clone.
            triggers = conn.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger' AND tbl_name='recognition_admin_audit'").fetchall()
            for row in triggers:
                conn.execute('DROP TRIGGER "' + row[0].replace('"', '""') + '"')
            conn.execute("UPDATE recognition_admin_audit SET body_sha256=? WHERE json_extract(body_json,'$.action')=?", ('0'*64, s.ACTION))
            for row in triggers:
                conn.execute(row[1])
            with self.assertRaisesRegex(ValueError, 'runtime_authority_record_integrity'):
                self.observe(conn)

    def test_scope_data_changes_do_not_reuse_an_observation(self):
        with self.connection() as conn:
            # Manifest is schema/history data, not an auth/activation verdict.
            # Even unrelated data mutation forces another read on the next call.
            self.observe(conn)
            self.assertGreater(conn.execute('SELECT count(*) FROM recognition_admin_sessions').fetchone()[0], 0)
            conn.execute('UPDATE recognition_admin_sessions SET revoked=1')
            self.assertEqual(1, self.observe(conn)[1])
            conn.execute('UPDATE recognition_admin_mfa SET epoch=epoch+1')
            self.assertEqual(1, self.observe(conn)[1])
            conn.execute('PRAGMA user_version=19')
            self.assertEqual(1, self.observe(conn)[1])
            conn.execute('PRAGMA query_only=ON')
            self.assertEqual(1, self.observe(conn)[1])

    def test_binding_generation_corruption_is_not_hidden_by_previous_read(self):
        with self.connection() as conn:
            self.observe(conn)
            triggers = conn.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger' AND tbl_name='recognition_admin_bindings'").fetchall()
            for row in triggers:
                conn.execute('DROP TRIGGER "' + row[0].replace('"', '""') + '"')
            conn.execute("UPDATE recognition_admin_bindings SET body_json=json_set(body_json,'$.installation_id',?)", ('00000000-0000-0000-0000-000000000000',))
            for row in triggers:
                conn.execute(row[1])
            with self.assertRaisesRegex(ValueError, 'transition_migration_scope'):
                self.observe(conn)

    def test_thread_has_independent_read_not_transferable_observation(self):
        with self.connection() as conn:
            expected = self.observe(conn)[0]
        def worker():
            with self.connection() as conn:
                return self.observe(conn)
        with ThreadPoolExecutor(max_workers=1) as pool:
            self.assertEqual((expected, 1), pool.submit(worker).result(timeout=20))

    def test_activation_and_generation_data_are_not_cached_or_authorized(self):
        from src.review.recognition import runtime_validation as runtime
        with self.connection() as conn:
            self.observe(conn)
            # Deliberate corruption only in this memory clone. Restore the exact
            # triggers so that a schema mismatch cannot mask data validation.
            for table, assignment in (
                ('recognition_local_activation', "body_sha256='" + '0'*64 + "'"),
                ('recognition_admin_bindings', "body_json=json_set(body_json,'$.generation',999)"),
            ):
                self.assertGreater(conn.execute('SELECT count(*) FROM '+table).fetchone()[0], 0)
                triggers = conn.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger' AND tbl_name=?", (table,)).fetchall()
                for row in triggers:
                    conn.execute('DROP TRIGGER "' + row[0].replace('"', '""') + '"')
                conn.execute('UPDATE '+table+' SET '+assignment)
                for row in triggers:
                    conn.execute(row[1])
                # A manifest is not an activation or generation authorization.
                self.assertEqual(1, self.observe(conn)[1])
            with self.assertRaises(ValueError):
                runtime._history(conn)

    def test_projection_timing_and_before_after_read_counts(self):
        with self.connection() as conn:
            results = {}
            expected = s.historical_manifest(conn)
            for label, reader, reads in (('before', _previous_manifest, 4), ('after', s.historical_manifest, 1)):
                start = time.perf_counter()
                for _ in range(20):
                    result, count = self.observe(conn, reader=reader)
                    self.assertEqual((expected, reads), (result, count))
                results[label] = dict(definition_reads=20*reads, elapsed_seconds=round(time.perf_counter()-start, 6))
            import json
            from pathlib import Path
            output = Path(__file__).resolve().parents[1] / '.tmp' / 'recognition-zr-local-timing.json'
            output.parent.mkdir(exist_ok=True)
            output.write_text(json.dumps(results)+'\n', encoding='utf-8')
            print('ZR_LOCAL_PROJECTION ' + json.dumps(results))

    def test_process_must_read_its_own_connection(self):
        with self.connection() as conn:
            expected = self.observe(conn)[0]
            dump = '\n'.join(conn.iterdump())
        code = '''import sqlite3,sys,json
from src.review.recognition import runtime_enrollment_transition_schema as s
c=sqlite3.connect(':memory:'); c.row_factory=sqlite3.Row
c.executescript(sys.stdin.read()); c.execute('BEGIN IMMEDIATE')
reads=[]
c.set_trace_callback(lambda q: reads.append(1) if q.startswith('SELECT name,sql FROM sqlite_master') else None)
value=s.historical_manifest(c)
print(json.dumps([value,len(reads)]))
c.close()
'''
        result = subprocess.run([sys.executable, '-B', '-c', code], input=dump, text=True,
                                capture_output=True, timeout=20, check=True)
        import json
        self.assertEqual([expected, 1], json.loads(result.stdout))


if __name__ == '__main__':
    unittest.main()
