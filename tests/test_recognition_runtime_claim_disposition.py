"""Disposition of real disposable claims; no promotion or execution."""

from contextlib import contextmanager
from copy import deepcopy
from datetime import timedelta
import json
import sqlite3
import unittest
from unittest.mock import patch

from src.review.recognition import administration as a, administration_schema, authorization
from src.review.recognition import runtime_claim_disposition as disposition
from src.review.recognition import runtime_claim_consumption as consumption
from src.review.recognition import runtime_execution_claim_schema as schema, runtime_validation as runtime
from src.review.recognition import writer_boundary, local_readiness
from src.review.recognition.rules import canonical, digest
from src.review.recognition.trust import utc
from tests import test_recognition_runtime_execution_claims as fixtures


class RuntimeClaimDispositionTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.RuntimeExecutionClaimTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.claim = self.f.acquire()
        self.body = json.loads(self.claim.canonical_json)
        self.config = self.f.config

    def at(self, seconds):
        return (utc(self.body['issued_at_utc'])+timedelta(seconds=seconds)).strftime('%Y-%m-%dT%H:%M:%SZ')

    def inspect(self, seconds=0, config=None):
        with patch.object(a, 'target_identity', side_effect=authorization.target_identity), \
                patch.object(runtime, '_utc_now', return_value=self.at(seconds)):
            return disposition.inspect_claims(config or self.config)

    def transition(self, state, seconds):
        # Schema-only fixture transition with the real immutable event/audit guards.
        with a.connect(self.config.control, write=True) as control:
            control.execute('BEGIN IMMEDIATE')
            old = control.execute('SELECT sequence,body_sha256 FROM '+schema.HISTORY+
                                  ' WHERE claim_id=? ORDER BY sequence DESC LIMIT 1',
                                  (self.body['claim_id'],)).fetchone()
            head = a._audit_head(control)
            event = dict(format=schema.EVENT_FORMAT, claim_id=self.body['claim_id'],
                claim_sha256=digest(self.body), sequence=old['sequence']+1,
                previous_sha256=old['body_sha256'], state=state,
                reason='disposable disposition fixture', at_utc=self.at(seconds))
            control.execute('INSERT INTO '+schema.HISTORY+' VALUES(?,?,?,?,?,?,?)',
                (event['claim_id'], event['sequence'], state, a.timestamp(event['at_utc']),
                 canonical(event), digest(event), head['sequence']+1))
            a._audit(control, 'runtime_execution_claim_state_changed', self.body['runtime_scope']['owner_id'],
                     event['at_utc'], dict(claim_id=event['claim_id'], claim_sha256=digest(self.body),
                     event_sequence=event['sequence'], event_sha256=digest(event)))
            administration_schema.check_control(control)
            control.commit()

    def test_live_exact_expiry_and_historical_expiry_do_not_mutate(self):
        before = self.f.dump()
        for seconds, expected, blocks in ((0, 'LIVE_ISSUED', True), (299, 'LIVE_ISSUED', True),
                                          (300, 'EXPIRED_ISSUED', False), (301, 'EXPIRED_ISSUED', False)):
            with self.subTest(seconds=seconds):
                report = self.inspect(seconds)
                row = report['claims'][0]
                self.assertEqual(expected, row['disposition'])
                self.assertIs(blocks, row['blocks_readiness'])
                self.assertEqual('ISSUED', row['state'])
                self.assertFalse(report['execution_authority'])
                self.assertFalse(report['retry_authorized'])
                self.assertTrue(report['snapshot_only'])
        self.assertEqual(before, self.f.dump())

    def test_revoked_and_explicit_expired_are_historical(self):
        self.transition('REVOKED', 1)
        before = self.f.dump()
        row = self.inspect(2)['claims'][0]
        self.assertEqual('REVOKED', row['disposition'])
        self.assertFalse(row['blocks_readiness'])
        self.assertEqual('NOT_ESTABLISHED', row['completion'])
        self.assertEqual(before, self.f.dump())

    def test_explicit_expired_event(self):
        self.transition('EXPIRED', 300)
        before = self.f.dump()
        row = self.inspect(301)['claims'][0]
        self.assertEqual('EXPIRED', row['disposition'])
        self.assertFalse(row['blocks_readiness'])
        self.assertEqual(before, self.f.dump())

    def test_real_consumption_is_not_completion_or_activated_authority(self):
        with consumption.consume(self.config, self.claim, self.f.snapshot,
                                 self.f.f.session, primary_token=self.f.f.primary) as handoff:
            with self.assertRaises(ValueError): writer_boundary.acquire(handoff, self.config.target, {})
        before = self.f.dump()
        row = self.inspect(10)['claims'][0]
        self.assertEqual('CONSUMED', row['disposition'])
        self.assertFalse(row['blocks_readiness'])
        self.assertEqual('NOT_ESTABLISHED', row['completion'])
        self.assertEqual('NOT_ASSESSED', row['commit_outcome'])
        self.assertFalse(local_readiness.assess(self.config, now=self.at(10))['activation_ready'])
        with self.assertRaises(ValueError):
            writer_boundary.acquire(self.inspect(10), self.config.target, {})
        self.assertEqual(before, self.f.dump())
        for table in ('recognition_execution_claims', 'recognition_execution_seals', 'recognition_operation_receipts'):
            self.assertEqual([], before[1][table])
        with self.assertRaises(ValueError): handoff.snapshot

    def test_recovery_fence_is_distinct_and_never_successful_execution(self):
        self.transition('CONSUMED', 1)
        self.transition('RECOVERY_REQUIRED', 2)
        before = self.f.dump()
        row = self.inspect(3)['claims'][0]
        self.assertTrue(row['blocks_readiness'])
        self.assertEqual('RECOVERY_REQUIRED', row['commit_outcome'])
        self.assertEqual('NOT_ESTABLISHED', row['completion'])
        self.assertEqual(before, self.f.dump())

    def test_no_target_or_key_open_read_only_query_only_and_write_denial(self):
        before = self.f.dump()
        opened = []
        original = a.connect
        @contextmanager
        def guarded(path, *, write=False):
            self.assertEqual(self.config.control, path)
            self.assertFalse(write)
            with original(path, write=write) as control:
                self.assertEqual(1, control.execute('PRAGMA query_only').fetchone()[0])
                control.execute('PRAGMA query_only=OFF')
                with self.assertRaises(sqlite3.OperationalError):
                    control.execute('INSERT INTO recognition_admin_attempts VALUES(999,0,0)')
                control.rollback()  # A failed SQLite DML can still open a transaction.
                control.execute('PRAGMA query_only=ON')
                def authorizer(action, *unused):
                    if action in (sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE,
                                  sqlite3.SQLITE_CREATE_TABLE, sqlite3.SQLITE_DROP_TABLE):
                        self.fail('disposition attempted a write')
                    return sqlite3.SQLITE_OK
                control.set_authorizer(authorizer)
                opened.append(path)
                yield control
        with patch.object(a, 'connect', side_effect=guarded), \
                patch('pathlib.Path.read_bytes', side_effect=AssertionError('key read')):
            self.inspect()
        self.assertEqual([self.config.control], opened)
        self.assertEqual(before, self.f.dump())

    def test_wrong_current_scope_rejected_after_complete_real_graph_validation(self):
        original = runtime._history
        for key in ('installation_id', 'target_id', 'owner_id', 'generation', 'runtime_profile_sha256'):
            def changed(control, field=key):
                binding, profile, head = original(control)  # Do not bypass schema/history readers.
                binding = deepcopy(binding)
                binding[field] = binding[field]+1 if type(binding[field]) is int else '0'*64
                return binding, profile, head
            with self.subTest(field=key), patch.object(runtime, '_history', side_effect=changed):
                with self.assertRaisesRegex(ValueError, 'runtime_claim_disposition_scope_mismatch'):
                    self.inspect()

    def test_identity_and_clock_errors_are_not_empty_success(self):
        with self.assertRaisesRegex(ValueError, 'control_identity_mismatch'):
            disposition.inspect_claims(self.config)  # Runtime identity is no deployment exemption.
        with self.assertRaisesRegex(ValueError, 'runtime_claim_clock_anomaly'):
            self.inspect(-1)
        with self.assertRaises(TypeError): disposition.inspect_claims(self.config, now=self.at(300))
        with self.assertRaises(ValueError): disposition.inspect_claims(self.claim)

    def test_durable_scope_tampering_rejected_by_real_schema_reader(self):
        with a.connect(self.config.control, write=True) as control:
            control.execute('BEGIN IMMEDIATE')
            triggers = control.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger' AND tbl_name=?",
                                       (schema.CLAIMS,)).fetchall()
            for row in triggers: control.execute('DROP TRIGGER '+row['name'])
            body = deepcopy(self.body)
            body['runtime_scope']['owner_id'] += 1
            control.execute('UPDATE '+schema.CLAIMS+' SET body_json=?,body_sha256=? WHERE claim_id=?',
                            (canonical(body), digest(body), body['claim_id']))
            for row in triggers: control.execute(row['sql'])
            control.commit()
        before = self.f.dump()
        with self.assertRaises(ValueError): self.inspect()
        self.assertEqual(before, self.f.dump())
