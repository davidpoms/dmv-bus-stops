"""Explicit live processing against disposable databases only."""

from contextlib import redirect_stdout, redirect_stderr
import io
import json
import unittest
from unittest.mock import patch

from scripts.active import process_live_recognition as live
from scripts.active import process_reviewer_recognition as historical
from src.review.recognition import RecognitionGate
from src.review.recognition.qualification import Quarantined
from src.review.recognition.rules import RULE_KEY
import tests.test_recognition_foundation as foundation


class LiveProcessorTests(unittest.TestCase):
    setUp = foundation.RecognitionTests.setUp
    sql = foundation.RecognitionTests.sql
    review = foundation.RecognitionTests.review
    capture_all = foundation.RecognitionTests.capture_all

    def populate(self, count=5):
        for assignment in range(1, count + 1):
            self.review(assignment)
        self.capture_all(count)

    def issue(self, **kwargs):
        return live.process(self.path, RULE_KEY, issue=True,
                            gate=RecognitionGate(capture=False, issuance=True), **kwargs)

    def test_required_arguments_and_no_apply(self):
        for arguments in ([], ['--db', str(self.path)], ['--rule-key', RULE_KEY],
                          ['--db', str(self.path), '--rule-key', RULE_KEY, '--apply']):
            with self.subTest(arguments=arguments), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                live.main(arguments)

    def test_missing_database_and_schema_never_created(self):
        missing = self.path.parent / 'absent.db'
        with self.assertRaisesRegex(ValueError, 'existing_file'):
            live.process(missing, RULE_KEY)
        self.assertFalse(missing.exists())
        before = self.path.read_bytes()
        with redirect_stdout(io.StringIO()):
            self.assertEqual(1, live.main(['--db', str(self.path), '--rule-key', RULE_KEY, '--issue']))
        self.assertEqual(before, self.path.read_bytes())

    def test_disabled_gate_and_read_only_verification(self):
        self.populate()
        before = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'issuance_disabled'):
            live.process(self.path, RULE_KEY, issue=True)
        result = live.process(self.path, RULE_KEY)
        self.assertEqual(5, result['jobs_found'])
        self.assertEqual(0, result['jobs_attempted'])
        self.assertEqual(before, self.path.read_bytes())

    def test_explicit_cli_issues_one_award_for_multiple_jobs(self):
        self.populate()
        output = io.StringIO()
        with redirect_stdout(output), patch.object(live, 'prepare_evaluation', wraps=live.prepare_evaluation) as prepare:
            self.assertEqual(0, live.main(['--db', str(self.path), '--rule-key', RULE_KEY, '--issue']))
        result = json.loads(output.getvalue())
        self.assertEqual(5, result['jobs_completed'])
        self.assertEqual(1, result['awards_issued'])
        self.assertEqual(1, prepare.call_count)
        self.assertEqual([(5,)], self.sql('SELECT COUNT(*) FROM recognition_award_witnesses'))
        self.assertEqual([('done', 1)] * 5, self.sql('SELECT state,attempts FROM recognition_jobs'))

    def test_empty_candidates_and_bounded_cohort(self):
        self.populate(3)
        result = self.issue(limit=1)
        self.assertEqual(1, result['jobs_completed'])
        self.assertEqual(0, result['awards_issued'])
        self.assertEqual([('pending', 0)] * 2,
                         self.sql('SELECT state,attempts FROM recognition_jobs WHERE assignment_id>1'))
        for limit in (0, 1001, True):
            with self.assertRaises(ValueError):
                self.issue(limit=limit)

    def test_expired_leases_are_untouched(self):
        self.populate(3)
        self.sql("UPDATE recognition_jobs SET state='leased',lease_token='old',lease_until_utc='2000-01-01T00:00:00Z' WHERE assignment_id=1")
        before = self.sql('SELECT * FROM recognition_jobs WHERE assignment_id=1')
        self.assertEqual(2, self.issue()['jobs_completed'])
        self.assertEqual(before, self.sql('SELECT * FROM recognition_jobs WHERE assignment_id=1'))

    def test_other_rule_jobs_are_untouched(self):
        from src.review.recognition.rules import canonical, digest, initial_definition
        from src.review.recognition.qualification import capture
        self.populate(1)
        self.sql("INSERT INTO recognition_rule_versions VALUES('explorer:v2','explorer',2,?,?,'2026-09-01T00:00:00Z')",
                 (canonical(initial_definition()), digest(initial_definition())))
        self.review(2)
        with live.connection(self.path, write=True) as conn:
            conn.execute('BEGIN IMMEDIATE')
            capture(conn, 2, 'explorer:v2', gate=RecognitionGate(capture=True))
            conn.commit()
        before = self.sql('SELECT * FROM recognition_jobs WHERE assignment_id=2')
        self.assertEqual(1, self.issue()['jobs_completed'])
        self.assertEqual(before, self.sql('SELECT * FROM recognition_jobs WHERE assignment_id=2'))

    def test_new_completion_between_same_reviewer_jobs_recalculates(self):
        self.populate()
        finalize = live.finalize_job
        prepare = live.prepare_evaluation
        real_connection = live.connection
        from contextlib import contextmanager
        writes = 0

        @contextmanager
        def connection(database, *, write=False):
            nonlocal writes
            if write:
                writes += 1
                if writes == 2:
                    self.review(6)
                    self.capture_all(6)
            with real_connection(database, write=write) as conn:
                yield conn

        with patch.object(live, 'connection', connection), \
             patch.object(live, 'prepare_evaluation', wraps=prepare) as prepared, \
             patch.object(live, 'finalize_job', wraps=finalize) as finalized:
            result = self.issue()
        self.assertEqual(1, result['stale_retries'])
        self.assertEqual(2, prepared.call_count)
        self.assertEqual(6, finalized.call_count)
        self.assertEqual(5, result['jobs_completed'])
        self.assertEqual(1, result['awards_issued'])
        self.assertEqual([('pending',)], self.sql('SELECT state FROM recognition_jobs WHERE assignment_id=6'))

    def test_quarantines_are_visible_and_only_stale_is_retried(self):
        self.populate(1)
        for code, attempts in [('stale_or_invalid_candidates', 3), ('candidate_identity_mismatch', 1)]:
            self.sql("UPDATE recognition_jobs SET state='pending',last_error_code=NULL")
            with patch.object(live, 'finalize_job', side_effect=Quarantined(code)) as finalize:
                result = self.issue()
            self.assertEqual(attempts, finalize.call_count)
            self.assertEqual([dict(assignment_id=1, code=code)], result['quarantined_jobs'])
            self.assertEqual([('quarantined', code)], self.sql('SELECT state,last_error_code FROM recognition_jobs'))
        self.assertEqual([(0,)], self.sql('SELECT COUNT(*) FROM recognition_awards'))

    def test_arbitrary_errors_not_retried_or_exposed(self):
        self.populate(1)
        with patch.object(live, 'finalize_job', side_effect=ValueError('private payload')) as finalize:
            result = self.issue()
        self.assertEqual(1, finalize.call_count)
        self.assertNotIn('private payload', json.dumps(result))
        self.assertEqual([('pending', 0)], self.sql('SELECT state,attempts FROM recognition_jobs'))
        self.assertEqual(1, len(result['error_jobs']))

    def test_historical_command_remains_read_only(self):
        self.populate(1)
        before = self.path.read_bytes()
        arguments = ['--db', str(self.path), '--rule-key', RULE_KEY, '--through-assignment', '1']
        with redirect_stdout(io.StringIO()):
            self.assertEqual(0, historical.main(arguments))
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            historical.main(arguments + ['--apply'])
        self.assertEqual(before, self.path.read_bytes())


if __name__ == '__main__':
    unittest.main()
