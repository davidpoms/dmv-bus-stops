"""4c-0 real lifecycle to intent DATA. APPROVED fixtures are synthetic only."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import os
import sqlite3
import threading
import unittest
from unittest.mock import patch
from uuid import uuid4

from src.review.recognition import administration as a, approvals, runtime_validation as v
from src.review.recognition import runtime_approval_transaction as owner, runtime_approval_ceremony as ceremony
from src.review.recognition import runtime_approval_contract as codec, runtime_proposal_records as records
from src.review.recognition import runtime_scope_validation as shared, runtime_auth, local_readiness, writer_boundary
from src.review.recognition.rules import canonical, digest
from tests import test_recognition_runtime_proposals as lifecycle
from tests import test_recognition_administration as f


class RuntimeApprovalFoundationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = lifecycle.RuntimeProposalTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.config = self.fixture.config
        self.primary, self.session = self.fixture.primary, self.fixture.session
        self.pair = self.fixture.create()
        self.reference = self.pair['reference']
        self.clock = self.fixture.fixture.fixture.clock
        self.clock.return_value = f.at(930)
        self.intent = canonical(dict(decision='approve', reason='Reviewed exact proposal', confirm=True))
        with a.connect(self.config.control) as control:
            self.original_approvals = [tuple(row) for row in control.execute('SELECT * FROM recognition_approvals ORDER BY approval_id')]

    def step(self):
        return ceremony.issue_step_up(self.config, self.session, f.independent_code(self.clock.return_value),
            self.reference, primary_token=self.primary)

    def confirm(self, step):
        return ceremony.begin_confirmation(self.config, self.session, step['token'], self.reference,
            self.intent, primary_token=self.primary)

    def consume(self, confirmation):
        return ceremony.consume_confirmation(self.config, self.session, confirmation['token'], self.reference,
            primary_token=self.primary)

    def test_real_lifecycle_stops_at_acknowledged_no_authority(self):
        step = self.step()
        confirmation = self.confirm(step)
        with patch('pathlib.Path.read_bytes', side_effect=AssertionError('key read after TOTP')):
            self.assertFalse(self.consume(confirmation)['approval_created'])
        with a.connect(self.config.control) as control:
            self.assertEqual(self.original_approvals, [tuple(row) for row in control.execute('SELECT * FROM recognition_approvals ORDER BY approval_id')])
            self.assertEqual([], control.execute('SELECT * FROM recognition_admin_stepups').fetchall())
            raw = '\n'.join(row[0] for row in control.execute('SELECT body_json FROM recognition_admin_audit'))
            self.assertNotIn(step['token'], raw)
            self.assertNotIn(confirmation['token'], raw)
        self.assertEqual('ACKNOWLEDGED', self.fixture.inspect()['status'])
        self.assertFalse(writer_boundary.verify_local(confirmation, self.config.target, {}))
        self.assertFalse(local_readiness.assess(self.config, now=f.at(930))['activation_ready'])

    def test_step_and_confirmation_replay(self):
        step = self.step()
        confirmation = self.confirm(step)
        with self.assertRaises(ValueError): self.confirm(step)
        self.consume(confirmation)
        with self.assertRaises(ValueError): self.consume(confirmation)

    def test_immutable_consumption_fences_resurrected_mutable_rows(self):
        step = self.step()
        with a.connect(self.config.control) as control:
            row = tuple(control.execute('SELECT * FROM recognition_admin_stepups WHERE token_hash=?', (a.token_hash(step['token']),)).fetchone())
        confirmation = self.confirm(step)
        self.fixture.fixture.fixture.sql('INSERT INTO recognition_admin_stepups VALUES(?,?,?,?,?,?,?,?)', row)
        with self.assertRaisesRegex(ValueError, 'runtime_approval_step_consumed'): self.confirm(step)
        self.consume(confirmation)
        self.fixture.fixture.fixture.sql('UPDATE recognition_admin_confirmations SET used=0 WHERE token_hash=?', (a.token_hash(confirmation['token']),))
        with self.assertRaisesRegex(ValueError, 'runtime_approval_confirmation_consumed'): self.consume(confirmation)

    def test_totp_replay_and_bad_code_fail_without_step(self):
        self.step()
        with self.assertRaises(a.AdminError): self.step()
        self.clock.return_value = f.at(960)
        with self.assertRaises(a.AdminError):
            ceremony.issue_step_up(self.config, self.session, 'invalid', self.reference, primary_token=self.primary)

    def test_expiry(self):
        step = self.step()
        self.clock.return_value = f.at(1530)
        with self.assertRaisesRegex(ValueError, 'runtime_approval_artifact_expired'): self.confirm(step)

    def test_canonical_explicit_intent(self):
        step = self.step()
        for value in ('{}', '{"decision":"approve","decision":"approve"}',
                      canonical(dict(decision='approve', reason='x', confirm=1)),
                      canonical(dict(decision='approve', reason='x\0', confirm=True)),
                      canonical(dict(decision='approve', reason='x'*2001, confirm=True)),
                      canonical(dict(decision='deny', reason='x', confirm=True)),
                      canonical(dict(decision='approve', reason='x', confirm=True, hostname='claim')),
                      self.intent+' ', '{"confirm":true,"decision":"approve","reason":1.5}'):
            with self.subTest(value=value[:80]), self.assertRaises(ValueError):
                ceremony.begin_confirmation(self.config, self.session, step['token'], self.reference, value, primary_token=self.primary)
        self.assertEqual(ceremony.CONFIRMATION, self.confirm(step)['artifact']['format'])

    def test_each_artifact_scope_field_rejects_independently(self):
        step = self.step()
        with owner.approval_transaction(self.config) as context:
            state = owner._state(context)
            for field in step['artifact']['local_target'].keys()-{'format'}:
                artifact = deepcopy(step['artifact'])
                old = artifact['local_target'][field]
                artifact['local_target'][field] = str(uuid4()) if field in ('installation_id', 'target_id') else (
                    '0'*64 if type(old) is str else old+1)
                with self.subTest(field=field), self.assertRaises(ValueError):
                    ceremony._check_scope(state, artifact, self.session, self.primary, self.reference)
        self.confirm(step)

    def test_changed_mfa_and_identity_reject(self):
        step = self.step()
        from dataclasses import replace
        real_identity = a.target_identity
        with patch.object(a, 'target_identity', side_effect=lambda subject: replace(real_identity(subject), hostname='different')):
            with self.assertRaises(a.AdminError): self.confirm(step)
        self.fixture.fixture.fixture.sql('UPDATE recognition_admin_mfa SET epoch=epoch+1')
        with self.assertRaises(a.AdminError): self.confirm(step)

    def test_concurrent_confirmation_and_consumption_single_winner(self):
        step = self.step()
        def confirm():
            try: return self.confirm(step)
            except ValueError: return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: confirm(), range(2)))
        winners = [x for x in results if x is not None]
        self.assertEqual(1, len(winners))
        def consume():
            try: return self.consume(winners[0])
            except ValueError: return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: consume(), range(2)))
        self.assertEqual(1, sum(x is not None for x in results))

    def test_owner_context_lifetime_pid_thread_and_facade_fences(self):
        with owner.approval_transaction(self.config) as context:
            view = owner.read_view(context)
            self.assertEqual(3, view.snapshot()['generation'])
            with patch.object(os, 'getpid', return_value=-1), self.assertRaises(a.AdminError): view.snapshot()
            with ThreadPoolExecutor(max_workers=1) as pool:
                with self.assertRaises(a.AdminError): pool.submit(view.snapshot).result(timeout=5)
            with self.assertRaises(a.AdminError): shared.read_view(context)
            with self.assertRaises(a.AdminError): runtime_auth._parts(context)
            state = owner._contexts[context]
            original = state.connections
            state.connections = (object(), state.target)
            with self.assertRaises(a.AdminError): view.snapshot()
            state.connections = original
        with self.assertRaises(a.AdminError): view.snapshot()
        for sql in ('COMMIT', 'ROLLBACK', 'BEGIN', 'SAVEPOINT bad', 'PRAGMA query_only=OFF',
                    'CREATE TABLE bad(x)', 'INSERT INTO recognition_approvals VALUES(NULL,NULL,NULL,NULL,NULL)'):
            with self.subTest(sql=sql), self.assertRaises((a.AdminError, sqlite3.Error)):
                with owner.approval_transaction(self.config) as context:
                    context.control.execute(sql)
        for name in ('commit', 'rollback', 'close', 'cursor', 'executescript', 'set_authorizer'):
            with self.subTest(method=name), self.assertRaises(a.AdminError):
                with owner.approval_transaction(self.config) as context:
                    getattr(context.control, name)()

    def test_confirmed_commit_rollback_and_cleanup_outcomes(self):
        from src.review.recognition import runtime_proposal_transaction as transaction
        with owner.approval_transaction(self.config) as context:
            committed = owner._contexts[context]
        self.assertIs(True, committed.control_committed)
        self.assertEqual('COMMITTED', committed.phase)
        with self.assertRaises(OSError):
            with owner.approval_transaction(self.config) as context:
                rolled_back = owner._contexts[context]
                raise OSError('body failed')
        self.assertIs(False, rolled_back.control_committed)
        self.assertEqual('ROLLED_BACK', rolled_back.phase)
        original = sqlite3.connect
        class Fault(sqlite3.Connection):
            def rollback(connection):
                super(Fault, connection).rollback()
                if connection.target: raise OSError('cleanup failed')
        def connect(path, *args, **kwargs):
            connection = original(path, *args, factory=Fault, **kwargs)
            connection.target = str(path).startswith(self.config.target.resolve().as_uri()+'?')
            return connection
        with patch.object(a.sqlite3, 'connect', side_effect=connect), self.assertRaises(transaction.ProposalCleanupError) as failure:
            with owner.approval_transaction(self.config): pass
        self.assertIs(True, failure.exception.control_committed)

    def synthetic(self, binding_changes=None):
        step = self.step()
        confirmation = self.confirm(step)
        self.consume(confirmation)
        body = dict(format=codec.FORMAT, approval_id=str(uuid4()),
            binding=dict(reference=self.reference, local_target=step['artifact']['local_target'],
                         step_up_sha256=digest(step['artifact']), confirmation_artifact_sha256=digest(confirmation['artifact'])),
            actor_id=1, primary_sha256=a.token_hash(self.primary), session_sha256=a.token_hash(self.session),
            confirmation_sha256=a.token_hash(confirmation['token']), approved_at_utc=f.at(930),
            state='APPROVED', decision='approve', reason='Reviewed exact proposal', predecessor_sha256=None, execution_authority=False)
        if binding_changes:
            body['binding'].update(binding_changes)
        codec.validate(body)
        # TEST ONLY: no production API inserts APPROVED records.
        with a.connect(self.config.control, write=True) as control:
            control.execute('BEGIN IMMEDIATE')
            control.execute('INSERT INTO recognition_approvals VALUES(?,?,?,?,?)',
                (body['approval_id'], self.reference['operation_id'], body['confirmation_sha256'], canonical(body), digest(body)))
            history = codec._history_body(body, [], 'APPROVED', 1, f.at(930), body['reason'])
            control.execute('INSERT INTO recognition_approval_history VALUES(?,?,?,?,?)',
                (body['approval_id'], 1, 'APPROVED', canonical(history), digest(history)))
            control.commit()
        return body

    def test_synthetic_codec_reader_and_version_invalidation(self):
        body = self.synthetic()
        self.assertEqual(body, codec.parse(canonical(body), approval_sha256=digest(body)))
        with owner.approval_transaction(self.config) as context:
            value = codec.read_current(owner.read_view(context), body['approval_id'], session_token=self.session, primary_token=self.primary)
            self.assertEqual('APPROVED', value['state'])
            with self.assertRaises(ValueError):
                records.read_acknowledged_proposal(owner.read_view(context), self.reference['operation_id'], session_token=self.session, primary_token=self.primary)
            with self.assertRaises(a.AdminError): approvals._read(context.control, body['approval_id'])
        with a.connect(self.config.control, write=True) as control:
            control.execute('BEGIN IMMEDIATE')
            before = tuple(control.execute('SELECT * FROM recognition_approvals WHERE approval_id=?', (body['approval_id'],)).fetchone())
            approvals._invalidate_all(control, 'trusted operator', f.at(960), 'generation changed')
            self.assertEqual(before, tuple(control.execute('SELECT * FROM recognition_approvals WHERE approval_id=?', (body['approval_id'],)).fetchone()))
            self.assertEqual('INVALIDATED', codec._historical(control, body['approval_id'])['state'])
            control.commit()

    def test_codec_strict_fields_and_types(self):
        body = self.synthetic()
        cases = []
        for key in body:
            value = deepcopy(body); del value[key]; cases.append(value)
        cases += [dict(body, extra=True), dict(body, format=approvals.FORMAT), dict(body, actor_id=True),
                  dict(body, actor_id=1.0), dict(body, reason='x\0'), dict(body, reason='x'*2001),
                  dict(body, approval_id=str(uuid4()).upper()), dict(body, confirmation_sha256='A'*64),
                  dict(body, approved_at_utc='not-time'), dict(body, execution_authority=True)]
        for value in cases:
            with self.subTest(value=str(value)[:80]), self.assertRaises(ValueError):
                codec.parse(canonical(value), approval_sha256=digest(value))
        for value in (canonical(body)+' ', '{"format":"x","format":"x"}'):
            with self.assertRaises(ValueError): codec.parse(value, approval_sha256=digest(body))

    def test_rollback_of_each_ceremony_includes_counter_and_consumption(self):
        def snapshot():
            with a.connect(self.config.control) as control:
                return v._denial_baseline(control), [tuple(row) for row in control.execute('SELECT * FROM recognition_admin_audit')]
        real = a._audit
        def fail(*args, **kwargs):
            real(*args, **kwargs)
            raise OSError('post audit failure')
        before = snapshot()
        with patch.object(a, '_audit', side_effect=fail), self.assertRaises(OSError): self.step()
        self.assertEqual(before, snapshot())
        step = self.step()
        before = snapshot()
        with patch.object(a, '_audit', side_effect=fail), self.assertRaises(OSError): self.confirm(step)
        self.assertEqual(before, snapshot())
        confirmation = self.confirm(step)
        before = snapshot()
        with patch.object(a, '_audit', side_effect=fail), self.assertRaises(OSError): self.consume(confirmation)
        self.assertEqual(before, snapshot())
        self.consume(confirmation)

    def test_expired_confirmation_and_wrong_session(self):
        confirmation = self.confirm(self.step())
        self.clock.return_value = f.at(960)
        other = self.fixture.fixture.fixture.session(self.primary)
        with self.assertRaises(ValueError):
            ceremony.consume_confirmation(self.config, other, confirmation['token'], self.reference, primary_token=self.primary)
        self.clock.return_value = f.at(1530)
        with self.assertRaisesRegex(ValueError, 'runtime_approval_artifact_expired'): self.consume(confirmation)

    def test_step_for_other_proposal_cannot_confirm_this_reference(self):
        self.fixture.request['request_id'] = str(uuid4())
        other = self.fixture.create()['reference']
        step = ceremony.issue_step_up(self.config, self.session, f.independent_code(f.at(930)), other, primary_token=self.primary)
        with self.assertRaisesRegex(ValueError, 'runtime_approval_artifact_scope'):
            self.confirm(step)
        result = ceremony.begin_confirmation(self.config, self.session, step['token'], other, self.intent, primary_token=self.primary)
        self.assertEqual(other, result['artifact']['reference'])

    def test_changed_target_graph_or_schema_cannot_issue_step(self):
        self.fixture.fixture.fixture.sql("UPDATE stop_review_assignments SET status='assigned' WHERE id=(SELECT MIN(id) FROM stop_review_assignments)", target=True)
        with self.assertRaises(ValueError): self.step()
        self.fixture.fixture.fixture.sql('CREATE TABLE unexpected_schema(x)', target=True)
        with self.assertRaises(a.AdminError): self.step()

    def test_revoked_session_and_nonowner_cannot_issue_step(self):
        with self.assertRaises(a.AdminError):
            runtime_auth.record_primary_authentication(self.config, actor_id=2, reviewer_key='owner-key')
        self.fixture.fixture.fixture.sql('UPDATE recognition_admin_sessions SET revoked=1 WHERE token_hash=?', (a.token_hash(self.session),))
        with self.assertRaises(a.AdminError): self.step()
        with a.connect(self.config.control) as control:
            self.assertEqual([], control.execute('SELECT * FROM recognition_admin_stepups').fetchall())
            self.assertEqual(self.original_approvals, [tuple(row) for row in control.execute('SELECT * FROM recognition_approvals ORDER BY approval_id')])

    def test_final_expiry_rolls_back_confirmation(self):
        step = self.step()
        real = ceremony._final_check
        def expire(state):
            self.clock.return_value = f.at(1530)
            real(state)
        with patch.object(ceremony, '_final_check', side_effect=expire), self.assertRaisesRegex(ValueError, 'runtime_approval_artifact_expired'): self.confirm(step)
        self.clock.return_value = f.at(930)
        self.confirm(step)

    def test_commit_faults_distinguish_durable_confirmation_from_rollback(self):
        step = self.step()
        original = sqlite3.connect
        for committed in (False, True):
            class Fault(sqlite3.Connection):
                def commit(connection):
                    if connection.control:
                        if committed: super(Fault, connection).commit()
                        raise OSError('uncertain control commit')
                    return super(Fault, connection).commit()
            def connect(path, *args, **kwargs):
                connection = original(path, *args, factory=Fault, **kwargs)
                connection.control = str(path).startswith(self.config.control.resolve().as_uri()+'?')
                return connection
            with self.subTest(committed=committed), patch.object(a.sqlite3, 'connect', side_effect=connect), self.assertRaises(OSError): self.confirm(step)
            with a.connect(self.config.control) as control:
                self.assertEqual(int(committed), control.execute("SELECT COUNT(*) FROM recognition_admin_confirmations WHERE token_hash NOT IN (SELECT confirmation_sha256 FROM recognition_approvals)").fetchone()[0])
                self.assertEqual(0 if committed else 1, control.execute('SELECT COUNT(*) FROM recognition_admin_stepups').fetchone()[0])

    def test_reservations_held_through_finalization_and_no_target_writes(self):
        target_before = self.config.target.read_bytes()
        real = ceremony._final_check
        observed = []
        def check(state):
            real(state)
            for path in (self.config.control, self.config.target):
                connection = sqlite3.connect(path, timeout=0)
                try:
                    with self.assertRaises(sqlite3.OperationalError): connection.execute('BEGIN IMMEDIATE')
                finally: connection.close()
            self.assertEqual(1, state.target.execute('PRAGMA query_only').fetchone()[0])
            observed.append(True)
        with patch.object(ceremony, '_final_check', side_effect=check): self.step()
        self.assertEqual([True], observed)
        self.assertEqual(target_before, self.config.target.read_bytes())

    def test_historical_version_reader_rejects_other_formats(self):
        with a.connect(self.config.control) as control:
            legacy = control.execute('SELECT approval_id FROM recognition_approvals LIMIT 1').fetchone()[0]
            self.assertEqual(approvals.FORMAT, approvals._read(control, legacy)['approval']['format'])
            with self.assertRaises(ValueError): codec._historical(control, legacy)

    def test_real_auth_epoch_change_invalidates_append_only_with_fresh_auth(self):
        from src.review.recognition import administration_schema
        body = self.synthetic()
        self.fixture.fixture.fixture.sql('UPDATE '+administration_schema.TARGET_TABLE+' SET auth_epoch=auth_epoch+1', target=True)
        self.clock.return_value = f.at(960)
        primary = self.fixture.fixture.fixture.primary()
        session = self.fixture.fixture.fixture.session(primary)
        with owner.approval_transaction(self.config) as context:
            with self.assertRaises(ValueError):
                codec.read_current(owner.read_view(context), body['approval_id'], session_token=session, primary_token=primary)
        result = codec.invalidate_stale_scope(self.config, session, primary_token=primary)
        self.assertEqual([body['approval_id']], result['invalidated'])
        with a.connect(self.config.control) as control:
            value = codec._historical(control, body['approval_id'])
            self.assertEqual(body, value['approval'])
            self.assertEqual('INVALIDATED', value['state'])
            self.assertEqual(2, len(value['history']))
        self.assertEqual([], codec.invalidate_stale_scope(self.config, session, primary_token=primary)['invalidated'])

    def test_synthetic_each_scope_dimension_gets_append_only_invalidation(self):
        template = self.synthetic()
        created = []
        with a.connect(self.config.control, write=True) as control:
            control.execute('BEGIN IMMEDIATE')
            for field in template['binding']['local_target'].keys()-{'format'}:
                body = deepcopy(template)
                body['approval_id'] = str(uuid4())
                body['confirmation_sha256'] = digest({'synthetic': field})
                body['binding']['reference']['operation_id'] = str(uuid4())
                old = body['binding']['local_target'][field]
                body['binding']['local_target'][field] = str(uuid4()) if field in ('installation_id', 'target_id') else (
                    '0'*64 if type(old) is str else old+1)
                if field == 'owner_id': body['actor_id'] = body['binding']['local_target']['owner_id']
                codec.validate(body)
                control.execute('INSERT INTO recognition_approvals VALUES(?,?,?,?,?)', (body['approval_id'],
                    body['binding']['reference']['operation_id'], body['confirmation_sha256'], canonical(body), digest(body)))
                item = codec._history_body(body, [], 'APPROVED', body['actor_id'], f.at(930), body['reason'])
                control.execute('INSERT INTO recognition_approval_history VALUES(?,?,?,?,?)',
                    (body['approval_id'], 1, 'APPROVED', canonical(item), digest(item)))
                created.append(body)
            control.commit()
        result = codec.invalidate_stale_scope(self.config, self.session, primary_token=self.primary)
        self.assertEqual({b['approval_id'] for b in created}, set(result['invalidated']))
        with a.connect(self.config.control) as control:
            for body in created:
                value = codec._historical(control, body['approval_id'])
                self.assertEqual(body, value['approval'])
                self.assertEqual('INVALIDATED', value['state'])
            self.assertEqual('APPROVED', codec._historical(control, template['approval_id'])['state'])

    def test_reader_rejects_wrong_step_digest(self):
        body = self.synthetic(dict(step_up_sha256='0'*64))
        with owner.approval_transaction(self.config) as context, self.assertRaises(ValueError):
            codec.read_current(owner.read_view(context), body['approval_id'], session_token=self.session, primary_token=self.primary)

    def test_reader_rejects_wrong_confirmation_digest(self):
        body = self.synthetic(dict(confirmation_artifact_sha256='0'*64))
        with owner.approval_transaction(self.config) as context, self.assertRaises(ValueError):
            codec.read_current(owner.read_view(context), body['approval_id'], session_token=self.session, primary_token=self.primary)

    def test_reader_rejects_wrong_acknowledgement(self):
        reference = dict(self.reference, acknowledgement_sha256='0'*64)
        body = self.synthetic(dict(reference=reference))
        with owner.approval_transaction(self.config) as context, self.assertRaises(ValueError):
            codec.read_current(owner.read_view(context), body['approval_id'], session_token=self.session, primary_token=self.primary)

    def test_current_reader_does_not_accept_detached_approval_or_legacy(self):
        body = self.synthetic()
        with self.assertRaises(ValueError): codec.read_current(body, body['approval_id'], session_token=self.session, primary_token=self.primary)
        with a.connect(self.config.control) as control:
            legacy = [row['approval_id'] for row in control.execute('SELECT * FROM recognition_approvals')
                      if row['approval_id'] != body['approval_id']][0]
        with owner.approval_transaction(self.config) as context, self.assertRaises(ValueError):
            codec.read_current(owner.read_view(context), legacy, session_token=self.session, primary_token=self.primary)

    def test_invalidation_failure_rolls_back_history_and_audit(self):
        body = self.synthetic(dict(local_target=dict(self.pair['operation']['local_target'], auth_epoch=2)))
        real = a._audit
        def fail(*args, **kwargs):
            real(*args, **kwargs)
            raise OSError('audit unavailable')
        with patch.object(a, '_audit', side_effect=fail), self.assertRaises(OSError):
            codec.invalidate_stale_scope(self.config, self.session, primary_token=self.primary)
        with a.connect(self.config.control) as control:
            self.assertEqual('APPROVED', codec._historical(control, body['approval_id'])['state'])


if __name__ == '__main__':
    unittest.main()
