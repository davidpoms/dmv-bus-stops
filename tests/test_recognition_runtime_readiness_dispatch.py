"""Enrolled v3 readiness selects existing owner authentication, never legacy identity."""

from dataclasses import replace
import unittest
from unittest.mock import patch

from src.review.recognition import administration as a, authorization, local_readiness as readiness
from src.review.recognition import runtime_activation as owner, runtime_validation as runtime
from src.review.recognition import runtime_execution_claim_schema as claims
from src.review.recognition import production_operations
from src.review.recognition import approval_schema
from src.review.recognition.rules import canonical
from tests import test_recognition_deployment_claim_recovery as recovery_fixture
from tests import test_recognition_administration as base


class RuntimeReadinessDispatchTests(unittest.TestCase):
    def setUp(self):
        self.f = recovery_fixture.DeploymentClaimRecoveryTests()
        install = a.install
        def complete_target(config, **options):
            with a.connect(config.target, write=True) as target:
                target.execute('BEGIN IMMEDIATE')
                production_operations.install_target(target)
                target.commit()
            return install(config, **options)
        with patch.object(a, 'install', side_effect=complete_target):
            self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.config = self.f.config
        self.enterContext(patch.object(a, 'target_identity', side_effect=authorization.target_identity))
        # Existing additive readiness storage, fixture only. No production
        # install/migration API is changed to establish this test prerequisite.
        with a.connect(self.config.control, write=True) as control:
            control.execute('BEGIN IMMEDIATE')
            binding, _, _ = runtime._history(control)
            for sql in approval_schema.definitions().values():
                control.execute(sql)
            for sql in readiness.definitions().values():
                control.execute(sql)
            readiness._append(control, binding, 'NOT_ACTIVATED', 1, 'disposable genesis', runtime._utc_now())
            control.commit()
        claims.migrate(self.config, expected_generation=5, operator='fixture', reason='disposable schema')
        self.primary = owner.record_primary_authentication(self.config, actor_id=1, reviewer_key='owner-key')
        self.session = owner.open_admin_session(self.config, self.primary, base.independent_code(runtime._utc_now()))

    def assess(self, **changes):
        options = dict(now=runtime._utc_now(), session_token=self.session, primary_token=self.primary)
        options.update(changes)
        return readiness.assess(self.config, **options)

    def snapshot(self):
        values = []
        for path in (self.config.control, self.config.target):
            with a.connect(path) as connection:
                values.append('\n'.join(connection.iterdump()))
        return values

    def test_generation_five_profile_accepted_without_mutation_or_activation(self):
        before = self.snapshot()
        with patch.object(a, 'transaction', side_effect=AssertionError('legacy path invoked')):
            result = self.assess()
        self.assertEqual('recognition-local-readiness-v1', result.get('format'), result)
        self.assertEqual(5, result['target']['restore_generation'])
        self.assertEqual('NOT_ACTIVATED', result['activation_state'])
        self.assertNotIn('runtime_profile_contract_not_enabled', canonical(result))
        self.assertEqual('BLOCKED', result['production_execution'])
        self.assertEqual(before, self.snapshot())

    def test_missing_or_invalid_profile_never_falls_back(self):
        for issue in ('runtime_profile_not_enrolled', 'runtime_profile_enrollment_invalid'):
            with self.subTest(issue=issue), patch.object(runtime, '_history', side_effect=a.AdminError(issue, 503)), \
                 patch.object(a, 'transaction', side_effect=AssertionError('legacy fallback')):
                result = self.assess()
            self.assertEqual('BLOCKED', result['status'])
            self.assertEqual([issue], result['issues'])

    def test_missing_or_invalid_runtime_session_rejected_without_mutation(self):
        before = self.snapshot()
        for changes in (dict(session_token=None), dict(primary_token=None), dict(session_token='not-a-session'),
                        dict(primary_token='not-a-primary')):
            with self.subTest(changes=changes):
                self.assertFalse(self.assess(**changes)['activation_ready'])
        self.assertEqual(before, self.snapshot())

    def test_runtime_identity_device_hostname_and_inode_still_enforced(self):
        before = self.snapshot()
        for field in ('device', 'inode', 'hostname'):
            def changed(subject):
                actual = authorization.target_identity(subject)
                return replace(actual, **{field: getattr(actual, field)+1 if field != 'hostname' else 'other-worker'})
            with self.subTest(field=field), patch.object(a, 'target_identity', side_effect=changed):
                result = self.assess()
                self.assertEqual('BLOCKED', result['status'])
                self.assertIn('runtime_profile_identity_mismatch', result['issues'])
        self.assertEqual(before, self.snapshot())

    def test_provider_selection_still_rejected(self):
        self.assertEqual(['external_or_test_provider_not_permitted'], self.assess(selected_provider=object())['issues'])

    def test_missing_durable_profile_rejected_without_legacy_fallback(self):
        from src.review.recognition import runtime_profile_schema as profiles
        with a.connect(self.config.control, write=True) as control:
            # Corrupt only this disposable fixture; production profile records
            # remain immutable and have no repair path in this patch.
            control.execute('PRAGMA foreign_keys=OFF')
            name = profiles.PROFILES+'_immutable_delete'
            sql = control.execute('SELECT sql FROM sqlite_master WHERE name=?', (name,)).fetchone()[0]
            control.execute('DROP TRIGGER '+name)
            control.execute('DELETE FROM '+profiles.PROFILES)
            control.execute(sql)
            control.commit()
        with patch.object(a, 'transaction', side_effect=AssertionError('legacy fallback')):
            result = self.assess()
        self.assertEqual('BLOCKED', result['status'])
        self.assertNotIn('runtime_profile_contract_not_enabled', canonical(result))

    def test_generic_http_readiness_uses_existing_runtime_session(self):
        from flask import Flask
        from src.review.recognition import admin_routes
        app = Flask(__name__)
        app.config.update(TESTING=True, SECRET_KEY='disposable-readiness-test')
        admin_routes.register_admin_routes(app)
        client = app.test_client()
        with client.session_transaction() as browser:
            browser.update(authenticated_reviewer_id=1, reviewer_key='owner-key',
                           recognition_primary=self.primary, recognition_admin=self.session)
        before = self.snapshot()
        with patch.object(admin_routes, 'configuration', return_value=self.config):
            response = client.get('/api/admin/recognition-control/readiness')
        self.assertEqual(200, response.status_code, response.get_json())
        self.assertEqual(5, response.get_json()['target']['restore_generation'])
        self.assertEqual('NOT_ACTIVATED', response.get_json()['activation_state'])
        self.assertEqual(before, self.snapshot())
