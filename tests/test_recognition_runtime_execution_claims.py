"""4d-1 real disposable lifecycle; no target DML or downstream authority."""

from contextlib import closing, contextmanager
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
import json
import os
import pickle
import sqlite3
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

from src.review.recognition import administration as a, administration_schema, authorization, approvals
from src.review.recognition import runtime_execution_claims as claims, runtime_execution_claim_schema as schema
from src.review.recognition import runtime_claim_validation as owner, runtime_admission_validation as shared
from src.review.recognition import runtime_execution_admission as admission, runtime_validation as runtime
from src.review.recognition import runtime_proposal_transaction as proposal, runtime_scope_validation as scope
from src.review.recognition import execution, local_execution, local_readiness, writer_boundary, production_operations
from src.review.recognition.rules import canonical, digest
from src.review.recognition.trust import utc
from tests import test_recognition_runtime_execution_admission as lifecycle
from tests import test_recognition_administration as f


class RuntimeExecutionClaimTests(unittest.TestCase):
    def setUp(self):
        self.f = lifecycle.RuntimeExecutionAdmissionTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.config = self.f.config
        self.snapshot = self.f.assess()
        self.clock = self.f.clock
        with patch.object(a,'target_identity',side_effect=authorization.target_identity):
            schema.migrate(self.config,expected_generation=3,operator='fixture',reason='disposable claim storage')
        self.child_clock_anchor = time.monotonic_ns()
        real_monotonic = time.monotonic_ns
        # Acquisition now detects stalled UTC. Keep the disposable parent and
        # child clocks advancing consistently instead of freezing UTC while real
        # I/O/scheduling elapses. Explicit fault tests still move return_value.
        self.clock.side_effect = lambda: (utc(self.clock.return_value)+timedelta(
            seconds=(real_monotonic()-self.child_clock_anchor)//claims._NS)).strftime('%Y-%m-%dT%H:%M:%SZ')

    def acquire(self, snapshot=None, **options):
        return claims.acquire(self.config,self.snapshot if snapshot is None else snapshot,
            self.f.session,primary_token=self.f.primary,**options)

    def dump(self):
        stores = self.f.snapshot()
        for index,path in enumerate((self.config.control,self.config.target)):
            with a.connect(path) as conn:
                stores[index]['__schema__'] = sorted(tuple(row) for row in conn.execute(
                    "SELECT name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"))
        return stores

    def count(self):
        with a.connect(self.config.control) as control:
            administration_schema.check_control(control)
            return tuple(control.execute('SELECT count(*) FROM '+name).fetchone()[0]
                         for name in (schema.CLAIMS,schema.HISTORY))

    def test_real_lifecycle_exact_claim_genesis_audit_no_downstream_authority(self):
        before = self.dump()
        leases = (dict(writer_boundary._leases),dict(writer_boundary._local_leases),dict(production_operations._contexts))
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('no keys')):
            receipt = self.acquire()
        body = json.loads(receipt.canonical_json)
        observed = json.loads(self.snapshot.canonical_json)
        self.assertEqual(schema.FORMAT,body['format'])
        self.assertEqual('ISSUED',body['state'])
        self.assertEqual(self.snapshot.sha256,body['admission_sha256'])
        self.assertEqual(digest(observed['proposal']),body['operation_sha256'])
        self.assertEqual(body['operation_sha256'],body['proposal_sha256'])
        self.assertEqual(observed['runtime_scope'],body['runtime_scope'])
        self.assertEqual(observed['target_snapshot'],body['target_snapshot'])
        self.assertEqual(observed['authentication'],body['authentication'])
        self.assertEqual(observed['reference'],body['proposal_reference'])
        self.assertEqual(observed['approval_sha256'],body['approval_sha256'])
        self.assertEqual(observed['approval_history_sha256'],body['approval_history_sha256'])
        self.assertEqual(digest(observed['dependency_snapshot']),body['dependency_snapshot_sha256'])
        self.assertEqual(digest(observed['target_snapshot']),body['target_snapshot_sha256'])
        self.assertEqual(digest(observed['emergency_stop_snapshot']),body['emergency_stop_snapshot_sha256'])
        self.assertEqual(300,a.timestamp(body['expires_at_utc'])-a.timestamp(body['issued_at_utc']))
        self.assertEqual(receipt.sha256,digest(body))
        self.assertEqual((1,1),self.count())
        after = self.dump()
        self.assertEqual(before[1],after[1])  # ALL target rows, including legacy claims/seals/receipts.
        for table in before[0].keys()-{schema.CLAIMS,schema.HISTORY,'recognition_admin_audit'}:
            self.assertEqual(before[0][table],after[0][table],table)
        self.assertEqual(len(before[0]['recognition_admin_audit'])+1,len(after[0]['recognition_admin_audit']))
        self.assertEqual(leases,(dict(writer_boundary._leases),dict(writer_boundary._local_leases),dict(production_operations._contexts)))
        self.assertFalse(writer_boundary.verify_local(receipt,self.config.target,{}))
        with self.assertRaises(ValueError): execution._context(receipt)
        with self.assertRaises(ValueError): production_operations.context_data(receipt)
        self.assertEqual('BLOCKED',local_execution.execute_approved_operation(receipt,self.f.session,
            self.f.approval['approval']['approval_id'],now=self.clock.return_value).admission)
        self.assertFalse(local_readiness.assess(self.config,now=self.clock.return_value)['activation_ready'])
        with a.connect(self.config.control) as control:
            bound = json.loads(control.execute('SELECT body_json FROM recognition_admin_bindings ORDER BY generation DESC LIMIT 1').fetchone()[0])
            self.assertEqual('NOT_ACTIVATED',bound['production_state'])
        for token in (self.f.primary,self.f.session): self.assertNotIn(token,receipt.inspection_reference)
        self.assertNotIn('pid',body)
        for name in ('execute','cursor','target','control','consume','renew','commit','writer_capability'):
            self.assertFalse(hasattr(receipt,name))
        with self.assertRaises(TypeError): claims.ExecutionClaim()
        with self.assertRaises(TypeError): pickle.dumps(receipt)
        with self.assertRaises(TypeError): receipt.snapshot['runtime_scope']['generation'] = 99
        with self.assertRaisesRegex(a.AdminError,'runtime_claim_already_acquired'): self.acquire()
        self.assertEqual(after,self.dump())

    def test_detached_forged_wrong_scope_and_duration_inputs_rejected(self):
        before = self.dump()
        for bad in (self.snapshot.canonical_json,dict(self.snapshot.snapshot),object.__new__(admission.ExecutionAdmission)):
            with self.assertRaises(ValueError): self.acquire(bad)
        with self.assertRaises(TypeError): self.acquire(duration=301)
        with self.assertRaises(ValueError): claims._receipt(object.__new__(claims.ExecutionClaim))
        real = a.target_identity
        for field in ('hostname','database','device','inode'):
            def changed(subject):
                value = real(subject)
                old = getattr(value,field)
                return replace(value,**{field:old+1 if type(old) is int else old+'-wrong'})
            with self.subTest(field=field), patch.object(a,'target_identity',side_effect=changed), self.assertRaises(ValueError):
                self.acquire()
        self.assertEqual(before,self.dump())

    def test_complete_scope_fences_before_insert_and_final_check(self):
        paths = [('runtime_scope',key) for key in ('generation','installation_id','target_id','owner_id',
            'runtime_profile_sha256','binding_sha256','auth_epoch','mfa_epoch')]
        paths += [('proposal','writer_manifest_sha256'),('reference','operation_sha256'),
            ('reference','acknowledgement_sha256'),('approval_sha256',),('approval_history_sha256',),
            ('dependency_snapshot','format'),('target_snapshot','target','schema_sha256'),
            ('emergency_stop_snapshot','sequence')]
        for prefix in (('target_snapshot','target','observation'),('target_snapshot','control_identity')):
            paths += [prefix+(field,) for field in ('hostname','database','device','inode')]
        before, real = self.dump(), shared._collect
        for call_number in (1,2):
            for path in paths:
                calls = []
                def changed(*args,**kwargs):
                    body = deepcopy(real(*args,**kwargs))
                    calls.append(True)
                    if len(calls) == call_number:
                        value = body
                        for field in path[:-1]: value = value[field]
                        old = value[path[-1]]
                        value[path[-1]] = old+1 if type(old) is int else old+'-wrong'
                    return body
                with self.subTest(stage=call_number,path=path):
                    with patch.object(shared,'_collect',side_effect=changed), self.assertRaisesRegex(ValueError,'runtime_admission_snapshot_stale'):
                        self.acquire()
                    self.assertEqual(call_number,len(calls))
                    self.assertEqual(before,self.dump())

    def test_partial_mutations_and_final_validation_failures_roll_back(self):
        before = self.dump()
        def audit_failure(*args,**kwargs): raise OSError('synthetic audit failure')
        original_insert = claims._insert
        def after_insert(state): original_insert(state); raise OSError('synthetic post-insert failure')
        original_final = claims._final_check
        def after_final(state): original_final(state); raise OSError('synthetic precommit failure')
        for target, name, fault in ((a,'_audit',audit_failure),(claims,'_insert',after_insert),(claims,'_final_check',after_final)):
            with self.subTest(stage=name), patch.object(target,name,side_effect=fault), self.assertRaises(OSError): self.acquire()
            self.assertEqual(before,self.dump())
        # Actual SQLite trigger faults at claim and history insertion stages;
        # exact schema validation itself is never relaxed in the product.
        for marker in ('claim','history'):
            def fail(state):
                pending = state.pending_claim
                if marker == 'claim': pending['row'] = tuple('bad' if i == 0 else x for i,x in enumerate(pending['row']))
                else: pending['event_row'] = tuple(2 if i == 1 else x for i,x in enumerate(pending['event_row']))
                return original_insert(state)
            with patch.object(claims,'_insert',side_effect=fail), self.assertRaises(ValueError): self.acquire()
            self.assertEqual(before,self.dump())

    def test_authentication_must_cover_entire_fixed_lifetime(self):
        with a.connect(self.config.control,write=True) as control:
            control.execute('UPDATE recognition_admin_sessions SET expires=? WHERE token_hash=?',
                (a.timestamp(self.clock.return_value)+299,a.token_hash(self.f.session)))
            control.commit()
        before = self.dump()
        with self.assertRaisesRegex(ValueError,'runtime_claim_insufficient_authentication_lifetime'): self.acquire()
        self.assertEqual(before,self.dump())

    def test_post_insert_authentication_denial_cannot_commit_a_claim_or_revocations(self):
        before, real = self.dump(), claims._insert
        def deny(state):
            real(state)
            pending = state.pending_claim
            shared.validate(pending['view'],pending['snapshot'],'x'*32,primary_token=self.f.primary)
        with patch.object(claims,'_insert',side_effect=deny), self.assertRaises(ValueError): self.acquire()
        self.assertEqual(before,self.dump())

    def test_missing_schema_is_never_implicitly_installed(self):
        self.doCleanups()
        self.f = lifecycle.RuntimeExecutionAdmissionTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.config, self.clock = self.f.config, self.f.clock
        self.snapshot = self.f.assess()
        before = self.dump()
        with self.assertRaisesRegex(ValueError,'runtime_claim_schema_not_installed'): self.acquire()
        self.assertEqual(before,self.dump())

    def test_clock_expiry_pid_thread_and_no_renewal(self):
        receipt = self.acquire()
        body = json.loads(receipt.inspection_reference)
        with patch.object(os,'getpid',return_value=-1), self.assertRaises(ValueError): receipt.sha256
        with ThreadPoolExecutor(max_workers=1) as pool:
            with self.assertRaises(ValueError): pool.submit(lambda: receipt.sha256).result(timeout=5)
        clock = claims._receipts[receipt]['clock']
        base = clock.previous[2]
        self.clock.return_value = body['expires_at_utc']
        with patch.object(claims.time,'monotonic_ns',side_effect=[base+300*claims._NS]*2), self.assertRaises(ValueError): receipt.sha256
        self.assertEqual(body,json.loads(receipt.inspection_reference))
        with self.assertRaisesRegex(ValueError,'runtime_claim_already_acquired'): self.acquire()
        self.assertEqual((1,1),self.count())

    def test_generated_claim_tampering_fails_before_commit(self):
        before, real = self.dump(), claims._body
        changes = (('issued_at_utc','advance'),('issued_at_utc','nul'),
            ('expires_at_utc','advance'),('format','wrong-format'),('admission_sha256','bad'))
        for field,mutation in changes:
            def changed(*args):
                body = real(*args)
                if mutation == 'advance':
                    value = (utc(body[field])+timedelta(seconds=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
                else:
                    value = body[field]+'\0' if mutation == 'nul' else mutation
                self.assertNotEqual(body[field],value)  # Never a no-op as the trusted test clock advances.
                return dict(body,**{field:value})
            with self.subTest(field=field,mutation=mutation), patch.object(claims,'_body',side_effect=changed), self.assertRaises(ValueError): self.acquire()
            self.assertEqual(before,self.dump())

    def test_target_prohibited_writes_poison_and_never_commit(self):
        real = claims._insert
        for mode in ('DELETE','WAL'):
            self._journal(mode)
            before = self.dump()
            for sql in ('INSERT INTO recognition_execution_claims DEFAULT VALUES',
                        'UPDATE stop_review_assignments SET status=status','DELETE FROM recognition_frozen_events',
                        'CREATE TABLE prohibited(x)','PRAGMA query_only=OFF','COMMIT','ROLLBACK','BEGIN IMMEDIATE'):
                def attack(state):
                    self.assertEqual(1,state.target.execute('PRAGMA query_only').fetchone()[0])
                    # The actual guarded read facade, not a private raw handle.
                    # Lexical/lifecycle rejection poisons even before SQLite.
                    with self.assertRaises((ValueError,sqlite3.DatabaseError)):
                        state.body_target.execute(sql)
                    real(state)
                with self.subTest(mode=mode,sql=sql), patch.object(claims,'_insert',side_effect=attack), self.assertRaises(ValueError): self.acquire()
                self.assertEqual(before,self.dump())

    def test_commit_order_no_target_commit_and_no_escaped_live_registration(self):
        commit = owner._commit
        real_connect = a.sqlite3.connect
        class Target(sqlite3.Connection):
            def commit(self): raise AssertionError('target commit forbidden')
        def connect(*args,**kwargs):
            if str(args[0]).startswith(self.config.target.resolve().as_uri()): kwargs['factory'] = Target
            return real_connect(*args,**kwargs)
        def checked(state):
            self.assertEqual(1,state.target.execute('PRAGMA query_only').fetchone()[0])
            self.assertEqual(state.target_changes,state.target.total_changes)
            for path in (self.config.control,self.config.target):
                with closing(real_connect(path,timeout=0)) as lock:
                    with self.assertRaises(sqlite3.OperationalError): lock.execute('BEGIN IMMEDIATE')
            commit(state)
            with closing(real_connect(self.config.target,timeout=0)) as lock:
                with self.assertRaises(sqlite3.OperationalError): lock.execute('BEGIN IMMEDIATE')
        before_contexts = len(owner._contexts),len(shared._views),len(scope._claim_views)
        with patch.object(a.sqlite3,'connect',side_effect=connect), patch.object(owner,'_commit',side_effect=checked):
            self.acquire()
        import gc
        gc.collect()
        self.assertEqual(before_contexts,(len(owner._contexts),len(shared._views),len(scope._claim_views)))

    def test_uncertain_commit_before_and_after_engine_commit(self):
        for index, committed in enumerate((False,True)):
            if index: self.doCleanups(); self.setUp()
            original = a.sqlite3.connect
            class LostAcknowledgement(sqlite3.Connection):
                def commit(conn):
                    if committed: super(LostAcknowledgement,conn).commit()
                    raise OSError('synthetic commit acknowledgement lost')
            def connect(*args,**kwargs):
                if str(args[0]).startswith(self.config.control.resolve().as_uri()): kwargs['factory'] = LostAcknowledgement
                return original(*args,**kwargs)
            before_receipts = len(claims._receipts)
            with patch.object(a.sqlite3,'connect',side_effect=connect), self.assertRaises(claims.ClaimCommitOutcome) as caught:
                self.acquire()
            self.assertIsNone(caught.exception.control_committed)
            self.assertNotIn(self.f.session,str(caught.exception))
            self.assertNotIn(self.f.primary,caught.exception.inspection_reference)
            self.assertEqual(before_receipts,len(claims._receipts))
            self.assertEqual((int(committed),)*2,self.count())
            with patch.object(a,'target_identity',side_effect=authorization.target_identity):
                result = claims.inspect_acquisition(self.config,caught.exception.inspection_reference)
            self.assertEqual('PRESENT_EXACT' if committed else 'ABSENT_AT_SNAPSHOT',result['status'])
            self.assertFalse(result['retry_authorized'])

    def test_silent_commit_failure_never_publishes_a_receipt(self):
        original = a.sqlite3.connect
        class NoCommit(sqlite3.Connection):
            def commit(conn): pass  # Driver fault: transaction remains pending.
        def connect(*args,**kwargs):
            if str(args[0]).startswith(self.config.control.resolve().as_uri()): kwargs['factory'] = NoCommit
            return original(*args,**kwargs)
        before = self.dump()
        with patch.object(a.sqlite3,'connect',side_effect=connect), self.assertRaises(claims.ClaimCommitOutcome) as caught:
            self.acquire()
        self.assertIsNone(caught.exception.control_committed)
        self.assertEqual(before,self.dump())

    def test_cleanup_failure_after_commit_is_durable_without_handle(self):
        original = a.connect
        @contextmanager
        def failing(path,**kwargs):
            with original(path,**kwargs) as conn: yield conn
            if path == self.config.control and kwargs.get('write'): raise OSError('synthetic cleanup failure')
        count = len(claims._receipts)
        with patch.object(a,'connect',side_effect=failing), self.assertRaises(claims.ClaimCommitOutcome) as caught:
            self.acquire()
        self.assertIs(True,caught.exception.control_committed)
        self.assertEqual(count,len(claims._receipts))
        self.assertEqual((1,1),self.count())

    def test_clock_change_at_actual_commit_boundary_rejects(self):
        before, commit = self.dump(), owner._commit
        def expire(state):
            self.clock.return_value = f.at(1230)
            commit(state)
        with patch.object(owner,'_commit',side_effect=expire), self.assertRaises(ValueError): self.acquire()
        self.assertEqual(before,self.dump())

    def test_inspection_is_strict_read_only_data_and_never_adopts(self):
        receipt = self.acquire()
        reference = receipt.inspection_reference
        before = self.dump()
        with patch.object(a,'target_identity',side_effect=authorization.target_identity):
            self.assertEqual('PRESENT_EXACT',claims.inspect_acquisition(self.config,reference)['status'])
            changed = dict(json.loads(reference),approval_sha256='0'*64)
            self.assertEqual('PRESENT_CONFLICT',claims.inspect_acquisition(self.config,canonical(changed))['status'])
        # Runtime identity is not a deployment-side inspection exemption.
        self.assertEqual('UNKNOWN',claims.inspect_acquisition(self.config,reference)['status'])
        with self.assertRaises(ValueError): claims.inspect_acquisition(self.config,reference+' ')
        self.assertEqual(before,self.dump())

    def _journal(self,mode):
        for path in (self.config.control,self.config.target):
            with closing(sqlite3.connect(path)) as conn: conn.execute('PRAGMA journal_mode='+mode)

    def _options(self,stage='normal',bad_host=False):
        return dict(paths=[str(self.config.target),str(self.config.control),str(self.config.key_file)],
            now=self.clock.return_value,anchor=self.child_clock_anchor,primary=self.f.primary,session=self.f.session,
            approval_id=self.f.approval['approval']['approval_id'],approval_sha256=self.f.approval['approval_sha256'],
            reference=self.f.reference,stage=stage,bad_host=bad_host)

    def _start(self,stage='normal',bad_host=False):
        child = subprocess.Popen([sys.executable,'-B','-u','-c',_CHILD],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,text=True)
        self.addCleanup(self._stop,child)
        child.stdin.write(json.dumps(self._options(stage,bad_host))+'\n'); child.stdin.flush()
        ready = child.stdout.readline().strip()
        if ready != 'READY':
            _,error = child.communicate(timeout=30)
            self.fail('child did not establish admission: '+error)
        return child

    def _go(self,child):
        child.stdin.write('GO\n'); child.stdin.flush()

    def _stop(self,child):
        if child.poll() is None: child.kill()
        child.communicate(timeout=30)

    def _result(self,child):
        output,error = child.communicate(timeout=30)
        self.assertEqual(0,child.returncode,error)
        return json.loads(output.strip().splitlines()[-1])

    def _concurrent(self,mode,bad_host=False):
        self._journal(mode)
        target_before = self.dump()[1]
        children = (self._start(),self._start(bad_host=bad_host))
        for child in children: self._go(child)
        results = [self._result(child) for child in children]
        self.assertEqual(['ACQUIRED','REJECTED'],sorted(row['status'] for row in results))
        if not bad_host:
            self.assertEqual(['runtime_claim_already_acquired'],[row['code'] for row in results if row['status']=='REJECTED'])
        self.assertEqual((1,1),self.count())
        self.assertEqual(target_before,self.dump()[1])

    def test_single_winner_delete(self): self._concurrent('DELETE')
    def test_single_winner_wal(self): self._concurrent('WAL')
    def test_different_runtime_scopes_delete(self): self._concurrent('DELETE',True)
    def test_different_runtime_scopes_wal(self): self._concurrent('WAL',True)

    def test_mutation_races_fence_pending_acquisition(self):
        cases = [(mode,kind) for mode in ('DELETE','WAL') for kind in ('approval','generation','dependency','stop')]
        for index, (mode,kind) in enumerate(cases):
            if index: self.doCleanups(); self.setUp()
            self._journal(mode)
            child = self._start()
            path = self.config.target if kind == 'dependency' else self.config.control
            with a.connect(path,write=True) as conn:
                conn.execute('BEGIN IMMEDIATE')
                if kind == 'approval': approvals._invalidate_all(conn,'owner',self.clock.return_value,'concurrent invalidation')
                elif kind == 'generation':
                    row = conn.execute('SELECT * FROM recognition_admin_bindings ORDER BY generation DESC LIMIT 1').fetchone()
                    body = dict(json.loads(row['body_json']),generation=row['generation']+1,
                        runtime_profile_sha256=None,previous_sha256=row['body_sha256'],at_utc=self.clock.return_value)
                    conn.execute('INSERT INTO recognition_admin_bindings VALUES(?,?,?)',(body['generation'],canonical(body),digest(body)))
                    a._audit(conn,'test_generation_fenced','owner',self.clock.return_value,dict(generation=body['generation']))
                elif kind == 'dependency':
                    conn.execute("UPDATE stop_review_assignments SET status='assigned' WHERE id=(SELECT MIN(id) FROM stop_review_assignments)")
                else:
                    body = dict(active=True,sequence=1,previous_sha256=None)
                    conn.execute('INSERT INTO recognition_execution_stops VALUES(?,?,?)',(1,canonical(body),digest(body)))
                self._go(child)
                self.assertEqual('ACQUIRING',child.stdout.readline().strip())
                conn.commit()
            result = self._result(child)
            self.assertEqual('REJECTED',result['status'],kind)
            self.assertNotEqual('runtime_claim_clock_anomaly',result['code'],kind)
            expected = dict(approval='runtime_approval_not_current',generation='runtime_profile_not_enrolled',
                dependency='runtime_admission_dependencies_not_ready',stop='emergency_stop')
            self.assertEqual(expected[kind],result['code'],(mode,kind))
            self.assertEqual((0,0),self.count())

    def _crash_cases(self,mode):
        for index,(stage,expected) in enumerate((('before_insert',0),('after_insert',0),('before_commit',0),
                ('around_commit',None),('after_commit',1),('after_return',1),('connection_loss',0))):
            if index: self.doCleanups(); self.setUp()
            self._journal(mode)
            target_before = self.dump()[1]
            child = self._start(stage)
            self._go(child)
            self.assertEqual('ACQUIRING',child.stdout.readline().strip())
            line = child.stdout.readline().strip()
            if stage == 'connection_loss':
                result = json.loads(line)
                self.assertEqual('REJECTED',result['status'])
            else:
                self.assertTrue(line.startswith('PHASE ') or stage == 'after_return',line)
                if stage == 'around_commit': self._go(child)
            self._stop(child)
            # Ordinary SQLite recovery in a DISPOSABLE store only. No checkpoint,
            # journal deletion, forced repair, retry, or production recovery code.
            with a.connect(self.config.control,write=True) as conn:
                conn.execute('BEGIN IMMEDIATE')
                administration_schema.check_control(conn)
                a._audit_head(conn)
                counts = tuple(conn.execute('SELECT count(*) FROM '+name).fetchone()[0] for name in (schema.CLAIMS,schema.HISTORY))
                self.assertIn(counts,((0,0),(1,1)))
                if expected is not None: self.assertEqual((expected,expected),counts,(mode,stage))
            self.assertEqual(target_before,self.dump()[1])
            if counts == (1,1):
                restart = self._start()
                self._go(restart)
                self.assertEqual('ACQUIRING',restart.stdout.readline().strip())
                self.assertEqual('REJECTED',self._result(restart)['status'])
                self.assertEqual((1,1),self.count())

    def test_crashes_connection_loss_restart_delete(self): self._crash_cases('DELETE')
    def test_crashes_connection_loss_restart_wal(self): self._crash_cases('WAL')


_CHILD = r'''
import json,sys,time,tempfile,re,os
from pathlib import Path
from dataclasses import replace
from datetime import timedelta
from urllib.parse import urlsplit
from urllib.request import url2pathname
options=json.loads(sys.stdin.readline())
allowed=(Path(tempfile.gettempdir()).resolve(),Path.cwd()/'.tmp',Path.cwd()/'tests')
assert all(any(Path(p).resolve().is_relative_to(base) for base in allowed) for p in options['paths'])
databases={Path(p).resolve() for p in options['paths'][:2]}
def guard(event,args):
    if event=='sqlite3.connect':
        raw=os.fsdecode(os.fspath(args[0]))
        if raw in ('',':memory:'): return
        if raw.startswith('file:'):
            uri=urlsplit(raw)
            if uri.netloc not in ('','localhost'): raise PermissionError('child_nonlocal_database_denied')
            raw=url2pathname(uri.path)
        if Path(raw).resolve() not in databases: raise PermissionError('child_nonfixture_database_denied')
    elif event in ('socket.connect','socket.getaddrinfo'):
        raise PermissionError('child_network_denied')
sys.addaudithook(guard)
from src.review.recognition import administration as a,dependencies,runtime_validation as v
from src.review.recognition import runtime_execution_admission as d,runtime_execution_claims as c,runtime_claim_validation as o
from src.review.recognition.trust import utc
base=a.target_identity
def observed(subject):
    value=base(subject)
    return replace(value,hostname='synthetic-web',device=value.device+1)
a.target_identity=dependencies.target_identity=observed
origin=utc(options['now'])
v._utc_now=lambda:(origin+timedelta(seconds=(time.monotonic_ns()-options['anchor'])//1_000_000_000)).strftime('%Y-%m-%dT%H:%M:%SZ')
config=a.LocalAdministration(*(Path(x) for x in options['paths']))
snapshot=d.assess(config,options['session'],options['approval_id'],approval_sha256=options['approval_sha256'],reference=options['reference'],primary_token=options['primary'])
stage=options['stage']
insert,commit=c._insert,o._commit
def pause(name):
    print('PHASE '+name,flush=True)
    sys.stdin.readline()
def fault_insert(state):
    if stage=='before_insert': pause(stage)
    insert(state)
    if stage=='after_insert': pause(stage)
    if stage=='connection_loss': state.control.close()
def fault_commit(state):
    if stage in ('before_commit','around_commit'): pause(stage)
    commit(state)
    if stage in ('after_commit','around_commit'): pause('after_commit')
c._insert,o._commit=fault_insert,fault_commit
print('READY',flush=True)
sys.stdin.readline()
if options['bad_host']:
    def wrong(subject): return replace(observed(subject),hostname='other-runtime')
    a.target_identity=wrong
print('ACQUIRING',flush=True)
try:
    receipt=c.acquire(config,snapshot,options['session'],primary_token=options['primary'])
    print(json.dumps(dict(status='ACQUIRED',reference=receipt.inspection_reference)),flush=True)
    if stage=='after_return': sys.stdin.readline()
except Exception as error:
    code=getattr(error,'code',None)
    if code is None:
        message=str(error)
        code=message if isinstance(error,ValueError) and re.fullmatch('[a-z0-9_:]{1,200}',message) else type(error).__name__
    print(json.dumps(dict(status='REJECTED',code=code)),flush=True)
'''


class ClaimClockTests(unittest.TestCase):
    def test_quantized_clock_consistency(self):
        with (patch.object(runtime,'_utc_now',side_effect=[f.at(930),f.at(930),f.at(931)]),
              patch.object(claims.time,'monotonic_ns',side_effect=[0,1,500_000_000,500_000_001,1_000_000_000,1_000_000_001])):
            clock = claims._Clock()
            self.assertEqual(a.timestamp(f.at(930)),clock.read()[1])
            self.assertEqual(a.timestamp(f.at(931)),clock.read()[1])

    def test_rollback_stall_forward_jump_and_monotonic_anomaly(self):
        cases = ((f.at(929),(2,3)),(f.at(930),(2_000_000_000,2_000_000_001)),
                 (f.at(960),(2,3)),(f.at(930),(0,0)),(f.at(930),(True,True)))
        for next_utc, reading in cases:
            with self.subTest(utc=next_utc,reading=reading):
                with patch.object(runtime,'_utc_now',side_effect=[f.at(930),next_utc]), patch.object(
                        claims.time,'monotonic_ns',side_effect=[0,1,*reading]):
                    clock = claims._Clock()
                    with self.assertRaisesRegex(ValueError,'runtime_claim_clock_anomaly'): clock.read()

    def test_exact_expiry_boundary_and_inconsistent_lifetime(self):
        for seconds,expires,valid in ((299,1230,True),(300,1230,False),(0,1231,False)):
            with self.subTest(seconds=seconds,expires=expires):
                with patch.object(runtime,'_utc_now',side_effect=[f.at(930),f.at(930+seconds)]), patch.object(
                        claims.time,'monotonic_ns',side_effect=[0,1,seconds*claims._NS+2,seconds*claims._NS+3]):
                    clock = claims._Clock()
                    clock.issued = clock.previous
                    pending = dict(clock=clock,body=dict(issued_at_utc=f.at(930),expires_at_utc=f.at(expires)))
                    if valid: self.assertEqual(a.timestamp(f.at(1229)),claims._live_time(pending))
                    else:
                        with self.assertRaises(ValueError): claims._live_time(pending)

    def test_malformed_utc_is_rejected(self):
        for value in ('2099-01-01T00:00:00+00:00','2099-01-01T00:00:00Z\0',True,1.5):
            with patch.object(runtime,'_utc_now',return_value=value), self.assertRaises((ValueError,TypeError)):
                claims._Clock()
