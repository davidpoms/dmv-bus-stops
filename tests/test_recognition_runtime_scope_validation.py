"""4b-0 real enrolled/authenticated lifecycle, no proposal writer."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import sqlite3
from types import MappingProxyType
import unittest
from unittest.mock import patch

from src.review.recognition import administration as a, administration_schema as schema
from src.review.recognition import runtime_scope_validation as s, runtime_validation as v
from src.review.recognition import runtime_operation_contract as contract
from src.review.recognition import runtime_profile_schema as profiles
from src.review.recognition import trust
from tests import test_recognition_runtime_authentication as lifecycle
from tests import test_recognition_administration as f
from tests import test_recognition_runtime_validation as validation


class RuntimeScopeTests(unittest.TestCase):
    def setUp(self):
        self.fixture = lifecycle.RuntimeAuthenticationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.config = self.fixture.config
        self.primary = self.fixture.primary()
        self.session = self.fixture.session(self.primary)

    def snapshot(self):
        return self.config.control.read_bytes(), self.config.target.read_bytes()

    def test_real_lifecycle_read_validation_no_writes_or_key_reads(self):
        before = self.snapshot()
        with patch('pathlib.Path.read_bytes', side_effect=AssertionError('no key reads')):
            with v.authentication_transaction(self.config) as context:
                view = s.read_view(context)
                self.assertEqual(3, view.snapshot()['generation'])
                self.assertEqual({'actor_id': 1, 'generation': 3},
                    view.validate_session(self.session, primary_token=self.primary))
                self.assertEqual(contract.build_target(context), contract.build_target(view))
                self.assertIsInstance(view.snapshot(), MappingProxyType)
        # Includes all authentication, operation/approval/execution and audit
        # records, not a hand-picked set of empty tables.
        self.assertEqual(before, self.snapshot())
        with self.assertRaises(a.AdminError):
            view.snapshot()
        with self.assertRaisesRegex(a.AdminError, 'runtime_profile_contract_not_enabled'):
            a.get_installation_control(self.config)

    def test_no_sql_cursor_handle_or_transaction_api(self):
        with v.authentication_transaction(self.config) as context:
            view = s.read_view(context)
            for name in ('control', 'target', 'connection', 'cursor', 'execute', 'executemany',
                         'executescript', 'commit', 'rollback', 'close', 'set_authorizer',
                         'set_trace_callback', 'create_function'):
                with self.subTest(name=name), self.assertRaises(AttributeError):
                    getattr(view, name)
            with self.assertRaises(TypeError):
                view.snapshot()['generation'] = 99
            with self.assertRaises(TypeError):
                s.RuntimeReadView()

    def test_detached_and_forged_objects_rejected(self):
        with v.authentication_transaction(self.config) as context:
            view = s.read_view(context)
            for fake in (dict(view.snapshot()), {}, object(),
                         object.__new__(v.RuntimeValidationContext), object.__new__(s.RuntimeReadView)):
                with self.subTest(fake=type(fake)), self.assertRaises(a.AdminError):
                    s.read_view(fake)
            for key in ('profile_sha256', 'generation', 'installation_id', 'target_id', 'owner_id'):
                forged = dict(view.snapshot())
                forged[key] = 'forged'
                with self.subTest(key=key), self.assertRaises(a.AdminError):
                    s._contract_parts(forged)
            with self.assertRaises(a.AdminError):
                view.validate_session({'actor': 1}, primary_token={'actor': 1})

    def test_pid_thread_and_process_restart_context_reuse(self):
        with v.authentication_transaction(self.config) as context:
            view = s.read_view(context)
            with patch.object(v.os, 'getpid', return_value=-1):
                with self.assertRaises(a.AdminError):
                    view.snapshot()
            with ThreadPoolExecutor(max_workers=1) as pool:
                with self.assertRaises(a.AdminError):
                    pool.submit(view.snapshot).result()
            self.assertEqual(3, view.snapshot()['generation'])
        with v.authentication_transaction(self.config):
            with self.assertRaises(a.AdminError):
                view.snapshot()

    def test_connection_substitution_rejected(self):
        with v.authentication_transaction(self.config) as context:
            data = v._contexts[context]
            with a.connect(self.config.target) as other:
                with self.assertRaises(a.AdminError):
                    v._context_data(context, data['control'], other)
            view = s.read_view(context)
            with self.assertRaises(a.AdminError):
                s._parts(view)  # A read view cannot become an auth-issuance context.

    def test_query_only_and_guarded_facades_unchanged(self):
        for which in ('control', 'target'):
            for sql in ('COMMIT', 'ROLLBACK', 'BEGIN IMMEDIATE', 'SAVEPOINT replacement',
                        'PRAGMA query_only=OFF'):
                with self.subTest(which=which, sql=sql):
                    with self.assertRaises(a.AdminError):
                        with v.authentication_transaction(self.config) as context:
                            view = s.read_view(context)
                            conn = v._contexts[context][which]
                            with self.assertRaises(sqlite3.DatabaseError):
                                conn.execute(sql)
                            view.snapshot()
        with v.authentication_transaction(self.config) as context:
            view = s.read_view(context)
            target = v._contexts[context]['target']
            self.assertEqual(1, target.execute('PRAGMA query_only').fetchone()[0])
            for sql in ('CREATE TABLE forbidden(value)',
                        f'UPDATE {schema.TARGET_TABLE} SET auth_epoch=auth_epoch'):
                with self.subTest(sql=sql), self.assertRaises(sqlite3.DatabaseError):
                    target.execute(sql)
            cursor = target.execute('SELECT 1')
            with self.assertRaises(AttributeError):
                cursor.connection
            self.assertEqual(3, view.snapshot()['generation'])

    def test_actual_runtime_identity_rechecked(self):
        with v.authentication_transaction(self.config) as context:
            view = s.read_view(context)
            for field, value in (('hostname', 'wrong'), ('device', 999), ('inode', 999),
                                 ('database', str(self.config.target.parent / 'wrong.db'))):
                with self.subTest(field=field), patch.object(a, 'target_identity',
                    side_effect=lambda obj: replace(self.fixture.runtime_identity(obj), **{field: value})):
                    with self.assertRaises(a.AdminError):
                        view.snapshot()

    def test_mfa_epoch_change_rejected(self):
        with v.authentication_transaction(self.config) as context:
            view = s.read_view(context)
            control = v._contexts[context]['control']
            control.execute('UPDATE recognition_admin_mfa SET epoch=epoch+1')
            with self.assertRaises(a.AdminError):
                view.snapshot()
            control.execute('UPDATE recognition_admin_mfa SET epoch=epoch-1')

    def test_expiry_and_revocation_use_existing_validator(self):
        self.fixture.clock.return_value = f.at(100000)
        with self.assertRaises(a.AdminError):
            with v.authentication_transaction(self.config) as context:
                s.read_view(context).validate_session(self.session, primary_token=self.primary)

    def test_revoked_session_rejected(self):
        self.fixture.sql('UPDATE recognition_admin_sessions SET revoked=1')
        with self.assertRaises(a.AdminError):
            with v.authentication_transaction(self.config) as context:
                s.read_view(context).validate_session(self.session, primary_token=self.primary)

    def test_parent_primary_and_runtime_auth_binding_rejected(self):
        other = self.fixture.primary()
        with self.assertRaises(a.AdminError):
            with v.authentication_transaction(self.config) as context:
                s.read_view(context).validate_session(self.session, primary_token=other)

    def test_missing_runtime_auth_binding_rejected(self):
        self.fixture.sql('DROP TRIGGER ' + profiles.AUTH + '_immutable_delete')
        self.fixture.sql(f"DELETE FROM {profiles.AUTH} WHERE token_kind='session'")
        self.fixture.sql(profiles.definitions()[profiles.AUTH + '_immutable_delete'])
        with self.assertRaisesRegex(a.AdminError, 'runtime_authentication_scope_required'):
            with v.authentication_transaction(self.config) as context:
                s.read_view(context).validate_session(self.session, primary_token=self.primary)

    def test_changed_owner_rejected(self):
        self.fixture.sql('UPDATE recognition_local_installation SET owner_id=2', target=True)
        with self.assertRaises(a.AdminError):
            with v.authentication_transaction(self.config) as context:
                s.read_view(context)

    def test_changed_auth_epoch_rejected(self):
        self.fixture.sql('UPDATE recognition_local_installation SET auth_epoch=auth_epoch+1', target=True)
        with self.assertRaises(a.AdminError):
            with v.authentication_transaction(self.config) as context:
                s.read_view(context).validate_session(self.session, primary_token=self.primary)

    def test_changed_mfa_epoch_invalidates_session(self):
        self.fixture.sql('UPDATE recognition_admin_mfa SET epoch=epoch+1')
        with self.assertRaises(a.AdminError):
            with v.authentication_transaction(self.config) as context:
                s.read_view(context).validate_session(self.session, primary_token=self.primary)

    def test_changed_schema_rejected(self):
        self.fixture.sql('CREATE TABLE changed_schema(value)', target=True)
        with self.assertRaises(a.AdminError):
            with v.authentication_transaction(self.config) as context:
                s.read_view(context)

    def test_stale_durable_generation_rejected(self):
        # Recompute the row digest: failure must not rely on an old body hash.
        validation.RuntimeValidationTests.update_body(self, 'recognition_admin_bindings',
            'generation', 3, lambda body: body.update(generation=4))
        with self.assertRaisesRegex(trust.TrustError, 'runtime_profile_control_binding_mismatch'):
            with v.authentication_transaction(self.config) as context:
                s.read_view(context)

    def test_stale_durable_profile_rejected(self):
        self.fixture.sql('DROP TRIGGER ' + profiles.PROFILES + '_immutable_update')
        self.fixture.sql(f"UPDATE {profiles.PROFILES} SET hostname='different-worker'")
        self.fixture.sql(profiles.definitions()[profiles.PROFILES + '_immutable_update'])
        with self.assertRaisesRegex(trust.TrustError, 'runtime_profile_digest_mismatch'):
            with v.authentication_transaction(self.config) as context:
                s.read_view(context)


if __name__ == '__main__':
    unittest.main()
