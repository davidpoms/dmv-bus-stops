"""Z7 invariants and bounded Z8 profiling; no metadata/target-entry invocation."""

from contextlib import ExitStack, contextmanager
import cProfile
from collections import Counter
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
import json
import os
from pathlib import Path
import pickle
import pstats
import sqlite3
import threading
import time
import unittest
import sys
from unittest.mock import patch

from src.review.recognition import administration as a, administration_schema as schema
from src.review.recognition import runtime_attempt_schema_manifest_observation as observation
from src.review.recognition import runtime_execution_coordinator as c, runtime_validation as runtime
from src.review.recognition import runtime_execution_claim_schema as claims
from src.review.recognition import runtime_execution_attempt_schema as attempts
from src.review.recognition import runtime_activation_authority_issuance as issuer
from src.review.recognition import writer_boundary, execution, local_execution, permanent
from src.review.recognition import runtime_scope_validation as shared, runtime_approval_contract as approval
from src.review.recognition import runtime_proposal_records as proposals, local_readiness, dependencies
from src.review.recognition import runtime_activated_owner as activated, runtime_proposal_transaction as transaction
from src.review.recognition import rules, runtime_operation_contract as operation
from src.review.recognition.rules import canonical, digest
from src.review.recognition.trust import utc
from tests import test_recognition_runtime_execution_coordinator as fixtures
from tests.test_recognition_runtime_execution_attempt_creation import _cleanup_fixture_tree
from tests.test_recognition_runtime_coordinator_final_validation_efficiency import measurement


class _Z8Profile:
    """Test-only exclusive accounting plus at most eight samples per reader kind.

    Full Python profiling is NOT enabled throughout the authority lifecycle.
    No arguments, locals, credentials, observations or database rows are exported.
    """
    def __init__(self):
        self.stage=None;self.stack=[];self.layers={};self.samples=Counter()
        self.profiles={name:cProfile.Profile() for name in ('construction','final')}
        self.sampling=False;self.sample_times={}

    def timed(self,fn,label,*,reader=False):
        def call(*args,**kwargs):
            call.call_count+=1
            construction=label=='observation_construction'
            previous=self.stage
            if construction:self.stage='construction'
            if self.stage is None:return fn(*args,**kwargs)
            profile=self.profiles[self.stage];sample=None
            if construction and not self.sampling:sample='construction'
            elif reader and self.stage=='final' and not self.sampling:
                kind=label+('_native' if type(args[0]) is sqlite3.Connection else '_adapter')
                if self.samples[kind]<8:sample=kind
            key=(self.stage,label)
            entry=self.layers.setdefault(key,dict(calls=0,inclusive_seconds=0.0,exclusive_seconds=0.0))
            entry['calls']+=1
            frame=[time.perf_counter(),0.0];self.stack.append(frame)
            cpu=time.thread_time()
            if sample:
                self.sampling=True;self.samples[sample]+=1;profile.enable()
            try:return fn(*args,**kwargs)
            finally:
                if sample:profile.disable();self.sampling=False
                elapsed=time.perf_counter()-frame[0];cpu_elapsed=time.thread_time()-cpu
                self.stack.pop();entry['inclusive_seconds']+=elapsed;entry['exclusive_seconds']+=elapsed-frame[1]
                if self.stack:self.stack[-1][1]+=elapsed
                if sample:
                    row=self.sample_times.setdefault(sample,dict(calls=0,wall_seconds=0.0,thread_cpu_seconds=0.0))
                    row['calls']+=1;row['wall_seconds']+=elapsed;row['thread_cpu_seconds']+=cpu_elapsed
                if construction:self.stage=previous
        call.call_count=0
        return call

    @contextmanager
    def installed(self):
        watched=((observation,'_mint','observation_construction'),
                 (observation,'_check','observation_validation'),
                 (observation,'_physical','physical_observation'),
                 (observation,'_credential_scope','credential_scope'),
                 (observation,'_definition_code','definition_code'),
                 (c,'_attempt_state','registry_provenance'),
                 (c._Outer,'check','owner_deadline'),(c._State,'check','coordinator_ownership'),
                 (activated._State,'check','reservation_mode'),
                 (transaction._State,'check','connection_transaction'),
                 (operation,'_copy','object_copy'))
        with ExitStack() as patches:
            for module,name,label in watched:
                patches.enter_context(patch.object(module,name,new=self.timed(getattr(module,name),label)))
            # Instrument existing aliases too: imported digest functions resolve
            # rules.canonical dynamically. Every wrapper calls the real codec.
            for module in tuple(sys.modules.values()):
                if module is None or not getattr(module,'__name__','').startswith('src.review.recognition.'):
                    continue
                for name,original,label in (('canonical',canonical,'canonical_codec'),('digest',digest,'digest')):
                    if getattr(module,name,None) is original:
                        patches.enter_context(patch.object(module,name,new=self.timed(original,label)))
            for name in ('_objects','_names'):
                patches.enter_context(patch.object(observation,name,new=self.timed(getattr(observation,name),'schema'+name,reader=True)))
            yield

    @contextmanager
    def final(self):
        self.stage='final';wall=time.perf_counter();cpu=time.thread_time()
        try:yield
        finally:
            self.wall_seconds=time.perf_counter()-wall
            self.thread_cpu_seconds=time.thread_time()-cpu
            self.stage=None

    def report(self):
        result=dict(layers={stage:{label:values for (part,label),values in self.layers.items() if part==stage}
                            for stage in ('construction','final')},samples=self.sample_times,
                    wall_seconds=self.wall_seconds,thread_cpu_seconds=self.thread_cpu_seconds,
                    sampled_functions={})
        for stage,profile in self.profiles.items():
            rows=[]
            for (filename,line,name),(primitive,calls,exclusive,inclusive,callers) in pstats.Stats(profile).stats.items():
                rows.append(dict(file=Path(filename).name,line=line,name=name,calls=calls,
                    exclusive_seconds=exclusive,inclusive_seconds=inclusive,
                    callers=[dict(file=Path(key[0]).name,line=key[1],name=key[2],
                        metrics=list(value) if isinstance(value,tuple) else [value]) for key,value in callers.items()]))
            result['sampled_functions'][stage]=sorted(rows,key=lambda row:row['exclusive_seconds'],reverse=True)
        functions=result['sampled_functions']['final']
        result['sampled_native_sql']=[row for row in functions if row['file']=='~'
            and any(name in row['name'] for name in ('sqlite3.Connection','sqlite3.Cursor'))]
        result['sampled_query_only_execute_seconds']=sum(caller['metrics'][2]
            for row in result['sampled_native_sql'] if "'execute'" in row['name']
            for caller in row['callers'] if caller['file']=='runtime_activated_owner.py' and caller['name']=='check')
        result['wait_limit']='Wall minus thread CPU is an upper bound on all non-CPU delay, not measured SQLite lock wait. Native cursor iteration is partly charged to its Python caller.'
        return result


class AttemptSchemaManifestObservationTests(unittest.TestCase):
    def test_no_public_constructor_or_standalone_continuity(self):
        with self.assertRaises(TypeError):observation._Observation()
        with sqlite3.connect(':memory:') as conn:
            conn.execute('CREATE TABLE first(value TEXT)')
            first = schema._control_objects(conn)
            conn.execute('CREATE TABLE second(value TEXT)')
            self.assertNotEqual(first,schema._control_objects(conn))
            self.assertIn('second',schema._control_names(conn))
        with self.assertRaises((AttributeError,ValueError)):
            observation._mint(object())

    def test_genuine_attempt_final_validation_equivalence_cost_and_invalidation(self):
        done=threading.Event();self.addCleanup(done.set)
        output=Path(__file__).resolve().parents[1]/'.tmp'/'recognition-z7-final-timing.json'
        output.parent.mkdir(exist_ok=True)
        report=dict(phase='fixture',results={})
        def save():output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        def watchdog():
            if not done.wait(300):
                try:save()
                finally:os._exit(124)
        threading.Thread(target=watchdog,daemon=True).start()
        f=fixtures.RuntimeExecutionCoordinatorTests();self.addCleanup(_cleanup_fixture_tree,f);f.setUp()
        paths=(f.config.target,f.config.control)
        backups=tuple(path.parent/('z7-'+path.name) for path in paths)
        for path,backup in zip(paths,backups):
            with a.connect(path) as source,sqlite3.connect(backup) as destination:source.backup(destination)
        def restore():
            for backup,path in zip(backups,paths):
                with sqlite3.connect(backup) as source,sqlite3.connect(path) as destination:source.backup(destination)
        original_finish=c._finish
        origin=utc(runtime._utc_now())
        observations=[];results=[];states=[]
        def probes(state):
            # These are isolated predicates on the genuine, registered owner;
            # no authentication/owner validator or provenance registry is mocked.
            facts=state.schema_facts
            self.assertIs(observation._check(state),facts)
            self.assertEqual(facts.manifest_sha256,claims.manifest(state.control))
            with self.assertRaises(FrozenInstanceError):facts.obtained_at_utc='changed'
            with self.assertRaises(TypeError):pickle.dumps(state.schema_observation)
            for name in ('execute','control','target','cursor','commit','rollback','writer'):
                self.assertFalse(hasattr(state.schema_observation,name))
            with patch.object(schema,'definitions',wraps=schema.definitions):
                with self.assertRaises(ValueError):observation._check(state)
            for field,value in (('phase',object()),('connections',(object(),state.target)),
                    ('epochs',(-1,-1)),('snapshot_json','wrong generation/profile'),
                    ('subject_json','wrong installation/profile'),('authority_json','different authority'),
                    ('credential_scope_sha256','0'*64),('owner',(0,None,0,None))):
                with self.subTest(invalidation=field):
                    state.schema_facts=replace(facts,**{field:value})
                    try:
                        with self.assertRaises(ValueError):observation._check(state)
                    finally:state.schema_facts=facts
            for attribute in ('activation_sha256','session','primary','approval_sha256'):
                previous=getattr(state,attribute)
                setattr(state,attribute,'changed')
                try:
                    with self.subTest(live_scope=attribute),self.assertRaises(ValueError):observation._check(state)
                finally:setattr(state,attribute,previous)
            previous=state.snapshot
            for key,value in (('generation',previous['generation']+1),('profile_sha256','0'*64),
                              ('installation_id','different installation')):
                state.snapshot=dict(previous,**{key:value})
                try:
                    with self.subTest(current_scope=key),self.assertRaises(ValueError):observation._check(state)
                finally:state.snapshot=previous
            actual=a.target_identity
            for key in ('device','inode','hostname','database'):
                def changed(path):
                    observed=actual(path);value=getattr(observed,key)
                    return replace(observed,**{key:value+1 if type(value) is int else value+'-different'})
                with self.subTest(physical=key),patch.object(a,'target_identity',side_effect=changed):
                    with self.assertRaises(ValueError):observation._check(state)
            for field,value in (('objects',()),('manifest_sha256','0'*64)):
                state.schema_facts=replace(facts,**{field:value})
                try:
                    with self.subTest(schema_manifest=field),self.assertRaises(ValueError):observation._write_proof(state)
                finally:state.schema_facts=facts
            # Exact schema/mode/transaction mutation attempts are denied by the
            # same real authorizer implementation. A separate unregistered state
            # tests that predicate without poisoning the genuine successful run.
            for action in (sqlite3.SQLITE_CREATE_TABLE,sqlite3.SQLITE_ALTER_TABLE,
                           sqlite3.SQLITE_ATTACH,sqlite3.SQLITE_TRANSACTION,sqlite3.SQLITE_SAVEPOINT):
                denied=c._State(state.outer,False)
                with self.subTest(forbidden_action=action):
                    self.assertEqual(sqlite3.SQLITE_DENY,denied.authorize(False,action,'unexpected',None))
                    self.assertTrue(denied.poisoned)
            for action,table,column in ((sqlite3.SQLITE_UPDATE,'recognition_admin_sessions','revoked'),
                    (sqlite3.SQLITE_INSERT,'recognition_admin_audit',None),
                    (sqlite3.SQLITE_DELETE,'recognition_admin_stepups',None)):
                denial=c._State(state.outer,False)
                denial.kernel_write=True
                denial.schema_observation=object();denial.schema_facts=object()
                with self.subTest(extra_dml=action):
                    # This runs the real authorizer, even if the eventual SQL
                    # affects zero rows. Existing denial permission is unchanged.
                    self.assertEqual(sqlite3.SQLITE_OK,denial.authorize(False,action,table,column))
                    self.assertIsNone(denial.schema_observation)
                    self.assertIsNone(denial.schema_facts)
            # A statement from another connection never borrows the observation.
            with sqlite3.connect(':memory:') as other:
                other.execute('CREATE TABLE unrelated(value TEXT)')
                token=observation._active.set(state)
                try:self.assertEqual(('unrelated',),schema._control_names(other))
                finally:observation._active.reset(token)

        def fresh_objects(conn):return tuple(tuple(row) for row in conn.execute(observation._SQL))
        def fresh_names(conn):return tuple(row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"))
        for label in ('before','after'):
            restore();report['phase']=label+' issuance';save()
            profiler=_Z8Profile()
            def finish(state):
                if state.issuance_phase:
                    self.assertIsNone(state.schema_observation)
                    return original_finish(state)
                report['phase']=label+' final validation';save()
                self.assertIsNotNone(state.schema_observation)
                self.assertIs(c._admission_contexts[state.context],state)
                if label=='after':probes(state)
                observations.append(state.schema_observation)
                states.append(state)
                # Count real consumers; wraps do not replace any live validator.
                watched=((runtime,'_history'),(issuer,'_subject_for_owner'),(c,'_current'),
                         (attempts,'check_rows'),(claims,'check_rows'),(shared,'_session'),
                         (approval,'read_current'),(proposals,'read_approved_proposal'),
                         (local_readiness,'require_activated'),(dependencies,'recheck'),(execution,'_stop'))
                with ExitStack() as stack:
                    checks=[stack.enter_context(patch.object(module,name,wraps=getattr(module,name))) for module,name in watched]
                    reads=observation._check
                    with measurement(state.control,state.target) as stats,profiler.final():
                        report['results'][label]=stats;save()
                        expected=claims.manifest(state.control)
                        original_finish(state)
                    self.assertTrue(all(check.call_count for check in checks))
                    stats['live_check_calls']={module.__name__.rsplit('.',1)[-1]+'.'+name:check.call_count
                        for (module,name),check in zip(watched,checks)}
                    if label=='after':self.assertGreater(reads.call_count,1)
                stats['z8_profile']=profiler.report()
                self.assertIsNone(state.schema_observation)
                self.assertIsNone(state.schema_facts)
                results.append((expected,dict(state.snapshot),canonical(state.subject)))
                for kind in ('INSERT','UPDATE','DELETE','CREATE'):
                    self.assertEqual(0,stats['sql'][kind])
                self.assertEqual(1,stats['sql']['COMMIT'])
                save()
            with ExitStack() as patches:
                anchor=time.monotonic_ns()
                patches.enter_context(patch.object(runtime,'_utc_now',side_effect=lambda:
                    (origin+timedelta(seconds=(time.monotonic_ns()-anchor)//1_000_000_000)).strftime('%Y-%m-%dT%H:%M:%SZ')))
                if label=='before':
                    patches.enter_context(patch.object(observation,'_objects',new=fresh_objects))
                    patches.enter_context(patch.object(observation,'_names',new=fresh_names))
                patches.enter_context(profiler.installed())
                patches.enter_context(patch.object(c,'_finish',side_effect=finish))
                for module,name in ((writer_boundary,'acquire'),(writer_boundary,'_local_lease'),
                        (execution,'execute_operation'),(local_execution,'execute_approved_operation'),(permanent,'finalize')):
                    patches.enter_context(patch.object(module,name,side_effect=AssertionError('downstream authority forbidden')))
                with f.coordinator() as owner:
                    result=owner.create_attempt()
                    self.assertIsNone(observation._active.get())
                    with self.assertRaises(ValueError):observation._check(states[-1])
                    self.assertFalse(result.snapshot['execution_authority'])
                    self.assertEqual('ATTEMPT_CREATED',result.snapshot['state'])
                    self.assertFalse(writer_boundary.verify_local(result,f.config.target,{}))
            for table in ('recognition_execution_claims','recognition_execution_seals','recognition_operation_receipts'):
                self.assertEqual(0,f.sql('SELECT count(*) FROM '+table,target=True)[0][0])
        self.assertEqual(results[0],results[1])
        self.assertIsNot(observations[0],observations[1])
        self.assertLess(report['results']['after']['sql']['schema_reads'],report['results']['before']['sql']['schema_reads'])
        self.assertEqual(report['results']['before']['live_check_calls'],report['results']['after']['live_check_calls'])
        for label in ('audit_reads','profile_reads','claim_reads','activation_reads','approval_reads'):
            self.assertEqual(report['results']['before']['sql'][label],report['results']['after']['sql'][label])
        self.assertEqual(report['results']['before']['pragmas']['foreign_key_check'],
                         report['results']['after']['pragmas']['foreign_key_check'])
        report['phase']='complete';save()
        print('Z7_FINAL_TIMING '+str(output))
