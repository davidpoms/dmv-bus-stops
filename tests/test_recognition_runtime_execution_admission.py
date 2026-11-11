"""4d-0 real lifecycle, immutable observations, no execution or durable authority."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from copy import deepcopy
from dataclasses import replace
import json
import os
import pickle
import sqlite3
import subprocess
import sys
import unittest
from unittest.mock import patch
from uuid import uuid4

from src.review.recognition import administration as a, administration_schema, approvals
from src.review.recognition import runtime_execution_admission as admission, runtime_validation as runtime
from src.review.recognition import runtime_proposal_transaction as owner, runtime_proposal_records as records
from src.review.recognition import runtime_approval_contract as codec, runtime_operation_contract as contract
from src.review.recognition import dependencies, events, execution, local_execution, local_readiness, writer_boundary
from src.review.recognition import production_operations, permanent
from src.review.recognition.rules import canonical, digest
from tests import test_recognition_runtime_approvals as lifecycle
from tests import test_recognition_administration as f


class RuntimeExecutionAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = lifecycle.RuntimeApprovalTests()
        install = a.install
        def prepared_target(config, **options):
            # Existing explicit storage prerequisite, installed only on this
            # newly created disposable target BEFORE any installation/profile
            # captures its schema hash. Never repair a bound target in admission.
            with a.connect(config.target, write=True) as target:
                target.execute('BEGIN IMMEDIATE')
                production_operations.install_target(target)
                target.commit()
            return install(config, **options)
        with patch.object(a, 'install', side_effect=prepared_target):
            self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.config = self.fixture.config
        self.primary, self.session = self.fixture.primary, self.fixture.session
        self.approval = self.fixture.issue()
        self.reference = self.fixture.reference
        self.clock = self.fixture.fixture.clock

    def assess(self, **changes):
        options = dict(approval_sha256=self.approval['approval_sha256'], reference=self.reference, primary_token=self.primary)
        approval_id = changes.pop('approval_id', self.approval['approval']['approval_id'])
        session = changes.pop('session', self.session)
        options.update(changes)
        return admission.assess(self.config, session, approval_id, **options)

    def snapshot(self):
        return (self.fixture.snapshot(self.config.control), self.fixture.snapshot(self.config.target))

    def test_real_lifecycle_immutable_exact_snapshot_no_authority_or_writes(self):
        before = self.snapshot()
        leases = (dict(writer_boundary._leases), dict(writer_boundary._local_leases), dict(production_operations._contexts))
        with patch('pathlib.Path.read_bytes', side_effect=AssertionError('no keys')):
            result = self.assess()
        body = result.snapshot
        self.assertEqual(admission.FORMAT, body['format'])
        self.assertEqual('ELIGIBLE_CANDIDATE', body['eligibility'])
        self.assertFalse(body['execution_authority'])
        self.assertEqual(self.approval['approval_sha256'], body['approval_sha256'])
        self.assertEqual(self.reference['acknowledgement_sha256'], body['reference']['acknowledgement_sha256'])
        self.assertEqual(result.sha256, digest(json.loads(result.canonical_json)))
        self.assertEqual(before, self.snapshot())
        with a.connect(self.config.target) as target:
            for table in ('recognition_execution_claims','recognition_execution_seals','recognition_operation_receipts'):
                self.assertEqual(0,target.execute('SELECT COUNT(*) FROM '+table+' WHERE operation_id=?',
                    (self.reference['operation_id'],)).fetchone()[0])
        with a.connect(self.config.control) as control:
            binding = json.loads(control.execute('SELECT body_json FROM recognition_admin_bindings ORDER BY generation DESC LIMIT 1').fetchone()[0])
            self.assertEqual('NOT_ACTIVATED',binding['production_state'])
        self.assertEqual(leases, (dict(writer_boundary._leases),dict(writer_boundary._local_leases),dict(production_operations._contexts)))
        self.assertNotIn(self.primary, result.canonical_json)
        self.assertNotIn(self.session, result.canonical_json)
        with self.assertRaises(TypeError): body['eligibility'] = 'EXECUTING'
        with self.assertRaises(TypeError): body['runtime_scope']['generation'] = 99
        with self.assertRaises(AttributeError): result.sha256 = '0'*64
        with self.assertRaises(TypeError): admission.ExecutionAdmission()
        with self.assertRaises(TypeError): pickle.dumps(result)
        for name in ('control','target','cursor','commit','rollback','writer_capability','execution_token'):
            self.assertFalse(hasattr(result, name))
        self.assertFalse(writer_boundary.verify_local(result, self.config.target, {}))
        self.assertEqual('BLOCKED', local_execution.execute_approved_operation(result, self.session,
            self.approval['approval']['approval_id'], now=self.clock.return_value).admission)
        self.assertEqual('BLOCKED', execution.admit_operation(result, artifact_json='{}', snapshot_json='{}',
            trusted_now_utc=self.clock.return_value).admission)
        for call in (lambda: execution._context(result), lambda: production_operations.context_data(result),
                     lambda: production_operations.activation_guard()):
            with self.assertRaises(ValueError): call()
        self.assertFalse(local_readiness.assess(self.config, now=self.clock.return_value)['activation_ready'])
        self.assertEqual(before, self.snapshot())

    def test_missing_legacy_invalidated_and_wrong_digest_approval(self):
        before = self.snapshot()
        with self.assertRaises(ValueError): self.assess(approval_id=str(uuid4()))
        with self.assertRaises(ValueError): self.assess(approval_sha256='0'*64)
        with a.connect(self.config.control) as control:
            legacy = control.execute('SELECT approval_id FROM recognition_approvals WHERE approval_id!=?',
                                     (self.approval['approval']['approval_id'],)).fetchone()[0]
        with self.assertRaises(ValueError): self.assess(approval_id=legacy)
        self.assertEqual(before, self.snapshot())
        with a.connect(self.config.control, write=True) as control:
            control.execute('BEGIN IMMEDIATE')
            approvals._invalidate_all(control, 'owner', self.clock.return_value, 'explicit-invalidation')
            control.commit()
        with self.assertRaises(ValueError): self.assess()

    def test_each_reference_and_scope_mismatch(self):
        for field in self.reference.keys()-{'format'}:
            value = dict(self.reference)
            value[field] = str(uuid4()) if field == 'operation_id' else ('0'*64 if type(value[field]) is str else value[field]+1)
            with self.subTest(reference=field), self.assertRaises(ValueError): self.assess(reference=value)
        base = runtime._snapshot
        for field in ('profile_sha256','generation','installation_id','target_id','owner_id','auth_epoch'):
            def changed(*args):
                value = dict(base(*args))
                old = value[field]
                value[field] = str(uuid4()) if field in ('installation_id','target_id') else ('0'*64 if type(old) is str else old+1)
                return value
            with self.subTest(scope=field), patch.object(runtime, '_snapshot', side_effect=changed), self.assertRaises(ValueError):
                self.assess()

    def test_expired_and_revoked_session_and_mfa_epoch(self):
        self.clock.return_value = f.at(40000)
        with self.assertRaises(ValueError): self.assess()
        self.clock.return_value = f.at(930)
        # Existing bounded authentication denial may revoke proof state. No
        # approval/execution authority is created on rejection.
        with self.assertRaises(ValueError): self.assess(session='x'*32)
        with a.connect(self.config.control) as control:
            self.assertEqual(1, control.execute('SELECT COUNT(*) FROM recognition_approvals WHERE approval_id=?',
                             (self.approval['approval']['approval_id'],)).fetchone()[0])

    def test_mfa_epoch_changed_after_approval(self):
        self.fixture.fixture.fixture.fixture.fixture.sql('UPDATE recognition_admin_mfa SET epoch=epoch+1')
        with self.assertRaises(ValueError): self.assess()

    def test_revocation_after_approval(self):
        self.fixture.fixture.fixture.fixture.fixture.sql('UPDATE recognition_admin_sessions SET revoked=1')
        with self.assertRaises(ValueError): self.assess()

    def test_dependency_actual_change_and_read_only_error_classification(self):
        original = self.snapshot()
        for state in ('INVALID','STALE','VERIFICATION_FAILURE'):
            with self.subTest(state=state), patch.object(dependencies,'recheck',return_value=dict(state=state,reasons=['test'])):
                with self.assertRaisesRegex(ValueError,'runtime_admission_dependencies_not_ready'): self.assess()
        self.assertEqual(original, self.snapshot())
        snapshot = self.assess()
        self.fixture.fixture.fixture.fixture.fixture.sql("UPDATE stop_review_assignments SET status='assigned' WHERE id=(SELECT MIN(id) FROM stop_review_assignments)",target=True)
        with self.assertRaises(ValueError): admission.revalidate(snapshot,self.config,self.session,primary_token=self.primary)

    def test_missing_dependency_and_wrong_dependency_generation(self):
        real = events.get_event
        for mode in ('missing','generation','invalid'):
            def changed(*args, **kwargs):
                result = deepcopy(real(*args, **kwargs))
                if mode == 'missing': result['preparation'].pop('dependencies')
                elif mode == 'generation': result['preparation']['request']['generation_reference'] = 'other:99'
                else: result['state'] = 'INVALID'
                return result
            with self.subTest(mode=mode), patch.object(events,'get_event',side_effect=changed), self.assertRaises((ValueError,KeyError)):
                self.assess()

    def test_target_identity_path_device_inode_hostname_and_schema_fail_closed(self):
        real = a.target_identity
        for field in ('hostname','device','inode','database'):
            def changed(subject):
                current = real(subject)
                old = getattr(current,field)
                return replace(current,**{field:old+1 if type(old) is int else old+'-changed'})
            with self.subTest(field=field), patch.object(a,'target_identity',side_effect=changed), self.assertRaises(ValueError): self.assess()
        snapshot = self.assess()
        self.fixture.fixture.fixture.fixture.fixture.sql('CREATE TABLE unexpected_schema(x)',target=True)
        with self.assertRaises(ValueError): admission.revalidate(snapshot,self.config,self.session,primary_token=self.primary)

    def test_target_reservation_and_read_failure(self):
        original = sqlite3.connect
        def short_timeout(*args,**kwargs): return original(*args,**dict(kwargs,timeout=0.01))
        before = self.snapshot()
        with closing(sqlite3.connect(self.config.target)) as lock:
            lock.execute('BEGIN IMMEDIATE')
            with patch.object(a.sqlite3,'connect',side_effect=short_timeout), self.assertRaises(sqlite3.OperationalError): self.assess()
            lock.rollback()
        with patch.object(permanent,'_prepare',side_effect=sqlite3.OperationalError('read failed')), self.assertRaises(sqlite3.OperationalError):
            self.assess()
        self.assertEqual(before,self.snapshot())

    def test_no_execution_function_and_real_stop_or_execution_block_rejects(self):
        with (patch.object(execution,'execute_operation',side_effect=AssertionError('execution')),
              patch.object(execution,'admit_operation',side_effect=AssertionError('claim')),
              patch.object(local_execution,'execute_approved_operation',side_effect=AssertionError('writer'))):
            self.assess()
        body = dict(active=True,sequence=1,previous_sha256=None)
        with a.connect(self.config.control,write=True) as control:
            control.execute('INSERT INTO recognition_execution_stops VALUES(?,?,?)',(1,canonical(body),digest(body)))
            control.commit()
        with self.assertRaisesRegex(ValueError,'emergency_stop'): self.assess()

    def test_durable_execution_block_is_not_repaired_or_ignored(self):
        with a.connect(self.config.control,write=True) as control:
            body = dict(reason='existing-block')
            control.execute('INSERT INTO recognition_execution_blocks VALUES(?,?,?)',
                (self.reference['operation_id'],canonical(body),digest(body)))
            control.commit()
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError,'runtime_admission_execution_blocked'): self.assess()
        self.assertEqual(before,self.snapshot())

    def test_locks_release_snapshot_needs_fresh_auth_and_comparison(self):
        old = self.assess()
        for path in (self.config.target,self.config.control):
            with closing(sqlite3.connect(path,timeout=0)) as conn:
                conn.execute('BEGIN IMMEDIATE'); conn.rollback()
        self.clock.return_value = f.at(960)
        new = admission.revalidate(old,self.config,self.session,primary_token=self.primary)
        self.assertNotEqual(old.sha256,new.sha256)
        self.assertEqual(f.at(960),new.snapshot['checked_at_utc'])
        self.assertEqual(old.snapshot['reference'],new.snapshot['reference'])
        with patch.object(os,'getpid',return_value=-1), self.assertRaises(ValueError): old.snapshot
        with ThreadPoolExecutor(max_workers=1) as pool:
            with self.assertRaises(ValueError): pool.submit(lambda: old.snapshot).result(timeout=5)
        with self.assertRaises(ValueError): admission.revalidate(object.__new__(admission.ExecutionAdmission),self.config,self.session,primary_token=self.primary)

    def test_post_snapshot_approval_invalidation_rejects(self):
        old = self.assess()
        with a.connect(self.config.control,write=True) as control:
            control.execute('BEGIN IMMEDIATE'); approvals._invalidate_all(control,'owner',self.clock.return_value,'invalidate')
            control.commit()
        with self.assertRaises(ValueError): admission.revalidate(old,self.config,self.session,primary_token=self.primary)

    def test_post_snapshot_profile_generation_owner_auth_mfa_changes_rejected(self):
        old = self.assess()
        base = runtime._snapshot
        for field in ('profile_sha256','generation','owner_id','auth_epoch'):
            def changed(*args):
                result = dict(base(*args))
                result[field] = '0'*64 if field == 'profile_sha256' else result[field]+1
                return result
            with self.subTest(field=field), patch.object(runtime,'_snapshot',side_effect=changed), self.assertRaises(ValueError):
                admission.revalidate(old,self.config,self.session,primary_token=self.primary)
        self.fixture.fixture.fixture.fixture.fixture.sql('UPDATE recognition_admin_mfa SET epoch=epoch+1')
        with self.assertRaises(ValueError): admission.revalidate(old,self.config,self.session,primary_token=self.primary)

    def test_post_snapshot_proposal_ack_and_dependency_mutation_rejected(self):
        old = self.assess()
        original = records.read_approved_proposal
        for field in ('operation','acknowledgement'):
            def changed(*args,**kwargs):
                pair = original(*args,**kwargs)
                pair[field] = dict(pair[field], synthetic_mutation=True)
                return pair
            # Fault injection only after the real durable reader has checked the
            # original pair: comparison must independently fence changed output.
            with self.subTest(field=field), patch.object(records,'read_approved_proposal',side_effect=changed), self.assertRaises(ValueError):
                admission.revalidate(old,self.config,self.session,primary_token=self.primary)

    def test_final_scope_expiry_and_query_only_reservations(self):
        original = owner._finish
        def finish(state):
            self.assertEqual(1,state.target.execute('PRAGMA query_only').fetchone()[0])
            for path in (self.config.control,self.config.target):
                with closing(sqlite3.connect(path,timeout=0)) as conn:
                    with self.assertRaises(sqlite3.OperationalError): conn.execute('BEGIN IMMEDIATE')
            original(state)
        with patch.object(owner,'_finish',side_effect=finish): self.assess()
        def expire(state):
            self.clock.return_value = f.at(40000)
            original(state)
        registered = set(admission._snapshots)
        with patch.object(owner,'_finish',side_effect=expire), self.assertRaises(ValueError): self.assess()
        self.assertEqual(registered,set(admission._snapshots))

    def test_delete_wal_restart_loses_object_requires_real_validation_no_durable_changes(self):
        code = r'''
import json,sys,pickle
from pathlib import Path
from dataclasses import replace
from src.review.recognition import administration as a, dependencies, runtime_validation as v, runtime_execution_admission as d
options=json.loads(sys.stdin.readline())
base=a.target_identity
def identity(subject):
    value=base(subject)
    return replace(value,hostname='synthetic-web',device=value.device+1)
a.target_identity=dependencies.target_identity=identity
v._utc_now=lambda:options['now']
config=a.LocalAdministration(*(Path(x) for x in options['paths']))
result=d.assess(config,options['session'],options['approval_id'],approval_sha256=options['approval_sha256'],reference=options['reference'],primary_token=options['primary'])
try: pickle.dumps(result)
except TypeError: pass
else: raise AssertionError('restorable admission')
print('OBSERVED',flush=True)
sys.stdin.readline()
'''
        for mode in ('DELETE','WAL'):
            for path in (self.config.control,self.config.target):
                with closing(sqlite3.connect(path)) as conn: conn.execute('PRAGMA journal_mode='+mode)
            before = self.snapshot()
            options = dict(paths=[str(self.config.target),str(self.config.control),str(self.config.key_file)],now=self.clock.return_value,
                primary=self.primary,session=self.session,approval_id=self.approval['approval']['approval_id'],
                approval_sha256=self.approval['approval_sha256'],reference=self.reference)
            for restart in range(2):
                process = subprocess.Popen([sys.executable,'-B','-u','-c',code],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                try:
                    process.stdin.write(json.dumps(options)+'\n'); process.stdin.flush()
                    line = process.stdout.readline().strip()
                    if line != 'OBSERVED':
                        _,error=process.communicate(timeout=15)
                        self.fail('child validation failed: '+error)
                    process.kill(); process.communicate(timeout=15)
                finally:
                    if process.poll() is None: process.kill(); process.communicate(timeout=15)
                self.assertEqual(before,self.snapshot())
