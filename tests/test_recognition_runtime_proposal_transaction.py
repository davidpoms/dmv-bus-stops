"""Independent proposal ownership adapter, real lifecycle, NO proposal writes."""

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from contextlib import closing, contextmanager
from dataclasses import replace
import json
import sqlite3
import threading
import unittest
from unittest.mock import patch

from src.review.recognition import administration as a, admin_auth, administration_schema
from src.review.recognition import runtime_proposal_transaction as p, runtime_scope_validation as shared
from src.review.recognition import runtime_validation as v, runtime_auth as auth
from src.review.recognition import runtime_operation_contract as contract, runtime_proposal_records as records
from src.review.recognition import runtime_profile_schema as profiles, writer_boundary, local_execution
from src.review.recognition.rules import canonical, digest
from tests import test_recognition_runtime_operation_contract as lifecycle
from tests import test_recognition_administration as f


class ProposalTransactionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = lifecycle.RuntimeOperationContractTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.config = self.fixture.config
        self.primary, self.session = self.fixture.primary, self.fixture.session

    def snapshot(self):
        return self.config.control.read_bytes(), self.config.target.read_bytes()

    def validate(self, context):
        return p.read_view(context).validate_session(self.session, primary_token=self.primary)

    def assert_unlocked(self):
        for path in (self.config.control, self.config.target):
            with closing(sqlite3.connect(path, timeout=0)) as connection:
                connection.execute('BEGIN IMMEDIATE')
                connection.rollback()

    def test_real_lifecycle_shared_auth_4a_4b1_no_persistence_or_key_reads(self):
        before = self.snapshot()
        contexts, states = dict(v._contexts), dict(v._states)
        with patch('pathlib.Path.read_bytes', side_effect=AssertionError('key/file read')):
            with p.proposal_transaction(self.config) as context:
                state = p._contexts[context]
                self.assertEqual('ACTIVE', state.phase)
                self.assertEqual({'actor_id': 1, 'generation': 3}, self.validate(context))
                self.assertNotIn(context, v._contexts)
                self.assertNotIn(context, v._states)
                self.assertEqual(contexts, dict(v._contexts))
                self.assertEqual(states, dict(v._states))
                view = p.read_view(context)
                body = self.fixture.build(view)
                ack = records.build_acknowledgement(body, context=view, frozen=self.fixture.frozen,
                    operation_sha256=digest(body), acknowledged_at_utc=f.at(900), previous_sha256=None)
                decoded = records.parse_acknowledgement(canonical(ack), acknowledgement_sha256=digest(ack))
                self.assertEqual(ack, records.match_acknowledgement(body, context=view,
                    frozen=self.fixture.frozen, operation_sha256=digest(body),
                    acknowledgement=decoded, acknowledgement_sha256=digest(ack)))
                self.assertEqual(1, context.target.execute('PRAGMA query_only').fetchone()[0])
                self.assertEqual('VALIDATION_READ_ONLY', state.target_access)
        self.assertEqual('COMMITTED', state.phase)
        self.assertIs(True, state.control_committed)
        self.assertNotIn(context, p._contexts)
        self.assertNotIn(view, shared._proposal_views)
        with self.assertRaises(a.AdminError): view.snapshot()
        with self.assertRaises(a.AdminError): p.read_view(context)
        self.assertEqual(before, self.snapshot())
        self.assert_unlocked()

    def test_contexts_are_not_interchangeable_and_no_issuance_adapter(self):
        with self.assertRaises(TypeError): p.ProposalTransactionContext()
        with p.proposal_transaction(self.config) as context:
            view = p.read_view(context)
            for call in (
                lambda: shared.read_view(context), lambda: shared._parts(context),
                lambda: auth._parts(context), lambda: auth._parts(view),
                lambda: auth._primary(view, self.primary, f.at(900)),
                lambda: auth._session(view, self.session, self.primary, f.at(900)),
                lambda: auth._primary(context, self.primary, f.at(900)),
                lambda: auth._session(context, self.session, self.primary, f.at(900)),
                lambda: v._require_auth_expiry(context, a.timestamp(f.at(901)), 'primary_authentication_required'),
                lambda: auth._insert_scope(context, 'primary', 'x'*32, f.at(900)),
                lambda: auth._insert_scope(view, 'session', 'x'*32, f.at(900)),
                lambda: contract.build_target(context)):
                with self.subTest(call=call), self.assertRaises(ValueError): call()
        with v.authentication_transaction(self.config) as context:
            with self.assertRaises(a.AdminError): p.read_view(context)
        for fake in ({}, object(), object.__new__(p.ProposalTransactionContext)):
            with self.subTest(fake=type(fake)), self.assertRaises(a.AdminError): p.read_view(fake)

    def test_body_lifecycle_protection_in_delete_and_wal(self):
        actions = (
            lambda c: c.control.commit(), lambda c: c.target.rollback(), lambda c: c.commit(),
            lambda c: c.target.close(), lambda c: c.control.executescript('SELECT 1;'),
            lambda c: c.target.set_authorizer(None), lambda c: c.control.set_trace_callback(None),
            lambda c: c.control.execute('COMMIT'), lambda c: c.target.execute('ROLLBACK'),
            lambda c: c.target.execute('ROLLBACK; BEGIN IMMEDIATE'),
            lambda c: c.control.execute('SAVEPOINT replacement'), lambda c: c.target.execute('BEGIN'),
            lambda c: c.target.execute('PRAGMA query_only=OFF'),
            lambda c: c.control.execute('PRAGMA writable_schema=ON'),
            lambda c: c.control.execute('PRAGMA journal_mode=WAL'),
            lambda c: c.control.execute("ATTACH DATABASE ':memory:' AS extra"),
            lambda c: c.target.execute('CREATE TABLE forbidden(value)'),
            lambda c: c.target_writer, lambda c: c.acknowledgement_writer)
        for mode in ('DELETE', 'WAL'):
            for path in (self.config.control, self.config.target):
                with closing(sqlite3.connect(path)) as connection:
                    self.assertEqual(mode.lower(), connection.execute('PRAGMA journal_mode='+mode).fetchone()[0])
            for index, action in enumerate(actions):
                with self.subTest(mode=mode, action=index), self.assertRaises(a.AdminError):
                    with p.proposal_transaction(self.config) as context:
                        with self.assertRaises((a.AdminError, sqlite3.DatabaseError)):
                            action(context)
                        with self.assertRaises(a.AdminError): p.read_view(context).snapshot()
                self.assert_unlocked()

    def test_no_body_writes_to_any_protected_store(self):
        attempts = (
            ('control', 'recognition_admin_primary'), ('control', 'recognition_admin_sessions'),
            ('control', 'recognition_admin_mfa'), ('control', 'recognition_admin_stepups'),
            ('control', profiles.AUTH), ('control', 'recognition_admin_audit'),
            ('control', 'recognition_approvals'), ('control', profiles.PROFILES),
            ('control', 'recognition_admin_bindings'),
            ('target', 'recognition_operation_contracts'), ('target', 'recognition_preparations'),
            ('target', 'recognition_frozen_events'), ('target', 'recognition_operation_decisions'),
            ('target', 'recognition_operation_executions'), ('target', 'recognition_execution_claims'))
        before = self.snapshot()
        for which, table in attempts:
            for verb in ('INSERT', 'UPDATE', 'DELETE'):
                statement = (f'INSERT INTO {table} DEFAULT VALUES' if verb == 'INSERT' else
                             f'UPDATE {table} SET unused=1' if verb == 'UPDATE' else f'DELETE FROM {table}')
                with self.subTest(which=which, table=table, verb=verb), self.assertRaises(a.AdminError):
                    with p.proposal_transaction(self.config) as context:
                        getattr(context, which).execute(statement)
        self.assertEqual(before, self.snapshot())

    def test_kernel_cannot_issue_authentication_or_acknowledgements(self):
        for table in ('recognition_admin_primary', 'recognition_admin_sessions', profiles.AUTH, 'recognition_admin_stepups'):
            with self.subTest(table=table), self.assertRaises((a.AdminError, sqlite3.DatabaseError)):
                with p.proposal_transaction(self.config) as context:
                    control = shared._view_parts(p.read_view(context))[1][0]
                    control.execute(f'INSERT INTO {table} DEFAULT VALUES')
        before = self.snapshot()
        with self.assertRaises(a.AdminError):
            with p.proposal_transaction(self.config) as context:
                control = shared._view_parts(p.read_view(context))[1][0]
                a._audit(control, records.ACK_ACTION, 1, f.at(900), {'test_only': 'not an acknowledgement'})
        self.assertEqual(before, self.snapshot())

    def test_raw_handles_and_cursor_escape_unavailable(self):
        with p.proposal_transaction(self.config) as context:
            view = p.read_view(context)
            for facade in (context.control, context.target, view):
                for name in ('connection', 'control_connection', 'target_connection', 'in_transaction'):
                    with self.subTest(name=name), self.assertRaises(AttributeError): getattr(facade, name)
            cursor = context.target.execute('SELECT 1')
            with self.assertRaises(AttributeError): cursor.connection
            self.assertEqual(1, cursor.fetchone()[0])
        with self.assertRaises(a.AdminError): cursor.fetchone()

    def test_pid_thread_connection_and_lifetime_binding(self):
        with p.proposal_transaction(self.config) as context:
            view = p.read_view(context)
            with patch.object(p.os, 'getpid', return_value=-1):
                with self.assertRaises(a.AdminError): view.snapshot()
            with ThreadPoolExecutor(max_workers=1) as pool:
                with self.assertRaises(a.AdminError): pool.submit(view.snapshot).result()
            state = p._contexts[context]
            for which in ('control', 'target'):
                original = getattr(state, which)
                try:
                    with a.connect(getattr(self.config, which)) as replacement:
                        setattr(state, which, replacement)
                        with self.assertRaises(a.AdminError): view.snapshot()
                finally:
                    setattr(state, which, original)
            self.assertEqual(3, view.snapshot()['generation'])
        with p.proposal_transaction(self.config):
            with self.assertRaises(a.AdminError): view.snapshot()

    def test_expiry_constraints_are_owned_and_cannot_be_extended(self):
        with self.assertRaisesRegex(a.AdminError, 'administrative_session_expired_or_revoked'):
            with p.proposal_transaction(self.config) as context:
                self.validate(context)
                state = p._contexts[context]
                self.assertTrue(state.auth_expiries)
                self.assertFalse(v._states)
                expires = min(e for e, _ in state.auth_expiries)
                p._require_auth_expiry(context, expires+100, 'administrative_session_expired_or_revoked')
                self.fixture.fixture.clock.return_value = f.at(expires-a.timestamp(f.at(0)))
        self.fixture.fixture.clock.return_value = f.at(900)
        self.assert_unlocked()

    def test_expired_primary_revocation_and_denial_persist_without_issuance(self):
        self.fixture.fixture.clock.return_value = f.at(40000)
        with self.assertRaisesRegex(a.AdminError, 'primary_authentication_required'):
            with p.proposal_transaction(self.config) as context:
                self.validate(context)
        with a.connect(self.config.control) as control:
            self.assertEqual(1, control.execute('SELECT revoked FROM recognition_admin_primary WHERE token_hash=?',
                (a.token_hash(self.primary),)).fetchone()[0])
            self.assertEqual(1, control.execute('SELECT revoked FROM recognition_admin_sessions WHERE token_hash=?',
                (a.token_hash(self.session),)).fetchone()[0])
            head = load_audit(control)
            self.assertEqual('administration_denied', head['action'])

    def test_existing_throttle_protocol_uses_deferred_denial_commit(self):
        with self.assertRaisesRegex(a.AdminError, 'invalid_or_replayed_totp'):
            with p.proposal_transaction(self.config) as context:
                state = p._contexts[context]
                control = shared._view_parts(p.read_view(context))[1][0]
                control.execute('INSERT INTO recognition_admin_attempts VALUES(?,?,?)',
                                (1, a.timestamp(f.at(900)), 1))
                admin_auth._deny(control, 'invalid_or_replayed_totp', f.at(900), 1, 401)
        self.assertEqual('COMMITTED', state.phase)
        with a.connect(self.config.control) as control:
            self.assertEqual(1, control.execute('SELECT failures FROM recognition_admin_attempts').fetchone()[0])
            self.assertEqual('administration_denied', load_audit(control)['action'])

    def test_swallowed_denial_cannot_continue_or_commit(self):
        before = self.snapshot()
        with self.assertRaises(a.AdminError):
            with p.proposal_transaction(self.config) as context:
                control = shared._view_parts(p.read_view(context))[1][0]
                try: admin_auth._deny(control, 'primary_authentication_required', f.at(900), 1, 401)
                except a.AdminError: pass
        self.assertEqual(before, self.snapshot())

    def test_rollback_cleanup_and_locks_through_successful_control_commit(self):
        observations = []
        original = a.connect
        @contextmanager
        def connected(path, **kwargs):
            with original(path, **kwargs) as connection:
                if path == self.config.control:
                    def trace(sql):
                        if sql in ('COMMIT', 'ROLLBACK'):
                            with closing(sqlite3.connect(self.config.target, timeout=0)) as competitor:
                                try: competitor.execute('BEGIN IMMEDIATE')
                                except sqlite3.OperationalError: observations.append((sql, 'HELD'))
                                else:
                                    observations.append((sql, 'RELEASED'))
                                    competitor.rollback()
                    connection.set_trace_callback(trace)
                yield connection
        with patch.object(a, 'connect', side_effect=connected):
            with p.proposal_transaction(self.config) as context:
                self.validate(context)
            with self.assertRaisesRegex(RuntimeError, 'test rollback'):
                with p.proposal_transaction(self.config) as context:
                    state = p._contexts[context]
                    raise RuntimeError('test rollback')
        self.assertEqual([('COMMIT', 'HELD'), ('ROLLBACK', 'HELD')], observations)
        self.assertEqual('ROLLED_BACK', state.phase)
        self.assertFalse(state.active)
        self.assert_unlocked()

    def test_final_identity_change_rolls_back_denial(self):
        before = self.snapshot()
        changed = [False]
        fixture = self.fixture.fixture
        with patch.object(a, 'target_identity', side_effect=lambda subject:
                fixture.original_identity(subject) if changed[0] else fixture.runtime_identity(subject)), \
             self.assertRaisesRegex(a.AdminError, 'identity_mismatch'):
            with p.proposal_transaction(self.config) as context:
                state = p._contexts[context]
                # Simulate changed physical observation at the final validation,
                # without releasing either database reservation or changing data.
                changed[0] = True
                control = state.kernel_control
                admin_auth._deny(control, 'primary_authentication_required', f.at(900), 1, 401)
        self.assertEqual(before, self.snapshot())

    def test_pending_generation_change_serializes_and_invalidates_profile(self):
        begun = threading.Event()
        def change():
            with a.connect(self.config.control, write=True) as control:
                begun.set()
                control.execute('BEGIN IMMEDIATE')
                old = json.loads(control.execute('SELECT body_json FROM recognition_admin_bindings ORDER BY generation DESC LIMIT 1').fetchone()[0])
                body = dict(old, generation=old['generation']+1, previous_sha256=digest(old),
                            runtime_profile_sha256=None, at_utc=f.at(901))
                control.execute('INSERT INTO recognition_admin_bindings VALUES(?,?,?)',
                                (body['generation'], canonical(body), digest(body)))
                a._invalidate(control)
                a._audit(control, 'test_only_generation_change', 1, f.at(901))
                control.commit()
        with ThreadPoolExecutor(max_workers=1) as pool:
            with p.proposal_transaction(self.config) as context:
                self.validate(context)
                future = pool.submit(change)
                self.assertTrue(begun.wait(2))
                with self.assertRaises(TimeoutError): future.result(timeout=0.05)
            future.result(timeout=10)
        self.fixture.fixture.clock.return_value = f.at(901)
        with self.assertRaises(ValueError):
            with p.proposal_transaction(self.config): pass

    def test_installation_target_owner_and_epoch_changes_rejected(self):
        for column, bad in (('installation_id', str_uuid()), ('target_id', str_uuid()), ('owner_id', 2), ('auth_epoch', 999)):
            original = self.fixture.fixture.sql(f'SELECT {column} FROM recognition_local_installation', target=True)[0][0]
            self.fixture.fixture.sql(f'UPDATE recognition_local_installation SET {column}=?', (bad,), target=True)
            try:
                with self.subTest(column=column), self.assertRaises(ValueError):
                    with p.proposal_transaction(self.config) as context: self.validate(context)
            finally:
                self.fixture.fixture.sql(f'UPDATE recognition_local_installation SET {column}=?', (original,), target=True)

    def test_mfa_epoch_change_rejects_old_session(self):
        self.fixture.fixture.sql('UPDATE recognition_admin_mfa SET epoch=epoch+1')
        with self.assertRaisesRegex(a.AdminError, 'expired_or_revoked'):
            with p.proposal_transaction(self.config) as context: self.validate(context)

    def test_profile_corruption_or_replacement_fails_closed(self):
        self.fixture.fixture.sql('DROP TRIGGER '+profiles.PROFILES+'_immutable_update')
        self.fixture.fixture.sql(f"UPDATE {profiles.PROFILES} SET hostname='other-runtime'")
        self.fixture.fixture.sql(profiles.definitions()[profiles.PROFILES+'_immutable_update'])
        with self.assertRaises(ValueError):
            with p.proposal_transaction(self.config): pass

    def test_no_downstream_context_or_writer_capability(self):
        with p.proposal_transaction(self.config) as context:
            view = p.read_view(context)
            with self.assertRaises(ValueError):
                writer_boundary.acquire(context, self.config.target, self.fixture.frozen['preparation']['manifest'])
            result = local_execution.execute_approved_operation(view, self.session, 'test-only-no-approval', now=f.at(900))
            self.assertEqual('BLOCKED', result.admission)

    def test_real_primary_issuance_primitive_is_denied(self):
        before = self.snapshot()
        with self.assertRaises((ValueError, sqlite3.DatabaseError)):
            with p.proposal_transaction(self.config) as context:
                control, target, binding, _ = shared._view_parts(p.read_view(context))[1]
                admin_auth._record_primary(control, target, binding,
                    actor_id=1, reviewer_key='owner-key', now=f.at(900))
        self.assertEqual(before, self.snapshot())

    def test_confirmed_commit_cleanup_error_preserves_committed_outcome(self):
        original = sqlite3.connect
        target_uri = self.config.target.as_uri()
        class CleanupFailure(sqlite3.Connection):
            def rollback(connection):
                super().rollback()
                if connection.is_target:
                    raise OSError('test-only cleanup detail must not escape')
        def connect(path, **kwargs):
            connection = original(path, factory=CleanupFailure, **kwargs)
            connection.is_target = str(path).startswith(target_uri)
            return connection
        with patch.object(a.sqlite3, 'connect', side_effect=connect), self.assertRaises(p.ProposalCleanupError) as error:
            with p.proposal_transaction(self.config) as context:
                state = p._contexts[context]
                self.validate(context)
        self.assertIs(True, error.exception.control_committed)
        self.assertEqual('proposal_cleanup_after_commit', error.exception.code)
        self.assertNotIn('test-only cleanup detail', str(error.exception))
        self.assertEqual('COMMITTED', state.phase)
        self.assertNotIn(context, p._contexts)
        self.assert_unlocked()

    def test_commit_errors_never_claim_confirmed_rollback(self):
        original = sqlite3.connect
        control_uri = self.config.control.as_uri()
        for after_commit in (False, True):
            class CommitFailure(sqlite3.Connection):
                def commit(connection):
                    if connection.is_control:
                        if after_commit: super().commit()
                        raise sqlite3.OperationalError('test-only uncertain commit')
                    return super().commit()
            def connect(path, **kwargs):
                connection = original(path, factory=CommitFailure, **kwargs)
                connection.is_control = str(path).startswith(control_uri)
                return connection
            with self.subTest(after_commit=after_commit), patch.object(a.sqlite3, 'connect', side_effect=connect), \
                 self.assertRaises(sqlite3.OperationalError):
                with p.proposal_transaction(self.config) as context:
                    state = p._contexts[context]
                    self.validate(context)
            self.assertIsNone(state.control_committed)
            self.assertEqual('OUTCOME_UNKNOWN', state.phase)
            self.assertNotIn(context, p._contexts)
            self.assert_unlocked()

    def test_target_owner_epoch_writers_wait_until_context_finishes(self):
        for column, value in (('auth_epoch', 999), ('owner_id', 2)):
            previous = self.fixture.fixture.sql(f'SELECT {column} FROM recognition_local_installation', target=True)[0][0]
            begun = threading.Event()
            def update():
                with a.connect(self.config.target, write=True) as target:
                    begun.set()
                    target.execute('BEGIN IMMEDIATE')
                    target.execute(f'UPDATE recognition_local_installation SET {column}=?', (value,))
                    target.commit()
            try:
                with self.subTest(column=column), ThreadPoolExecutor(max_workers=1) as pool:
                    with p.proposal_transaction(self.config) as context:
                        self.assertEqual(3, p.read_view(context).snapshot()['generation'])
                        future = pool.submit(update)
                        self.assertTrue(begun.wait(2))
                        with self.assertRaises(TimeoutError): future.result(timeout=0.05)
                    future.result(timeout=10)
                with self.assertRaises(ValueError):
                    with p.proposal_transaction(self.config) as context: self.validate(context)
            finally:
                self.fixture.fixture.sql(f'UPDATE recognition_local_installation SET {column}=?', (previous,), target=True)


def load_audit(control):
    return json.loads(control.execute('SELECT body_json FROM recognition_admin_audit ORDER BY sequence DESC LIMIT 1').fetchone()[0])


def str_uuid():
    return '00000000-0000-4000-8000-000000000000'


if __name__ == '__main__':
    unittest.main()
