"""Z12: one disposable lifecycle, live product clock, bounded test-only tracing."""

from contextlib import ExitStack, contextmanager
from functools import wraps
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from uuid import uuid4

from tests import test_recognition_runtime_coordinator_final_validation_profile as fixture
from tests import test_recognition_runtime_target_entry_owner as z
from src.review.recognition import runtime_activation_authority_issuance as issuer


class _Deadline(BaseException):
    pass


class WatchdogConsentBoundaryDiagnostics(unittest.TestCase):
    """F1 only: no fixture, coordinator entry, preparation hook or issuance."""

    def test_watchdog_scheduling_and_external_process_bound(self):
        import subprocess
        child = r'''
import ctypes, json, threading, time
ready = threading.Event()
done = threading.Event()
records = []
def watchdog():
    start = time.monotonic()
    ready.set()
    signaled = done.wait(0.1)
    records.append(dict(timeout_seconds=0.1, elapsed_seconds=time.monotonic()-start, signaled=signaled))
thread = threading.Thread(target=watchdog)
thread.start()
ready.wait()
sleep = ctypes.PyDLL('kernel32').Sleep
sleep.argtypes = [ctypes.c_uint32]
sleep.restype = None
sleep(800)  # Test-only native call deliberately retaining the child GIL.
done.set()
thread.join()
print(json.dumps(records), flush=True)
'''
        options = dict(capture_output=True, text=True,
                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        completed = subprocess.run([sys.executable, '-B', '-c', child], timeout=5, **options)
        self.assertEqual(0, completed.returncode, completed.stderr)
        records = json.loads(completed.stdout)
        self.assertEqual(1, len(records))
        self.assertGreaterEqual(records[0]['elapsed_seconds'], 0.5)
        print('F1_THREAD_WATCHDOG '+json.dumps(records))
        started = time.monotonic()
        with self.assertRaises(subprocess.TimeoutExpired):
            subprocess.run([sys.executable, '-B', '-c',
                            "import ctypes; ctypes.PyDLL('kernel32').Sleep(5000)"],
                           timeout=1, **options)
        elapsed = time.monotonic()-started
        self.assertLess(elapsed, 5)
        print('F1_EXTERNAL_BOUND '+json.dumps(dict(timeout_seconds=1, elapsed_seconds=elapsed,
                                                 child_killed_and_waited=True)))

    def test_exact_consent_expiry_boundary_without_issuance(self):
        from datetime import timedelta
        from types import SimpleNamespace
        from src.review.recognition import runtime_authority_consent as consent, admin_auth
        from src.review.recognition import runtime_execution_claims as claims
        from src.review.recognition import runtime_issuance_schema_inventory as preparation
        from src.review.recognition.trust import TrustError, utc
        issued = '2099-01-01T00:00:00Z'
        self.assertEqual(600, admin_auth.RECENT_SECONDS)
        expires = utc(issued)+timedelta(seconds=admin_auth.RECENT_SECONDS)
        text = lambda moment: moment.strftime('%Y-%m-%dT%H:%M:%SZ')
        # A minimal predicate unit test, not a validated consent artifact/owner.
        # It deliberately cannot be used to enter any real issuance transaction.
        state = SimpleNamespace(subject={}, snapshot=dict(owner_id=1), primary='synthetic-primary-token-for-f1',
                                session='synthetic-session-token-for-f1', auth_expiries=[])
        artifact = dict(subject={}, subject_sha256=z.digest({}), actor_id=1,
                        primary_sha256=z.a.token_hash(state.primary), session_sha256=z.a.token_hash(state.session),
                        issued_at_utc=issued, expires_at_utc=text(expires))
        observations = []
        with ExitStack() as fences:
            mocks = [fences.enter_context(patch.object(module, name, side_effect=AssertionError('F1 boundary crossed')))
                     for module, name in ((issuer, 'issue'), (issuer, '_issue_for_coordinator'), (issuer, '_persist'),
                                          (z.coordinator, 'coordinator'), (z.metadata, 'create_target_entry'),
                                          (preparation, '_mint'))]
            with patch.object(z.v, '_utc_now', return_value=text(expires-timedelta(seconds=1))) as clock:
                state.clock = claims._Clock()
                state.started_at = z.a.timestamp(issued)
                consent._fresh(state, artifact)
                observations.append(dict(age_seconds=599, remaining_seconds=1, result='accepted by expiry predicate'))
                for overrun in (0, 1):
                    clock.return_value = text(expires+timedelta(seconds=overrun))
                    with self.assertRaises(TrustError) as failure:
                        consent._fresh(state, artifact)
                    self.assertEqual('authority_consent_expired', str(failure.exception))
                    observations.append(dict(age_seconds=600+overrun, remaining_seconds=-overrun,
                                             exception_class=type(failure.exception).__name__,
                                             error_code=str(failure.exception)))
            for mock in mocks:
                mock.assert_not_called()
        print('F1_CONSENT_BOUNDARY '+json.dumps(observations))


class LifecycleDeadlineTraceTests(unittest.TestCase):
    def setUp(self):
        # F6: 0700 denies this Windows test process access; 0777 works.
        # Intercept disposable workspace and unprefixed preview allocation in Z12.
        # TemporaryDirectory retains ownership/finalization; no existing ACL changes.
        root = Path(__file__).resolve().parents[1]
        self.disposable_allocations = []
        original_mkdtemp = tempfile.mkdtemp
        def workspace_directory(suffix=None, prefix=None, dir=None):
            if prefix not in (None, 'recognition-disposable-') or dir is not None:
                return original_mkdtemp(suffix=suffix, prefix=prefix, dir=dir)
            path = root / ((prefix or 'z12-preview-') + uuid4().hex + (suffix or ''))
            os.mkdir(path, 0o777)  # Creation only; no chmod/ACL repair or retry.
            self.disposable_allocations.append(path)
            return str(path)
        location = patch.object(tempfile, 'mkdtemp', workspace_directory)
        location.start()
        self.addCleanup(location.stop)

    def test_fixture_sqlite_setup_only(self):
        """Isolate the shared fixture's first SQLite setup; never enter runtime."""
        from tests.test_recognition_geography import GeographyReportTests
        output = Path(__file__).resolve().parents[1] / '.tmp' / 'recognition-z12-fixture-error.json'
        output.parent.mkdir(exist_ok=True)
        records = []
        operation = {}
        original_connect = sqlite3.connect

        def connect(database, *args, **kwargs):
            # Only the freshly allocated DisposableWorkspace is used by setup.
            record = dict(database=os.fspath(database), uri=kwargs.get('uri', False),
                          operation='sqlite3.connect', phase='open')
            records.append(record)
            operation.clear()
            operation.update(record)
            connection = original_connect(database, *args, **kwargs)
            identities[id(connection)] = record
            return connection

        identities = {}
        previous = sys.getprofile()
        def profile(frame, event, method):
            if event != 'c_call':
                return
            connection = getattr(method, '__self__', None)
            if isinstance(connection, sqlite3.Connection) and id(connection) in identities:
                name = getattr(method, '__name__', '')
                if name in ('execute', 'executescript', 'executemany', 'commit', 'rollback', 'close'):
                    operation.clear()
                    operation.update(identities[id(connection)], operation='Connection.'+name,
                                     phase='cleanup' if name=='close' else 'SQL/transaction',
                                     source=frame.f_code.co_filename, line=frame.f_lineno)

        case = GeographyReportTests()
        self.addCleanup(case.doCleanups)
        try:
            with patch.object(sqlite3, 'connect', connect):
                sys.setprofile(profile)
                try:
                    case.setUp()
                    probe = case.path.parent / 'z12-f3-file-access.txt'
                    operation.clear()
                    operation.update(operation='ordinary file exclusive create/write/read/delete',
                                     database=str(probe), phase='filesystem probe')
                    with probe.open('xb') as handle:
                        handle.write(b'z12-f3 disposable probe')
                    self.assertEqual(b'z12-f3 disposable probe', probe.read_bytes())
                    probe.unlink()
                    self.assertFalse(probe.exists())
                    directory = case.path.parent
                    operation.clear()
                    operation.update(operation='shared fixture cleanup', database=str(directory), phase='cleanup')
                    case.doCleanups()
                    self.assertFalse(directory.exists(), 'disposable workspace cleanup incomplete')
                finally:
                    sys.setprofile(previous)
        except (sqlite3.Error, OSError) as error:
            # This setup contains synthetic schema only; no tokens or credentials.
            import traceback
            report = dict(status='setup failed', exception=type(error).__name__,
                          message=str(error), sqlite_errorcode=getattr(error, 'sqlite_errorcode', None),
                          sqlite_errorname=getattr(error, 'sqlite_errorname', None),
                          errno=getattr(error, 'errno', None),
                          operation=operation, connections=records,
                          frames=[dict(file=f.filename, line=f.lineno, function=f.name)
                                  for f in traceback.extract_tb(error.__traceback__)])
            output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
            self.fail(json.dumps(report))
        else:
            output.write_text(json.dumps(dict(status='initial shared SQLite setup and ordinary file probe succeeded',
                                             connections=records), indent=2)+'\n', encoding='utf-8')

    def test_g2_preparation_permission_only(self):
        """F8: real preparation only; capture the first denied operation, not locals."""
        import traceback
        output = Path(__file__).resolve().parents[1] / '.tmp' / 'recognition-z12-preparation-permission.json'
        output.parent.mkdir(exist_ok=True)
        first = []
        previous = sys.gettrace()
        started = time.monotonic()
        done = threading.Event()

        def trace(frame, event, argument):
            if event == 'exception' and not first:
                _, error, _ = argument
                if isinstance(error, PermissionError):
                    first.append(dict(exception=type(error).__name__, message=str(error),
                                      errno=error.errno, winerror=getattr(error, 'winerror', None),
                                      path=error.filename, destination=getattr(error, 'filename2', None),
                                      function=frame.f_code.co_name, source=frame.f_code.co_filename,
                                      line=frame.f_lineno))
            return trace

        def watchdog():
            if not done.wait(240):
                output.write_text(json.dumps(dict(status='preparation external bound', first_permission_error=first)), encoding='utf-8')
                os._exit(124)

        threading.Thread(target=watchdog, daemon=True).start()
        report = dict(status='preparation not completed')
        class PreviewComplete(BaseException):
            pass
        original_preview = z.transition._preview
        def checked_preview(target):
            before = len(self.disposable_allocations)
            original_preview(target)
            allocated = self.disposable_allocations[before:]
            self.assertEqual(1, len(allocated))
            for path in allocated:
                self.assertEqual(Path(__file__).resolve().parents[1], path.parent)
                self.assertTrue(path.name.startswith('z12-preview-'))
                self.assertFalse(path.exists(), 'preview cleanup incomplete')
            report.update(status='preview completed and cleaned; stopped before further preparation',
                          preview_directories=[str(path) for path in allocated])
            raise PreviewComplete()
        try:
            with ExitStack() as fences:
                fences.enter_context(patch.object(z.transition, '_preview', checked_preview))
                for module, name in ((issuer, 'issue'), (issuer, '_issue_for_coordinator'),
                                     (z.coordinator, 'coordinator'), (z.metadata, 'create_target_entry')):
                    fences.enter_context(patch.object(module, name, side_effect=AssertionError('F8 preparation boundary crossed')))
                sys.settrace(trace)
                try:
                    fixture.CoordinatorFinalValidationProfileTests.prepare_g2(self)
                finally:
                    sys.settrace(previous)
            report['status'] = 'preparation succeeded; stopped before authority/coordinator'
        except PreviewComplete:
            pass
        except PermissionError as error:
            report.update(status='PermissionError isolated', exception=type(error).__name__,
                          message=str(error), errno=error.errno, winerror=getattr(error, 'winerror', None),
                          path=error.filename, destination=getattr(error, 'filename2', None),
                          frames=[dict(file=f.filename, line=f.lineno, function=f.name)
                                  for f in traceback.extract_tb(error.__traceback__)])
        finally:
            sys.settrace(previous)
            report.update(first_permission_error=first, elapsed_seconds=time.monotonic()-started)
            output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
            done.set()
        print('Z12_F8 '+json.dumps(report))
        self.assertEqual('preview completed and cleaned; stopped before further preparation', report['status'])

    def test_one_g2_v2_lifecycle(self):
        """R12 only: same original owner, isolated policy selection, fresh checks."""
        self._r12_v2 = True
        self.test_one_g2_lifecycle()

    def test_one_g2_lifecycle(self):
        from tests.runtime_deadline_harness import MARKER, observe_consent, run_child
        v2 = getattr(self, '_r12_v2', False)
        if os.environ.get('RECOGNITION_Z18_DIAGNOSTIC_CHILD') != '1':
            environment = dict(os.environ, RECOGNITION_Z18_DIAGNOSTIC_CHILD='1')
            node = 'test_one_g2_v2_lifecycle' if v2 else 'test_one_g2_lifecycle'
            result = run_child([sys.executable, '-B', '-m', 'pytest',
                                __file__+'::LifecycleDeadlineTraceTests::'+node,
                                '-q', '-s', '-p', 'no:cacheprovider'], env=environment,
                               **(dict(timeout=540) if v2 else {}))
            print(('R12_PARENT_REPORT ' if v2 else 'Z18_PARENT_REPORT ')+json.dumps(result))
            if v2:
                path = Path(__file__).resolve().parents[1] / '.tmp' / 'recognition-r12-parent.json'
                path.parent.mkdir(exist_ok=True)
                path.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
            self.assertFalse(result['parent_bound_exceeded'],
                             'external parent deadline exceeded; invalid bounded measurement')
            self.assertTrue(result['reaped'] and result['cleanup_complete'],
                            'diagnostic direct child cleanup incomplete')
            self.assertEqual('snapshot', result['output_status'],
                             'bounded diagnostic output unavailable or collection deadline reached')
            self.assertEqual('child_exited', result['status'],
                             'external diagnostic timeout; not lifecycle/authority expiry')
            self.assertEqual(0, result['exit_code'], 'child failure; inspect structured child report')
            self.assertTrue(result['reports'], 'child exited without a diagnostic report')
            return
        from src.review.recognition import runtime_issuance_schema_inventory as preparation
        from src.review.recognition import runtime_authority_consent as consent
        from src.review.recognition import runtime_authority_lifetime_policy as lifetime_policy
        from src.review.recognition import runtime_schema_package_lineage as lineage
        started = time.monotonic()
        consent_records = []
        output = Path(__file__).resolve().parents[1] / '.tmp' / (
            'recognition-r12-deadline-trace.json' if v2 else 'recognition-z18-deadline-trace.json')
        output.parent.mkdir(exist_ok=True)
        labels = ['pre-authority/schema-inventory preparation', 'authority issuance', 'coordinator admission', 'attempt creation',
                  'coordinator final validation', 'metadata-owner admission',
                  'metadata-owner final validation', 'target mode transition',
                  'target-entry INSERT', 'target commit', 'reservation reacquisition',
                  'post-commit validation', 'cleanup/result publication']
        rows = []
        active = []
        expiry = [None]
        monotonic_deadline = [None]
        interrupted = [None]
        outcome = ['C']
        failure = [None]
        phase = ['fixture setup']
        authority = {}
        preparation_counts = dict(hook_calls=0, objects_created=0, reused_inventory_reads=0)
        cleanup_span = [None]
        isolation = dict(verified=False, lifetime_migrations=0)
        lifecycle_done = [None]

        def error_details(error):
            import re
            code = getattr(error, 'code', None)
            if code is None and isinstance(error, ValueError):
                candidate = str(error)
                if re.fullmatch(r'[a-z][a-z0-9_]{0,159}', candidate):
                    code = candidate
            return dict(exception_class=type(error).__name__, error_code=code,
                        sqlite_errorcode=getattr(error, 'sqlite_errorcode', None),
                        sqlite_errorname=getattr(error, 'sqlite_errorname', None),
                        errno=getattr(error, 'errno', None), winerror=getattr(error, 'winerror', None))

        def remaining():
            if expiry[0] is None:
                return None
            return expiry[0] - z.a.timestamp(z.v._utc_now())

        def report():
            seen = {row['stage'] for row in rows}
            data = dict(classification=outcome[0], elapsed_seconds=time.monotonic()-started,
                        authority_remaining_seconds=remaining(), failure=failure[0],
                        interrupted_stage=interrupted[0], authority=authority,
                        z15_preparation=preparation_counts, consent_validations=consent_records, stages=list(rows),
                        isolation=isolation, lifecycle_completed_elapsed_seconds=lifecycle_done[0],
                        authority_elapsed_seconds=None if not authority else
                            z.a.timestamp(z.v._utc_now())-z.a.timestamp(authority['issued_at_utc']),
                        observed_monotonic_remaining_seconds=None if monotonic_deadline[0] is None else
                            monotonic_deadline[0]-time.monotonic())
            for label in labels:
                if label not in seen:
                    data['stages'].append(dict(stage=label, status='UNMEASURED',
                                              start_elapsed_seconds=None, end_elapsed_seconds=None,
                                              remaining_authority_seconds=None))
            output.write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')
            print(MARKER+json.dumps(data), flush=True)

        @contextmanager
        def span(label, **metadata):
            row = dict(stage=label, start_elapsed_seconds=time.monotonic()-started,
                       start_remaining_authority_seconds=remaining(), status='running', **metadata)
            rows.append(row)
            active.append(row)
            try:
                yield
                row['status'] = 'success'
            except BaseException as error:
                if interrupted[0] is None:
                    interrupted[0] = label
                row.update(status='failure', **error_details(error))
                raise
            finally:
                row['end_elapsed_seconds'] = time.monotonic()-started
                row['duration_seconds'] = row['end_elapsed_seconds']-row['start_elapsed_seconds']
                row['remaining_authority_seconds'] = remaining()
                active.pop()

        def timed(fn, label):
            @wraps(fn)
            def call(*args, **kwargs):
                with span(label):
                    return fn(*args, **kwargs)
            return call

        original_body = issuer._body
        def authority_body(*args, **kwargs):
            body = original_body(*args, **kwargs)
            self.assertIsNone(expiry[0], 'more than one authority')
            if v2:
                state, artifact = args
                self.assertTrue(isolation['verified'])
                self.assertEqual(self.config, state.config)
                self.assertTrue(state.issuance_phase)
                self.assertIsNone(state.pending)
                from tests.recognition_authorization_fixture import workspace_for
                workspace = Path(workspace_for(state.config.target).name).resolve()
                self.assertIn(workspace, self.disposable_allocations)
                self.assertTrue(all(p.resolve().is_relative_to(workspace) for p in
                    (state.config.target, state.config.control, state.config.key_file)))
                # The original function above still performs its real consent
                # freshness check and builds the exact original-context body.
                # Select the closed TEST policy before any persistence; no
                # schema, validator, clock or credential-expiry rule is patched.
                step = issuer.storage._artifact(state.control, artifact['step_artifact_sha256'],
                    issuer.storage.STEP_ACTION, issuer.storage.STEP)
                deadlines = [state.control.execute('SELECT expires FROM '+table+' WHERE token_hash=?',
                    (body['authentication'][kind+'_sha256'],)).fetchone()[0]
                    for kind, table in (('primary','recognition_admin_primary'),('session','recognition_admin_sessions'))]
                deadlines += [z.a.timestamp(step['expires_at_utc']), z.a.timestamp(artifact['expires_at_utc'])]
                issued = z.a.timestamp(body['issued_at_utc'])
                clipped = min(issued+lifetime_policy.seconds(lineage.V2), *deadlines)
                self.assertEqual(300, clipped-issued, 'original credentials/consent do not permit a 300-second sample')
                body.update(lifetime_policy=lineage.V2, expires_at_utc=consent._time(clipped))
                body = issuer.storage.validate_authority(body)
                authority['original_deadline_remaining_seconds'] = [d-issued for d in deadlines]
            issued = z.a.timestamp(body['issued_at_utc'])
            expiry[0] = z.a.timestamp(body['expires_at_utc'])
            self.assertEqual(300 if v2 else 120, expiry[0]-issued)
            monotonic_deadline[0] = time.monotonic()+remaining()
            authority.update(issued_at_utc=body['issued_at_utc'], expires_at_utc=body['expires_at_utc'],
                             policy_version=body['lifetime_policy'],
                             body_built_elapsed_seconds=time.monotonic()-started,
                             lifetime_seconds=expiry[0]-issued,
                             observed_issue_age_seconds=z.a.timestamp(z.v._utc_now())-issued)
            return body

        original_mint = preparation._mint
        def prepared(context, artifact):
            with span('pre-authority/schema-inventory preparation'):
                preparation_counts['hook_calls'] += 1
                original_mint(context, artifact)
                state = z.coordinator._state(context)
                self.assertIs(type(state.issuance_inventory), preparation._Facts)
                preparation_counts['objects_created'] += 1

        original_objects = preparation._objects
        def inventory_objects(connection):
            result = original_objects(connection)
            state = preparation._active.get()
            if state is not None and state.issuance_inventory is not None and any(
                    connection is candidate for candidate in (state.control, state.kernel_control, state.body_control)):
                preparation_counts['reused_inventory_reads'] += 1
            return result

        original_finish = z.coordinator._finish
        def finish(state):
            with span('coordinator final validation', phase='issuance' if state.issuance_phase else 'attempt'):
                return original_finish(state)

        original_eval = z.metadata._evaluate
        def evaluate(state):
            label = ('post-commit validation' if state.target_committed else
                     'metadata-owner admission' if not any(r['stage']=='metadata-owner admission' for r in rows)
                     else 'metadata-owner final validation')
            with span(label):
                result = original_eval(state)
            if state.target_committed and cleanup_span[0] is None:
                cleanup_span[0] = span('cleanup/result publication')
                cleanup_span[0].__enter__()
            return result

        original_connect = z.a.connect
        @contextmanager
        def connected(*args, **kwargs):
            with original_connect(*args, **kwargs) as connection:
                insert = [None]
                def trace(sql):
                    # SQL is inspected transiently, never retained/exported.
                    entry_insert = sql.lstrip().upper().startswith('INSERT INTO '+z.storage.TABLE.upper())
                    if insert[0] is not None and not entry_insert and not sql.lstrip().startswith('--'):
                        row = insert[0]
                        row.update(end_elapsed_seconds=time.monotonic()-started,
                                   remaining_authority_seconds=remaining(), status='insert trace interval ended',
                                   timing_note='through next non-trigger statement; includes intervening bookkeeping')
                        row['duration_seconds'] = row['end_elapsed_seconds']-row['start_elapsed_seconds']
                        insert[0] = None
                    if phase[0]=='metadata' and entry_insert and insert[0] is None:
                        row = dict(stage='target-entry INSERT', start_elapsed_seconds=time.monotonic()-started,
                                   start_remaining_authority_seconds=remaining(), status='started')
                        rows.append(row)
                        insert[0] = row
                connection.set_trace_callback(trace)
                try:
                    yield connection
                finally:
                    connection.set_trace_callback(None)

        original_transition_migrate = z.s.migrate
        def transitioned(config, **options):
            result = original_transition_migrate(config, **options)
            # Install L before W's plan freezes the control-schema hash, and
            # before any G+2 authority consent exists. Never migrate mid-ceremony.
            from tests.recognition_authorization_fixture import workspace_for
            workspace = Path(workspace_for(config.target).name).resolve()
            self.assertIn(workspace, self.disposable_allocations)
            self.assertTrue(all(p.resolve().is_relative_to(workspace) for p in
                (config.target, config.control, config.key_file)))
            self.assertEqual(0, isolation['lifetime_migrations'])
            installed = lifetime_policy.migrate(config, expected_generation=options['expected_generation'],
                operator='r12-disposable', reason='test-only versioned representation before G+2 preparation')
            self.assertTrue(installed['installed'])
            isolation.update(verified=True, lifetime_migrations=1)
            return result

        consent_observer = patch.object(consent, '_fresh', observe_consent(consent._fresh, lambda: z.v._utc_now(), consent_records))
        consent_observer.start()
        try:
            # Reuse only the existing setup helper, not its diagnostic test/loops.
            with (patch.object(z.s, 'migrate', transitioned) if v2 else ExitStack()):
                config, session, confirmation, approval_id, options = fixture.CoordinatorFinalValidationProfileTests.prepare_g2(self)
            with ExitStack() as patches:
                for module, name, replacement in (
                    (issuer, '_body', authority_body),
                    (preparation, '_mint', prepared),
                    (preparation, '_objects', inventory_objects),
                    (z.coordinator, '_finish', finish),
                    (z.metadata, '_evaluate', evaluate),
                    (z.metadata, '_mode', timed(z.metadata._mode, 'target mode transition')),
                    (z.metadata, '_commit_target', timed(z.metadata._commit_target, 'target commit')),
                    (z.metadata, '_reacquire', timed(z.metadata._reacquire, 'reservation reacquisition')),
                    (z.a, 'connect', connected),
                ):
                    patches.enter_context(patch.object(module, name, replacement))
                for module, name in ((z.writer_boundary, 'acquire'), (z.execution, 'execute_operation'),
                                     (z.local_execution, 'execute_approved_operation'), (z.permanent, 'finalize')):
                    patches.enter_context(patch.object(module, name, side_effect=AssertionError('downstream authority forbidden')))
                manager = z.coordinator.coordinator(config, session, confirmation, approval_id, **options)
                with span('authority issuance'), span('coordinator admission'):
                    owner = manager.__enter__()
                try:
                    with span('attempt creation'):
                        attempt = owner.create_attempt()
                    phase[0] = 'metadata'
                    with span('metadata lifecycle (parent span)'):
                        try:
                            result = z.metadata.create_target_entry(attempt)
                        finally:
                            if cleanup_span[0] is not None:
                                cleanup_span[0].__exit__(*sys.exc_info())
                                cleanup_span[0] = None
                        self.assertFalse(result.snapshot['execution_authority'])
                        self.assertFalse(result.snapshot['retry_authorized'])
                        self.assertGreater(remaining(), 0)
                finally:
                    if v2:
                        with span('cleanup/result publication', phase='coordinator exit'):
                            manager.__exit__(*sys.exc_info())
                    else:
                        manager.__exit__(*sys.exc_info())
                self.assertGreater(remaining(), 0)
                self.assertEqual(1, preparation_counts['objects_created'])
                self.assertGreater(preparation_counts['reused_inventory_reads'], 0)
                lifecycle_done[0] = time.monotonic()-started
                outcome[0] = 'A'
        except BaseException as error:
            # Preserve actual product codes, without credentials/exception locals.
            failure[0] = error_details(error)
            code = failure[0]['error_code']
            if expiry[0] is not None and remaining() <= 0 and (
                    code in ('administrative_session_expired_or_revoked', 'administrative_primary_expired_or_revoked',
                             'coordinator_authority_expired', 'metadata_authority_expired', 'issued_authority_expired',
                             'authority_consent_expired', 'runtime_attempt_expired_or_clock_rollback')):
                outcome[0] = 'B'
            else:
                outcome[0] = 'C'
        finally:
            try:
                report()
            finally:
                consent_observer.stop()
        print('Z12_TRACE '+str(output))
        self.assertNotEqual('C', outcome[0], 'diagnostic failure; inspect sanitized trace')
