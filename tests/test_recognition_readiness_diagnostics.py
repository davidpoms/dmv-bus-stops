"""Fixed private diagnostics only; original exceptions and durable state survive."""

import json
import sqlite3
import unittest
from unittest.mock import patch

from src.review.recognition import administration as a, readiness_diagnostics as diagnostics
from src.review.recognition import runtime_activation as owner, runtime_validation as runtime
from src.review.recognition import runtime_claim_disposition as disposition, local_readiness as readiness
from src.review.recognition.qualification import Quarantined
from src.review.recognition.trust import TrustError
from tests import test_recognition_runtime_readiness_dispatch as fixture


SECRET = '/private/secret-path challenge=secret-challenge nonce=secret-nonce seed=secret-seed'


class DiagnosticClassificationTests(unittest.TestCase):
    def record(self, error, stage='claim_inspection'):
        with patch.object(diagnostics._logger, 'warning') as log:
            with self.assertRaises(type(error)) as caught:
                with diagnostics.assessment(), diagnostics.stage(stage):
                    raise error
        self.assertIs(error, caught.exception)
        log.assert_called_once()
        self.assertNotIn(SECRET, repr(log.call_args))
        self.assertNotIn('exc_info', log.call_args.kwargs)
        self.assertEqual('RECOGNITION_READINESS_DIAGNOSTIC %s', log.call_args.args[0])
        return json.loads(log.call_args.args[1])

    def test_fixed_exception_classes_and_allowlisted_admin_codes(self):
        cases = [(TrustError(SECRET), 'trust_validation_failed'),
                 (Quarantined(SECRET), 'recognition_inventory_rejected'),
                 (sqlite3.DatabaseError(SECRET), 'database_access_failed'),
                 (OSError(SECRET), 'filesystem_access_failed'),
                 (ImportError(SECRET), 'dependency_import_failed'),
                 (ValueError(SECRET), 'validation_failed'),
                 (RuntimeError(SECRET), 'unclassified_readiness_failure'),
                 (a.AdminError(SECRET, 503), 'administration_denied')]
        cases.extend((a.AdminError(code, 503), classification)
                     for code, classification in diagnostics._ADMIN_CLASSES.items())
        for error, expected in cases:
            with self.subTest(expected=expected):
                record = self.record(error)
                self.assertEqual(expected, record['failure_class'])
                self.assertEqual('claim_inspection', record['stage'])
                self.assertEqual({'stage', 'failure_class', 'error', 'pid'}, set(record))

    def test_unknown_stage_cannot_leak_caller_values(self):
        self.assertEqual('readiness_request', self.record(ValueError(SECRET), SECRET)['stage'])

    def test_nested_scopes_log_innermost_stage_once_and_reset(self):
        with patch.object(diagnostics._logger, 'warning') as log:
            for _ in range(2):
                with self.assertRaises(ValueError):
                    with diagnostics.assessment(), diagnostics.stage('authentication'):
                        with diagnostics.assessment(), diagnostics.stage('history_validation'):
                            raise ValueError(SECRET)
            self.assertEqual(2, log.call_count)
            for call in log.call_args_list:
                self.assertEqual('history_validation', json.loads(call.args[1])['stage'])

    def test_sink_failure_preserves_original_exception(self):
        error = TrustError(SECRET)
        with patch.object(diagnostics._logger, 'warning', side_effect=RuntimeError('sink '+SECRET)):
            with self.assertRaises(TrustError) as caught:
                with diagnostics.assessment(), diagnostics.stage('history_validation'):
                    raise error
        self.assertIs(error, caught.exception)

    def test_inactive_or_successful_scope_does_not_log(self):
        with patch.object(diagnostics._logger, 'warning') as log:
            with self.assertRaises(ValueError):
                with diagnostics.stage('runtime_identity_validation'):
                    raise ValueError(SECRET)
            with diagnostics.assessment(), diagnostics.stage('history_validation'):
                pass
        log.assert_not_called()


class AdminFailureBoundaryTests(unittest.TestCase):
    def test_failed_application_log_sink_preserves_http_response(self):
        from flask import Flask
        from src.review.recognition import admin_routes
        app = Flask(__name__)
        app.config.update(TESTING=True, SECRET_KEY='disposable-admin-failure-test')
        admin_routes.register_admin_routes(app)
        client = app.test_client()
        with client.session_transaction() as browser:
            browser['auth_csrf'] = 'test-csrf'
        for broken_sink in (False, True):
            with patch.object(admin_routes, 'configuration', side_effect=OSError(SECRET)), \
                 patch.object(app.logger, 'error', side_effect=RuntimeError(SECRET) if broken_sink else None) as log:
                for method, path in (('post', 'runtime-foundation/preview'), ('get', 'runtime-activation/readiness')):
                    options = dict(json=dict(csrf_token='test-csrf', operator='fixture', reason='review')) if method == 'post' else {}
                    response = getattr(client, method)('/api/admin/recognition-control/'+path, **options)
                    self.assertEqual(503, response.status_code)
                    self.assertEqual(dict(error='administrative_control_unavailable', diagnostic=dict(
                        stage='configuration', failure_class='filesystem_access_failed')), response.get_json())
                self.assertEqual(2, log.call_count)
                self.assertNotIn(SECRET, repr(log.call_args_list))
                for call in log.call_args_list:
                    self.assertEqual(('RECOGNITION_ADMIN_FAILURE stage=%s failure_class=%s',
                                      'configuration', 'filesystem_access_failed'), call.args)
                    self.assertEqual({}, call.kwargs)


class RuntimeReadinessDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.f = fixture.RuntimeReadinessDispatchTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)

    def test_real_entry_classifies_each_stage_without_changing_state(self):
        cases = [(runtime, '_history', 'history_validation'),
                 (runtime, '_identity_snapshot', 'runtime_identity_validation'),
                 (disposition, '_inspect_reserved', 'claim_inspection'),
                 (owner, '_view', 'authentication'),
                 (readiness, '_assess_inventory', 'readiness_inventory')]
        before = self.f.snapshot()
        for module, function, expected in cases:
            error = TrustError(SECRET)
            with self.subTest(stage=expected), patch.object(module, function, side_effect=error), \
                 patch.object(diagnostics._logger, 'warning') as log:
                with self.assertRaises(TrustError) as caught:
                    owner.assess(self.f.config, self.f.session, primary_token=self.f.primary)
                self.assertIs(error, caught.exception)
                log.assert_called_once()
                record = json.loads(log.call_args.args[1])
                self.assertEqual(expected, record['stage'])
                self.assertEqual('trust_validation_failed', record['failure_class'])
                self.assertNotIn(SECRET, repr(log.call_args))
        self.assertEqual(before, self.f.snapshot())

    def test_successful_assessment_has_no_diagnostic_or_durable_changes(self):
        before = self.f.snapshot()
        with patch.object(diagnostics._logger, 'warning') as log:
            result = owner.assess(self.f.config, self.f.session, primary_token=self.f.primary)
        self.assertEqual('NOT_ACTIVATED', result['activation_state'])
        log.assert_not_called()
        self.assertEqual(before, self.f.snapshot())

    def test_http_generic_error_and_explicit_identity_error_unchanged(self):
        from flask import Flask
        from src.review.recognition import admin_routes
        app = Flask(__name__)
        app.config.update(TESTING=True, SECRET_KEY='disposable-diagnostic-test')
        admin_routes.register_admin_routes(app)
        client = app.test_client()
        with client.session_transaction() as browser:
            browser.update(authenticated_reviewer_id=1, reviewer_key='owner-key',
                           recognition_primary=self.f.primary, recognition_admin=self.f.session)
        before = self.f.snapshot()
        with patch.object(admin_routes, 'configuration', return_value=self.f.config):
            for sink_fails in (False, True):
                with self.subTest(sink_fails=sink_fails), \
                     patch.object(readiness, '_assess_inventory', side_effect=TrustError(SECRET)), \
                     patch.object(diagnostics._logger, 'warning', side_effect=RuntimeError(SECRET) if sink_fails else None) as log:
                    response = client.get('/api/admin/recognition-control/runtime-activation/readiness')
                    self.assertEqual(503, response.status_code)
                    self.assertEqual({'error': 'administrative_control_unavailable', 'diagnostic': dict(
                        stage='readiness_inventory', failure_class='trust_validation_failed')}, response.get_json())
                    self.assertNotIn(SECRET, repr(log.call_args))
                    self.assertEqual('readiness_inventory', json.loads(log.call_args.args[1])['stage'])
            with patch.object(runtime, '_identity_snapshot', side_effect=a.AdminError('runtime_profile_identity_mismatch', 503)), \
                 patch.object(diagnostics._logger, 'warning') as log:
                response = client.get('/api/admin/recognition-control/runtime-activation/readiness')
                self.assertEqual(503, response.status_code)
                self.assertEqual({'error': 'runtime_profile_identity_mismatch', 'diagnostic': dict(
                    stage='runtime_identity_validation', failure_class='runtime_profile_identity_mismatch')}, response.get_json())
                self.assertEqual('runtime_identity_validation', json.loads(log.call_args.args[1])['stage'])
            with patch.object(a.schema, 'check_control', side_effect=TrustError(SECRET)), \
                 patch.object(diagnostics._logger, 'warning') as log:
                response = client.get('/api/admin/recognition-control/runtime-activation/readiness')
                self.assertEqual({'error': 'administrative_control_unavailable', 'diagnostic': dict(
                    stage='history_validation', failure_class='trust_validation_failed')}, response.get_json())
                self.assertEqual(503, response.status_code)
                self.assertEqual('history_validation', json.loads(log.call_args.args[1])['stage'])
        self.assertEqual(before, self.f.snapshot())

    def test_both_owner_actions_report_shared_context_failures(self):
        from flask import Flask
        from src.review import admin_dashboard
        from src.review.recognition import admin_routes, runtime_target_schema_completion as completion
        app = Flask(__name__)
        app.config.update(TESTING=True, SECRET_KEY='disposable-shared-context-test')
        admin_routes.register_admin_routes(app)
        client = app.test_client()
        with client.session_transaction() as browser:
            browser.update(authenticated_reviewer_id=1, reviewer_key='owner-key', auth_csrf='test-csrf',
                           recognition_primary=self.f.primary, recognition_admin=self.f.session)
        before = self.f.snapshot()
        cases = [(admin_routes, 'configuration', OSError(SECRET), 'configuration', 'filesystem_access_failed'),
                 (a, 'connect', OSError(SECRET), 'owner_access', 'filesystem_access_failed'),
                 (admin_dashboard, 'owner_access', ValueError(SECRET), 'owner_access', 'validation_failed'),
                 (a.schema, 'check_control', ValueError(SECRET), 'history_validation', 'validation_failed'),
                 (admin_routes, 'authentication_backend', sqlite3.DatabaseError(SECRET), 'authentication', 'database_access_failed'),
                 (owner, 'get_admin_identity', ImportError(SECRET), 'authentication', 'dependency_import_failed'),
                 (owner, 'require_recognition_admin', ValueError(SECRET), 'authentication', 'validation_failed')]
        server_stages = dict(configuration='configuration', connect='target_access', owner_access='owner_access',
                             check_control='control_access', authentication_backend='authentication_backend',
                             get_admin_identity='get_admin_identity', require_recognition_admin='admin_session')
        def before_handler(*args):
            self.assertIsNotNone(diagnostics._scope.get())  # Emitted before Flask's handler, not after unwind.
        with patch.object(admin_routes, 'configuration', return_value=self.f.config):
            for module, name, error, stage, classification in cases:
                with self.subTest(stage=stage, operation=name), patch.object(module, name, side_effect=error), \
                     patch.object(completion, 'preview') as preview, patch.object(owner, 'assess') as assess, \
                     patch.object(diagnostics._logger, 'warning'), \
                     patch.object(app.logger, 'error', side_effect=before_handler) as server_log:
                    responses = [client.post('/api/admin/recognition-control/runtime-foundation/preview',
                        json=dict(csrf_token='test-csrf', operator='fixture', reason='review')),
                        client.get('/api/admin/recognition-control/runtime-activation/readiness')]
                    for response in responses:
                        self.assertEqual(503, response.status_code)
                        self.assertEqual(dict(error='administrative_control_unavailable', diagnostic=dict(
                            stage=stage, failure_class=classification)), response.get_json())
                        self.assertNotIn(SECRET, response.get_data(as_text=True))
                        self.assertEqual('no-store', response.headers['Cache-Control'])
                    preview.assert_not_called()
                    assess.assert_not_called()
                    self.assertIsNone(diagnostics._scope.get())
                    self.assertEqual(2, server_log.call_count)  # Exactly once per failing request.
                    for call in server_log.call_args_list:
                        self.assertEqual(('RECOGNITION_ADMIN_FAILURE stage=%s failure_class=%s',
                                          server_stages[name], classification), call.args)
                        self.assertEqual({}, call.kwargs)
                        self.assertNotIn(SECRET, repr(call))
                self.assertEqual(before, self.f.snapshot())

            for actor, key in ((None, 'owner-key'), (1, 'wrong-owner-key')):
                with client.session_transaction() as browser:
                    browser.update(authenticated_reviewer_id=actor, reviewer_key=key)
                with patch.object(app.logger, 'error') as server_log:
                    responses = [client.post('/api/admin/recognition-control/runtime-foundation/preview',
                        json=dict(csrf_token='test-csrf', operator='fixture', reason='review')),
                        client.get('/api/admin/recognition-control/runtime-activation/readiness')]
                    server_log.assert_not_called()  # AdminError denials are not infrastructure failures.
                for response in responses:
                    self.assertEqual(403, response.status_code)
                    self.assertEqual(dict(error='recognition_owner_required', diagnostic=dict(
                        stage='owner_access', failure_class='administration_denied')), response.get_json())
                self.assertEqual(before, self.f.snapshot())

    def test_generic_readiness_blocked_payload_unchanged(self):
        with patch.object(readiness, '_assess_inventory', side_effect=TrustError(SECRET)), \
             patch.object(diagnostics._logger, 'warning') as log:
            result = self.f.assess()
        self.assertEqual('BLOCKED', result['status'])
        self.assertEqual(['installation_schema_identity_or_administration_unavailable'], result['issues'])
        self.assertEqual('readiness_inventory', json.loads(log.call_args.args[1])['stage'])
