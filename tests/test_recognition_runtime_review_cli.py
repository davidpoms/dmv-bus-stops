"""Private-log packaging with synthetic records and no database access."""

from contextlib import redirect_stderr, redirect_stdout
import copy
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts.active import prepare_recognition_runtime_review as cli
from src.review.recognition import runtime_enrollment as enrollment
from src.review.recognition import runtime_evidence as evidence
from src.review.recognition.rules import canonical, digest


class RuntimeReviewCliTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        observation = dict(format=evidence.FORMAT, role='runtime',
            installation_id='11111111-1111-4111-8111-111111111111',
            target_id='22222222-2222-4222-8222-222222222222', owner_id=1,
            source_generation=4, source_binding_sha256='a'*64,
            challenge_id='33333333-3333-4333-8333-333333333333', challenge_sha256='b'*64,
            nonce_sha256='c'*64, challenge_expires_at=700, observed_at=101,
            hostname='synthetic-worker', target_path=str(self.root / 'target.db'),
            target_device='60', target_inode=str(2**64-1),
            control_path=str(self.root / 'control.db'), control_device='60', control_inode='42',
            target_schema_sha256='d'*64, pid=123, python_version='synthetic Python',
            python_executable='/synthetic/python', evidence_channel=evidence.CHANNEL,
            provenance='REQUIRES_OPERATOR_REVIEW')
        self.record = dict(observation=observation, observation_sha256=digest(observation))
        self.scope = dict(challenge_id=observation['challenge_id'],
            challenge_sha256=observation['challenge_sha256'], expected_generation=4,
            source_binding_sha256=observation['source_binding_sha256'])
        self.log = self.root / 'private.log'
        self.output = self.root / 'review.json'

    def changed(self, **changes):
        record = copy.deepcopy(self.record)
        record['observation'].update(changes)
        record['observation_sha256'] = digest(record['observation'])
        return record

    def line(self, record=None):
        return '[provider prefix] WARNING ' + evidence.MARKER + ' ' + canonical(
            self.record if record is None else record) + '\n'

    def prepare(self, text, **changes):
        return cli.prepare_review(io.BytesIO(text.encode()), **dict(self.scope, **changes))

    def arguments(self):
        return ['--private-log', str(self.log), '--output', str(self.output),
            '--challenge-id', self.scope['challenge_id'],
            '--challenge-sha256', self.scope['challenge_sha256'], '--expected-generation', '4',
            '--source-binding-sha256', self.scope['source_binding_sha256']]

    def test_single_preserves_complete_envelope_and_uses_shared_validators(self):
        with patch.object(enrollment, 'validate_observation', wraps=enrollment.validate_observation) as validate, \
             patch.object(enrollment, 'parse_review', wraps=enrollment.parse_review) as parse:
            review = self.prepare('SQLite runtime: 3.54.1\n' + self.line())
        self.assertTrue(validate.called)
        parse.assert_called_once()
        self.assertEqual([self.record], review['observations'])
        self.assertEqual(self.record['observation_sha256'], review['selected_observation_sha256'])
        self.assertEqual('REQUIRES_OPERATOR_REVIEW', review['observations'][0]['observation']['provenance'])

    def test_startup_and_unmarked_json_are_not_evidence(self):
        for text in ('SQLite runtime: 3.54.1\nmapped library is correct\n', canonical(self.record)):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.prepare(text)

    def test_malformed_marked_records_fail_even_alongside_valid_evidence(self):
        bad_payloads = ['{', '{}', '[]', canonical(self.record) + ' trailing',
            '{"observation":{},"observation":{}}',
            canonical(dict(status='REJECTED', error='runtime_evidence_collection_failed', pid=1)),
            canonical(dict(self.record, observation_sha256='0'*64))]
        for payload in bad_payloads:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                self.prepare(self.line() + evidence.MARKER + ' ' + payload + '\n')
        for text in (evidence.MARKER, evidence.MARKER + canonical(self.record),
                     'X' + self.line().split('WARNING ')[1]):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.prepare(text)

    def test_every_scope_mismatch_rejects_without_filtering(self):
        for changes in (dict(challenge_id='44444444-4444-4444-8444-444444444444'),
                        dict(challenge_sha256='e'*64), dict(source_generation=3),
                        dict(source_binding_sha256='f'*64)):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.prepare(self.line() + self.line(self.changed(**changes)),
                             selected_observation_sha256=self.record['observation_sha256'])

    def test_multiple_require_explicit_unique_selection_and_preserve_all(self):
        second = self.changed(pid=124, observed_at=102)
        text = self.line() + self.line(second)
        with self.assertRaises(ValueError):
            self.prepare(text)
        with self.assertRaises(ValueError):
            self.prepare(text, selected_observation_sha256='0'*64)
        with self.assertRaises(ValueError):
            self.prepare(self.line()*2, selected_observation_sha256=self.record['observation_sha256'])
        review = self.prepare(text, selected_observation_sha256=second['observation_sha256'])
        self.assertEqual([self.record, second], review['observations'])
        self.assertEqual(second['observation_sha256'], review['selected_observation_sha256'])

    def test_worker_disagreement_rejects_despite_explicit_selection(self):
        for changes in (dict(hostname='other-worker'), dict(target_device='61'),
                        dict(control_inode='43'), dict(owner_id=2), dict(nonce_sha256='e'*64)):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.prepare(self.line() + self.line(self.changed(**changes)),
                             selected_observation_sha256=self.record['observation_sha256'])

    def test_bounds_and_invalid_utf8(self):
        with self.assertRaises(ValueError):
            self.prepare('x'*(cli.MAX_LOG_LINE_BYTES+1))
        with self.assertRaises(ValueError):
            self.prepare(''.join(self.line(self.changed(pid=i+1)) for i in range(33)),
                         selected_observation_sha256=self.record['observation_sha256'])
        with self.assertRaises(UnicodeError):
            cli.prepare_review(io.BytesIO(b'\xff\n'), **self.scope)

    def test_cli_exclusive_artifact_and_canonical_digests_no_database_access(self):
        self.log.write_text(self.line(), encoding='utf-8')
        stdout = io.StringIO()
        with patch.object(sqlite3, 'connect', side_effect=AssertionError('database access')), \
             patch.object(enrollment, 'enroll_runtime_profile', side_effect=AssertionError('enrollment')), \
             redirect_stdout(stdout):
            cli.main(self.arguments())
        review = enrollment.parse_review(self.output.read_text(encoding='utf-8'))
        self.assertEqual(dict(review_sha256=digest(review),
            selected_observation_sha256=self.record['observation_sha256']), json.loads(stdout.getvalue()))
        self.assertEqual([self.record], review['observations'])
        if os.name != 'nt':
            self.assertEqual(0o600, self.output.stat().st_mode & 0o777)
        before = self.output.read_bytes()
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            cli.main(self.arguments())
        self.assertEqual(before, self.output.read_bytes())

    def test_cli_refuses_existing_database_input_and_hardlink_outputs(self):
        self.log.write_text(self.line(), encoding='utf-8')
        protected = self.root / 'target.db'
        protected.write_bytes(b'existing database sentinel')
        linked = self.root / 'linked.db'
        os.link(protected, linked)
        for path in (protected, linked, self.log):
            before = path.read_bytes()
            args = self.arguments()
            args[3] = str(path)
            with self.subTest(path=path), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                cli.main(args)
            self.assertEqual(before, path.read_bytes())

    def test_cli_failure_has_no_artifact_and_does_not_echo_private_log(self):
        self.log.write_text(evidence.MARKER + ' private-invalid-secret\n', encoding='utf-8')
        stderr, stdout = io.StringIO(), io.StringIO()
        with redirect_stderr(stderr), redirect_stdout(stdout), self.assertRaises(SystemExit):
            cli.main(self.arguments())
        self.assertFalse(self.output.exists())
        self.assertEqual('', stdout.getvalue())
        self.assertNotIn('private-invalid-secret', stderr.getvalue())

    def test_fresh_cli_process_forbids_database_connections(self):
        self.log.write_text(self.line(), encoding='utf-8')
        code = """
import runpy, sys
def guard(event, args):
    if event == 'sqlite3.connect':
        raise AssertionError('database access forbidden')
sys.addaudithook(guard)
script = sys.argv.pop(1)
runpy.run_path(script, run_name='__main__')
"""
        result = subprocess.run([sys.executable, '-B', '-c', code, str(Path(cli.__file__).resolve()),
                                 *self.arguments()], capture_output=True, text=True,
                                cwd=cli.ROOT, timeout=30)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(digest(enrollment.parse_review(self.output.read_text(encoding='utf-8'))),
                         json.loads(result.stdout)['review_sha256'])


if __name__ == '__main__':
    unittest.main()
