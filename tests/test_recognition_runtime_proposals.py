"""4b-2 disposable real enrollment/authentication -> durable proposal pairs."""

from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import json
import sqlite3
import subprocess
import sys
import unittest
from unittest.mock import patch
from uuid import uuid4

from src.review.recognition import administration as a, dependencies, runtime_proposals as proposals
from src.review.recognition import runtime_proposal_transaction as owner, runtime_proposal_records as records
from src.review.recognition import runtime_validation as runtime, local_readiness, production_operations, administration_schema
from src.review.recognition import operations, writer_boundary, local_execution
from tests import test_recognition_administration as f
from tests import test_recognition_runtime_operation_contract as lifecycle


class RuntimeProposalTests(unittest.TestCase):
    def setUp(self):
        self.fixture = lifecycle.RuntimeOperationContractTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.config = self.fixture.config
        # Apply the fixture's simulated worker identity consistently to the
        # dependency module's imported strict observer as well as administration.
        identity_patch = patch.object(dependencies, 'target_identity', side_effect=self.fixture.fixture.runtime_identity)
        identity_patch.start()
        self.addCleanup(identity_patch.stop)
        self.session, self.primary = self.fixture.session, self.fixture.primary
        source = self.fixture.frozen['preparation']['request']
        self.request = dict(request_id=str(uuid4()), family=source['family'], inputs=deepcopy(source['inputs']),
            evaluation_at_utc=source['evaluation_at_utc'], review_reference=source['review_reference'], parent_operation_id=None)

    def create(self):
        return proposals.create_proposal(self.config, self.session, self.request, primary_token=self.primary)

    def inspect(self):
        return proposals.inspect_proposal(self.config, self.session, self.request, primary_token=self.primary)

    def test_real_lifecycle_pair_retry_and_reader(self):
        self.assertEqual('ABSENT', self.inspect()['status'])
        result = self.create()
        self.assertEqual('ACKNOWLEDGED', result['status'])
        self.assertEqual(result, self.create())
        self.assertEqual(result, self.inspect())
        with owner.proposal_transaction(self.config) as context:
            self.assertEqual(result, records.read_acknowledged_proposal(owner.read_view(context),
                result['operation']['operation_id'], session_token=self.session, primary_token=self.primary))

    def test_target_orphan_is_never_promoted(self):
        with patch.object(records, 'build_acknowledgement', side_effect=OSError('interruption')):
            with self.assertRaises(OSError): self.create()
        result = self.inspect()
        self.assertEqual('UNACKNOWLEDGED', result['status'])
        self.assertEqual(result, self.create())

    def test_conflicting_retry(self):
        self.create()
        self.request['review_reference'] += ' changed'
        with self.assertRaises(ValueError): self.create()

    def test_graph_failure_rolls_back(self):
        from src.review.recognition import events, operations
        real = events._insert
        def graph_snapshot():
            tables = ('recognition_preparations', 'recognition_frozen_events', 'recognition_event_history',
                'recognition_operation_contracts', 'recognition_operation_decisions', 'recognition_operation_executions')
            with a.connect(self.config.target) as target:
                return {table: [tuple(row) for row in target.execute('SELECT * FROM '+table+' ORDER BY 1,2')]
                        for table in tables}
        before = graph_snapshot()
        for stage in range(1, 7):
            calls = []
            def fail(*args, **kwargs):
                calls.append(1)
                real(*args, **kwargs)
                if len(calls) == stage:
                    raise OSError('graph interruption')
            with self.subTest(stage=stage), patch.object(events, '_insert', side_effect=fail), \
                    patch.object(operations, '_insert', side_effect=fail):
                with self.assertRaises(OSError): self.create()
            self.assertEqual('ABSENT', self.inspect()['status'])
            self.assertEqual(before, graph_snapshot())

    def test_no_key_reads_protected_records_schema_or_authority_changes(self):
        protected = ('recognition_admin_bindings', 'recognition_admin_primary', 'recognition_admin_sessions',
            'recognition_admin_stepups', 'recognition_admin_confirmations', 'recognition_admin_mfa',
            'recognition_runtime_profiles', 'recognition_runtime_auth_bindings', 'recognition_approvals')
        def snapshot():
            with a.connect(self.config.control) as control:
                return {table: [tuple(row) for row in control.execute('SELECT * FROM ' + table)] for table in protected}
        def schemas():
            result = []
            for path in (self.config.target, self.config.control):
                with a.connect(path) as conn:
                    result.append([tuple(row) for row in conn.execute('SELECT * FROM sqlite_master ORDER BY name')])
            return result
        before, schema = snapshot(), schemas()
        writers, executions = dict(writer_boundary._leases), dict(production_operations._contexts)
        local_writers = dict(writer_boundary._local_leases)
        with patch('pathlib.Path.read_bytes', side_effect=AssertionError('key read')):
            result = self.create()
        self.assertEqual(before, snapshot())
        self.assertEqual(schema, schemas())
        self.assertEqual(writers, dict(writer_boundary._leases))
        self.assertEqual(local_writers, dict(writer_boundary._local_leases))
        self.assertEqual(executions, dict(production_operations._contexts))
        operation_id = result['operation']['operation_id']
        with a.connect(self.config.target) as target:
            if target.execute("SELECT 1 FROM sqlite_master WHERE name='recognition_execution_claims'").fetchone():
                self.assertIsNone(target.execute('SELECT 1 FROM recognition_execution_claims WHERE operation_id=?', (operation_id,)).fetchone())
        readiness = local_readiness.assess(self.config, now=f.at(900))
        self.assertEqual('BLOCKED', readiness['status'])
        self.assertFalse(readiness['activation_ready'])
        self.assertEqual('BLOCKED', readiness['production_execution'])
        self.assertFalse(writer_boundary.verify_local(result, self.config.target, {}))
        for call in (lambda: local_execution._context(result),
                     lambda: production_operations.load_context(self.config, operation_id),
                     lambda: production_operations.activation_guard()):
            with self.assertRaises(a.AdminError): call()
        with a.connect(self.config.control) as control:
            self.assertEqual('NOT_ACTIVATED', json.loads(control.execute(
                'SELECT body_json FROM recognition_admin_bindings ORDER BY generation DESC LIMIT 1').fetchone()[0])['production_state'])

    def test_concurrent_same_request_has_exactly_one_pair(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(self.create) for _ in range(2)]
            results = [future.result(timeout=20) for future in futures]
        self.assertEqual(results[0], results[1])
        with a.connect(self.config.control) as control:
            self.assertEqual(1, control.execute("SELECT COUNT(*) FROM recognition_admin_audit WHERE json_extract(body_json,'$.action')=?",
                (records.ACK_ACTION,)).fetchone()[0])

    def test_new_current_session_retrieves_original_creation_scope(self):
        result = self.create()
        self.fixture.fixture.clock.return_value = f.at(930)
        self.primary = self.fixture.fixture.primary()
        self.session = self.fixture.fixture.session(self.primary)
        self.assertNotEqual(a.token_hash(self.session), result['operation']['creation']['session_sha256'])
        self.assertEqual(result, self.create())

    def test_contradictory_ack_for_orphan_operation_id_rejects(self):
        first = self.create()
        self.request['request_id'] = str(uuid4())
        with patch.object(records, 'build_acknowledgement', side_effect=OSError('gap')):
            with self.assertRaises(OSError): self.create()
        orphan = self.inspect()
        subject = deepcopy(first['acknowledgement']['subject'])
        subject['operation_id'] = orphan['operation_id']
        with a.connect(self.config.control, write=True) as control:
            control.execute('BEGIN IMMEDIATE')
            a._audit(control, records.ACK_ACTION, 1, f.at(900), subject)
            control.commit()
        with self.assertRaises(ValueError): self.inspect()
        with self.assertRaises(ValueError): self.create()

    def test_revisions_malformed_requests_and_bad_credentials_write_nothing(self):
        for key, value in (('parent_operation_id', str(uuid4())), ('request_id', str(uuid4())+'\0'),
                           ('review_reference', 'bad\0reference'), ('evaluation_at_utc', True)):
            request = dict(self.request, **{key: value})
            with self.subTest(key=key), self.assertRaises((ValueError, TypeError)):
                proposals.create_proposal(self.config, self.session, request, primary_token=self.primary)
        with self.assertRaises(a.AdminError):
            proposals.create_proposal(self.config, 'not-a-session', self.request, primary_token=self.primary)
        self.assertEqual('ABSENT', self.inspect()['status'])

    def test_failure_before_and_after_reservations_writes_nothing(self):
        for function in ('_history', '_snapshot'):
            with self.subTest(function=function), patch.object(runtime, function, side_effect=OSError('unavailable')):
                with self.assertRaises(OSError): self.create()
            self.assertEqual('ABSENT', self.inspect()['status'])
        with patch.object(a, 'connect', side_effect=OSError('cannot open')):
            with self.assertRaises(OSError): self.create()
        self.assertEqual('ABSENT', self.inspect()['status'])

    def test_ack_write_failure_leaves_orphan(self):
        real = proposals._mode
        def deny(state, mode):
            real(state, mode)
            if mode == 'ACK':
                raise OSError('ack unavailable')
        with patch.object(proposals, '_mode', side_effect=deny):
            with self.assertRaises(OSError): self.create()
        self.assertEqual('UNACKNOWLEDGED', self.inspect()['status'])

    def test_busy_control_and_target_fail_without_creation(self):
        original = sqlite3.connect
        def short_timeout(path, *args, **kwargs):
            kwargs['timeout'] = 0.05
            return original(path, *args, **kwargs)
        for path in (self.config.control, self.config.target):
            with self.subTest(path=path), closing(original(path)) as blocker:
                blocker.execute('BEGIN IMMEDIATE')
                with patch.object(a.sqlite3, 'connect', side_effect=short_timeout):
                    with self.assertRaises(sqlite3.OperationalError): self.create()
                blocker.rollback()
            self.assertEqual('ABSENT', self.inspect()['status'])

    def test_final_control_commit_keeps_both_reservations(self):
        real = proposals._final_check
        observed = []
        def check(state):
            real(state)
            for path in (self.config.control, self.config.target):
                with closing(sqlite3.connect(path, timeout=0)) as conn:
                    with self.assertRaises(sqlite3.OperationalError): conn.execute('BEGIN IMMEDIATE')
            self.assertEqual(1, state.target.execute('PRAGMA query_only').fetchone()[0])
            observed.append(True)
        with patch.object(proposals, '_final_check', side_effect=check):
            self.assertEqual('ACKNOWLEDGED', self.create()['status'])
        self.assertEqual([True], observed)

    def test_failure_after_target_commit_and_before_reread_leaves_orphan(self):
        real = proposals._target_commit_and_reserve
        def fail(state):
            real(state)
            raise OSError('post target commit')
        with patch.object(proposals, '_target_commit_and_reserve', side_effect=fail):
            with self.assertRaises(OSError): self.create()
        self.assertEqual('UNACKNOWLEDGED', self.inspect()['status'])

    def test_final_scope_or_expiry_failure_leaves_orphan(self):
        real = proposals._final_check
        def fail(state):
            self.fixture.fixture.clock.return_value = f.at(90000)
            real(state)
        with patch.object(proposals, '_final_check', side_effect=fail):
            with self.assertRaises(a.AdminError): self.create()
        self.fixture.fixture.clock.return_value = f.at(900)
        self.assertEqual('UNACKNOWLEDGED', self.inspect()['status'])

    def test_uncertain_target_and_control_commits_are_inspected_without_repair(self):
        original = sqlite3.connect
        for store, committed in (('target', False), ('target', True), ('control', False), ('control', True)):
            self.request['request_id'] = str(uuid4())
            selected = self.config.target if store == 'target' else self.config.control
            class CommitFailure(sqlite3.Connection):
                def commit(connection):
                    if connection.selected:
                        if committed:
                            super(CommitFailure, connection).commit()
                        raise OSError('uncertain commit')
                    return super(CommitFailure, connection).commit()
            def connect(path, *args, **kwargs):
                connection = original(path, *args, factory=CommitFailure, **kwargs)
                connection.selected = str(path).startswith(selected.resolve().as_uri()+'?')
                return connection
            with self.subTest(store=store, committed=committed), patch.object(a.sqlite3, 'connect', side_effect=connect):
                with self.assertRaises(OSError): self.create()
            expected = ('ABSENT' if not committed else 'UNACKNOWLEDGED') if store == 'target' else (
                'ACKNOWLEDGED' if committed else 'UNACKNOWLEDGED')
            result = self.inspect()
            self.assertEqual(expected, result['status'])
            if expected != 'ABSENT':
                self.assertEqual(result, self.create())

    def test_generation_profile_owner_auth_and_mfa_fences_after_target_commit(self):
        real = proposals._target_commit_and_reserve
        for field in ('generation', 'profile_sha256', 'owner_id', 'auth_epoch', 'mfa_epoch'):
            self.request['request_id'] = str(uuid4())
            def drift(state):
                real(state)
                original = runtime._snapshot
                def changed(*args):
                    value = dict(original(*args))
                    if field == 'mfa_epoch':
                        raise a.AdminError('runtime_validation_changed', 503)
                    value[field] = '0'*64 if field == 'profile_sha256' else value[field]+1
                    return value
                patcher = patch.object(runtime, '_snapshot', side_effect=changed)
                patcher.start()
                patches.append(patcher)
            patches = []
            try:
                with self.subTest(field=field), patch.object(proposals, '_target_commit_and_reserve', side_effect=drift):
                    with self.assertRaises(a.AdminError): self.create()
            finally:
                for patcher in patches: patcher.stop()
            self.assertEqual('UNACKNOWLEDGED', self.inspect()['status'])

    def test_target_owner_and_epoch_changes_in_commit_gap_reject_ack(self):
        for column in ('owner_id', 'auth_epoch'):
            # Separate lifecycle per destructive target-scope change.
            if column == 'auth_epoch':
                self.fixture.fixture.sql('UPDATE '+administration_schema.TARGET_TABLE+' SET owner_id=1', target=True)
            self.request['request_id'] = str(uuid4())
            def gap(state):
                state.lifecycle = True
                try:
                    state.target.commit()
                    with a.connect(self.config.target, write=True) as target:
                        target.execute('UPDATE '+administration_schema.TARGET_TABLE+' SET '+column+'='+column+'+1')
                        target.commit()
                    state.target.execute('BEGIN IMMEDIATE')
                    state.target.execute('PRAGMA query_only=ON')
                finally:
                    state.lifecycle = False
            with self.subTest(column=column), patch.object(proposals, '_target_commit_and_reserve', side_effect=gap):
                with self.assertRaises(a.AdminError): self.create()
            with a.connect(self.config.control) as control:
                self.assertEqual([], proposals._ack_rows(control, self.request['request_id']))

    def test_review_dependency_change_in_commit_gap_rejects_ack(self):
        def gap(state):
            state.lifecycle = True
            try:
                state.target.commit()
                with a.connect(self.config.target, write=True) as target:
                    target.execute("UPDATE stop_review_assignments SET status='assigned' "
                                   'WHERE id=(SELECT MIN(id) FROM stop_review_assignments)')
                    target.commit()
                state.target.execute('BEGIN IMMEDIATE')
                state.target.execute('PRAGMA query_only=ON')
            finally:
                state.lifecycle = False
        with patch.object(proposals, '_target_commit_and_reserve', side_effect=gap):
            with self.assertRaises(ValueError): self.create()
        self.assertEqual('UNACKNOWLEDGED', self.inspect()['status'])

    def test_real_process_termination_at_target_and_control_boundaries(self):
        code = r'''
import json,sys,os
from pathlib import Path
from dataclasses import replace
from src.review.recognition import administration as a, dependencies, runtime_validation as v
from src.review.recognition import runtime_proposals as p, runtime_proposal_transaction as owner
options=json.loads(sys.stdin.readline())
base=a.target_identity
def identity(subject):
    value=base(subject)
    return replace(value,hostname='synthetic-web',device=value.device+1)
a.target_identity=dependencies.target_identity=identity
v._utc_now=lambda:options['now']
config=a.LocalAdministration(*(Path(x) for x in options['paths']))
stage=options['stage']
def boundary():
    print('BOUNDARY',flush=True)
    sys.stdin.readline()
if stage=='graph':
    original=p._target_commit_and_reserve
    def hook(state): boundary(); original(state)
    p._target_commit_and_reserve=hook
elif stage=='target':
    original=p._target_commit_and_reserve
    def hook(state): original(state); boundary()
    p._target_commit_and_reserve=hook
elif stage=='ack':
    original=p._final_check
    def hook(state): original(state); boundary()
    p._final_check=hook
result=p.create_proposal(config,options['session'],options['request'],primary_token=options['primary'])
boundary()
'''
        for mode in ('DELETE', 'WAL'):
            for path in (self.config.target, self.config.control):
                with closing(sqlite3.connect(path)) as conn:
                    self.assertEqual(mode.lower(), conn.execute('PRAGMA journal_mode='+mode).fetchone()[0])
            for stage in ('graph', 'target', 'ack', 'committed'):
                self.request['request_id'] = str(uuid4())
                options = dict(paths=[str(self.config.target), str(self.config.control), str(self.config.key_file)],
                    now=f.at(900), session=self.session, primary=self.primary, request=self.request, stage=stage)
                process = subprocess.Popen([sys.executable, '-B', '-u', '-c', code], stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                try:
                    process.stdin.write(json.dumps(options)+'\n'); process.stdin.flush()
                    line = process.stdout.readline().strip()
                    if line != 'BOUNDARY':
                        _, errors = process.communicate(timeout=15)
                        self.fail('child did not reach boundary: '+errors)
                    process.kill()
                    process.communicate(timeout=15)
                finally:
                    if process.poll() is None:
                        process.kill(); process.communicate(timeout=15)
                with self.subTest(mode=mode, stage=stage):
                    result = self.inspect()
                    expected = 'ABSENT' if stage == 'graph' else ('ACKNOWLEDGED' if stage == 'committed' else 'UNACKNOWLEDGED')
                    self.assertEqual(expected, result['status'])
                    for path in (self.config.target, self.config.control):
                        with closing(sqlite3.connect(path, timeout=0)) as conn:
                            self.assertEqual('ok', conn.execute('PRAGMA integrity_check').fetchone()[0])
                            conn.execute('BEGIN IMMEDIATE'); conn.rollback()


if __name__ == '__main__':
    unittest.main()
