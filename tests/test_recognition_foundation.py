"""Permanent foundation: disposable files only; no application activation."""

from pathlib import Path
from contextlib import contextmanager
from contextlib import redirect_stderr
import io
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from src.review.recognition import DISABLED, RecognitionGate
from src.review.recognition.backfill import capture_batch, dry_run
from src.review.recognition.processing import finalize_job, lease_jobs, ledger_candidates
from src.review.recognition.processing import prepare_evaluation, materialize_ledger
from src.review.recognition.integrity import check_award_integrity
from src.review.recognition.qualification import Quarantined, capture, permanent_time, qualify
from src.review.recognition.rules import RULE_KEY, canonical, digest, explorer_candidates, initial_definition
from src.review.recognition.schema import TABLES, connection, migrate
from scripts.active import rehearse_recognition_capture as rehearsal
from scripts.active import issue_historical_explorer as issuance


ENABLED = RecognitionGate(capture=True, issuance=True)


class RecognitionTests(unittest.TestCase):
    def issuance_fixture(self):
        source, path, manifest, arguments = self.rehearsal_fixture()
        # Four awards across three owners: 42, 7, 5, 1 distinct completions.
        self.sql("INSERT INTO community_reviewers VALUES(3,'third'),(4,'fourth')")
        for start, end, owner in ((184, 190, 2), (191, 195, 3), (196, 196, 4)):
            self.sql("UPDATE stop_review_assignments SET reviewer_id=? WHERE id BETWEEN ? AND ?", (owner, start, end))
            self.sql("UPDATE stop_observations SET reviewer_id=? WHERE assignment_id BETWEEN ? AND ?", (owner, start, end))
        # Snapshot may include initialized but empty recognition tables.
        source.write_bytes(self.path.read_bytes())
        manifest = dry_run(self.path, RULE_KEY, after_assignment=141, through_assignment=210,
                           sqlite_utc_provenance="synthetic-fixture-current-timestamp")
        capture_batch(self.path, manifest, gate=RecognitionGate(capture=True))
        capture_path = self.path.parent / 'reviewed-capture.json'
        # File-byte identity deliberately differs from the canonical ledger digest.
        capture_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
        self.capture_manifest_hash = rehearsal.file_hash(capture_path)
        manifest = dry_run(self.path, RULE_KEY, after_assignment=141, through_assignment=210,
                           sqlite_utc_provenance="synthetic-fixture-current-timestamp")
        path.write_text(canonical(manifest), encoding="utf-8")
        arguments.update(source_sha256=rehearsal.file_hash(source), manifest_sha256=rehearsal.file_hash(path),
                         capture_manifest_path=capture_path)
        self.binding_path = self.path.parent / 'reviewed-binding.json'
        binding_patch = patch.object(issuance, 'BINDING_PATH', self.binding_path)
        binding_patch.start()
        self.addCleanup(binding_patch.stop)
        announce_patch = patch.object(issuance, 'announce')
        self.announcements = announce_patch.start()
        self.addCleanup(announce_patch.stop)
        self.write_issuance_binding(arguments)
        self.assertEqual(4, len(manifest['candidates']))
        return source, path, manifest, arguments

    def write_issuance_binding(self, arguments):
        stat = self.path.stat()
        self.binding_path.write_text(canonical(dict(environment='production', hostname=issuance.socket.getfqdn(),
            database=str(self.path.resolve()), device=stat.st_dev, inode=stat.st_ino,
            capture_manifest_sha256=self.capture_manifest_hash,
            issuance_manifest_sha256=arguments['manifest_sha256'], snapshot_sha256=arguments['source_sha256'],
            review_reference='SYNTHETIC TEST AUTHORIZATION ONLY')), encoding='utf-8')

    def test_production_binding_accepts_uppercase_stored_hashes(self):
        self.binding_path = self.path.parent / 'reviewed-binding.json'
        manifest_hash = 'abcdef01' * 8
        self.capture_manifest_hash = ('abcdef23' * 8).upper()
        snapshot_hash = 'fedcba98' * 8
        self.write_issuance_binding(dict(manifest_sha256=manifest_hash.upper(),
                                        source_sha256=snapshot_hash.upper()))
        before = self.binding_path.read_bytes()
        with patch.object(issuance, 'BINDING_PATH', self.binding_path):
            binding = issuance.target_binding(self.path.resolve(), manifest_hash, snapshot_hash)
            self.assertEqual(manifest_hash.upper(), binding['issuance_manifest_sha256'])
            self.assertEqual(self.capture_manifest_hash, binding['capture_manifest_sha256'])
            self.assertEqual(snapshot_hash.upper(), binding['snapshot_sha256'])
            with self.assertRaisesRegex(ValueError, 'binding_manifest_hash_mismatch'):
                issuance.target_binding(self.path.resolve(), '0' * 64, snapshot_hash)
            with self.assertRaisesRegex(ValueError, 'binding_source_hash_mismatch'):
                issuance.target_binding(self.path.resolve(), manifest_hash, '0' * 64)
        self.assertEqual(before, self.binding_path.read_bytes())

    def test_issuance_default_and_cli_require_explicit_authorization(self):
        source, path, manifest, args = self.issuance_fixture()
        before = self.path.read_bytes()
        with patch.object(issuance, 'lease_jobs', side_effect=AssertionError('write')):
            self.assertEqual('verify-only', issuance.issue(self.path, source, path, **args)['mode'])
        bootstrap = "from pathlib import Path; from scripts.active import issue_historical_explorer as m; " \
                    "m.BINDING_PATH=Path(" + repr(str(self.binding_path)) + "); m.main()"
        command = [sys.executable, '-B', '-c', bootstrap, '--production-db', str(self.path),
                   '--source-snapshot', str(source), '--manifest', str(path),
                   '--capture-manifest', str(args['capture_manifest_path']),
                   '--manifest-sha256', args['manifest_sha256'], '--source-sha256', args['source_sha256'],
                   '--expected-excluded', '1']
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual('verify-only', json.loads(result.stdout)['mode'])
        result = subprocess.run(command + ['--capture'], capture_output=True, text=True, timeout=30)
        self.assertEqual(2, result.returncode)
        self.assertEqual(before, self.path.read_bytes())

    def test_separate_binding_manifest_hashes_and_case_insensitive_checks(self):
        source, path, manifest, args = self.issuance_fixture()
        binding = json.loads(self.binding_path.read_text(encoding='utf-8'))
        capture_hash = binding['capture_manifest_sha256']
        issuance_hash = binding['issuance_manifest_sha256']
        self.assertNotEqual(capture_hash, issuance_hash)
        self.assertNotEqual(capture_hash, digest(dict(manifest, candidates=[])))
        before = self.path.read_bytes()
        uppercase = dict(binding, capture_manifest_sha256=capture_hash.upper(),
                         issuance_manifest_sha256=issuance_hash.upper(),
                         snapshot_sha256=binding['snapshot_sha256'].upper())
        self.binding_path.write_text(canonical(uppercase), encoding='utf-8')
        self.assertEqual('verify-only', issuance.issue(self.path, source, path, **args)['mode'])
        for field, value, error in (
            ('issuance_manifest_sha256', '0' * 64, 'binding_manifest_hash_mismatch'),
            ('capture_manifest_sha256', '0' * 64, 'binding_capture_manifest_hash_mismatch'),
            ('snapshot_sha256', '0' * 64, 'binding_source_hash_mismatch'),
            ('issuance_manifest_sha256', capture_hash, 'binding_manifest_hash_mismatch'),
            ('capture_manifest_sha256', issuance_hash, 'binding_capture_manifest_hash_mismatch'),
        ):
            self.binding_path.write_text(canonical(dict(binding, **{field: value})), encoding='utf-8')
            with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, error), \
                 patch.object(issuance, 'lease_jobs', side_effect=AssertionError('write')):
                issuance.issue(self.path, source, path, issue_production=True, **args)
        self.assertEqual(before, self.path.read_bytes())

    def test_separate_binding_fields_required_and_capture_content_pinned(self):
        source, path, manifest, args = self.issuance_fixture()
        binding = json.loads(self.binding_path.read_text(encoding='utf-8'))
        legacy = dict(binding, manifest_sha256=binding['issuance_manifest_sha256'])
        del legacy['capture_manifest_sha256']
        del legacy['issuance_manifest_sha256']
        invalid = [legacy, dict(binding, manifest_sha256=binding['issuance_manifest_sha256'])]
        invalid.extend(dict(binding, **{field: value}) for field in
                       ('capture_manifest_sha256', 'issuance_manifest_sha256') for value in ('', ' ', None))
        for changed in invalid:
            self.binding_path.write_text(canonical(changed), encoding='utf-8')
            with self.subTest(binding=changed), self.assertRaisesRegex(ValueError, 'invalid_target_binding'):
                issuance.issue(self.path, source, path, **args)
        capture_path = args['capture_manifest_path']
        capture = json.loads(capture_path.read_text(encoding='utf-8'))
        capture['sqlite_utc_provenance'] = 'different capture artifact'
        capture_path.write_text(canonical(capture), encoding='utf-8')
        binding['capture_manifest_sha256'] = rehearsal.file_hash(capture_path)
        self.binding_path.write_text(canonical(binding), encoding='utf-8')
        before = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'capture_manifest_mismatch'), \
             patch.object(issuance, 'lease_jobs', side_effect=AssertionError('write')):
            issuance.issue(self.path, source, path, issue_production=True, **args)
        self.assertEqual(before, self.path.read_bytes())

    def test_issuance_four_awards_pending_jobs_and_idempotent_retry(self):
        source, path, manifest, args = self.issuance_fixture()
        source_before = source.read_bytes()
        with patch.object(issuance, 'lease_jobs', wraps=lease_jobs) as lease:
            result = issuance.issue(self.path, source, path, issue_production=True, **args)
        self.assertEqual(55, lease.call_count)
        self.assertTrue(all(c.kwargs['gate'] == RecognitionGate(capture=False, issuance=True)
                            for c in lease.call_args_list))
        self.assertEqual(4, result['awards_issued'])
        self.assertEqual(35, sum(a['witness_count'] for a in result['awards']))
        self.assertTrue(all(j['state'] == 'done' and j['attempts'] == 1 for j in result['jobs']))
        before = self.path.read_bytes()
        self.assertEqual(0, issuance.issue(self.path, source, path, issue_production=True, **args)['awards_issued'])
        self.assertEqual(before, self.path.read_bytes())
        self.assertEqual(source_before, source.read_bytes())
        self.assertEqual(RecognitionGate(), DISABLED)
        for name in ('src/api/app.py', 'src/review/complete_stop_review.py'):
            self.assertNotIn('issue_historical_explorer', Path(name).read_text(encoding='utf-8'))

    def test_issuance_rejects_manifest_hash_rule_and_candidate_changes(self):
        source, path, manifest, args = self.issuance_fixture()
        before = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'manifest_hash'):
            issuance.issue(self.path, source, path, **dict(args, manifest_sha256='0' * 64))
        for defect in ('rule', 'candidate', 'cohort'):
            changed = json.loads(canonical(manifest))
            if defect == 'rule':
                changed['rule_key'] = 'explorer:v2'
            elif defect == 'candidate':
                changed['candidates'][0]['earned_at_utc'] = '2000-01-01T00:00:00Z'
            else:
                changed['cohort']['after_assignment'] = 140
            path.write_text(canonical(changed), encoding='utf-8')
            with self.subTest(defect=defect), self.assertRaises(ValueError), \
                 patch.object(issuance, 'lease_jobs', side_effect=AssertionError('write')):
                issuance.issue(self.path, source, path, issue_production=True,
                               **dict(args, manifest_sha256=rehearsal.file_hash(path)))
        self.assertEqual(before, self.path.read_bytes())

    def test_issuance_rejects_missing_unexpected_or_leased_jobs(self):
        source, path, manifest, args = self.issuance_fixture()
        for mutation in ("DELETE FROM recognition_jobs WHERE assignment_id=142",
                         "UPDATE recognition_jobs SET attempts=1 WHERE assignment_id=142",
                         "UPDATE recognition_jobs SET state='leased',lease_token='other',"
                         "lease_until_utc='2099-01-01T00:00:00Z' WHERE assignment_id=142"):
            backup = self.path.read_bytes()
            self.sql(mutation)
            before = self.path.read_bytes()
            with self.assertRaisesRegex(ValueError, 'unexpected_job'), \
                 patch.object(issuance, 'lease_jobs', side_effect=AssertionError('write')):
                issuance.issue(self.path, source, path, issue_production=True, **args)
            self.assertEqual(before, self.path.read_bytes())
            self.path.write_bytes(backup)

    def test_issuance_rejects_changed_evidence_schema_and_source_alias(self):
        source, path, manifest, args = self.issuance_fixture()
        with self.assertRaisesRegex(ValueError, 'source_target_alias'):
            issuance.issue(source, source, path, **args)
        with self.assertRaisesRegex(ValueError, 'source_hash'):
            issuance.issue(self.path, source, path, **dict(args, source_sha256='0' * 64))
        self.sql("UPDATE stop_review_assignments SET completed_at='2026-09-24 21:10:27' WHERE id=142")
        before = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'reviewed_manifest'), \
             patch.object(issuance, 'lease_jobs', side_effect=AssertionError('write')):
            issuance.issue(self.path, source, path, issue_production=True, **args)
        self.assertEqual(before, self.path.read_bytes())

    def test_issuance_partial_witness_failure_rolls_back_lease_and_awards(self):
        source, path, manifest, args = self.issuance_fixture()
        before = {table: self.sql('SELECT * FROM ' + table) for table in TABLES}
        original = issuance.connection

        @contextmanager
        def fail_witnesses(*a, **kw):
            with original(*a, **kw) as conn:
                if kw.get('write'):
                    class PartialWitnessConnection:
                        def __getattr__(self, name):
                            return getattr(conn, name)

                        def executemany(self, sql, rows):
                            self_outer.assertIn('recognition_award_witnesses', sql)
                            conn.execute(sql, rows[0])
                            self_outer.assertEqual(1, conn.execute(
                                'SELECT COUNT(*) FROM recognition_award_witnesses').fetchone()[0])
                            raise sqlite3.IntegrityError('injected after first witness')
                    self_outer = self
                    yield PartialWitnessConnection()
                else:
                    yield conn
        with patch.object(issuance, 'connection', side_effect=fail_witnesses):
            with self.assertRaises(sqlite3.DatabaseError):
                issuance.issue(self.path, source, path, issue_production=True, **args)
        self.assertEqual(before, {table: self.sql('SELECT * FROM ' + table) for table in TABLES})
        self.assertEqual(4, issuance.issue(self.path, source, path, issue_production=True, **args)['awards_issued'])

    def test_issuance_partial_cohort_retry_and_unexpected_job(self):
        source, path, manifest, args = self.issuance_fixture()
        def fail_second(conn, assignment_id, *a, **kw):
            if assignment_id == 143:
                raise RuntimeError('interrupted cohort')
            return finalize_job(conn, assignment_id, *a, **kw)
        with patch.object(issuance, 'finalize_job', side_effect=fail_second):
            with self.assertRaisesRegex(RuntimeError, 'interrupted cohort'):
                issuance.issue(self.path, source, path, issue_production=True, **args)
        self.assertEqual([('done', 1), ('pending', 0)], self.sql(
            'SELECT state,attempts FROM recognition_jobs WHERE assignment_id IN (142,143) ORDER BY assignment_id'))
        self.assertEqual(2, issuance.issue(self.path, source, path, issue_production=True, **args)['awards_issued'])
        # Corrupt fixture only: extra orphan job must fail integrity before leasing.
        conn = sqlite3.connect(self.path)
        try:
            conn.execute("INSERT INTO recognition_jobs(assignment_id,rule_key,updated_at_utc) VALUES(999,?,'now')", (RULE_KEY,))
            conn.commit()
        finally:
            conn.close()
        with self.assertRaisesRegex(ValueError, 'foreign_key_check'), \
             patch.object(issuance, 'lease_jobs', side_effect=AssertionError('write')):
            issuance.issue(self.path, source, path, issue_production=True, **args)

    def test_issuance_rejects_unexpected_award_trigger_before_writes(self):
        source, path, manifest, args = self.issuance_fixture()
        self.sql("CREATE TRIGGER unwanted AFTER INSERT ON recognition_awards BEGIN "
                 "UPDATE community_reviewers SET display_name='changed'; END")
        before = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'unexpected_capture_trigger'), \
             patch.object(issuance, 'lease_jobs', side_effect=AssertionError('write')):
            issuance.issue(self.path, source, path, issue_production=True, **args)
        self.assertEqual(before, self.path.read_bytes())

    def test_production_binding_rejects_rehearsal_copy_host_and_replacement(self):
        source, path, manifest, args = self.issuance_fixture()
        original_binding = self.binding_path.read_text(encoding='utf-8')
        working = self.path.parent / 'recognition-working.db'
        working.write_bytes(self.path.read_bytes())
        before = working.read_bytes()
        with self.assertRaisesRegex(ValueError, 'unauthorized_production_target'):
            issuance.issue(working, source, path, issue_production=True, **args)
        self.assertEqual(before, working.read_bytes())
        for key, value in (('hostname', 'not-this-host'), ('environment', 'rehearsal'), ('inode', -1)):
            changed = json.loads(original_binding)
            changed[key] = value
            self.binding_path.write_text(canonical(changed), encoding='utf-8')
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'unauthorized_production_target'):
                issuance.issue(self.path, source, path, issue_production=True, **args)
        self.binding_path.write_text(original_binding, encoding='utf-8')
        result = issuance.issue(self.path, source, path, **args)
        self.assertEqual(str(self.path.resolve()), result['target'])
        self.assertEqual(manifest['candidates'], result['expected_candidates'])
        self.assertEqual(55, result['expected_jobs'])
        self.assertEqual('production', result['environment'])

    def test_issuance_accepts_unrelated_live_drift_and_preserves_it(self):
        source, path, manifest, args = self.issuance_fixture()
        self.sql("INSERT INTO community_reviewers VALUES(9,'new profile')")
        self.review(300, timestamp='2026-10-01T00:00:00Z')
        self.sql('UPDATE stop_review_assignments SET reviewer_id=9 WHERE id=300')
        self.sql('UPDATE stop_observations SET reviewer_id=9 WHERE assignment_id=300')
        self.sql("UPDATE community_reviewers SET display_name='updated unrelated profile' WHERE id=9")
        self.sql('CREATE TABLE unrelated_application_data(value TEXT)')
        self.sql("INSERT INTO unrelated_application_data VALUES('new live data')")
        with connection(self.path) as conn:
            before = rehearsal.application_fingerprint(conn)
        result = issuance.issue(self.path, source, path, issue_production=True, **args)
        self.assertEqual(4, result['awards_total'])
        with connection(self.path) as conn:
            self.assertEqual(before, rehearsal.application_fingerprint(conn))

    def test_issuance_pins_all_candidate_identity_fields(self):
        source, path, manifest, args = self.issuance_fixture()
        before = self.path.read_bytes()
        for field in ('reviewer_id', 'tier_key', 'earned_at_utc', 'rule_key',
                      'assignment_id', 'observation_id', 'physical_stop_id'):
            changed = json.loads(canonical(manifest))
            candidate = changed['candidates'][0]
            if field in ('assignment_id', 'observation_id', 'physical_stop_id'):
                candidate['evidence']['witnesses'][0][field] += 1
            else:
                candidate[field] = 99 if field == 'reviewer_id' else 'changed'
            path.write_text(canonical(changed), encoding='utf-8')
            changed_args = dict(args, manifest_sha256=rehearsal.file_hash(path))
            self.write_issuance_binding(changed_args)
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'unexpected_candidate_set'), \
                 patch.object(issuance, 'lease_jobs', side_effect=AssertionError('first write reached')):
                issuance.issue(self.path, source, path, issue_production=True, **changed_args)
            self.assertEqual(before, self.path.read_bytes())

    def test_issuance_rejects_pinned_historical_row_mutations(self):
        source, path, manifest, args = self.issuance_fixture()
        for statement in (
            "UPDATE community_reviewers SET display_name='historical owner changed' WHERE id=1",
            'UPDATE stop_review_assignments SET reviewer_id=2 WHERE id=142',
            'UPDATE stop_observations SET physical_stop_id=143 WHERE assignment_id=142',
            "UPDATE stop_observations SET observed_at='changed' WHERE assignment_id=142",
        ):
            backup = self.path.read_bytes()
            self.sql(statement)
            with self.subTest(statement=statement), self.assertRaises(ValueError), \
                 patch.object(issuance, 'lease_jobs', side_effect=AssertionError('first write reached')):
                issuance.issue(self.path, source, path, issue_production=True, **args)
            self.path.write_bytes(backup)

    def test_issuance_expired_lease_refused_and_inflight_expiry_rolls_back(self):
        source, path, manifest, args = self.issuance_fixture()
        backup = self.path.read_bytes()
        self.sql("UPDATE recognition_jobs SET state='leased',attempts=1,lease_token='old',"
                 "lease_until_utc='2000-01-01T00:00:00Z' WHERE assignment_id=142")
        with self.assertRaisesRegex(ValueError, 'unexpected_job_state'):
            issuance.issue(self.path, source, path, issue_production=True, **args)
        self.path.write_bytes(backup)

        def expire(conn, *a, **kw):
            jobs = lease_jobs(conn, *a, **kw)
            conn.execute("UPDATE recognition_jobs SET lease_until_utc='2000-01-01T00:00:00Z' WHERE assignment_id=?",
                         (jobs[0]['assignment_id'],))
            return jobs
        with patch.object(issuance, 'lease_jobs', side_effect=expire), self.assertRaisesRegex(ValueError, 'stale_job_lease'):
            issuance.issue(self.path, source, path, issue_production=True, **args)
        self.assertEqual(backup, self.path.read_bytes())

    def test_issuance_later_award_failure_rolls_back_entire_job(self):
        source, path, manifest, args = self.issuance_fixture()
        before = self.path.read_bytes()
        calls = []
        def fail_later(conn, award_id):
            result = check_award_integrity(conn, award_id)
            calls.append(award_id)
            if len(calls) == 2:
                self.assertEqual(2, conn.execute('SELECT COUNT(*) FROM recognition_awards').fetchone()[0])
                self.assertEqual(25, conn.execute('SELECT COUNT(*) FROM recognition_award_witnesses').fetchone()[0])
                raise ValueError('later award injected failure')
            return result
        with patch('src.review.recognition.processing.check_award_integrity', side_effect=fail_later), \
             self.assertRaisesRegex(ValueError, 'later award injected'):
            issuance.issue(self.path, source, path, issue_production=True, **args)
        self.assertEqual(before, self.path.read_bytes())

    def test_issuance_rechecks_cohort_and_schema_before_first_write(self):
        source, path, manifest, args = self.issuance_fixture()
        for change in ('cohort', 'schema'):
            backup = self.path.read_bytes()
            def race(event, *a, **kw):
                if event == 'issuance-authorization-boundary':
                    if change == 'cohort':
                        self.sql("UPDATE community_reviewers SET display_name='changed after verification' WHERE id=1")
                    else:
                        self.sql("CREATE TRIGGER racing AFTER INSERT ON recognition_awards BEGIN SELECT 1; END")
            with self.subTest(change=change), patch.object(issuance, 'announce', side_effect=race), \
                 patch.object(issuance, 'lease_jobs', side_effect=AssertionError('first write reached')), \
                 self.assertRaisesRegex(ValueError, 'historical_cohort_changed|schema_changed'):
                issuance.issue(self.path, source, path, issue_production=True, **args)
            self.assertEqual([(0,)], self.sql('SELECT COUNT(*) FROM recognition_awards'))
            self.path.write_bytes(backup)

    def test_issuance_writer_has_no_full_application_or_integrity_scan(self):
        source, path, manifest, args = self.issuance_fixture()
        original = issuance.connection
        statements = []
        @contextmanager
        def trace(*a, **kw):
            with original(*a, **kw) as conn:
                if kw.get('write'):
                    conn.set_trace_callback(statements.append)
                yield conn
        with patch.object(issuance, 'connection', side_effect=trace), \
             patch.object(rehearsal, 'application_fingerprint', side_effect=AssertionError('whole application scan')):
            issuance.issue(self.path, source, path, issue_production=True, **args)
        self.assertFalse(any('PRAGMA integrity_check' in s or 'PRAGMA foreign_key_check' in s for s in statements))
        self.assertTrue(any('BEGIN IMMEDIATE' in s for s in statements))

    def test_issuance_source_snapshot_race_rejected_before_write(self):
        source, path, manifest, args = self.issuance_fixture()
        before = self.path.read_bytes()
        def race(event, *a, **kw):
            if event == 'issuance-authorization-boundary':
                with source.open('ab') as stream:
                    stream.write(b'changed snapshot')
        with patch.object(issuance, 'announce', side_effect=race), \
             patch.object(issuance, 'lease_jobs', side_effect=AssertionError('first write reached')), \
             self.assertRaisesRegex(ValueError, 'source_snapshot_changed'):
            issuance.issue(self.path, source, path, issue_production=True, **args)
        self.assertEqual(before, self.path.read_bytes())

    def test_issuance_cli_reports_partial_progress_after_committed_job(self):
        source, path, manifest, args = self.issuance_fixture()
        def fail_second(conn, assignment_id, *a, **kw):
            if assignment_id == 143:
                raise ValueError('second job failed')
            return finalize_job(conn, assignment_id, *a, **kw)
        output = io.StringIO()
        argv = ['--production-db', str(self.path), '--source-snapshot', str(source), '--manifest', str(path),
                '--capture-manifest', str(args['capture_manifest_path']),
                '--manifest-sha256', args['manifest_sha256'], '--source-sha256', args['source_sha256'],
                '--expected-excluded', '1', '--issue-production']
        with patch.object(issuance, 'finalize_job', side_effect=fail_second), redirect_stderr(output), \
             self.assertRaises(SystemExit) as stopped:
            issuance.main(argv)
        self.assertEqual(1, stopped.exception.code)
        result = json.loads(output.getvalue())
        self.assertEqual('second job failed', result['error'])
        self.assertEqual(2, result['partial_progress']['awards_total'])
        self.assertIn(dict(state='done', attempts=1, count=1), result['partial_progress']['jobs'])
        self.assertTrue(any(c.args[0] == 'job-committed' for c in self.announcements.call_args_list))
        self.assertTrue(any(c.args[0] == 'issuance-authorization-boundary' for c in self.announcements.call_args_list))

    def test_issuance_hard_termination_recovery_only_then_retry(self):
        source, path, manifest, args = self.issuance_fixture()
        code = """
import os, sys
from src.review.recognition.schema import connection
from src.review.recognition import RecognitionGate
from src.review.recognition.processing import lease_jobs, prepare_evaluation, finalize_job
p = prepare_evaluation(sys.argv[1], 1, 'explorer:v1')
with connection(sys.argv[1], write=True) as c:
    c.execute('PRAGMA cache_size=1')
    c.execute('BEGIN IMMEDIATE')
    g=RecognitionGate(issuance=True)
    j=lease_jobs(c,'explorer:v1',gate=g,limit=1)[0]
    finalize_job(c,j['assignment_id'],j['lease_token'],'explorer:v1',p,gate=g)
    # Force dirty pages into the DB while the rollback journal protects them.
    c.execute("UPDATE community_reviewers SET display_name=? WHERE id=1", ('x'*200000,))
    os._exit(73)
"""
        child = subprocess.run([sys.executable, '-B', '-c', code, str(self.path)], capture_output=True, timeout=30)
        self.assertEqual(73, child.returncode, child.stderr)
        journal = Path(str(self.path) + '-journal')
        self.assertTrue(journal.exists())
        with self.assertRaisesRegex(ValueError, 'offline_copy_required'):
            issuance.issue(self.path, source, path, **args)
        with patch.object(issuance, 'lease_jobs', side_effect=AssertionError('recovery cannot issue')):
            result = issuance.issue(self.path, source, path, recover_production=True, **args)
        self.assertFalse(journal.exists())
        self.assertEqual('recover-production', result['mode'])
        self.assertEqual(0, result['awards_total'])
        self.assertTrue(all(j['state'] == 'pending' and j['attempts'] == 0 for j in result['jobs']))
        self.assertEqual(4, issuance.issue(self.path, source, path, issue_production=True, **args)['awards_total'])
        with self.assertRaisesRegex(ValueError, 'recovery_cannot_issue'):
            issuance.issue(self.path, source, path, issue_production=True, recover_production=True, **args)

    def rehearsal_fixture(self):
        for assignment in range(142, 197):
            self.review(assignment, timestamp="2026-09-23 21:10:27")
        self.sql("INSERT INTO stop_review_assignments VALUES(210,142,1,'assigned',NULL)")
        source = self.path.parent / "snapshot.db"
        source.write_bytes(self.path.read_bytes())
        migrate(self.path, apply=True)
        manifest = dry_run(self.path, RULE_KEY, after_assignment=141, through_assignment=210,
                           sqlite_utc_provenance="synthetic-fixture-current-timestamp")
        path = self.path.parent / "reviewed.json"
        path.write_text(canonical(manifest), encoding="utf-8")
        arguments = dict(source_sha256=rehearsal.file_hash(source),
                         manifest_sha256=rehearsal.file_hash(path), expected_excluded=1)
        return source, path, manifest, arguments

    def test_rehearsal_default_is_read_only_and_cli_has_no_issuance(self):
        source, path, manifest, arguments = self.rehearsal_fixture()
        before = self.path.read_bytes()
        with patch.object(rehearsal, "capture_batch", side_effect=AssertionError("write")):
            result = rehearsal.rehearse(source, self.path, path, **arguments)
        self.assertEqual("empty", result["state"])
        self.assertEqual(before, self.path.read_bytes())
        command = [sys.executable, "-B", str(Path(rehearsal.__file__)),
                   "--source-snapshot", str(source), "--disposable-target", str(self.path),
                   "--manifest", str(path), "--source-sha256", arguments["source_sha256"],
                   "--manifest-sha256", arguments["manifest_sha256"], "--expected-excluded", "1"]
        result = subprocess.run(command, capture_output=True, text=True, timeout=20)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("verify-only", json.loads(result.stdout)["mode"])
        result = subprocess.run(command + ["--issuance"], capture_output=True, text=True, timeout=20)
        self.assertEqual(2, result.returncode)
        self.assertEqual(before, self.path.read_bytes())

    def test_rehearsal_paths_and_uninitialized_target_rejected(self):
        source, path, manifest, arguments = self.rehearsal_fixture()
        alias = source.parent / "hardlink.db"
        os.link(source, alias)
        for target in (source, source.parent / "." / source.name, alias):
            with self.subTest(target=target), self.assertRaisesRegex(ValueError, "source_target_alias"):
                rehearsal.rehearse(source, target, path, **arguments)
        missing = source.parent / "missing.db"
        with self.assertRaises(FileNotFoundError):
            rehearsal.rehearse(source, missing, path, **arguments)
        self.assertFalse(missing.exists())
        uninitialized = source.parent / "uninitialized.db"
        uninitialized.write_bytes(source.read_bytes())
        with self.assertRaisesRegex(ValueError, "initialized_schema_required"):
            rehearsal.rehearse(source, uninitialized, path, **arguments)
        with patch.dict(os.environ, {"DMV_BUS_STOPS_DB": str(self.path)}):
            with self.assertRaisesRegex(ValueError, "application_target_forbidden"):
                rehearsal.rehearse(source, self.path, path, **arguments)

    def test_rehearsal_capture_55_pending_only_and_exact_retry(self):
        source, path, manifest, arguments = self.rehearsal_fixture()
        source_before = source.read_bytes()
        with patch.object(rehearsal, "capture_batch", wraps=capture_batch) as batch, \
             patch("src.review.recognition.processing.lease_jobs", side_effect=AssertionError("lease")), \
             patch("src.review.recognition.processing.finalize_job", side_effect=AssertionError("issue")):
            result = rehearsal.rehearse(source, self.path, path, capture_disposable=True, **arguments)
            self.assertEqual(RecognitionGate(capture=True, issuance=False), batch.call_args.kwargs["gate"])
        self.assertEqual("captured", result["state"])
        before = {table: self.sql("SELECT * FROM " + table) for table in TABLES}
        rehearsal.rehearse(source, self.path, path, capture_disposable=True, **arguments)
        self.assertEqual(before, {table: self.sql("SELECT * FROM " + table) for table in TABLES})
        self.assertEqual(55, len(before["recognition_completions"]))
        self.assertEqual([(55,)], self.sql("SELECT COUNT(*) FROM recognition_jobs WHERE state='pending' "
                         "AND attempts=0 AND lease_token IS NULL AND lease_until_utc IS NULL"))
        self.assertEqual([], before["recognition_awards"])
        self.assertEqual([], before["recognition_award_witnesses"])
        self.assertEqual(1, len(before["recognition_runs"]))
        self.assertEqual(source_before, source.read_bytes())
        self.assertTrue(dry_run(self.path, RULE_KEY, after_assignment=141, through_assignment=210,
                               sqlite_utc_provenance=manifest["sqlite_utc_provenance"])["candidates"])
        self.assertEqual(RecognitionGate(), DISABLED)

    def test_rehearsal_tampered_manifest_and_changed_source_rejected(self):
        source, path, manifest, arguments = self.rehearsal_fixture()
        before = self.path.read_bytes()
        for field, value in (("rule_sha256", "wrong"), ("excluded", []), ("source_sha256", "wrong"),
                             ("candidates", [{}]), ("qualified", []), ("source", []),
                             ("cohort", dict(manifest["cohort"], has_more=True)),
                             ("cohort", dict(manifest["cohort"], after_assignment=142)),
                             ("excluded", [dict(manifest["excluded"][0], reason="fabricated")])):
            tampered = dict(manifest, **{field: value})
            path.write_text(canonical(tampered), encoding="utf-8")
            with self.subTest(field=field), self.assertRaises(ValueError):
                rehearsal.rehearse(source, self.path, path, capture_disposable=True,
                                   **dict(arguments, manifest_sha256=rehearsal.file_hash(path)))
        self.assertEqual(before, self.path.read_bytes())
        path.write_text(canonical(manifest) + " ", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "manifest_hash_mismatch"):
            rehearsal.rehearse(source, self.path, path, **arguments)
        path.write_text(canonical(manifest), encoding="utf-8")
        self.sql("UPDATE stop_review_assignments SET completed_at='2026-09-24 00:00:00' WHERE id=142")
        with self.assertRaisesRegex(ValueError, "source_target_data_mismatch"):
            rehearsal.rehearse(source, self.path, path, capture_disposable=True, **arguments)
        with self.assertRaisesRegex(ValueError, "source_hash_mismatch"):
            rehearsal.rehearse(source, self.path, path, **dict(arguments, source_sha256="0" * 64))

    def test_rehearsal_failure_rolls_back_completion_job_and_run(self):
        source, path, manifest, arguments = self.rehearsal_fixture()
        before = self.path.read_bytes()
        with patch("src.review.recognition.backfill.record_run", side_effect=RuntimeError("injected")):
            with self.assertRaisesRegex(RuntimeError, "injected"):
                rehearsal.rehearse(source, self.path, path, capture_disposable=True, **arguments)
        self.assertEqual(before, self.path.read_bytes())
        for table in ("recognition_completions", "recognition_jobs", "recognition_runs"):
            self.assertEqual([(0,)], self.sql("SELECT COUNT(*) FROM " + table))
        rehearsal.rehearse(source, self.path, path, capture_disposable=True, **arguments)

    def test_rehearsal_refuses_unexpected_jobs_and_missing_protection(self):
        source, path, manifest, arguments = self.rehearsal_fixture()
        rehearsal.rehearse(source, self.path, path, capture_disposable=True, **arguments)
        self.sql("UPDATE recognition_jobs SET attempts=1 WHERE assignment_id=142")
        with self.assertRaisesRegex(ValueError, "job_state_mismatch"):
            rehearsal.rehearse(source, self.path, path, capture_disposable=True, **arguments)
        self.sql("DROP TRIGGER recognition_completion_sequence")
        with self.assertRaisesRegex(ValueError, "recognition_protection_missing"):
            rehearsal.rehearse(source, self.path, path, **arguments)

    def test_rehearsal_rejects_replaced_trigger_before_capture(self):
        source, path, manifest, arguments = self.rehearsal_fixture()
        self.sql("DROP TRIGGER recognition_completion_sequence")
        self.sql("CREATE TRIGGER recognition_completion_sequence BEFORE INSERT ON recognition_completions "
                 "BEGIN SELECT 1; END")
        before = self.path.read_bytes()
        for apply in (False, True):
            with self.subTest(capture=apply), patch.object(rehearsal, "capture_batch") as batch:
                with self.assertRaisesRegex(ValueError, "recognition_protection_mismatch"):
                    rehearsal.rehearse(source, self.path, path, capture_disposable=apply, **arguments)
                batch.assert_not_called()
            self.assertEqual(before, self.path.read_bytes())

    def test_rehearsal_rejects_extra_trigger_on_each_capture_table_before_writes(self):
        source, path, manifest, arguments = self.rehearsal_fixture()
        source_before = source.read_bytes()
        for table in ("recognition_completions", "recognition_jobs", "recognition_runs"):
            self.sql(f"CREATE TRIGGER unexpected_mutation AFTER INSERT ON {table} "
                     "BEGIN UPDATE community_reviewers SET display_name='changed'; END")
            before = self.path.read_bytes()
            for apply in (False, True):
                with self.subTest(table=table, capture=apply), patch.object(rehearsal, "capture_batch") as batch:
                    with self.assertRaisesRegex(ValueError, "unexpected_capture_trigger"):
                        rehearsal.rehearse(source, self.path, path, capture_disposable=apply, **arguments)
                    batch.assert_not_called()
                self.assertEqual(before, self.path.read_bytes())
                self.assertEqual(source_before, source.read_bytes())
            self.sql("DROP TRIGGER unexpected_mutation")

    def test_rehearsal_fingerprint_is_lossless_and_deterministic(self):
        with sqlite3.connect(":memory:") as conn:
            conn.execute("CREATE TABLE values_to_compare(value)")
            fingerprints = []
            for value in (None, 1, 1.0, "1", b"1", "prefix\x00one", "prefix\x00two",
                          b"prefix\x00one", b"prefix\x00two"):
                conn.execute("DELETE FROM values_to_compare")
                conn.execute("INSERT INTO values_to_compare VALUES(?)", (value,))
                result = rehearsal.application_fingerprint(conn)
                self.assertEqual(result, rehearsal.application_fingerprint(conn))
                fingerprints.append(canonical(result))
            self.assertEqual(len(fingerprints), len(set(fingerprints)))
            conn.execute("DELETE FROM values_to_compare")
            conn.executemany("INSERT INTO values_to_compare VALUES(?)", [("a\x00b",), (b"a\x00b",)])
            original = rehearsal.application_fingerprint(conn)
            conn.execute("DELETE FROM values_to_compare")
            conn.executemany("INSERT INTO values_to_compare VALUES(?)", [(b"a\x00b",), ("a\x00b",)])
            self.assertEqual(original, rehearsal.application_fingerprint(conn))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "fixture.db"
        with sqlite3.connect(self.path) as db:
            db.executescript("""
                CREATE TABLE community_reviewers(id INTEGER PRIMARY KEY,display_name TEXT);
                INSERT INTO community_reviewers VALUES(1,'Private Name'),(2,'Other');
                CREATE TABLE physical_stops(id INTEGER PRIMARY KEY);
                CREATE TABLE stop_gtfs_status(physical_stop_id INTEGER PRIMARY KEY,current_gtfs INTEGER);
                CREATE TABLE stop_review_assignments(id INTEGER PRIMARY KEY,stop_id INTEGER,reviewer_id INTEGER,status TEXT,completed_at TEXT);
                CREATE TABLE stop_observations(id INTEGER PRIMARY KEY,assignment_id INTEGER,reviewer_id INTEGER,physical_stop_id INTEGER,source TEXT,observed_at TEXT);
            """)
        db.close()

    def sql(self, query, parameters=()):
        with connection(self.path, write=True) as conn:
            rows = conn.execute(query, parameters).fetchall()
            conn.commit()
            return [tuple(row) for row in rows]

    def review(self, assignment, stop=None, timestamp=None):
        stop = assignment if stop is None else stop
        timestamp = timestamp or f"2026-09-01T00:{assignment // 60:02d}:{assignment % 60:02d}Z"
        with connection(self.path, write=True) as conn:
            conn.execute("INSERT OR IGNORE INTO physical_stops VALUES(?)", (stop,))
            conn.execute("INSERT OR IGNORE INTO stop_gtfs_status VALUES(?,0)", (stop,))
            conn.execute("INSERT INTO stop_review_assignments VALUES(?,?,1,'completed',?)", (assignment, stop, timestamp))
            conn.execute("INSERT INTO stop_observations VALUES(?,?,1,?,'community_review','2026-09-01 01:00:00')", (assignment, assignment, stop))
            conn.commit()

    def capture_all(self, count):
        migrate(self.path, apply=True)
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            for assignment in range(1, count + 1):
                capture(conn, assignment, RULE_KEY, gate=ENABLED)
            conn.commit()

    def issue(self, rule=RULE_KEY, limit=100):
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            jobs = lease_jobs(conn, rule, gate=ENABLED, limit=limit)
            conn.commit()
        for job in jobs:
            owner = self.sql("SELECT reviewer_id FROM recognition_completions WHERE assignment_id=?", (job["assignment_id"],))[0][0]
            prepared = prepare_evaluation(self.path, owner, rule)
            with connection(self.path, write=True) as conn:
                conn.execute("BEGIN IMMEDIATE")
                finalize_job(conn, job["assignment_id"], job["lease_token"], rule,
                             prepared, gate=ENABLED)
                conn.commit()
        return jobs

    def test_migration_rehearsal_repeat_source_preservation_and_fk(self):
        self.review(1)
        original = self.path.read_bytes()
        migrate(self.path)
        self.assertEqual(original, self.path.read_bytes())
        before = self.sql("SELECT * FROM stop_observations")
        migrate(self.path, apply=True)
        migrate(self.path, apply=True)
        self.assertEqual(before, self.sql("SELECT * FROM stop_observations"))
        tables = {r[0] for r in self.sql("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'recognition_%'")}
        self.assertEqual(set(TABLES), tables)
        with connection(self.path, write=True) as conn:
            self.assertEqual(1, conn.execute("PRAGMA foreign_keys").fetchone()[0])
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("INSERT INTO recognition_jobs(assignment_id,rule_key,updated_at_utc) VALUES(999,?,'now')", (RULE_KEY,))
        self.assertEqual([], self.sql("PRAGMA foreign_key_check"))

    def test_incompatible_schema_rolls_back_and_missing_path_not_created(self):
        self.sql("CREATE TABLE recognition_jobs(wrong TEXT)")
        with self.assertRaisesRegex(ValueError, "incompatible_recognition_schema"):
            migrate(self.path, apply=True)
        self.assertEqual([], self.sql("SELECT name FROM sqlite_master WHERE name='recognition_completions'"))
        missing = self.path.parent / "missing.db"
        with self.assertRaises(sqlite3.OperationalError):
            migrate(missing, apply=True)
        self.assertFalse(missing.exists())

    def test_migration_on_repository_schema_and_drift_detection(self):
        path = self.path.parent / "current-schema.db"
        db = sqlite3.connect(path)
        try:
            db.executescript((Path(__file__).resolve().parents[1] / "src/database/schema.sql").read_text(encoding="utf-8"))
            db.commit()
        finally:
            db.close()
        migrate(path, apply=True)
        migrate(path, apply=True)
        with connection(path, write=True) as conn:
            conn.execute("DROP TRIGGER recognition_completions_immutable_update")
            conn.execute("CREATE TRIGGER recognition_completions_immutable_update BEFORE UPDATE ON recognition_completions BEGIN SELECT 1; END")
            conn.commit()
        with self.assertRaisesRegex(ValueError, "incompatible_recognition_schema"):
            migrate(path, apply=True)

    def test_commands_require_explicit_paths_and_processor_has_no_apply(self):
        root = Path(__file__).resolve().parents[1]
        for script, arguments in (
            ("create_recognition_tables.py", []),
            ("process_reviewer_recognition.py", []),
            ("process_reviewer_recognition.py", ["--db", str(self.path), "--rule-key", RULE_KEY,
                                                 "--through-assignment", "0", "--apply"]),
        ):
            result = subprocess.run([sys.executable, "-B", str(root / "scripts/active" / script), *arguments],
                                    capture_output=True, text=True, timeout=20, cwd=root)
            self.assertEqual(2, result.returncode, result.stderr)
        self.assertEqual([], self.sql("SELECT name FROM sqlite_master WHERE name LIKE 'recognition_%'"))

    def test_qualification_rejects_duplicates_before_matching(self):
        self.review(1)
        self.sql("INSERT INTO stop_observations VALUES(2,1,2,999,'community_review',NULL)")
        with connection(self.path) as conn, self.assertRaisesRegex(Quarantined, "ambiguous"):
            qualify(conn, 1)

    def test_qualification_identity_source_status_and_missing_rows(self):
        self.review(1)
        self.sql("INSERT INTO stop_observations VALUES(2,1,2,999,'import',NULL)")
        with connection(self.path) as conn:
            self.assertEqual(1, qualify(conn, 1)["observation_id"])
        for column, wrong in (("reviewer_id", 2), ("physical_stop_id", 999)):
            self.sql(f"UPDATE stop_observations SET {column}=? WHERE id=1", (wrong,))
            with connection(self.path) as conn, self.assertRaisesRegex(Quarantined, "identity_mismatch"):
                qualify(conn, 1)
            self.sql(f"UPDATE stop_observations SET {column}=1 WHERE id=1")
        self.sql("DELETE FROM physical_stops")
        with connection(self.path) as conn, self.assertRaisesRegex(Quarantined, "missing_identity"):
            qualify(conn, 1)
        self.sql("UPDATE stop_review_assignments SET status='assigned'")
        with connection(self.path) as conn, self.assertRaisesRegex(Quarantined, "not_completed"):
            qualify(conn, 1)

    def test_timestamp_policy_and_no_observed_fallback(self):
        for value in (None, "bad", "2026-02-30T00:00:00Z", "2026-09-01T00:00:00.000Z",
                      "2026-09-01T00:00:00.1-04:00", "2026-09-01 00:00:00"):
            with self.subTest(value=value), self.assertRaises(Quarantined):
                permanent_time(value)
        self.assertEqual(("2026-09-01T04:00:00Z", "explicit_offset"), permanent_time("2026-09-01T00:00:00-04:00"))
        self.assertEqual("2026-09-01T00:00:00Z", permanent_time("2026-09-01 00:00:00", sqlite_utc_provenance="reviewed-submit-writer")[0])
        self.review(1, timestamp="bad")
        with connection(self.path) as conn, self.assertRaisesRegex(Quarantined, "invalid_completion_time"):
            qualify(conn, 1)

    def test_capture_inactive_history_and_retries_preserve_evidence(self):
        self.review(1)
        self.capture_all(1)
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            capture(conn, 1, RULE_KEY, gate=ENABLED)
            conn.commit()
        self.assertEqual([(1,)], self.sql("SELECT count(*) FROM recognition_completions"))
        self.assertEqual([(1,)], self.sql("SELECT count(*) FROM recognition_jobs"))
        self.sql("UPDATE stop_review_assignments SET completed_at='2026-09-02T00:00:00Z'")
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            with self.assertRaisesRegex(Quarantined, "immutable_completion_conflict"):
                capture(conn, 1, RULE_KEY, gate=ENABLED)

    def test_explorer_all_boundaries_and_explicit_rule_definition(self):
        facts = [dict(assignment_id=n, observation_id=n, reviewer_id=1, physical_stop_id=n,
                      completed_at_utc=f"2026-09-01T00:{n // 60:02d}:{n % 60:02d}Z") for n in range(1, 102)]
        for count in (0, 4, 5, 19, 20, 49, 50, 99, 100, 101):
            with self.subTest(count=count):
                candidates = explorer_candidates(facts[:count], RULE_KEY, initial_definition())
                self.assertEqual([str(n) for n in (5, 20, 50, 100) if n <= count], [c["tier_key"] for c in candidates])
                for c in candidates:
                    self.assertEqual(c["numerator"], len(c["evidence"]["witnesses"]))
                    self.assertEqual(facts[c["numerator"]-1]["completed_at_utc"], c["earned_at_utc"])
        # Proves evaluator uses supplied definition, not module thresholds.
        changed = initial_definition()
        changed["thresholds"] = [20]
        self.assertEqual(["20"], [c["tier_key"] for c in explorer_candidates(facts, "test-rule", changed)])

    def test_earliest_distinct_witnesses_order_is_deterministic(self):
        for n in range(1, 7):
            self.review(n, stop=1 if n == 6 else n, timestamp="2026-09-01T00:00:00Z")
        self.capture_all(6)
        with connection(self.path) as conn:
            conn.execute("BEGIN")
            snapshot = materialize_ledger(conn, RULE_KEY, reviewer_id=1)
            facts = [dict(r) for r in conn.execute("SELECT * FROM recognition_completions ORDER BY assignment_id DESC")]
        candidates = ledger_candidates(snapshot)
        self.assertEqual(candidates, explorer_candidates(facts, RULE_KEY, initial_definition()))
        self.assertEqual([1, 2, 3, 4, 5], [w["assignment_id"] for w in candidates[0]["evidence"]["witnesses"]])

    def test_immutable_triggers_and_lifetime_uniqueness(self):
        for n in range(1, 6):
            self.review(n)
        self.capture_all(5)
        self.issue()
        for table in set(TABLES) - {"recognition_jobs", "recognition_runs"}:
            column = self.sql(f"PRAGMA table_info({table})")[0][1]
            for statement in (f"DELETE FROM {table}", f"UPDATE {table} SET {column}={column}"):
                with self.subTest(statement=statement), self.assertRaises(sqlite3.IntegrityError):
                    self.sql(statement)
        with self.assertRaises(sqlite3.IntegrityError):
            self.sql("""INSERT INTO recognition_awards SELECT 'different-id',reviewer_id,family,scope_key,tier_key,
                rule_key,earned_at_utc,evaluated_at_utc,origin,numerator,evidence_json,evidence_sha256 FROM recognition_awards""")
        self.assertEqual([(1,)], self.sql("SELECT count(*) FROM recognition_awards"))
        # Protect against REPLACE even through a connection with recursive triggers off.
        with sqlite3.connect(self.path) as legacy:
            with self.assertRaises(sqlite3.IntegrityError):
                legacy.execute("INSERT OR REPLACE INTO recognition_rule_versions SELECT * FROM recognition_rule_versions")
        legacy.close()

    def test_version_changes_do_not_reaward_and_stale_delivery_fails(self):
        for n in range(1, 6):
            self.review(n)
        self.capture_all(5)
        jobs = self.issue()
        original_awards = self.sql("SELECT * FROM recognition_awards")
        original_witnesses = self.sql("SELECT * FROM recognition_award_witnesses")
        definition = initial_definition()
        self.sql("INSERT INTO recognition_rule_versions VALUES('explorer:v2','explorer',2,?,?,'2026-10-01T00:00:00Z')", (canonical(definition), digest(definition)))
        self.review(6)
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            capture(conn, 6, "explorer:v2", gate=ENABLED)
            conn.commit()
        self.issue("explorer:v2")
        self.assertEqual([(1,)], self.sql("SELECT count(*) FROM recognition_awards"))
        self.assertEqual(original_awards, self.sql("SELECT * FROM recognition_awards"))
        self.assertEqual(original_witnesses, self.sql("SELECT * FROM recognition_award_witnesses"))
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            with self.assertRaisesRegex(Quarantined, "stale_job_lease"):
                finalize_job(conn, 1, jobs[0]["lease_token"], RULE_KEY, [], gate=ENABLED)

    def test_disabled_services_do_not_open_or_write(self):
        self.assertEqual(RecognitionGate(), DISABLED)
        self.assertIsNone(capture(None, 1, RULE_KEY))
        self.assertEqual([], lease_jobs(None, RULE_KEY))
        self.assertEqual([], finalize_job(None, 1, "token", RULE_KEY, []))
        self.assertIsNone(capture_batch("missing.db", {}))
        self.review(1)
        before = self.path.read_bytes()
        with connection(self.path, write=True) as conn:
            self.assertIsNone(capture(conn, 1, RULE_KEY))
        self.assertEqual(before, self.path.read_bytes())

    def test_backfill_deterministic_bounded_private_manifest_and_idempotent_capture(self):
        for n in range(1, 7):
            self.review(n)
        self.sql("UPDATE stop_review_assignments SET completed_at='2026-09-01T00:00:00.5Z' WHERE id=6")
        migrate(self.path, apply=True)
        before = self.path.read_bytes()
        plan = dry_run(self.path, RULE_KEY, through_assignment=6, limit=6)
        self.assertEqual(plan, dry_run(self.path, RULE_KEY, through_assignment=6, limit=6))
        self.assertEqual(before, self.path.read_bytes())
        self.assertEqual([], plan["candidates"])
        self.assertEqual("fractional_timestamp_policy_unresolved", plan["excluded"][0]["reason"])
        self.assertNotIn("Private Name", canonical(plan))
        partial = dry_run(self.path, RULE_KEY, through_assignment=6, limit=2)
        self.assertEqual(2, partial["cohort"]["next_after_assignment"])
        self.assertTrue(partial["cohort"]["has_more"])
        run = capture_batch(self.path, plan, gate=ENABLED)
        self.assertEqual(run, capture_batch(self.path, plan, gate=ENABLED))
        self.assertEqual([(5,)], self.sql("SELECT count(*) FROM recognition_completions"))
        self.assertEqual([(1,)], self.sql("SELECT count(*) FROM recognition_runs"))
        self.assertEqual([(0,)], self.sql("SELECT count(*) FROM recognition_awards"))
        repeated = dry_run(self.path, RULE_KEY, through_assignment=6, limit=6)
        self.assertEqual(repeated, dry_run(self.path, RULE_KEY, through_assignment=6, limit=6))
        self.assertEqual(["5"], [c["tier_key"] for c in repeated["candidates"]])
        for query in ("DELETE FROM recognition_runs", "UPDATE recognition_runs SET state='running',finished_at_utc=NULL"):
            with self.assertRaises(sqlite3.IntegrityError):
                self.sql(query)

    def test_changed_backfill_input_rejected_and_failure_rolls_back_closes(self):
        self.review(1)
        self.review(2)
        migrate(self.path, apply=True)
        plan = dry_run(self.path, RULE_KEY, through_assignment=2)
        with patch("src.review.recognition.backfill.record_run", side_effect=RuntimeError("injected")):
            with self.assertRaisesRegex(RuntimeError, "injected"):
                capture_batch(self.path, plan, gate=ENABLED)
        self.assertEqual([(0,)], self.sql("SELECT count(*) FROM recognition_completions"))
        # Independent writer succeeding demonstrates no retained write lock.
        self.sql("UPDATE stop_review_assignments SET completed_at='2026-10-01T00:00:00Z' WHERE id=1")
        with self.assertRaisesRegex(Quarantined, "backfill_input_changed"):
            capture_batch(self.path, plan, gate=ENABLED)

    def test_award_witness_failure_rolls_back_group_and_expired_lease_retries(self):
        for n in range(1, 6):
            self.review(n)
        self.capture_all(5)
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            first = lease_jobs(conn, RULE_KEY, gate=ENABLED, limit=1)[0]
            conn.commit()
        self.sql("UPDATE recognition_jobs SET lease_until_utc='2000-01-01T00:00:00Z' WHERE assignment_id=1")
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            job = lease_jobs(conn, RULE_KEY, gate=ENABLED, limit=1)[0]
            self.assertNotEqual(first["lease_token"], job["lease_token"])
            conn.commit()
        before_source = self.sql("SELECT * FROM stop_observations")
        self.sql("""CREATE TRIGGER injected_failure BEFORE INSERT ON recognition_award_witnesses
            WHEN (SELECT count(*) FROM recognition_award_witnesses)=2
            BEGIN SELECT RAISE(ABORT,'injected'); END""")
        prepared = prepare_evaluation(self.path, 1, RULE_KEY)
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            with self.assertRaisesRegex(sqlite3.IntegrityError, "injected"):
                finalize_job(conn, 1, job["lease_token"], RULE_KEY, prepared, gate=ENABLED)
            # Even if a caller catches the exception and commits, no partial award.
            conn.commit()
        self.assertEqual([(0,)], self.sql("SELECT count(*) FROM recognition_awards"))
        self.assertEqual([(0,)], self.sql("SELECT count(*) FROM recognition_award_witnesses"))
        self.assertEqual(before_source, self.sql("SELECT * FROM stop_observations"))
        self.assertEqual([('leased',)], self.sql("SELECT state FROM recognition_jobs WHERE assignment_id=1"))
        self.sql("DROP TRIGGER injected_failure")

    def test_completion_job_failure_is_atomic_with_assignment_transaction(self):
        self.review(1)
        self.sql("UPDATE stop_review_assignments SET status='assigned',completed_at=NULL")
        migrate(self.path, apply=True)
        self.sql("CREATE TRIGGER reject_job BEFORE INSERT ON recognition_jobs BEGIN SELECT RAISE(ABORT,'injected'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            with connection(self.path, write=True) as conn:
                conn.execute("BEGIN IMMEDIATE")
                conn.execute("UPDATE stop_review_assignments SET status='completed',completed_at='2026-09-01T00:00:00Z'")
                capture(conn, 1, RULE_KEY, gate=ENABLED)
                conn.commit()
        self.assertEqual([('assigned', None)], self.sql("SELECT status,completed_at FROM stop_review_assignments"))
        self.assertEqual([(0,)], self.sql("SELECT count(*) FROM recognition_completions"))
        self.assertEqual([(1,)], self.sql("SELECT count(*) FROM stop_observations"))

    def test_connection_closes_even_if_rollback_raises(self):
        mock = MagicMock()
        mock.rollback.side_effect = RuntimeError("rollback failure")
        with patch("src.review.recognition.schema.sqlite3.connect", return_value=mock):
            with self.assertRaisesRegex(RuntimeError, "rollback failure"):
                with connection(self.path):
                    pass
        mock.close.assert_called_once()

    def test_cross_rule_changed_qualification_is_rejected_without_rewriting_award(self):
        for n in range(1, 6):
            self.review(n)
        self.capture_all(5)
        self.issue()
        original = self.sql("SELECT * FROM recognition_awards")
        witnesses = self.sql("SELECT * FROM recognition_award_witnesses")
        definition = initial_definition()
        self.sql("INSERT INTO recognition_rule_versions VALUES('explorer:v2','explorer',2,?,?,'2026-10-01T00:00:00Z')", (canonical(definition), digest(definition)))
        self.review(6, timestamp="2026-08-01T00:00:00Z")
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            capture(conn, 6, "explorer:v2", gate=ENABLED)
            job = lease_jobs(conn, "explorer:v2", gate=ENABLED, limit=1)[0]
            conn.commit()
        prepared = prepare_evaluation(self.path, 1, "explorer:v2")
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            with self.assertRaisesRegex(Quarantined, "award_qualification_evidence_conflict"):
                finalize_job(conn, 6, job["lease_token"], "explorer:v2", prepared, gate=ENABLED)
            conn.commit()
        self.assertEqual(original, self.sql("SELECT * FROM recognition_awards"))
        self.assertEqual(witnesses, self.sql("SELECT * FROM recognition_award_witnesses"))
        self.assertEqual([('leased',)], self.sql("SELECT state FROM recognition_jobs WHERE assignment_id=6"))

    def test_calculation_is_read_only_and_finalization_does_not_scan_history(self):
        for n in range(1, 101):
            self.review(n)
        self.capture_all(100)
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            job = lease_jobs(conn, RULE_KEY, gate=ENABLED, limit=1)[0]
            with self.assertRaisesRegex(ValueError, "read_only"):
                materialize_ledger(conn, RULE_KEY, reviewer_id=1)
            conn.commit()
        def calculate(*args):
            # This runs synchronously inside CPU calculation, with no sleeps.
            # A reservation alone is insufficient: COMMIT needs the read lock gone.
            other = sqlite3.connect(self.path, timeout=0)
            try:
                self.assertEqual('delete', other.execute("PRAGMA journal_mode").fetchone()[0])
                other.execute("UPDATE community_reviewers SET display_name='committed during calculation' WHERE id=1")
                other.commit()
            finally:
                other.close()
            return explorer_candidates(*args)
        with patch("src.review.recognition.processing.explorer_candidates", side_effect=calculate) as calculator:
            prepared = prepare_evaluation(self.path, 1, RULE_KEY)
            self.assertEqual(1, calculator.call_count)
        with connection(self.path, write=True) as conn:
            statements = []
            conn.set_trace_callback(statements.append)
            conn.execute("BEGIN IMMEDIATE")
            with patch("src.review.recognition.processing.ledger_candidates", side_effect=AssertionError("full-history scan")):
                finalize_job(conn, 1, job["lease_token"], RULE_KEY, prepared, gate=ENABLED)
            conn.commit()
        self.assertFalse(any("FROM recognition_completions WHERE reviewer_id=" in " ".join(sql.split())
                             for sql in statements))
        self.assertEqual([(4,)], self.sql("SELECT count(*) FROM recognition_awards"))
        self.assertEqual([('committed during calculation',)], self.sql("SELECT display_name FROM community_reviewers WHERE id=1"))

    def test_late_completion_invalidates_prepared_snapshot(self):
        for n in range(1, 6):
            self.review(n)
        self.capture_all(5)
        prepared = prepare_evaluation(self.path, 1, RULE_KEY)
        # A lower assignment ID proves MAX(assignment_id) is not the checkpoint.
        self.review(0, stop=6, timestamp="2026-08-01T00:00:00Z")
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            capture(conn, 0, RULE_KEY, gate=ENABLED)
            job = lease_jobs(conn, RULE_KEY, gate=ENABLED, limit=1)[0]
            with self.assertRaisesRegex(Quarantined, "stale_or_invalid_candidates"):
                finalize_job(conn, job["assignment_id"], job["lease_token"], RULE_KEY, prepared, gate=ENABLED)
            conn.commit()
        self.assertEqual([(0,)], self.sql("SELECT count(*) FROM recognition_awards"))

    def test_preparation_and_dry_run_close_connections_before_cpu_calculation(self):
        for n in range(1, 6):
            self.review(n)
        self.capture_all(5)
        original_plan = dry_run(self.path, RULE_KEY, through_assignment=5)

        def independent_commit():
            other = sqlite3.connect(self.path, timeout=0)
            try:
                self.assertEqual('delete', other.execute("PRAGMA journal_mode").fetchone()[0])
                other.execute("UPDATE community_reviewers SET display_name='CPU-stage commit' WHERE id=1")
                other.commit()
            finally:
                other.close()

        # Negative control: the old retained read snapshot really prevents this
        # exact independent COMMIT, even though BEGIN IMMEDIATE would succeed.
        with connection(self.path) as reader:
            reader.execute("BEGIN")
            reader.execute("SELECT * FROM recognition_completions").fetchall()
            with self.assertRaisesRegex(sqlite3.OperationalError, "locked"):
                independent_commit()

        for operation, module in (
            (lambda: prepare_evaluation(self.path, 1, RULE_KEY), "processing"),
            (lambda: dry_run(self.path, RULE_KEY, through_assignment=5), "backfill"),
        ):
            with self.subTest(module=module):
                opened = []

                @contextmanager
                def track_connection(*args, **kwargs):
                    with connection(*args, **kwargs) as conn:
                        opened.append(conn)
                        yield conn

                def calculate(*args):
                    self.assertEqual(1, len(opened))
                    with self.assertRaises(sqlite3.ProgrammingError):
                        opened[0].execute("SELECT 1")
                    independent_commit()
                    return explorer_candidates(*args)

                with patch(f"src.review.recognition.{module}.connection", side_effect=track_connection):
                    with patch("src.review.recognition.processing.explorer_candidates", side_effect=calculate) as cpu:
                        result = operation()
                        self.assertEqual(1, cpu.call_count)
                if module == "backfill":
                    self.assertEqual(original_plan, result)
        self.assertEqual([('CPU-stage commit',)], self.sql("SELECT display_name FROM community_reviewers WHERE id=1"))

    def test_preparation_read_failure_closes_snapshot(self):
        self.review(1)
        self.capture_all(1)
        opened = []

        @contextmanager
        def track_connection(*args, **kwargs):
            with connection(*args, **kwargs) as conn:
                opened.append(conn)
                yield conn

        with patch("src.review.recognition.processing.connection", side_effect=track_connection):
            with patch("src.review.recognition.processing.load_rule", side_effect=RuntimeError("read failed")):
                with self.assertRaisesRegex(RuntimeError, "read failed"):
                    prepare_evaluation(self.path, 1, RULE_KEY)
        with self.assertRaises(sqlite3.ProgrammingError):
            opened[0].execute("SELECT 1")
        self.sql("UPDATE community_reviewers SET display_name='after failure' WHERE id=1")

    def test_backfill_capture_never_calculates_candidates_under_writer(self):
        self.review(1)
        migrate(self.path, apply=True)
        plan = dry_run(self.path, RULE_KEY, through_assignment=1)
        with patch("src.review.recognition.backfill.ledger_candidates", side_effect=AssertionError("candidate read under writer")):
            capture_batch(self.path, plan, gate=ENABLED)
        self.assertEqual([(1,)], self.sql("SELECT count(*) FROM recognition_completions"))

    def test_legacy_replacement_refuses_retained_sources_and_preserves_unreferenced_behavior(self):
        from src.review import complete_stop_review as legacy
        self.review(1)
        self.review(2)
        for column in ("shelter_present", "bench_present", "bench_condition", "waiting_area_type", "notes"):
            self.sql(f"ALTER TABLE stop_observations ADD COLUMN {column} TEXT")
        args = ("no", "no", "none", "sidewalk", "fixture")
        # Pre-migration replacement is still supported.
        with patch.object(legacy, "DATABASE_PATH", self.path):
            legacy.complete_stop_review(2, 1, *args)
        self.capture_all(1)
        before = self.sql("SELECT * FROM stop_observations")
        with patch.object(legacy, "DATABASE_PATH", self.path):
            with self.assertRaisesRegex(ValueError, "recognition_retention"):
                legacy.complete_stop_review(1, 1, *args)
        self.assertEqual(before, self.sql("SELECT * FROM stop_observations"))
        # Successful subsequent mutation verifies rollback/close and unrelated use.
        with patch.object(legacy, "DATABASE_PATH", self.path):
            legacy.complete_stop_review(2, 1, *args)
        self.assertEqual([], self.sql("PRAGMA foreign_key_check"))

    def test_award_integrity_detects_missing_extra_mismatch_duplicates_and_order(self):
        for n in range(1, 7):
            self.review(n)
        self.capture_all(6)
        prepared = prepare_evaluation(self.path, 1, RULE_KEY)
        candidate = json.loads(prepared.candidates_json)[0]
        for defect in ("missing", "extra", "mismatch", "duplicate", "order", "hash"):
            with self.subTest(defect=defect), connection(self.path, write=True) as conn:
                conn.execute("BEGIN IMMEDIATE")
                evidence = json.loads(canonical(candidate["evidence"]))
                ids = list(range(1, 6))
                if defect == "missing":
                    ids.pop()
                elif defect == "extra":
                    ids.append(6)
                elif defect == "mismatch":
                    evidence["witnesses"][0]["observation_id"] = 999
                elif defect == "duplicate":
                    evidence["witnesses"][1] = evidence["witnesses"][0]
                elif defect == "order":
                    evidence["witnesses"][0], evidence["witnesses"][1] = evidence["witnesses"][1], evidence["witnesses"][0]
                conn.execute("INSERT INTO recognition_awards VALUES('corrupt',1,'explorer','global','5',?,?,?,'live',5,?,?)",
                             (RULE_KEY, candidate["earned_at_utc"], candidate["earned_at_utc"], canonical(evidence),
                              "bad-hash" if defect == "hash" else digest(evidence)))
                conn.executemany("INSERT INTO recognition_award_witnesses VALUES('corrupt',?)", [(n,) for n in ids])
                with self.assertRaises(Quarantined):
                    check_award_integrity(conn, "corrupt")
                job = lease_jobs(conn, RULE_KEY, gate=ENABLED, limit=1)[0]
                with self.assertRaises(Quarantined):
                    finalize_job(conn, 1, job["lease_token"], RULE_KEY, prepared, gate=ENABLED)
                self.assertEqual('leased', conn.execute("SELECT state FROM recognition_jobs WHERE assignment_id=1").fetchone()[0])
                # No commit: discard deliberately corrupt fixture records.

    def test_multiprocess_workers_cannot_duplicate_awards(self):
        for n in range(1, 6):
            self.review(n)
        self.capture_all(5)
        code = """
import sys
from src.review.recognition import RecognitionGate
from src.review.recognition.schema import connection
from src.review.recognition.processing import lease_jobs, prepare_evaluation, finalize_job
gate=RecognitionGate(issuance=True)
with connection(sys.argv[1],write=True) as conn:
    conn.execute('BEGIN IMMEDIATE')
    jobs=lease_jobs(conn,'explorer:v1',gate=gate,limit=1)
    conn.commit()
prepared=prepare_evaluation(sys.argv[1],1,'explorer:v1')
with connection(sys.argv[1],write=True) as conn:
    conn.execute('BEGIN IMMEDIATE')
    for job in jobs:
        finalize_job(conn,job['assignment_id'],job['lease_token'],'explorer:v1',prepared,gate=gate)
    conn.commit()
"""
        children = [subprocess.Popen([sys.executable, "-B", "-c", code, str(self.path)],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                     cwd=Path(__file__).resolve().parents[1]) for _ in range(2)]
        try:
            for child in children:
                _, error = child.communicate(timeout=30)
                self.assertEqual(0, child.returncode, error)
        finally:
            for child in children:
                if child.poll() is None:
                    child.kill()
                child.communicate()
        self.assertEqual([(1,)], self.sql("SELECT count(*) FROM recognition_awards"))
        self.assertEqual([(5,)], self.sql("SELECT count(*) FROM recognition_award_witnesses"))
        self.assertEqual([(2,)], self.sql("SELECT count(*) FROM recognition_jobs WHERE state='done'"))


if __name__ == "__main__":
    unittest.main()
