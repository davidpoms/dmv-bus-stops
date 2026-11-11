"""4c real enrollment -> authentication -> proposal -> confirmed approval."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from copy import deepcopy
import json
import sqlite3
import subprocess
import sys
import unittest
from unittest.mock import patch
from uuid import uuid4

from src.review.recognition import administration as a, runtime_approvals as issuer
from src.review.recognition import runtime_approval_transaction as owner, runtime_approval_contract as codec
from src.review.recognition import runtime_approval_ceremony as ceremony, runtime_validation as v
from src.review.recognition import approvals, local_readiness, writer_boundary, local_execution
from src.review.recognition import production_operations
from src.review.recognition.rules import canonical
from tests import test_recognition_runtime_approval_foundation as foundation
from tests import test_recognition_administration as f


class RuntimeApprovalTests(unittest.TestCase):
    def setUp(self):
        self.fixture = foundation.RuntimeApprovalFoundationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.config = self.fixture.config
        self.primary, self.session = self.fixture.primary, self.fixture.session
        self.reference = self.fixture.reference
        self.confirmation = self.fixture.confirm(self.fixture.step())
        self.request = dict(approval_id=str(uuid4()), reference=deepcopy(self.reference))

    def issue(self, request=None, confirmation=None):
        return issuer.issue_approval(self.config, self.session,
            (confirmation or self.confirmation)['token'], canonical(request or self.request), primary_token=self.primary)

    def snapshot(self, path):
        with a.connect(path) as conn:
            tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
            return {table: sorted([tuple(row) for row in conn.execute('SELECT * FROM "'+table+'"')], key=repr)
                    for table in tables}

    def test_real_lifecycle_and_exact_idempotent_retry_without_keys_or_target_writes(self):
        before = self.snapshot(self.config.target)
        with patch('pathlib.Path.read_bytes', side_effect=AssertionError('no key reads')):
            result = self.issue()
            durable = self.snapshot(self.config.control)
            self.assertEqual(result, self.issue())
        self.assertEqual(durable, self.snapshot(self.config.control))
        self.assertEqual(before, self.snapshot(self.config.target))
        self.assertEqual('APPROVED', result['state'])
        self.assertEqual(self.reference, result['approval']['binding']['reference'])
        self.assertFalse(result['approval']['execution_authority'])
        with owner.approval_transaction(self.config) as context:
            self.assertEqual(result, codec.read_current(owner.read_view(context), self.request['approval_id'],
                session_token=self.session, primary_token=self.primary))
            with self.assertRaises(ValueError):
                from src.review.recognition import runtime_proposal_records as records
                records.read_proposal_reference(owner.read_view(context), self.reference,
                    session_token=self.session, primary_token=self.primary)
        self.assertFalse(writer_boundary.verify_local(result, self.config.target, {}))
        self.assertFalse(local_readiness.assess(self.config, now=f.at(930))['activation_ready'])
        with a.connect(self.config.control) as control:
            with self.assertRaises(a.AdminError): approvals._read(control, self.request['approval_id'])
            text = '\n'.join(control.iterdump())
            self.assertNotIn(self.confirmation['token'], text)
            self.assertIn('NOT_ACTIVATED', text)
        for call in (lambda: local_execution._context(result),
                     lambda: production_operations.load_context(self.config, self.reference['operation_id']),
                     lambda: production_operations.activation_guard()):
            with self.assertRaises(a.AdminError): call()

    def test_request_strictness_and_changed_identity_rejected(self):
        before = self.snapshot(self.config.control)
        bad = ['{}', canonical(dict(self.request, hostname='claim')), canonical(dict(self.request, approval_id=True)),
               canonical(dict(self.request, approval_id=str(uuid4())+'\0')), canonical(self.request)+' ',
               '{"approval_id":"x","approval_id":"y","reference":{}}', '[]', '{"approval_id":1.5}',
               'x'*8193]
        for serialized in bad:
            with self.subTest(serialized=serialized[:80]), self.assertRaises(ValueError):
                issuer.issue_approval(self.config, self.session, self.confirmation['token'], serialized, primary_token=self.primary)
        self.assertEqual(before, self.snapshot(self.config.control))
        self.issue()
        for key, value in [('approval_id', str(uuid4())), ('reference', dict(self.reference, acknowledgement_sha256='0'*64))]:
            with self.subTest(key=key), self.assertRaises(ValueError): self.issue(dict(self.request, **{key:value}))
        with self.assertRaises(ValueError): self.issue(confirmation=dict(token='other-token'))

    def test_exact_pair_scope_and_expiry_fail_without_consumption(self):
        before = self.snapshot(self.config.control)
        for field in self.reference.keys()-{'format'}:
            changed = deepcopy(self.request)
            old = changed['reference'][field]
            changed['reference'][field] = str(uuid4()) if field == 'operation_id' else ('0'*64 if type(old) is str else old+1)
            with self.subTest(field=field), self.assertRaises(ValueError): self.issue(changed)
        self.fixture.clock.return_value = f.at(1530)
        with self.assertRaises(ValueError): self.issue()
        self.fixture.clock.return_value = f.at(930)
        self.assertEqual(before, self.snapshot(self.config.control))

    def test_standalone_consumption_is_not_approval_and_cannot_be_reused(self):
        self.fixture.consume(self.confirmation)
        before = self.snapshot(self.config.control)
        with self.assertRaises(ValueError): self.issue()
        self.assertEqual(before, self.snapshot(self.config.control))

    def test_concurrent_identical_and_different_attempts(self):
        def call(request):
            try: return self.issue(request)
            except ValueError: return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            identical = list(pool.map(call, [self.request, self.request]))
        self.assertEqual(identical[0], identical[1])
        self.assertIsNotNone(identical[0])
        with ThreadPoolExecutor(max_workers=2) as pool:
            attempts = list(pool.map(call, [dict(self.request, approval_id=str(uuid4())) for _ in range(2)]))
        self.assertEqual([None, None], attempts)
        with a.connect(self.config.control) as control:
            self.assertEqual(1, control.execute('SELECT COUNT(*) FROM recognition_approvals WHERE operation_id=?',
                                               (self.reference['operation_id'],)).fetchone()[0])

    def test_two_different_fresh_approval_attempts_have_one_winner(self):
        def call(request):
            try: return self.issue(request)
            except ValueError: return None
        requests = [dict(self.request, approval_id=str(uuid4())) for _ in range(2)]
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(call, requests))
        self.assertEqual(1, sum(result is not None for result in results))
        winner = next(result for result in results if result is not None)
        self.assertEqual('APPROVED', winner['state'])

    def test_retry_does_not_spend_another_preexisting_ceremony(self):
        self.fixture.clock.return_value = f.at(960)
        other = self.fixture.confirm(self.fixture.step())
        result = self.issue()
        before = self.snapshot(self.config.control)
        self.assertEqual(result, self.issue())
        with self.assertRaises(ValueError):
            self.issue(dict(self.request, approval_id=str(uuid4())), confirmation=other)
        self.assertEqual(before, self.snapshot(self.config.control))
        with a.connect(self.config.control) as control:
            self.assertEqual(0, control.execute('SELECT used FROM recognition_admin_confirmations WHERE token_hash=?',
                                                (a.token_hash(other['token']),)).fetchone()[0])

    def test_explicit_invalidation_and_restore_rebind_remain_fail_closed(self):
        result = self.issue()
        with a.connect(self.config.control, write=True) as control:
            control.execute('BEGIN IMMEDIATE')
            approvals._invalidate_all(control, 'owner', f.at(930), 'explicit-revocation')
            control.commit()
        with a.connect(self.config.control) as control:
            value = codec._historical(control, self.request['approval_id'])
            self.assertEqual(result['approval'], value['approval'])
            self.assertEqual('INVALIDATED', value['state'])
        with self.assertRaises(ValueError): self.issue()
        # Existing deployment-only v3 restore/rebind admission is not broadened.
        with self.assertRaisesRegex(a.AdminError, 'runtime_profile_contract_not_enabled'):
            with a.transaction(self.config, lock_target=True): pass

    def test_real_auth_epoch_invalidation_keeps_original_body(self):
        from src.review.recognition import administration_schema
        result = self.issue()
        auth_fixture = self.fixture.fixture.fixture.fixture
        auth_fixture.sql('UPDATE '+administration_schema.TARGET_TABLE+' SET auth_epoch=auth_epoch+1', target=True)
        self.fixture.clock.return_value = f.at(960)
        primary = auth_fixture.primary()
        session = auth_fixture.session(primary)
        with owner.approval_transaction(self.config) as context:
            with self.assertRaises(ValueError): codec.read_current(owner.read_view(context), self.request['approval_id'],
                session_token=session, primary_token=primary)
        self.assertEqual([self.request['approval_id']],
            codec.invalidate_stale_scope(self.config, session, primary_token=primary)['invalidated'])
        with a.connect(self.config.control) as control:
            value = codec._historical(control, self.request['approval_id'])
            self.assertEqual(result['approval'], value['approval'])
            self.assertEqual('INVALIDATED', value['state'])

    def test_every_mutation_and_final_failure_roll_back_entire_control_state(self):
        before = self.snapshot(self.config.control)
        for module, name in ((ceremony, '_current'), (issuer, '_confirmation')):
            original_boundary = getattr(module, name)
            def boundary(*args, **kwargs):
                original_boundary(*args, **kwargs)
                raise OSError('after reserved validation boundary')
            with self.subTest(boundary=name), patch.object(module, name, side_effect=boundary):
                with self.assertRaises(OSError): self.issue()
            self.assertEqual(before, self.snapshot(self.config.control))
        real_audit = a._audit
        for action in (ceremony.CONSUME_ACTION, issuer.ACTION):
            def fail(*args, **kwargs):
                real_audit(*args, **kwargs)
                if args[1] == action: raise OSError('after audit insertion')
            with self.subTest(action=action), patch.object(a, '_audit', side_effect=fail):
                with self.assertRaises(OSError): self.issue()
            self.assertEqual(before, self.snapshot(self.config.control))
        for function in ('_final_check',):
            with patch.object(issuer, function, side_effect=OSError('final validation')):
                with self.assertRaises(OSError): self.issue()
            self.assertEqual(before, self.snapshot(self.config.control))
        original = a.sqlite3.connect
        for sql in ('UPDATE recognition_admin_confirmations', 'INSERT INTO recognition_approvals',
                    'INSERT INTO recognition_approval_history'):
            class Fault(sqlite3.Connection):
                def execute(connection, statement, *args, **kwargs):
                    result = super().execute(statement, *args, **kwargs)
                    if statement.startswith(sql): raise OSError('after mutation')
                    return result
            def connect(*args, **kwargs): return original(*args, **dict(kwargs, factory=Fault))
            with self.subTest(sql=sql), patch.object(a.sqlite3, 'connect', side_effect=connect):
                with self.assertRaises(OSError): self.issue()
            self.assertEqual(before, self.snapshot(self.config.control))

    def test_final_scope_auth_deadline_and_dependencies_rechecked(self):
        original = issuer._final_check
        before = self.snapshot(self.config.control)
        for field in ('generation', 'profile_sha256', 'owner_id', 'auth_epoch'):
            base = v._snapshot
            def finish(state):
                def changed(*args):
                    scope = dict(base(*args))
                    scope[field] = '0'*64 if field == 'profile_sha256' else scope[field]+1
                    return scope
                with patch.object(v, '_snapshot', side_effect=changed): original(state)
            with self.subTest(field=field), patch.object(issuer, '_final_check', side_effect=finish):
                with self.assertRaises(ValueError): self.issue()
            self.assertEqual(before, self.snapshot(self.config.control))
        def expired(state):
            self.fixture.clock.return_value = f.at(1530)
            original(state)
        with patch.object(issuer, '_final_check', side_effect=expired):
            with self.assertRaises(ValueError): self.issue()
        self.fixture.clock.return_value = f.at(930)
        self.assertEqual(before, self.snapshot(self.config.control))

    def test_final_reservations_and_schema_unchanged(self):
        original = issuer._final_check
        def finish(state):
            self.assertEqual(1, state.target.execute('PRAGMA query_only').fetchone()[0])
            for path in (self.config.control, self.config.target):
                with closing(sqlite3.connect(path, timeout=0)) as other:
                    with self.assertRaises(sqlite3.OperationalError): other.execute('BEGIN IMMEDIATE')
            original(state)
        with a.connect(self.config.control) as control, a.connect(self.config.target) as target:
            before = [list(conn.execute('SELECT type,name,sql FROM sqlite_master ORDER BY name')) for conn in (control,target)]
            before = [[tuple(row) for row in rows] for rows in before]
        with patch.object(issuer, '_final_check', side_effect=finish): self.issue()
        with a.connect(self.config.control) as control, a.connect(self.config.target) as target:
            after = [[tuple(row) for row in conn.execute('SELECT type,name,sql FROM sqlite_master ORDER BY name')]
                     for conn in (control,target)]
        self.assertEqual(before, after)

    def test_scope_and_graph_mutation_races_cannot_cross_reserved_commit(self):
        from src.review.recognition import administration_schema
        original = issuer._final_check
        attempts = []
        def finish(state):
            statements = (
                ('generation', self.config.control, 'UPDATE recognition_admin_bindings SET generation=generation+1'),
                ('profile', self.config.control, "UPDATE recognition_runtime_profiles SET hostname='other'"),
                ('owner', self.config.target, 'UPDATE '+administration_schema.TARGET_TABLE+' SET owner_id=owner_id+1'),
                ('auth_epoch', self.config.target, 'UPDATE '+administration_schema.TARGET_TABLE+' SET auth_epoch=auth_epoch+1'),
                ('mfa_epoch', self.config.control, 'UPDATE recognition_admin_mfa SET epoch=epoch+1'),
                ('acknowledgement', self.config.control, 'DELETE FROM recognition_admin_audit'),
                ('proposal', self.config.target, 'DELETE FROM recognition_operation_contracts'),
                ('session_revocation', self.config.control, 'UPDATE recognition_admin_sessions SET revoked=1'),
            )
            def contender(path, statement):
                with closing(sqlite3.connect(path, timeout=0)) as conn:
                    # UPDATE/DELETE must first acquire the other connection's
                    # writer lock, even for tables with immutable SQL triggers.
                    with self.assertRaisesRegex(sqlite3.OperationalError, 'locked'):
                        conn.execute(statement)
            with ThreadPoolExecutor(max_workers=1) as pool:
                for name, path, statement in statements:
                    pool.submit(contender, path, statement).result(timeout=5)
                    attempts.append(name)
            original(state)
        with patch.object(issuer, '_final_check', side_effect=finish): self.issue()
        self.assertEqual(8, len(attempts))

    def test_revoked_session_before_reservation_cannot_spend_confirmation(self):
        self.fixture.fixture.fixture.fixture.sql('UPDATE recognition_admin_sessions SET revoked=1')
        with self.assertRaises(a.AdminError): self.issue()
        with a.connect(self.config.control) as control:
            self.assertIsNone(control.execute('SELECT 1 FROM recognition_approvals WHERE approval_id=?',
                                              (self.request['approval_id'],)).fetchone())
            actions = [json.loads(row[0])['action'] for row in control.execute('SELECT body_json FROM recognition_admin_audit')]
            self.assertNotIn(issuer.ACTION, actions)

    def test_synthetic_current_scope_mismatches_reject_real_approval_append_only(self):
        from src.review.recognition.rules import digest
        result = self.issue()
        # The schema deliberately has no rotation/recovery issuance primitive.
        # Per-field stale-scope invalidation is tested using the real approval
        # writer's body as template, with explicitly synthetic historical scope.
        changed_ids = []
        with a.connect(self.config.control, write=True) as control:
            control.execute('BEGIN IMMEDIATE')
            for field in ('generation', 'runtime_profile_sha256', 'owner_id', 'auth_epoch', 'mfa_epoch'):
                body = deepcopy(result['approval'])
                body['approval_id'] = str(uuid4())
                body['confirmation_sha256'] = digest({'synthetic':field})
                body['binding']['reference']['operation_id'] = str(uuid4())
                target = body['binding']['local_target']
                target[field] = '0'*64 if field == 'runtime_profile_sha256' else target[field]+1
                if field == 'owner_id': body['actor_id'] = target[field]
                codec.validate(body)
                history = codec._history_body(body, [], 'APPROVED', body['actor_id'], body['approved_at_utc'], body['reason'])
                control.execute('INSERT INTO recognition_approvals VALUES(?,?,?,?,?)', (body['approval_id'],
                    body['binding']['reference']['operation_id'],body['confirmation_sha256'],canonical(body),digest(body)))
                control.execute('INSERT INTO recognition_approval_history VALUES(?,?,?,?,?)',
                    (body['approval_id'],1,'APPROVED',canonical(history),digest(history)))
                changed_ids.append(body['approval_id'])
            control.commit()
        before = self.snapshot(self.config.control)['recognition_approvals']
        invalidated = codec.invalidate_stale_scope(self.config, self.session, primary_token=self.primary)
        self.assertEqual(set(changed_ids), set(invalidated['invalidated']))
        self.assertEqual(before, self.snapshot(self.config.control)['recognition_approvals'])
        self.assertEqual(result, self.issue())

    def test_uncertain_commit_inspects_durable_state_before_same_identity_retry(self):
        original = a.sqlite3.connect
        for committed in (False, True):
            class Fault(sqlite3.Connection):
                def commit(connection):
                    if committed: super().commit()
                    raise OSError('uncertain commit')
            def connect(*args, **kwargs):
                if str(args[0]).startswith(self.config.control.resolve().as_uri()):
                    kwargs['factory'] = Fault
                return original(*args, **kwargs)
            with self.subTest(committed=committed), patch.object(a.sqlite3, 'connect', side_effect=connect):
                with self.assertRaises(OSError): self.issue()
            with a.connect(self.config.control) as control:
                exists = control.execute('SELECT 1 FROM recognition_approvals WHERE approval_id=?',
                                         (self.request['approval_id'],)).fetchone() is not None
                self.assertEqual(committed, exists)
        self.assertEqual('APPROVED', self.issue()['state'])

    def test_locked_control_fails_before_consuming(self):
        before = self.snapshot(self.config.control)
        original = a.sqlite3.connect
        def connect(*args, **kwargs): return original(*args, **dict(kwargs, timeout=0.01))
        with closing(sqlite3.connect(self.config.control)) as lock:
            lock.execute('BEGIN IMMEDIATE')
            with patch.object(a.sqlite3, 'connect', side_effect=connect):
                with self.assertRaises(sqlite3.OperationalError): self.issue()
            lock.rollback()
        self.assertEqual(before, self.snapshot(self.config.control))

    def test_process_termination_before_and_after_control_commit_delete_and_wal(self):
        code = r'''
import json,sys
from pathlib import Path
from dataclasses import replace
from src.review.recognition import administration as a, dependencies, runtime_validation as v, runtime_approvals as issuer
options=json.loads(sys.stdin.readline())
base=a.target_identity
def identity(subject):
    value=base(subject)
    return replace(value,hostname='synthetic-web',device=value.device+1)
a.target_identity=dependencies.target_identity=identity
v._utc_now=lambda:options['now']
config=a.LocalAdministration(*(Path(x) for x in options['paths']))
def boundary():
    print('BOUNDARY',flush=True)
    sys.stdin.readline()
if options['stage']=='before':
    original=issuer._final_check
    def finish(state): original(state); boundary()
    issuer._final_check=finish
issuer.issue_approval(config,options['session'],options['confirmation'],options['request'],primary_token=options['primary'])
boundary()
'''
        for mode in ('DELETE', 'WAL'):
            if mode == 'WAL':
                self.fixture.clock.return_value = f.at(960)
                self.fixture.fixture.request['request_id'] = str(uuid4())
                self.reference = self.fixture.fixture.create()['reference']
                self.fixture.reference = self.reference
                self.confirmation = self.fixture.confirm(self.fixture.step())
                self.request = dict(approval_id=str(uuid4()), reference=deepcopy(self.reference))
            for path in (self.config.target, self.config.control):
                with closing(sqlite3.connect(path)) as conn:
                    self.assertEqual(mode.lower(), conn.execute('PRAGMA journal_mode='+mode).fetchone()[0])
            # Each mode uses a fresh real proposal and confirmation. Precommit
            # termination must leave it unused, postcommit must consume it.
            for stage in ('before', 'after'):
                options = dict(paths=[str(self.config.target),str(self.config.control),str(self.config.key_file)],
                    now=self.fixture.clock.return_value, session=self.session, primary=self.primary, confirmation=self.confirmation['token'],
                    request=canonical(self.request), stage=stage)
                process = subprocess.Popen([sys.executable,'-B','-u','-c',code], stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                try:
                    process.stdin.write(json.dumps(options)+'\n'); process.stdin.flush()
                    line = process.stdout.readline().strip()
                    if line != 'BOUNDARY':
                        _, error = process.communicate(timeout=15)
                        self.fail('boundary not reached: '+error)
                    process.kill(); process.communicate(timeout=15)
                finally:
                    if process.poll() is None: process.kill(); process.communicate(timeout=15)
                with a.connect(self.config.control) as control:
                    exists = control.execute('SELECT 1 FROM recognition_approvals WHERE approval_id=?',
                                             (self.request['approval_id'],)).fetchone() is not None
                    self.assertEqual(stage == 'after', exists)
                    self.assertEqual(int(stage == 'after'), control.execute(
                        'SELECT used FROM recognition_admin_confirmations WHERE token_hash=?',
                        (a.token_hash(self.confirmation['token']),)).fetchone()[0])
                    self.assertEqual(int(stage == 'after'), control.execute(
                        'SELECT COUNT(*) FROM recognition_approval_history WHERE approval_id=?',
                        (self.request['approval_id'],)).fetchone()[0])
                if stage == 'after':
                    self.assertEqual('APPROVED', self.issue()['state'])
                for path in (self.config.target, self.config.control):
                    with closing(sqlite3.connect(path)) as conn:
                        self.assertEqual('ok', conn.execute('PRAGMA integrity_check').fetchone()[0])
        self.assertEqual('APPROVED', self.issue()['state'])
