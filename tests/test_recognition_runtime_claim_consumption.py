"""4d-2 guarded disposable lifecycle: consumption never writes the target."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, contextmanager
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
import json
import os
import pickle
import sqlite3
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch

from src.review.recognition import runtime_claim_consumption as consume, runtime_execution_claims as claims
from src.review.recognition import runtime_claim_validation as owner, runtime_execution_claim_schema as schema
from src.review.recognition import runtime_admission_validation as shared, runtime_execution_admission as admission
from src.review.recognition import administration as a, administration_schema, authorization, approvals
from src.review.recognition import writer_boundary, local_execution, local_readiness, execution, production_operations
from src.review.recognition.rules import canonical, digest
from tests import test_recognition_runtime_execution_claims as fixture


class RuntimeClaimConsumptionTests(unittest.TestCase):
    def setUp(self):
        self.f = fixture.RuntimeExecutionClaimTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.config = self.f.config

    def acquire(self):
        return self.f.acquire()

    @contextmanager
    def clock_at(self,value):
        original=self.f.clock.side_effect
        self.f.clock.side_effect=lambda:value
        try:yield
        finally:self.f.clock.side_effect=original

    def consume(self, claim, **changes):
        options = dict(config=self.config,claim=claim,operation_context=self.f.snapshot,
                       session_token=self.f.f.session,primary_token=self.f.f.primary)
        options.update(changes)
        return consume.consume(**options)

    def test_real_lifecycle_consumption_exact_history_audit_and_no_downstream_authority(self):
        claim = self.acquire()
        before = self.f.dump()
        registries = dict(writer_boundary._leases),dict(writer_boundary._local_leases),dict(production_operations._contexts)
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('no key reads')):
            with self.consume(claim) as handoff:
                binding = handoff.snapshot
                self.assertEqual(claim.sha256,binding['claim_sha256'])
                self.assertEqual(claim.snapshot,binding['claim'])
                self.assertEqual('CONSUMED',binding['consumption']['state'])
                self.assertEqual(2,binding['consumption']['sequence'])
                self.assertEqual(self.f.snapshot.snapshot['proposal'],binding['operation'])
                self.assertEqual(binding['operation']['writer_manifest_sha256'],binding['manifest_sha256'])
                with self.assertRaises(TypeError): binding['claim']['state'] = 'EXECUTING'
                self.assertFalse(writer_boundary.verify_local(handoff,self.config.target,{}))
                self.assertFalse(writer_boundary.verify_local(claim,self.config.target,{}))
                for token in (handoff,claim):
                    with self.assertRaises(ValueError): writer_boundary.acquire(token,self.config.target,{})
                    with self.assertRaises(ValueError): execution._context(token)
                    with self.assertRaises(ValueError): production_operations.context_data(token)
                    self.assertEqual('BLOCKED',local_execution.execute_approved_operation(token,self.f.f.session,
                        self.f.f.approval['approval']['approval_id'],now=self.f.clock.return_value).admission)
                for name in ('cursor','target','control','execute','commit','rollback','writer','canonical_json'):
                    self.assertFalse(hasattr(handoff,name))
                with self.assertRaises(TypeError): pickle.dumps(handoff)
                with self.assertRaises(TypeError): consume.ExecutionHandoff()
                self.assertEqual(binding,consume.take_handoff(handoff))
                with self.assertRaises(ValueError): handoff.snapshot
                with self.assertRaises(ValueError): consume.take_handoff(handoff)
        with self.assertRaises(ValueError): handoff.snapshot
        after = self.f.dump()
        self.assertEqual(before[1],after[1])
        for name in before[0].keys()-{schema.HISTORY,'recognition_admin_audit'}:
            self.assertEqual(before[0][name],after[0][name],name)
        self.assertEqual((1,2),self.f.count())
        self.assertEqual(len(before[0]['recognition_admin_audit'])+1,len(after[0]['recognition_admin_audit']))
        self.assertEqual(registries,(dict(writer_boundary._leases),dict(writer_boundary._local_leases),dict(production_operations._contexts)))
        self.assertFalse(local_readiness.assess(self.config,now=self.f.clock.return_value)['activation_ready'])
        with a.connect(self.config.control) as control:
            administration_schema.check_control(control)
            bound=json.loads(control.execute('SELECT body_json FROM recognition_admin_bindings ORDER BY generation DESC LIMIT 1').fetchone()[0])
            self.assertEqual('NOT_ACTIVATED',bound['production_state'])
        with self.assertRaisesRegex(ValueError,'runtime_claim_not_consumable'):
            with self.consume(claim): self.fail('second handoff')
        self.assertEqual(after,self.f.dump())

    def test_original_context_and_registered_claim_required(self):
        claim=self.acquire()
        before=self.f.dump()
        for bad in (claim.inspection_reference,dict(claim.snapshot),object.__new__(claims.ExecutionClaim)):
            with self.subTest(input=type(bad)),self.assertRaises(ValueError):
                with self.consume(bad): self.fail('detached claim')
        for bad in (self.f.snapshot.canonical_json,dict(self.f.snapshot.snapshot),object.__new__(admission.ExecutionAdmission)):
            with self.assertRaises(ValueError):
                with self.consume(claim,operation_context=bad): self.fail('detached context')
        newer=self.f.f.assess()
        # Even a genuine context cannot substitute a different bound digest.
        with patch.dict(admission._snapshots[newer],sha256='0'*64),self.assertRaises(ValueError):
            with self.consume(claim,operation_context=newer): self.fail('replacement context')
        with self.assertRaises(ValueError):
            with self.consume(claim,config=replace(self.config,target=self.config.control)): self.fail('replacement target')
        for key in ('operation','target','manifest','duration','approval','generation','profile'):
            with self.subTest(keyword=key),self.assertRaises(TypeError):
                with self.consume(claim,**{key:'replacement'}):self.fail('caller replacement scope')
        self.assertEqual(before,self.f.dump())

    def test_claim_digest_and_indexed_identity_mismatch_rejected(self):
        claim=self.acquire()
        before=self.f.dump()
        value=claims._receipts[claim]
        for key,replacement in (('sha256','0'*64),('json',value['json']+' ')):
            with self.subTest(key=key),patch.dict(value,**{key:replacement}),self.assertRaises(ValueError):
                with self.consume(claim): self.fail('tampered receipt')
        for field,replacement in (('format','wrong'),('state','CONSUMED')):
            with self.subTest(field=field),patch.dict(value,body=dict(value['body'],**{field:replacement})),self.assertRaisesRegex(ValueError,'runtime_consumption_claim_body_mismatch'):
                with self.consume(claim):self.fail('receipt body disagrees with durable digest')
        self.assertEqual(before,self.f.dump())

    def test_initial_authentication_denial_keeps_existing_error_semantics(self):
        claim=self.acquire()
        with self.assertRaises(ValueError) as caught:
            with self.consume(claim,session_token='x'*32):self.fail('invalid authentication')
        self.assertNotIsInstance(caught.exception,consume.ConsumptionCommitOutcome)
        self.assertNotIsInstance(caught.exception,KeyError)
        self.assertEqual((1,1),self.f.count())

    def test_clearing_stop_does_not_revive_original_claim_scope(self):
        claim=self.acquire()
        with a.connect(self.config.control,write=True) as control:
            previous=None
            for sequence,active in ((1,True),(2,False)):
                body=dict(active=active,sequence=sequence,previous_sha256=previous)
                control.execute('INSERT INTO recognition_execution_stops VALUES(?,?,?)',(sequence,canonical(body),digest(body)))
                previous=digest(body)
            control.commit()
        before=self.f.dump()
        with self.assertRaisesRegex(ValueError,'runtime_admission_snapshot_stale'):
            with self.consume(claim):self.fail('stop cleared into old scope')
        self.assertEqual(before,self.f.dump())

    def test_full_scope_fences_initial_and_final_after_real_validation(self):
        claim=self.acquire()
        before,real=self.f.dump(),shared._collect
        paths=[('runtime_scope',k) for k in ('generation','installation_id','target_id','owner_id','runtime_profile_sha256','binding_sha256','auth_epoch','mfa_epoch')]
        paths += [('proposal','writer_manifest_sha256'),('reference','acknowledgement_sha256'),('approval_sha256',),
            ('approval_history_sha256',),('dependency_snapshot','format'),('emergency_stop_snapshot','sequence'),
            ('target_snapshot','target','schema_sha256')]
        for prefix in (('target_snapshot','target','observation'),('target_snapshot','control_identity')):
            paths += [prefix+(key,) for key in ('hostname','database','device','inode')]
        for stage in (1,2):
            for path in paths:
                calls=[]
                def changed(*args,**kwargs):
                    result=deepcopy(real(*args,**kwargs)); calls.append(True)
                    if len(calls)==stage:
                        part=result
                        for key in path[:-1]: part=part[key]
                        old=part[path[-1]]
                        part[path[-1]]=old+1 if type(old) is int else old+'-wrong'
                    return result
                with self.subTest(stage=stage,path=path),patch.object(shared,'_collect',side_effect=changed),self.assertRaisesRegex(ValueError,'runtime_admission_snapshot_stale'):
                    with self.consume(claim): self.fail('stale scope')
                self.assertEqual(stage,len(calls))
                self.assertEqual(before,self.f.dump())

    def test_rollback_at_history_audit_final_and_denial_stages(self):
        claim=self.acquire();before=self.f.dump()
        reached=[]
        insert,final=consume._insert,consume._final_check
        def after_insert(state): insert(state);reached.append('after_insert');raise OSError('test after history/audit')
        def audit(*args,**kwargs): reached.append('audit');raise OSError('test audit')
        def after_final(state): final(state);reached.append('after_final');raise OSError('test final')
        def denial(state):
            insert(state)
            reached.append('denial')
            p=state.pending_claim
            shared.validate(p['view'],p['snapshot'],'x'*32,primary_token=self.f.f.primary)
        for module,name,fn in ((consume,'_insert',after_insert),(a,'_audit',audit),(consume,'_final_check',after_final),(consume,'_insert',denial)):
            reached.clear()
            with self.subTest(stage=name),patch.object(module,name,side_effect=fn),self.assertRaises((ValueError,OSError)):
                with self.consume(claim):self.fail('failed transaction published')
            self.assertEqual([fn.__name__],reached)
            self.assertEqual(before,self.f.dump())
        def invalid_event(state):
            p=state.pending_claim
            p['event_row']=tuple(3 if i==1 else x for i,x in enumerate(p['event_row']))
            insert(state)
        with patch.object(consume,'_insert',side_effect=invalid_event),self.assertRaises(sqlite3.IntegrityError):
            with self.consume(claim):self.fail('illegal history')
        self.assertEqual(before,self.f.dump())

    def test_expiry_and_recent_approval_scope_are_independently_enforced(self):
        for index,kind in enumerate(('claim','ceremony')):
            if index:self.doCleanups();self.setUp()
            if kind=='ceremony':
                with a.connect(self.config.control) as control:
                    moment=control.execute("SELECT MIN(json_extract(body_json,'$.subject.expires_at_utc')) FROM recognition_admin_audit WHERE json_extract(body_json,'$.action') IN ('runtime_approval_step_up_issued','runtime_approval_confirmation_issued')").fetchone()[0]
                # Acquire late in the original approval ceremony window, using
                # its unchanged historical artifacts and genuine original 4d-0.
                self.f.clock.return_value=(fixture.utc(moment)-timedelta(seconds=100)).strftime('%Y-%m-%dT%H:%M:%SZ')
            claim=self.acquire();before=self.f.dump()
            if kind=='claim':moment=claim.snapshot['expires_at_utc']
            else:self.assertLess(a.timestamp(moment),a.timestamp(claim.snapshot['expires_at_utc']))
            clock=claims._receipts[claim]['clock']
            monotonic=clock.previous[2]+(a.timestamp(moment)-clock.previous[1])*claims._NS
            code='runtime_claim_expired_or_invalid_time' if kind=='claim' else 'runtime_consumption_ceremony_expired'
            with self.subTest(kind=kind),self.clock_at(moment),patch.object(
                claims.time,'monotonic_ns',return_value=monotonic),self.assertRaisesRegex(ValueError,code):
                with self.consume(claim):self.fail('expired scope')
            self.assertEqual(before,self.f.dump())

    def test_rollback_anomaly_malformed_time_and_lifetime_rejected(self):
        claim=self.acquire();before=self.f.dump();entry=claims._receipts[claim]
        original=entry['body'];bad=dict(original,expires_at_utc=original['issued_at_utc'])
        with patch.dict(entry,body=bad),self.assertRaisesRegex(ValueError,'runtime_claim_expired_or_invalid_time'):
            with self.consume(claim):self.fail('invalid lifetime')
        for value in (fixture.f.at(1),original['issued_at_utc']+'\0',True):
            with self.subTest(value=value),self.clock_at(value),self.assertRaises((ValueError,TypeError)):
                with self.consume(claim):self.fail('invalid clock')
        self.assertEqual(before,self.f.dump())

    def test_pid_thread_context_exit_and_local_spend(self):
        claim=self.acquire()
        with self.consume(claim) as handoff:
            with patch.object(os,'getpid',return_value=-1),self.assertRaises(ValueError):handoff.snapshot
            with ThreadPoolExecutor(max_workers=1) as pool:
                with self.assertRaises(ValueError):pool.submit(lambda:handoff.snapshot).result(timeout=5)
            with patch.object(claims,'_live_time',side_effect=ValueError('expired')),self.assertRaises(ValueError):handoff.snapshot
        with self.assertRaises(ValueError):consume.take_handoff(handoff)

    def test_handoff_deadline_and_publication_failure_do_not_restore_claim(self):
        claim=self.acquire()
        with self.consume(claim) as handoff:
            entry=consume._handoffs[handoff]
            now=entry['clock'].previous[1]
            with patch.dict(entry,deadlines=((now,'expired_handoff_authentication'),)),self.assertRaisesRegex(ValueError,'expired_handoff_authentication'):
                consume.take_handoff(handoff)
        self.doCleanups();self.setUp();claim=self.acquire()
        class FailedPublication(dict):
            def __setitem__(self,key,value):raise OSError('synthetic publication failure')
        with patch.object(consume,'_handoffs',FailedPublication()),self.assertRaises(consume.ConsumptionCommitOutcome) as caught:
            with self.consume(claim):self.fail('failed publication yielded')
        self.assertIs(True,caught.exception.control_committed)
        self.assertEqual((1,2),self.f.count())
        with self.assertRaisesRegex(ValueError,'runtime_claim_not_consumable'):
            with self.consume(claim):self.fail('publication failure restored claim')

    def test_two_consumers_one_winner_durable_history_not_local_claim_flags(self):
        claim=self.acquire(); barrier=threading.Barrier(2)
        def other():
            barrier.wait(timeout=5)
            with self.assertRaises(ValueError):
                with self.consume(claim):self.fail('cross-thread claim')
            return 'REJECTED'
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(other);barrier.wait(timeout=5)
            with self.consume(claim):pass
            self.assertEqual('REJECTED',future.result(timeout=5))
        # The receipt has no consumed flag. The second same-thread attempt must
        # consult the durable history and fail, even though its receipt is live.
        self.assertNotIn('consumed',claims._receipts[claim])
        with self.assertRaisesRegex(ValueError,'runtime_claim_not_consumable'):
            with self.consume(claim):self.fail('duplicate durable consumption')
        with self.assertRaisesRegex(ValueError,'runtime_claim_already_acquired'):self.acquire()
        self.assertEqual((1,2),self.f.count())

    def test_target_guards_and_control_issuance_denial_delete_wal(self):
        claim=self.acquire();insert=consume._insert
        for mode in ('DELETE','WAL'):
            self.f._journal(mode);before=self.f.dump()
            for sql in ('INSERT INTO recognition_execution_claims DEFAULT VALUES',
                'UPDATE stop_review_assignments SET status=status','DELETE FROM recognition_execution_seals',
                'CREATE TABLE forbidden(x)','PRAGMA query_only=OFF','COMMIT','ROLLBACK'):
                def attack(state):
                    with self.assertRaises((ValueError,sqlite3.Error)):state.body_target.execute(sql)
                    insert(state)
                with self.subTest(mode=mode,sql=sql),patch.object(consume,'_insert',side_effect=attack),self.assertRaises(ValueError):
                    with self.consume(claim):self.fail('poisoned target')
                self.assertEqual(before,self.f.dump())
            def issuance(state):
                state.claim_write=True
                try:
                    state.control.set_authorizer(state.control_authorizer)
                    with self.assertRaises(sqlite3.DatabaseError):state.control.execute('INSERT INTO '+schema.CLAIMS+' DEFAULT VALUES')
                finally:state.claim_write=False
                insert(state)
            with patch.object(consume,'_insert',side_effect=issuance),self.assertRaises(ValueError):
                with self.consume(claim):self.fail('consumption issued a claim')
            self.assertEqual(before,self.f.dump())

    def test_target_reservation_through_control_commit_and_no_target_commit(self):
        claim=self.acquire();commit=owner._commit;connect=a.sqlite3.connect
        class Target(sqlite3.Connection):
            def commit(self):raise AssertionError('target commit')
        def factory(*args,**kwargs):
            if str(args[0]).startswith(self.config.target.resolve().as_uri()):kwargs['factory']=Target
            return connect(*args,**kwargs)
        def checked(state):
            for path in (self.config.control,self.config.target):
                with closing(connect(path,timeout=0)) as conn:
                    with self.assertRaises(sqlite3.OperationalError):conn.execute('BEGIN IMMEDIATE')
            commit(state)
            with closing(connect(self.config.target,timeout=0)) as conn:
                with self.assertRaises(sqlite3.OperationalError):conn.execute('BEGIN IMMEDIATE')
        before=self.f.dump()[1]
        with patch.object(a.sqlite3,'connect',side_effect=factory),patch.object(owner,'_commit',side_effect=checked):
            with self.consume(claim):pass
        self.assertEqual(before,self.f.dump()[1])

    def test_commit_uncertainty_inspection_and_cleanup_failure_publish_no_handoff(self):
        for index,stage in enumerate(('before','after','cleanup')):
            if index:self.doCleanups();self.setUp()
            claim=self.acquire();connect=a.sqlite3.connect;original=a.connect
            class Lost(sqlite3.Connection):
                def commit(conn):
                    if stage=='after':super(Lost,conn).commit()
                    raise OSError('synthetic lost acknowledgement')
            def factory(*args,**kwargs):
                if str(args[0]).startswith(self.config.control.resolve().as_uri()):kwargs['factory']=Lost
                return connect(*args,**kwargs)
            @contextmanager
            def cleanup(path,**kwargs):
                with original(path,**kwargs) as conn:yield conn
                if path==self.config.control and kwargs.get('write'):raise OSError('synthetic cleanup')
            patcher=patch.object(a,'connect',side_effect=cleanup) if stage=='cleanup' else patch.object(a.sqlite3,'connect',side_effect=factory)
            before=len(consume._handoffs)
            with patcher,self.assertRaises(consume.ConsumptionCommitOutcome) as caught:
                with self.consume(claim):self.fail('uncertain handoff')
            self.assertEqual(before,len(consume._handoffs))
            self.assertEqual((1,1 if stage=='before' else 2),self.f.count())
            self.assertEqual(True if stage=='cleanup' else None,caught.exception.control_committed)
            for secret in (self.f.f.primary,self.f.f.session):self.assertNotIn(secret,caught.exception.inspection_reference)
            with patch.object(a,'target_identity',side_effect=authorization.target_identity):
                inspected=consume.inspect_consumption(self.config,caught.exception.inspection_reference)
            self.assertEqual('ABSENT_AT_SNAPSHOT' if stage=='before' else 'PRESENT_EXACT',inspected['status'])
            self.assertFalse(inspected['retry_authorized'])

    def _start(self, stage='normal'):
        child=subprocess.Popen(_child_command(),stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,text=True)
        self.addCleanup(self.f._stop,child)
        child.stdin.write(json.dumps(self.f._options(stage))+'\n');child.stdin.flush()
        self.assertEqual('WORKER '+str(child.pid),child.stdout.readline().strip())
        line=child.stdout.readline().strip()
        if line!='READY':
            _,error=child.communicate(timeout=30)
            self.fail('child failed before consumption: '+line+' '+error)
        return child

    def test_crash_connection_loss_restart_delete(self):self._crashes('DELETE')
    def test_crash_connection_loss_restart_wal(self):self._crashes('WAL')

    def _crashes(self,mode):
        stages=(('before_history',1),('after_history',1),('before_commit',1),('around_commit',None),
                ('after_commit',2),('after_yield',2),('connection_loss',1))
        for index,(stage,expected) in enumerate(stages):
            if index:self.doCleanups();self.setUp()
            self.f._journal(mode);target_before=self.f.dump()[1]
            child=self._start(stage);self.f._go(child)
            self.assertEqual('CONSUMING',child.stdout.readline().strip())
            line=child.stdout.readline().strip()
            if stage=='connection_loss':self.assertEqual('REJECTED',json.loads(line)['status'])
            else:
                self.assertTrue(line.startswith('PHASE '),line)
                if stage=='around_commit':self.f._go(child)
            self.f._stop(child)
            # Normal SQLite recovery in a disposable store only; no checkpoint,
            # forced repair, retry, or production recovery path.
            with a.connect(self.config.control,write=True) as control:
                control.execute('BEGIN IMMEDIATE')
                administration_schema.check_control(control);a._audit_head(control)
                states=[row[0] for row in control.execute('SELECT state FROM '+schema.HISTORY+' ORDER BY sequence')]
                self.assertIn(states,(['ISSUED'],['ISSUED','CONSUMED']))
                if expected is not None:self.assertEqual(expected,len(states),(mode,stage))
            self.assertEqual(target_before,self.f.dump()[1])
            # A new process performs fresh auth/admission validation but cannot
            # acquire/adopt the durable old claim, consumed or otherwise.
            restart=subprocess.run(_child_command(),
                input=json.dumps(self.f._options('restart'))+'\nGO\n',capture_output=True,text=True,timeout=30)
            self.assertEqual(0,restart.returncode,restart.stderr)
            result=json.loads(restart.stdout.strip().splitlines()[-1])
            self.assertEqual('REJECTED',result['status'])
            self.assertEqual('runtime_claim_already_acquired',result['code'])

    def test_reserved_scope_mutation_races_delete_wal(self):
        cases=[(mode,kind) for mode in ('DELETE','WAL') for kind in
               ('auth','mfa','approval','dependency','generation','stop')]
        for index,(mode,kind) in enumerate(cases):
            if index:self.doCleanups();self.setUp()
            self.f._journal(mode);child=self._start()
            path=self.config.target if kind in ('dependency','auth') else self.config.control
            with a.connect(path,write=True) as conn:
                conn.execute('BEGIN IMMEDIATE')
                now=fixture.runtime._utc_now()
                if kind=='auth':conn.execute('UPDATE '+administration_schema.TARGET_TABLE+' SET auth_epoch=auth_epoch+1')
                elif kind=='mfa':conn.execute('UPDATE recognition_admin_mfa SET epoch=epoch+1')
                elif kind=='approval':approvals._invalidate_all(conn,'owner',now,'consumption race')
                elif kind=='dependency':conn.execute("UPDATE stop_review_assignments SET status='assigned' WHERE id=(SELECT MIN(id) FROM stop_review_assignments)")
                elif kind=='generation':
                    row=conn.execute('SELECT * FROM recognition_admin_bindings ORDER BY generation DESC LIMIT 1').fetchone()
                    body=dict(json.loads(row['body_json']),generation=row['generation']+1,runtime_profile_sha256=None,
                              previous_sha256=row['body_sha256'],at_utc=now)
                    conn.execute('INSERT INTO recognition_admin_bindings VALUES(?,?,?)',(body['generation'],canonical(body),digest(body)))
                    a._audit(conn,'test_generation_fence','owner',now,dict(generation=body['generation']))
                else:
                    body=dict(active=True,sequence=1,previous_sha256=None)
                    conn.execute('INSERT INTO recognition_execution_stops VALUES(?,?,?)',(1,canonical(body),digest(body)))
                self.f._go(child)
                self.assertEqual('CONSUMING',child.stdout.readline().strip())
                conn.commit()
            result=self.f._result(child)
            self.assertEqual('REJECTED',result['status'],(mode,kind))
            self.assertNotIn(result['code'],('runtime_claim_clock_anomaly','runtime_consumption_ceremony_expired'))
            if kind=='stop':self.assertEqual('emergency_stop',result['code'])
            if kind=='dependency':self.assertEqual('runtime_admission_dependencies_not_ready',result['code'])
            if kind=='approval':self.assertEqual('runtime_approval_not_current',result['code'])
            if kind=='generation':self.assertEqual('runtime_profile_not_enrolled',result['code'])
            if kind=='auth':self.assertEqual('primary_authentication_required',result['code'])
            if kind=='mfa':self.assertEqual('administrative_session_expired_or_revoked',result['code'])
            self.assertEqual((1,1),self.f.count())

    def test_history_database_constraint_serializes_two_consumer_transitions(self):
        # Both database contenders use the exact event/audit from a real,
        # successful consumption, replayed against the real durable ISSUED row.
        # Product APIs still require the original thread's genuine receipt.
        claim=self.acquire();captured=[]
        def capture(state):
            p=state.pending_claim
            captured.append((p['event_row'],p['audit_subject'],p['event']['at_utc']))
            raise RuntimeError('capture before write')
        with patch.object(consume,'_insert',side_effect=capture),self.assertRaises(RuntimeError):
            with self.consume(claim):self.fail('capture published')
        event,subject,now=captured[0]
        # Pass actor as immutable data; no cross-thread receipt access is allowed.
        actor=claim.snapshot['runtime_scope']['owner_id']
        barrier=threading.Barrier(2)
        def sql_contender():
            try:
                with a.connect(self.config.control,write=True) as conn:
                    barrier.wait(timeout=5)
                    conn.execute('BEGIN IMMEDIATE')
                    conn.execute('INSERT INTO '+schema.HISTORY+' VALUES(?,?,?,?,?,?,?)',event)
                    a._audit(conn,'runtime_execution_claim_state_changed',actor,now,subject)
                    conn.commit()
                return 'CONSUMED'
            except sqlite3.IntegrityError:return 'REJECTED'
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs=[pool.submit(sql_contender) for _ in range(2)]
            self.assertEqual(['CONSUMED','REJECTED'],sorted(job.result(timeout=10) for job in jobs))
        self.assertEqual((1,2),self.f.count())
        with self.assertRaisesRegex(ValueError,'runtime_claim_not_consumable'):
            with self.consume(claim):self.fail('SQL history ignored')


def _child_command():
    # Windows venv python.exe can be a redirector with a different worker PID.
    # Kill the actual SQLite process, not that launcher. Preserve the parent's
    # interpreter import environment; no key, DB or authority behavior changes.
    executable=getattr(sys,'_base_executable',None) or sys.executable
    bootstrap='import sys\nsys.path[:]=' + repr(sys.path) + '\n'
    return [executable,'-B','-u','-c',bootstrap+_CHILD]


_CHILD=fixture._CHILD.split('from src.review.recognition')[0]+r'''
print('WORKER '+str(os.getpid()),flush=True)
from datetime import timedelta
from dataclasses import replace
from src.review.recognition import administration as a,dependencies,runtime_validation as v
from src.review.recognition import runtime_execution_admission as d,runtime_execution_claims as c
from src.review.recognition import runtime_claim_consumption as consume,runtime_claim_validation as o
from src.review.recognition.trust import utc
base=a.target_identity
def observed(subject):
    value=base(subject)
    return replace(value,hostname='synthetic-web',device=value.device+1)
a.target_identity=dependencies.target_identity=observed
origin=utc(options['now'])
v._utc_now=lambda:(origin+timedelta(seconds=(time.monotonic_ns()-options['anchor'])//1_000_000_000)).strftime('%Y-%m-%dT%H:%M:%SZ')
config=a.LocalAdministration(*(Path(x) for x in options['paths']))
def reject(error):
    code=getattr(error,'code',None)
    if code is None:
        message=str(error)
        code=message if isinstance(error,ValueError) and re.fullmatch('[a-z0-9_:]{1,200}',message) else type(error).__name__
    print(json.dumps(dict(status='REJECTED',code=code)),flush=True)
try:
    snapshot=d.assess(config,options['session'],options['approval_id'],approval_sha256=options['approval_sha256'],reference=options['reference'],primary_token=options['primary'])
    claim=c.acquire(config,snapshot,options['session'],primary_token=options['primary'])
except Exception as error:
    reject(error)
    sys.exit(0)
stage=options['stage']
insert,commit=consume._insert,o._commit
def pause(name):
    print('PHASE '+name,flush=True)
    sys.stdin.readline()
def fault_insert(state):
    if stage=='before_history':pause(stage)
    insert(state)
    if stage=='after_history':pause(stage)
    if stage=='connection_loss':state.control.close()
def fault_commit(state):
    if stage in ('before_commit','around_commit'):pause(stage)
    commit(state)
    if stage in ('after_commit','around_commit'):pause('after_commit')
consume._insert,o._commit=fault_insert,fault_commit
print('READY',flush=True)
sys.stdin.readline()
print('CONSUMING',flush=True)
try:
    with consume.consume(config,claim,snapshot,options['session'],primary_token=options['primary']) as handoff:
        if stage=='after_yield':pause(stage)
        print(json.dumps(dict(status='CONSUMED')),flush=True)
except Exception as error:reject(error)
'''
