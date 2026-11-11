"""F2 harness tests only: no G+2 fixture or lifecycle imports."""

import json
import os
import signal
import sys
import unittest
from unittest.mock import patch

from tests.runtime_deadline_harness import MARKER, MAX_OUTPUT_BYTES, observe_consent, run_child


class ExternalHarnessTests(unittest.TestCase):
    def test_long_native_wait_is_not_used_for_deadline_or_cleanup(self):
        import subprocess
        with patch.object(subprocess.Popen,'wait',side_effect=AssertionError('long native wait forbidden')):
            result=run_child([sys.executable,'-B','-c','import time; time.sleep(30)'],
                             timeout=0.2,cleanup_timeout=1)
        self.assertEqual('subprocess_timeout',result['status'])
        self.assertTrue(result['termination_requested'])
        self.assertTrue(result['reaped']);self.assertTrue(result['cleanup_complete'])
        self.assertFalse(result['parent_bound_exceeded'])
    def test_child_exit_and_consent_failure_are_preserved(self):
        report = dict(failure=dict(exception_class='TrustError', error_code='authority_consent_expired'))
        script = 'import sys; print('+repr(MARKER+json.dumps(report))+', flush=True); sys.exit(7)'
        result = run_child([sys.executable, '-B', '-c', script], timeout=5)
        self.assertEqual('child_exited', result['status'])
        self.assertEqual(7, result['exit_code'])
        self.assertEqual([report], result['reports'])
        self.assertTrue(result['reaped'])
        self.assertTrue(result['cleanup_complete'])
        self.assertFalse(result['parent_bound_exceeded'])

    def test_parent_kills_and_reaps_blocking_child(self):
        script = 'import time; print('+repr(MARKER+'{"started":true}')+', flush=True); time.sleep(60)'
        result = run_child([sys.executable, '-B', '-c', script], timeout=1)
        self.assertEqual('subprocess_timeout', result['status'])
        self.assertNotEqual(0, result['exit_code'])
        self.assertEqual([dict(started=True)], result['reports'])
        self.assertTrue(result['reaped'])
        self.assertLess(result['elapsed_seconds'], 5)

    def _retained_output(self, *, block_direct_child):
        # A real descendant keeps both inherited output descriptors open. No
        # recognition fixture/module is involved. Cleanup kills only its own PID.
        script = ('import json,subprocess,sys,time; '
                  'p=subprocess.Popen([sys.executable,"-B","-c","import time; time.sleep(20)"],'
                  'stdout=sys.stdout,stderr=sys.stderr); '
                  'print('+repr(MARKER)+'+json.dumps({"descendant_pid":p.pid}),flush=True); '
                  + ('time.sleep(20)' if block_direct_child else 'sys.exit(0)'))
        result = run_child([sys.executable, '-B', '-c', script], timeout=0.75, cleanup_timeout=1)
        self.assertTrue(result['reports'], result)
        pid = result['reports'][0]['descendant_pid']
        if os.name == 'nt':
            import _winapi
            handle = _winapi.OpenProcess(0x00100000 | 1, False, pid)
            def cleanup():
                try:
                    if _winapi.WaitForSingleObject(handle, 0) == _winapi.WAIT_TIMEOUT:
                        _winapi.TerminateProcess(handle, 1)
                    self.assertEqual(_winapi.WAIT_OBJECT_0, _winapi.WaitForSingleObject(handle, 2000))
                finally:
                    _winapi.CloseHandle(handle)
            self.addCleanup(cleanup)
            self.assertEqual(_winapi.WAIT_TIMEOUT, _winapi.WaitForSingleObject(handle, 0))
        else:
            self.addCleanup(os.kill, pid, signal.SIGTERM)
            os.kill(pid, 0)
        # The descendant is demonstrably alive when the parent returns.
        self.assertTrue(result['reaped'])
        self.assertTrue(result['cleanup_complete'])
        self.assertFalse(result['parent_bound_exceeded'], result)
        self.assertLess(result['elapsed_seconds'], result['deadlines_seconds']['parent_return'])
        self.assertEqual('snapshot', result['output_status'])
        self.assertNotIn('communicate', result['timings'])
        self.assertLessEqual(result['timings']['reap_end'], result['deadlines_seconds']['reap'])
        print('R4_RETAINED_OUTPUT '+json.dumps(dict(case='timeout' if block_direct_child else 'normal_exit',
              **{key:result[key] for key in ('status','exit_code','reaped','elapsed_seconds',
                 'termination_requested','timings','deadlines_seconds','cleanup_budget_seconds')})))
        return result

    def test_direct_child_exit_does_not_wait_for_descendant_output(self):
        result = self._retained_output(block_direct_child=False)
        self.assertEqual('child_exited', result['status'])
        self.assertEqual(0, result['exit_code'])
        self.assertFalse(result['termination_requested'])

    def test_timeout_returns_with_live_descendant_output_handles(self):
        result = self._retained_output(block_direct_child=True)
        self.assertEqual('subprocess_timeout', result['status'])
        self.assertNotEqual(0, result['exit_code'])
        self.assertTrue(result['termination_requested'])
        self.assertIn('direct_child_exit_observed', result['timings'])

    def test_output_is_bounded_snapshot_and_preserves_available_report(self):
        script = ('import sys; sys.stdout.write("x"*'+str(MAX_OUTPUT_BYTES*2)+'); '
                  'print("\\n"+'+repr(MARKER+'{"available":true}')+',flush=True)')
        result = run_child([sys.executable, '-B', '-c', script], timeout=5)
        self.assertTrue(result['output_truncated'])
        self.assertEqual([dict(available=True)], result['reports'])
        self.assertEqual('snapshot', result['output_status'])
        self.assertFalse(result['parent_bound_exceeded'])

    def test_diagnostic_budgets_must_be_finite_positive_numbers(self):
        for value in (0, -1, True, float('inf'), float('nan')):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    run_child([], timeout=value)
                with self.assertRaises(ValueError):
                    run_child([], cleanup_timeout=value)

    def test_consent_observer_preserves_exception_and_excludes_secrets(self):
        class TrustError(ValueError):
            pass
        error = TrustError('authority_consent_expired')
        def fresh(state, artifact):
            raise error
        records = []
        observed = observe_consent(fresh, lambda: '2099-01-01T00:10:00Z', records)
        with self.assertRaises(TrustError) as caught:
            observed(object(), dict(issued_at_utc='2099-01-01T00:00:00Z',
                                    expires_at_utc='2099-01-01T00:10:00Z', token='SECRET'))
        self.assertIs(error, caught.exception)
        self.assertEqual('authority_consent_expired', records[0]['error_code'])
        self.assertEqual('TrustError', records[0]['exception_class'])
        self.assertEqual({'issued_at', 'expires_at', 'validation_start', 'validation_end',
                          'monotonic_elapsed_seconds', 'exception_class', 'error_code'}, set(records[0]))
        self.assertNotIn('SECRET', json.dumps(records))
