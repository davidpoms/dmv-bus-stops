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
                 (ValueError(SECRET), 'unclassified_readiness_failure'),
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
                    self.assertEqual({'error': 'administrative_control_unavailable'}, response.get_json())
                    self.assertNotIn(SECRET, repr(log.call_args))
                    self.assertEqual('readiness_inventory', json.loads(log.call_args.args[1])['stage'])
            with patch.object(runtime, '_identity_snapshot', side_effect=a.AdminError('runtime_profile_identity_mismatch', 503)), \
                 patch.object(diagnostics._logger, 'warning') as log:
                response = client.get('/api/admin/recognition-control/runtime-activation/readiness')
                self.assertEqual(503, response.status_code)
                self.assertEqual({'error': 'runtime_profile_identity_mismatch'}, response.get_json())
                self.assertEqual('runtime_identity_validation', json.loads(log.call_args.args[1])['stage'])
            with patch.object(a.schema, 'check_control', side_effect=TrustError(SECRET)), \
                 patch.object(diagnostics._logger, 'warning') as log:
                response = client.get('/api/admin/recognition-control/runtime-activation/readiness')
                self.assertEqual({'error': 'administrative_control_unavailable'}, response.get_json())
                self.assertEqual(503, response.status_code)
                self.assertEqual('history_validation', json.loads(log.call_args.args[1])['stage'])
        self.assertEqual(before, self.f.snapshot())

    def test_generic_readiness_blocked_payload_unchanged(self):
        with patch.object(readiness, '_assess_inventory', side_effect=TrustError(SECRET)), \
             patch.object(diagnostics._logger, 'warning') as log:
            result = self.f.assess()
        self.assertEqual('BLOCKED', result['status'])
        self.assertEqual(['installation_schema_identity_or_administration_unavailable'], result['issues'])
        self.assertEqual('readiness_inventory', json.loads(log.call_args.args[1])['stage'])
