"""Slice 3a real disposable enrollment/validation and reservation boundaries."""

from contextlib import closing, contextmanager
from dataclasses import replace
import json
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
import unittest
from unittest.mock import patch

from src.review.recognition import administration as a, administration_schema as s
from src.review.recognition import runtime_validation as v, runtime_profile_schema as r
from src.review.recognition.rules import canonical, digest
from tests import test_recognition_runtime_enrollment as enrollment
from tests import test_recognition_administration as f


class RuntimeValidationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = enrollment.RuntimeEnrollmentTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.enroll()
        self.config = self.fixture.f.config
        self.original_identity = a.target_identity
        self.identity_patch = patch.object(a, 'target_identity', side_effect=self.runtime_identity)
        self.identity_patch.start()
        self.addCleanup(self.identity_patch.stop)
        clock = patch.object(v, '_utc_now', return_value=f.at(900))
        self.clock = clock.start()
        self.addCleanup(clock.stop)

    def runtime_identity(self, subject):
        value = self.original_identity(subject)
        return replace(value, hostname='synthetic-web', device=value.device + 1)

    def snapshot(self):
        return self.config.target.read_bytes(), self.config.control.read_bytes()

    def update_body(self, table, key, value, change):
        with a.connect(self.config.control, write=True) as conn:
            conn.execute('BEGIN IMMEDIATE')
            trigger = table + '_immutable_update'
            conn.execute('DROP TRIGGER ' + trigger)
            body = json.loads(conn.execute(f'SELECT body_json FROM {table} WHERE {key}=?', (value,)).fetchone()[0])
            change(body)
            conn.execute(f'UPDATE {table} SET body_json=?,body_sha256=? WHERE {key}=?', (canonical(body), digest(body), value))
            conn.execute(s.definitions()[trigger])
            conn.commit()

    def test_real_enrolled_runtime_differs_from_deployment_no_auth_or_key(self):
        before = self.snapshot()
        with patch('pathlib.Path.read_bytes', side_effect=AssertionError('key/file read')):
            snapshot = v.validate_runtime_snapshot(self.config)
        self.assertEqual(2, snapshot['generation'])
        self.assertEqual(1, snapshot['owner_id'])
        self.assertEqual(before, self.snapshot())
        # Challenge expired long ago; enrollment was valid then, so remains valid.
        self.assertGreater(a.timestamp(f.at(900)), self.fixture.challenge['expires_at'])
        with a.connect(self.config.control) as conn:
            self.assertEqual(0, conn.execute(f'SELECT count(*) FROM {r.AUTH}').fetchone()[0])
            self.assertEqual(0, conn.execute('SELECT count(*) FROM recognition_admin_primary WHERE revoked=0').fetchone()[0])
        with self.assertRaisesRegex(a.AdminError, 'runtime_profile_contract_not_enabled'):
            a.get_installation_control(self.config)

    def test_each_actual_physical_mismatch_independently(self):
        for which in ('target', 'control'):
            path = getattr(self.config, which)
            for field, change in (('hostname', lambda x: 'wrong'), ('device', lambda x: x + 1),
                                  ('inode', lambda x: x + 1), ('database', lambda x: str(path.parent / 'other.db'))):
                def observe(subject):
                    value = self.runtime_identity(subject)
                    if self.original_identity(subject).database == str(path):
                        value = replace(value, **{field: change(getattr(value, field))})
                    return value
                with self.subTest(which=which, field=field), patch.object(a, 'target_identity', side_effect=observe):
                    with self.assertRaises(a.AdminError):
                        v.validate_runtime_snapshot(self.config)

    def test_canonical_actual_values_fail_closed(self):
        for values in (dict(hostname='web\x00'), dict(database=str(self.config.target)+'\x00'),
                       dict(device=True), dict(inode=False), dict(device=-1), dict(inode=0)):
            with self.subTest(values=values), patch.object(a, 'target_identity',
                    side_effect=lambda subject: replace(self.runtime_identity(subject), **values)):
                with self.assertRaises((a.AdminError, ValueError)):
                    v.validate_runtime_snapshot(self.config)

    def test_target_schema_and_logical_scope(self):
        for column, value in (('installation_id', '00000000-0000-0000-0000-000000000000'),
                              ('target_id', '00000000-0000-0000-0000-000000000000'), ('owner_id', 9)):
            with a.connect(self.config.target, write=True) as conn:
                old = conn.execute(f'SELECT {column} FROM {s.TARGET_TABLE}').fetchone()[0]
                conn.execute(f'UPDATE {s.TARGET_TABLE} SET {column}=?', (value,)); conn.commit()
            with self.subTest(column=column), self.assertRaisesRegex(a.AdminError, 'scope_mismatch'):
                v.validate_runtime_snapshot(self.config)
            with a.connect(self.config.target, write=True) as conn:
                conn.execute(f'UPDATE {s.TARGET_TABLE} SET {column}=?', (old,)); conn.commit()
        with a.connect(self.config.target, write=True) as conn:
            conn.execute('CREATE TABLE unexpected(value)'); conn.commit()
        with self.assertRaisesRegex(a.AdminError, 'schema_mismatch'):
            v.validate_runtime_snapshot(self.config)

    def test_owner_demotion_no_revocation_write_from_validation(self):
        with a.connect(self.config.target, write=True) as conn:
            conn.execute("UPDATE community_reviewers SET role='reviewer' WHERE id=1"); conn.commit()
        before = self.snapshot()
        with self.assertRaisesRegex(a.AdminError, 'recognition_owner_required'):
            v.validate_runtime_snapshot(self.config)
        self.assertEqual(before, self.snapshot())

    def test_binding_history_canonical_and_generation_failures(self):
        with a.connect(self.config.control) as conn:
            original = json.loads(conn.execute('SELECT body_json FROM recognition_admin_bindings WHERE generation=2').fetchone()[0])
        for change in (dict(generation=True), dict(generation=3), dict(installation_id='BAD'),
                       dict(target_id=original['target_id']+'\x00'), dict(owner_id=True),
                       dict(previous_sha256='0'*64), dict(runtime_profile_sha256=None),
                       dict(runtime_profile_sha256='0'*64), dict(production_state='ACTIVATED')):
            self.update_body('recognition_admin_bindings', 'generation', 2, lambda body: body.update(change))
            with self.subTest(change=change), self.assertRaises((a.AdminError, ValueError)):
                v.validate_runtime_snapshot(self.config)
            self.update_body('recognition_admin_bindings', 'generation', 2, lambda body: (body.clear(), body.update(original)))
        self.update_body('recognition_admin_bindings', 'generation', 1, lambda body: body.pop('previous_sha256'))
        with self.assertRaises((a.AdminError, ValueError)):
            v.validate_runtime_snapshot(self.config)

    def test_profile_digest_and_partial_schema_fail_closed(self):
        with a.connect(self.config.control, write=True) as conn:
            trigger = r.PROFILES + '_immutable_update'
            conn.execute('DROP TRIGGER ' + trigger)
            conn.execute(f"UPDATE {r.PROFILES} SET hostname='wrong'")
            conn.execute(r.definitions()[trigger]); conn.commit()
        with self.assertRaisesRegex(ValueError, 'digest_mismatch'):
            v.validate_runtime_snapshot(self.config)
        with a.connect(self.config.control, write=True) as conn:
            conn.execute('DROP TRIGGER ' + r.AUTH + '_immutable_delete'); conn.commit()
        with self.assertRaisesRegex(ValueError, 'schema_mismatch'):
            v.validate_runtime_snapshot(self.config)

    def test_enrollment_audit_and_selected_observation_linkage(self):
        with a.connect(self.config.control) as conn:
            sequence = conn.execute(f'SELECT audit_sequence FROM {r.PROFILES}').fetchone()[0]
            original = json.loads(conn.execute('SELECT body_json FROM recognition_admin_audit WHERE sequence=?', (sequence,)).fetchone()[0])
        for key, value in (('challenge_sha256', '0'*64), ('observation_sha256', '0'*64),
                           ('private_log_review_confirmed', False), ('previous_generation', True)):
            self.update_body('recognition_admin_audit', 'sequence', sequence, lambda body: body['subject'].update({key:value}))
            with self.subTest(key=key), self.assertRaises((a.AdminError, ValueError)):
                v.validate_runtime_snapshot(self.config)
            self.update_body('recognition_admin_audit', 'sequence', sequence, lambda body: (body.clear(), body.update(original)))
        self.update_body('recognition_admin_audit', 'sequence', sequence, lambda body: body.update(previous_sha256='0'*64))
        with self.assertRaisesRegex(a.AdminError, 'audit_integrity_failure'):
            v.validate_runtime_snapshot(self.config)

    def test_context_pid_connection_lifetime_and_no_authority(self):
        from src.review.recognition.authorization import Authorization
        from src.review.recognition.production_operations import ProductionOperationContext
        with self.assertRaises(TypeError): v.RuntimeValidationContext()
        with v.authentication_transaction(self.config) as context:
            data = v._contexts[context]
            self.assertNotIsInstance(context, Authorization)
            self.assertNotIsInstance(context, ProductionOperationContext)
            with patch.object(v.os, 'getpid', return_value=data['pid'] + 1):
                with self.assertRaisesRegex(a.AdminError, 'runtime_context_invalid'):
                    v._context_data(context, data['control'], data['target'])
            with a.connect(self.config.target) as other:
                with self.assertRaisesRegex(a.AdminError, 'runtime_context_invalid'):
                    v._context_data(context, data['control'], other)
        with self.assertRaisesRegex(a.AdminError, 'runtime_context_invalid'):
            v._context_data(context, data['control'], data['target'])
        # New transaction validates again; no process/worker success cache.
        with patch.object(a, 'target_identity', side_effect=self.original_identity):
            with self.assertRaisesRegex(a.AdminError, 'identity_mismatch'):
                v.validate_runtime_snapshot(self.config)

    def test_valid_context_is_rejected_by_real_downstream_boundaries(self):
        from src.review.recognition import writer_boundary, production_operations, local_execution, local_readiness
        from src.review.recognition.authorization import AuthorizationError
        before = self.snapshot()
        with v.authentication_transaction(self.config) as context:
            with self.assertRaises(a.AdminError):
                production_operations.context_data(context)
            with self.assertRaises(AuthorizationError):
                writer_boundary.acquire(context, self.config.target, {})
            result = local_execution.verify_approved_operation(context, 'no-session', 'no-approval', now=f.at(900))
            self.assertEqual('NOT_STARTED', result.state)
            self.assertEqual('production_execution_unavailable', result.reason)
        readiness = local_readiness.assess(self.config, now=f.at(900))
        self.assertFalse(readiness['activation_ready'])
        self.assertIn('runtime_profile_contract_not_enabled', canonical(readiness))
        self.assertEqual(before, self.snapshot())

    def test_target_query_only_and_locks_through_commit(self):
        original_connect = a.connect
        observations = []
        @contextmanager
        def connected(path, **kwargs):
            with original_connect(path, **kwargs) as conn:
                if path == self.config.control:
                    def trace(sql):
                        if sql == 'COMMIT':
                            with sqlite3.connect(self.config.target, timeout=0) as contender:
                                try:
                                    contender.execute('BEGIN IMMEDIATE')
                                except sqlite3.OperationalError as error:
                                    observations.append(str(error))
                                else:
                                    observations.append('UNLOCKED')
                                    contender.rollback()
                    conn.set_trace_callback(trace)
                yield conn
        with patch.object(a, 'connect', side_effect=connected):
            with v.authentication_transaction(self.config) as context:
                target = v._contexts[context]['target']
                self.assertEqual(1, target.execute('PRAGMA query_only').fetchone()[0])
                with self.assertRaises(sqlite3.DatabaseError):
                    target.execute(f'UPDATE {s.TARGET_TABLE} SET auth_epoch=99')
        self.assertEqual(['database is locked'], observations)
        with sqlite3.connect(self.config.target, timeout=0) as conn:
            conn.execute('BEGIN IMMEDIATE'); conn.rollback()

    def test_control_auth_records_atomic_with_rollback_and_no_issuance_api(self):
        def write_synthetic(context):
            control = v._contexts[context]['control']
            scope = v._contexts[context]['snapshot']
            # SQL-only fixture to test future issuance atomicity, not an API/token.
            control.execute('INSERT INTO recognition_admin_primary VALUES(?,?,?,?,?,?,?,0)',
                ('a'*64, 1, scope['owner_key_sha256'], scope['auth_epoch'], 2, a.timestamp(f.at(900)), a.timestamp(f.at(901))))
            control.execute(f'INSERT INTO {r.AUTH} VALUES(?,?,?,?)',
                ('primary', 'a'*64, scope['profile_sha256'], a.timestamp(f.at(900))))
            a._audit(control, 'synthetic_runtime_atomicity_test', 1, f.at(900))
        before = self.snapshot()
        with self.assertRaisesRegex(RuntimeError, 'injected'):
            with v.authentication_transaction(self.config) as context:
                write_synthetic(context)
                raise RuntimeError('injected')
        self.assertEqual(before, self.snapshot())
        with v.authentication_transaction(self.config) as context:
            write_synthetic(context)
        with a.connect(self.config.control) as conn:
            self.assertEqual(1, conn.execute(f'SELECT count(*) FROM {r.AUTH}').fetchone()[0])
            s.check_control(conn)

    def test_final_failure_and_clock_rollback_roll_back_with_target_held(self):
        before = self.snapshot()
        with self.assertRaisesRegex(a.AdminError, 'clock_rollback'):
            with v.authentication_transaction(self.config) as context:
                control = v._contexts[context]['control']
                a._audit(control, 'synthetic_rollback', 1, f.at(900))
                self.clock.return_value = f.at(899)
        self.assertEqual(before, self.snapshot())
        with sqlite3.connect(self.config.target, timeout=0) as conn:
            conn.execute('BEGIN IMMEDIATE'); conn.rollback()

    def test_control_scope_forbids_non_authentication_mutation(self):
        before = self.snapshot()
        with v.authentication_transaction(self.config) as context:
            conn = v._contexts[context]['control']
            for statement in ('UPDATE recognition_admin_bindings SET generation=generation',
                              f'UPDATE {r.PROFILES} SET hostname=hostname',
                              'UPDATE recognition_approvals SET body_json=body_json',
                              'CREATE TABLE unsafe(value)', "ATTACH DATABASE ':memory:' AS unsafe"):
                with self.subTest(statement=statement), self.assertRaises(sqlite3.DatabaseError):
                    conn.execute(statement)
        self.assertEqual(before, self.snapshot())

    def test_commit_failure_rolls_back_before_target_release(self):
        events = []
        before = self.snapshot()
        connect = sqlite3.connect
        control_path = self.config.control.as_uri()
        target_path = self.config.target
        class FaultConnection(sqlite3.Connection):
            def commit(conn):
                if conn.is_control:
                    raise sqlite3.OperationalError('injected manager commit failure')
                return super().commit()
            def rollback(conn):
                if conn.is_control and conn.in_transaction:
                    with connect(target_path, timeout=0) as contender:
                        try:
                            contender.execute('BEGIN IMMEDIATE')
                        except sqlite3.OperationalError as error:
                            events.append(str(error))
                        else:
                            events.append('UNLOCKED')
                            contender.rollback()
                return super().rollback()
        def connected(path, **kwargs):
            conn = connect(path, factory=FaultConnection, **kwargs)
            conn.is_control = str(path).startswith(control_path)
            return conn
        with patch.object(a.sqlite3, 'connect', side_effect=connected), self.assertRaises(sqlite3.DatabaseError):
            with v.authentication_transaction(self.config) as context:
                self.synthetic_primary(context)
                control = v._contexts[context]['control']
                a._audit(control, 'synthetic_commit_failure', 1, f.at(900))
        self.assertEqual(['database is locked'], events)
        self.assertEqual(before, self.snapshot())

    def test_target_reservation_released_after_initial_validation_failure_rollback(self):
        original_connect = a.connect
        events = []
        @contextmanager
        def connected(path, **kwargs):
            with original_connect(path, **kwargs) as conn:
                if path == self.config.control:
                    conn.set_trace_callback(lambda sql: events.append(sql))
                try:
                    yield conn
                finally:
                    if path == self.config.target:
                        self.assertIn('ROLLBACK', events)
                        self.assertTrue(conn.in_transaction)
        with patch.object(a, 'connect', side_effect=connected), \
             patch.object(a, 'target_identity', side_effect=self.original_identity), \
             self.assertRaisesRegex(a.AdminError, 'identity_mismatch'):
            v.validate_runtime_snapshot(self.config)

    def test_final_identity_change_rolls_back_control(self):
        before = self.snapshot()
        changed = [False]
        def observe(subject):
            return self.original_identity(subject) if changed[0] else self.runtime_identity(subject)
        with patch.object(a, 'target_identity', side_effect=observe), \
             self.assertRaisesRegex(a.AdminError, 'identity_mismatch'):
            with v.authentication_transaction(self.config) as context:
                a._audit(v._contexts[context]['control'], 'synthetic_identity_change', 1, f.at(900))
                changed[0] = True
        self.assertEqual(before, self.snapshot())

    def test_profile_relationship_selected_evidence_tampering(self):
        with a.connect(self.config.control) as conn:
            sequence = conn.execute(f'SELECT audit_sequence FROM {r.PROFILES}').fetchone()[0]
            original = json.loads(conn.execute('SELECT body_json FROM recognition_admin_audit WHERE sequence=?', (sequence,)).fetchone()[0])
        for changes in (dict(source_generation=True), dict(target_device='01'),
                        dict(nonce_sha256='0'*64), dict(observed_at=self.fixture.challenge['expires_at']),
                        dict(hostname='contradictory-worker'), dict(target_inode='1\x00'),
                        dict(installation_id='NOT-A-UUID')):
            def tamper(body):
                review = body['subject']['review']
                record = review['observations'][0]
                record['observation'].update(changes)
                record['observation_sha256'] = digest(record['observation'])
                review['selected_observation_sha256'] = record['observation_sha256']
                body['subject']['review_sha256'] = digest(review)
            self.update_body('recognition_admin_audit', 'sequence', sequence, tamper)
            with self.subTest(changes=changes), self.assertRaises((a.AdminError, ValueError)):
                v.validate_runtime_snapshot(self.config)
            self.update_body('recognition_admin_audit', 'sequence', sequence, lambda body: (body.clear(), body.update(original)))

    def test_large_device_and_inode_observations_are_lossless(self):
        from contextlib import ExitStack
        import sys
        huge = 2**80
        # All preparation/approval aliases must see the same synthetic hardware,
        # not just administration. No validation/history function is replaced.
        def hardware(subject):
            return replace(self.original_identity(subject), device=huge, inode=huge + 1)
        with ExitStack() as stack:
            for module in list(sys.modules.values()):
                if (getattr(module, '__name__', '').startswith('src.review.recognition')
                        and getattr(module, 'target_identity', None) is self.original_identity):
                    stack.enter_context(patch.object(module, 'target_identity', side_effect=hardware))
            stack.enter_context(patch.object(a, 'target_identity', side_effect=hardware))
            other = enrollment.RuntimeEnrollmentTests()
            other.setUp()
            self.addCleanup(other.doCleanups)
            other.enroll()
        with patch.object(a, 'target_identity', side_effect=lambda subject:
                          replace(self.original_identity(subject), hostname='synthetic-web', device=huge + 1, inode=huge + 1)):
            self.assertEqual(2, v.validate_runtime_snapshot(other.f.config)['generation'])
        with a.connect(other.f.control) as conn:
            row = conn.execute(f'SELECT target_device,target_inode,control_device,control_inode FROM {r.PROFILES}').fetchone()
            self.assertEqual((str(huge + 1),) * 4, tuple(row))

    def assert_target_locked(self):
        with closing(sqlite3.connect(self.config.target, timeout=0)) as conn:
            with self.assertRaisesRegex(sqlite3.OperationalError, 'locked'):
                conn.execute('BEGIN IMMEDIATE')

    def synthetic_primary(self, context):
        data = v._contexts[context]
        conn, scope = data['control'], data['snapshot']
        conn.execute('INSERT INTO recognition_admin_primary VALUES(?,?,?,?,?,?,?,0)',
            ('c'*64, 1, scope['owner_key_sha256'], scope['auth_epoch'], scope['generation'],
             a.timestamp(f.at(900)), a.timestamp(f.at(901))))
        conn.execute(f'INSERT INTO {r.AUTH} VALUES(?,?,?,?)',
            ('primary', 'c'*64, scope['profile_sha256'], a.timestamp(f.at(900))))

    def test_target_lifecycle_and_protection_owned_in_delete_and_wal(self):
        actions = (lambda c:c.rollback(), lambda c:c.commit(), lambda c:c.close(),
                   lambda c:c.execute('ROLLBACK'), lambda c:c.execute('COMMIT'),
                   lambda c:c.execute('END'), lambda c:c.execute('BEGIN'),
                   lambda c:c.execute('SAVEPOINT replacement'),
                   lambda c:c.execute('PRAGMA query_only=OFF'),
                   lambda c:c.execute('PRAGMA query_only=ON'),
                   lambda c:c.executescript('ROLLBACK; BEGIN;'),
                   lambda c:c.set_authorizer(None))
        for mode in ('DELETE', 'WAL'):
            with closing(sqlite3.connect(self.config.target)) as conn:
                self.assertEqual(mode.lower(), conn.execute('PRAGMA journal_mode='+mode).fetchone()[0])
            for index, action in enumerate(actions):
                with self.subTest(mode=mode, action=index), self.assertRaises(a.AdminError):
                    with v.authentication_transaction(self.config) as context:
                        data = v._contexts[context]
                        with self.assertRaises((a.AdminError, sqlite3.DatabaseError)):
                            action(data['target'])
                        self.assert_target_locked()
                        with self.assertRaisesRegex(a.AdminError, 'runtime_context_invalid'):
                            v._context_data(context, data['control'], data['target'])
                with closing(sqlite3.connect(self.config.target, timeout=0)) as conn:
                    conn.execute('BEGIN IMMEDIATE'); conn.rollback()

    def test_control_lifecycle_and_implicit_commit_cannot_persist_issuance(self):
        actions = (lambda c:c.commit(), lambda c:c.rollback(), lambda c:c.close(),
                   lambda c:c.execute('COMMIT'), lambda c:c.execute('ROLLBACK'),
                   lambda c:c.execute('BEGIN'), lambda c:c.execute('SAVEPOINT replacement'),
                   lambda c:c.executescript('SELECT 1;'), lambda c:c.set_authorizer(None),
                   lambda c:c.execute('PRAGMA writable_schema=ON'))
        before = self.snapshot()
        for index, action in enumerate(actions):
            with self.subTest(action=index), self.assertRaises(a.AdminError):
                with v.authentication_transaction(self.config) as context:
                    self.synthetic_primary(context)
                    data = v._contexts[context]
                    with self.assertRaises((a.AdminError, sqlite3.DatabaseError)):
                        action(data['control'])
                    with self.assertRaisesRegex(a.AdminError, 'runtime_context_invalid'):
                        v._context_data(context, data['control'], data['target'])
                    self.assert_target_locked()
            self.assertEqual(before, self.snapshot())

    def test_thread_identity_and_thread_object_both_required(self):
        with v.authentication_transaction(self.config) as context:
            data = v._contexts[context]
            self.assertIs(data, v._context_data(context, data['control'], data['target']))
            owner_ident = threading.get_ident()
            def foreign():
                with self.assertRaisesRegex(a.AdminError, 'runtime_context_invalid'):
                    v._context_data(context, data['control'], data['target'])
                # Even an OS/Python thread-ident reuse does not inherit ownership.
                state = v._states[context]
                state.ident = threading.get_ident()
                try:
                    with self.assertRaisesRegex(a.AdminError, 'runtime_context_invalid'):
                        v._context_data(context, data['control'], data['target'])
                finally:
                    state.ident = owner_ident
            with ThreadPoolExecutor(max_workers=1) as pool:
                pool.submit(foreign).result()
            self.assertIs(data, v._context_data(context, data['control'], data['target']))

    def test_cursor_and_views_expose_no_raw_handles_or_mutable_snapshot(self):
        with v.authentication_transaction(self.config) as context:
            data = v._contexts[context]
            cursor = data['control'].execute('SELECT 1')
            with self.assertRaises(AttributeError): cursor.connection
            with self.assertRaises(TypeError): data['control'] = None
            with self.assertRaises(TypeError): data['snapshot']['generation'] = 999
            self.assertEqual(1, cursor.fetchone()[0])
        with self.assertRaisesRegex(a.AdminError, 'runtime_context_invalid'):
            cursor.fetchone()

    def test_real_deny_throttle_commit_is_deferred_and_has_no_new_auth(self):
        from src.review.recognition import admin_auth
        with self.assertRaisesRegex(a.AdminError, 'invalid_or_replayed_totp'):
            with v.authentication_transaction(self.config) as context:
                conn = v._contexts[context]['control']
                with patch.object(admin_auth, '_cipher', side_effect=AssertionError('key read')):
                    # Exercise the real _deny write/commit/raise protocol without
                    # decrypting a seed or performing authentication issuance.
                    conn.execute('INSERT INTO recognition_admin_attempts VALUES(?,?,?)', (1,a.timestamp(f.at(900)),1))
                    admin_auth._deny(conn, 'invalid_or_replayed_totp', f.at(900), 1, 401)
        with a.connect(self.config.control) as conn:
            self.assertEqual((1,a.timestamp(f.at(900)),1), tuple(conn.execute('SELECT * FROM recognition_admin_attempts').fetchone()))
            self.assertEqual(0, conn.execute(f'SELECT count(*) FROM {r.AUTH}').fetchone()[0])
            self.assertEqual(0, conn.execute('SELECT count(*) FROM recognition_admin_primary WHERE revoked=0').fetchone()[0])
            self.assertEqual('administration_denied', load_audit(conn)['action'])

    def test_denial_never_commits_new_usable_authentication(self):
        from src.review.recognition import admin_auth
        before = self.snapshot()
        with self.assertRaises(a.AdminError):
            with v.authentication_transaction(self.config) as context:
                self.synthetic_primary(context)
                admin_auth._deny(v._contexts[context]['control'], 'primary_authentication_required', f.at(900), 1, 401)
        self.assertEqual(before, self.snapshot())
        with self.assertRaises(a.AdminError):
            with v.authentication_transaction(self.config) as context:
                try:
                    admin_auth._deny(v._contexts[context]['control'], 'primary_authentication_required', f.at(900), 1, 401)
                except a.AdminError:
                    self.synthetic_primary(context)
        self.assertEqual(before, self.snapshot())

    def test_denial_does_not_bypass_final_identity_validation(self):
        from src.review.recognition import admin_auth
        before = self.snapshot()
        changed = [False]
        with patch.object(a, 'target_identity', side_effect=lambda subject:
                          self.original_identity(subject) if changed[0] else self.runtime_identity(subject)):
            with self.assertRaisesRegex(a.AdminError, 'identity_mismatch'):
                with v.authentication_transaction(self.config) as context:
                    changed[0] = True
                    admin_auth._deny(v._contexts[context]['control'], 'primary_authentication_required', f.at(900), 1, 401)
        self.assertEqual(before, self.snapshot())

    def test_actual_migration_challenge_enrollment_validation_lifecycle(self):
        from src.review.recognition import runtime_enrollment as n, runtime_evidence as e
        from tests.test_recognition_runtime_challenges import RuntimeChallengeTests
        with patch.object(a, 'target_identity', side_effect=self.original_identity):
            fixture = RuntimeChallengeTests()  # Normal fixture runs the real v2 -> v3 migration.
            fixture.setUp()
            self.addCleanup(fixture.doCleanups)
            self.assertEqual(2, fixture.binding['generation'])
            issued = fixture.issue()
        record = e._collect(fixture.f.path, fixture.f.control,
            challenge_id=issued['challenge']['challenge_id'],
            challenge_sha256=issued['challenge']['challenge_sha256'], now=f.at(181))
        review = dict(format=n.REVIEW_FORMAT, observations=[record], selected_observation_sha256=record['observation_sha256'])
        options = {k:value for k,value in fixture.options.items() if k != 'now'}
        with patch.object(a, 'target_identity', side_effect=self.original_identity), patch.object(n, '_utc_now', return_value=f.at(182)):
            result = n.enroll_runtime_profile(fixture.f.config, canonical(review), issued['nonce'], **options,
                challenge_id=issued['challenge']['challenge_id'], challenge_sha256=issued['challenge']['challenge_sha256'],
                approved_review_sha256=digest(review), approved_observation_sha256=record['observation_sha256'],
                confirm_private_log_review=True, confirm_enroll_runtime_profile=True)
        self.assertEqual(3, result['generation'])
        self.assertEqual(3, v.validate_runtime_snapshot(fixture.f.config)['generation'])

    def test_concurrent_generation_mutation_serializes_and_invalidates_profile(self):
        from concurrent.futures import TimeoutError
        begun = threading.Event()
        def advance():
            with a.connect(self.config.control, write=True) as conn:
                begun.set()
                conn.execute('BEGIN IMMEDIATE')
                row = conn.execute('SELECT body_json FROM recognition_admin_bindings ORDER BY generation DESC LIMIT 1').fetchone()
                old = json.loads(row[0])
                # Synthetic next-generation record, not a recovery/enrollment API.
                body = dict(old, generation=old['generation']+1, previous_sha256=digest(old),
                            runtime_profile_sha256=None, at_utc=f.at(901))
                conn.execute('INSERT INTO recognition_admin_bindings VALUES(?,?,?)', (body['generation'],canonical(body),digest(body)))
                a._invalidate(conn)
                a._audit(conn, 'synthetic_generation_change', 1, f.at(901))
                conn.commit()
        with ThreadPoolExecutor(max_workers=1) as pool:
            with v.authentication_transaction(self.config):
                future = pool.submit(advance)
                self.assertTrue(begun.wait(2))
                with self.assertRaises(TimeoutError): future.result(timeout=0.05)
            future.result(timeout=5)
        with self.assertRaisesRegex(a.AdminError, 'runtime_profile_not_enrolled'):
            v.validate_runtime_snapshot(self.config)

    def test_concurrent_owner_epoch_mutation_waits_for_target_release(self):
        from concurrent.futures import TimeoutError
        begun = threading.Event()
        def mutate():
            with sqlite3.connect(self.config.target, timeout=5) as conn:
                begun.set()
                conn.execute(f'UPDATE {s.TARGET_TABLE} SET auth_epoch=auth_epoch+1')
        with ThreadPoolExecutor(max_workers=1) as pool:
            with v.authentication_transaction(self.config) as context:
                epoch = v._contexts[context]['snapshot']['auth_epoch']
                future = pool.submit(mutate)
                self.assertTrue(begun.wait(2))
                with self.assertRaises(TimeoutError): future.result(timeout=0.05)
            future.result(timeout=5)
        self.assertEqual(epoch+1, v.validate_runtime_snapshot(self.config)['auth_epoch'])

    def test_target_reservation_acquisition_failure_rolls_back_control(self):
        before = self.snapshot()
        with sqlite3.connect(self.config.target) as contender:
            contender.execute('BEGIN IMMEDIATE')
            with self.assertRaisesRegex(sqlite3.OperationalError, 'locked'):
                v.validate_runtime_snapshot(self.config)
            contender.rollback()
        self.assertEqual(before, self.snapshot())
        with sqlite3.connect(self.config.control, timeout=0) as conn:
            conn.execute('BEGIN IMMEDIATE'); conn.rollback()

    def test_target_release_failure_closes_connection_and_invalidates_context(self):
        connect = sqlite3.connect
        target_uri = self.config.target.as_uri()
        class FaultConnection(sqlite3.Connection):
            def rollback(conn):
                if conn.is_target and conn.in_transaction:
                    raise sqlite3.OperationalError('injected release failure')
                return super().rollback()
        def connected(path, **kwargs):
            conn = connect(path, factory=FaultConnection, **kwargs)
            conn.is_target = str(path).startswith(target_uri)
            return conn
        before = self.snapshot()
        with patch.object(a.sqlite3, 'connect', side_effect=connected), self.assertRaises(v.RuntimeCleanupError) as failure:
            with v.authentication_transaction(self.config) as context:
                data = v._contexts[context]
        self.assertTrue(failure.exception.control_committed)
        with self.assertRaisesRegex(a.AdminError, 'runtime_context_invalid'):
            v._context_data(context, data['control'], data['target'])
        with connect(self.config.target, timeout=0) as conn:
            conn.execute('BEGIN IMMEDIATE'); conn.rollback()
        self.assertEqual(before, self.snapshot())

    def test_coherent_digests_reach_historical_scope_and_time_checks(self):
        with a.connect(self.config.control) as conn:
            originals = {table:[dict(row) for row in conn.execute(f'SELECT * FROM {table}')]
                         for table in (r.PROFILES, 'recognition_admin_bindings', 'recognition_admin_audit')}
        for change, error in ((dict(nonce_sha256='0'*64), 'runtime_review_scope_mismatch'),
                              (dict(source_generation=8), 'runtime_review_scope_mismatch'),
                              (dict(observed_at=self.fixture.challenge['issued_at']-1), 'runtime_review_expired_or_future')):
            profile = dict(originals[r.PROFILES][0])
            audit_row = next(row for row in originals['recognition_admin_audit'] if row['sequence'] == profile['audit_sequence'])
            audit = json.loads(audit_row['body_json'])
            record = audit['subject']['review']['observations'][0]
            record['observation'].update(change)
            record['observation_sha256'] = digest(record['observation'])
            audit['subject']['review']['selected_observation_sha256'] = record['observation_sha256']
            profile.update(observation_sha256=record['observation_sha256'], observed_at=record['observation']['observed_at'])
            profile['profile_sha256'] = digest({k:value for k,value in profile.items() if k != 'profile_sha256'})
            binding_row = max(originals['recognition_admin_bindings'], key=lambda row:row['generation'])
            binding = json.loads(binding_row['body_json'])
            binding['runtime_profile_sha256'] = profile['profile_sha256']
            audit['subject'].update(profile_sha256=profile['profile_sha256'], observation_sha256=profile['observation_sha256'],
                review_sha256=digest(audit['subject']['review']), binding_sha256=digest(binding))
            with a.connect(self.config.control, write=True) as conn:
                definitions = {**s.definitions(), **r.definitions()}
                for table in originals:
                    conn.execute('DROP TRIGGER '+table+'_immutable_update')
                conn.execute(f"UPDATE {r.PROFILES} SET {','.join(k+'=?' for k in profile)}", tuple(profile.values()))
                conn.execute('UPDATE recognition_admin_bindings SET body_json=?,body_sha256=? WHERE generation=?',
                             (canonical(binding),digest(binding),binding['generation']))
                conn.execute('UPDATE recognition_admin_audit SET body_json=?,body_sha256=? WHERE sequence=?',
                             (canonical(audit),digest(audit),profile['audit_sequence']))
                for table in originals: conn.execute(definitions[table+'_immutable_update'])
                s.check_control(conn)  # Exact schema, profile digests and audit links are valid.
                a._audit_head(conn)
                conn.commit()
            with self.subTest(change=change), self.assertRaisesRegex(a.AdminError, error):
                v.validate_runtime_snapshot(self.config)
            with a.connect(self.config.control, write=True) as conn:
                for table, rows in originals.items():
                    conn.execute('DROP TRIGGER '+table+'_immutable_update')
                    for row in rows:
                        key = 'profile_sha256' if table == r.PROFILES else 'generation' if table == 'recognition_admin_bindings' else 'sequence'
                        # There is exactly one profile, whose primary key changed.
                        where, parameters = ('', ()) if table == r.PROFILES else (' WHERE '+key+'=?', (row[key],))
                        conn.execute(f"UPDATE {table} SET {','.join(k+'=?' for k in row)}"+where, tuple(row.values())+parameters)
                    conn.execute(definitions[table+'_immutable_update'])
                conn.commit()

    def test_actual_enrollment_serializes_runtime_validation(self):
        from src.review.recognition import runtime_enrollment as n, runtime_evidence as e
        from tests.test_recognition_runtime_challenges import RuntimeChallengeTests
        from concurrent.futures import TimeoutError
        with patch.object(a, 'target_identity', side_effect=self.original_identity):
            fixture = RuntimeChallengeTests()
            fixture.setUp()
            self.addCleanup(fixture.doCleanups)
            issued = fixture.issue()
        record = e._collect(fixture.f.path, fixture.f.control, challenge_id=issued['challenge']['challenge_id'],
                            challenge_sha256=issued['challenge']['challenge_sha256'], now=f.at(181))
        review = dict(format=n.REVIEW_FORMAT, observations=[record], selected_observation_sha256=record['observation_sha256'])
        options = {k:value for k,value in fixture.options.items() if k != 'now'}
        entered, proceed = threading.Event(), threading.Event()
        role = threading.local()
        original_audit = a._audit
        def audited(*args, **kwargs):
            original_audit(*args, **kwargs)
            if args[1] == 'runtime_profile_enrolled':
                entered.set()
                if not proceed.wait(5): raise RuntimeError('test synchronization timeout')
        def deploy():
            role.deployment = True
            return n.enroll_runtime_profile(fixture.f.config, canonical(review), issued['nonce'], **options,
                challenge_id=issued['challenge']['challenge_id'], challenge_sha256=issued['challenge']['challenge_sha256'],
                approved_review_sha256=digest(review), approved_observation_sha256=record['observation_sha256'],
                confirm_private_log_review=True, confirm_enroll_runtime_profile=True)
        with patch.object(a, 'target_identity', side_effect=lambda subject:
                          self.original_identity(subject) if getattr(role, 'deployment', False) else self.runtime_identity(subject)), \
             patch.object(a, '_audit', side_effect=audited), patch.object(n, '_utc_now', return_value=f.at(182)), \
             ThreadPoolExecutor(max_workers=2) as pool:
            enrolling = pool.submit(deploy)
            self.assertTrue(entered.wait(3))
            validating = pool.submit(v.validate_runtime_snapshot, fixture.f.config)
            try:
                with self.assertRaises(TimeoutError): validating.result(timeout=0.05)
            finally:
                proceed.set()
            self.assertEqual(3, enrolling.result(timeout=5)['generation'])
            self.assertEqual(3, validating.result(timeout=5)['generation'])

    def test_existing_rate_limit_denial_needs_no_key_and_preserves_status(self):
        from src.review.recognition import admin_auth
        with a.connect(self.config.control, write=True) as conn:
            conn.execute('INSERT INTO recognition_admin_attempts VALUES(?,?,?)', (1,a.timestamp(f.at(900)),5))
            conn.commit()
        with patch.object(admin_auth, '_cipher', side_effect=AssertionError('key read')), \
             self.assertRaisesRegex(a.AdminError, 'mfa_rate_limited') as failure:
            with v.authentication_transaction(self.config) as context:
                conn = v._contexts[context]['control']
                mfa = conn.execute('SELECT * FROM recognition_admin_mfa WHERE actor=1').fetchone()
                admin_auth._code(conn, self.config, dict(owner_id=1), mfa, '000000', f.at(900))
        self.assertEqual(429, failure.exception.status)
        with a.connect(self.config.control) as conn:
            self.assertEqual('mfa_rate_limited', load_audit(conn)['subject']['code'])
            self.assertEqual(0, conn.execute(f'SELECT count(*) FROM {r.AUTH}').fetchone()[0])

    def test_caught_denial_cannot_return_success(self):
        from src.review.recognition import admin_auth
        before = self.snapshot()
        with self.assertRaisesRegex(a.AdminError, 'runtime_context_invalid'):
            with v.authentication_transaction(self.config) as context:
                try:
                    admin_auth._deny(v._contexts[context]['control'], 'primary_authentication_required', f.at(900), 1, 401)
                except a.AdminError:
                    pass
        self.assertEqual(before, self.snapshot())

    def test_denial_persists_revocation_but_cannot_unrevoke_existing_auth(self):
        from src.review.recognition import admin_auth
        with v.authentication_transaction(self.config) as context:
            self.synthetic_primary(context)
        with self.assertRaisesRegex(a.AdminError, 'primary_authentication_required'):
            with v.authentication_transaction(self.config) as context:
                conn = v._contexts[context]['control']
                a._invalidate(conn)
                admin_auth._deny(conn, 'primary_authentication_required', f.at(900), 1, 401)
        with a.connect(self.config.control) as conn:
            self.assertEqual(1, conn.execute("SELECT revoked FROM recognition_admin_primary WHERE token_hash=?", ('c'*64,)).fetchone()[0])
        before = self.snapshot()
        with self.assertRaises(a.AdminError):
            with v.authentication_transaction(self.config) as context:
                conn = v._contexts[context]['control']
                conn.execute('UPDATE recognition_admin_primary SET revoked=0 WHERE token_hash=?', ('c'*64,))
                admin_auth._deny(conn, 'primary_authentication_required', f.at(900), 1, 401)
        self.assertEqual(before, self.snapshot())


def load_audit(conn):
    return json.loads(conn.execute('SELECT body_json FROM recognition_admin_audit ORDER BY sequence DESC LIMIT 1').fetchone()[0])


if __name__ == '__main__':
    unittest.main()
