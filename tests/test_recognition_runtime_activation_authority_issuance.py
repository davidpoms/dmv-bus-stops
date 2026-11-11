"""Disposable real-consent issuance. No production execution/activation provider."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from contextlib import closing
import os
import json
import pickle
from queue import Queue
import sqlite3
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch
from uuid import uuid4

from src.review.recognition import administration as a, authorization, administration_schema
from src.review.recognition import runtime_activation_authority_issuance as issuer
from src.review.recognition import runtime_activation_authority_schema as storage
from src.review.recognition import runtime_authority_consent as consent, runtime_validation as runtime
from src.review.recognition import writer_boundary, production_operations, local_readiness, approvals
from src.review.recognition.rules import canonical, digest
from src.review.recognition.trust import utc, load
from tests import test_recognition_runtime_authority_owner_consent as fixtures


class ActivationAuthorityIssuanceTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.AuthorityOwnerConsentTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.config, self.session, self.primary = self.f.config,self.f.session,self.f.primary
        self.scope, self.approval_id = dict(self.f.scope), self.f.approval_id
        self.confirmation = self.f.confirm(self.f.step())

    def issue(self, **changes):
        return issuer.issue(self.config,self.session,self.confirmation['token'],self.approval_id,**dict(self.scope,**changes))

    def dump(self, target=False):
        return self.f.fixture.dump(self.config.target if target else self.config.control)

    def inspect(self):
        with patch.object(a,'target_identity',side_effect=authorization.target_identity):
            return issuer.inspect_issuance(self.config,operation_id=self.scope['reference']['operation_id'],
                operation_sha256=self.scope['reference']['operation_sha256'],confirmation_sha256=a.token_hash(self.confirmation['token']))

    def test_real_issuance_exact_body_genesis_consumption_and_no_downstream_authority(self):
        target=self.dump(True)
        result=self.issue()
        self.assertIs(type(result),issuer.IssuedAuthority)
        body=dict(result.snapshot)
        self.assertEqual(self.scope['reference']['operation_id'],body['operation_reference']['operation_id'])
        with a.connect(self.config.control) as control:
            administration_schema.check_control(control)
            row=control.execute('SELECT * FROM '+storage.AUTHORITIES).fetchone()
            value=storage.parse_authority(row['body_json'],authority_sha256=row['body_sha256'])
            self.assertEqual(digest(value),result.sha256)
            self.assertEqual(120,row['expires_at']-row['issued_at'])
            event=control.execute('SELECT * FROM '+storage.LIFECYCLE).fetchone()
            genesis=storage.parse_genesis(event['body_json'],event_sha256=event['body_sha256'],authority=value)
            self.assertEqual(set(genesis['evidence']),{'format','authority_id','authority_sha256'})
            self.assertEqual(1,control.execute('SELECT used FROM recognition_admin_confirmations WHERE token_hash=?',
                (a.token_hash(self.confirmation['token']),)).fetchone()[0])
            self.assertEqual(0,control.execute('SELECT count(*) FROM recognition_runtime_execution_claims').fetchone()[0])
        self.assertEqual(target,self.dump(True))
        self.assertFalse(writer_boundary.verify_local(result,self.config.target,{}))
        with self.assertRaises(ValueError):writer_boundary.acquire(result,self.config.target,{})
        with self.assertRaises(ValueError):production_operations.context_data(result)
        self.assertEqual('PRESENT_EXACT',self.inspect()['status'])

    def test_duplicate_returns_inspection_only_without_second_object_or_write(self):
        first=self.issue();before=self.dump()
        second=self.issue()
        self.assertIsNot(type(second),issuer.IssuedAuthority)
        self.assertEqual(first.sha256,second['authority_sha256'])
        self.assertFalse(second['retry_authorized']);self.assertFalse(second['execution_authority'])
        self.assertEqual(before,self.dump())
        with self.assertRaises(ValueError):self.issue(reason='changed reason')

    def test_simultaneous_issue_at_most_one_new_result(self):
        def attempt():
            try:return self.issue()
            except sqlite3.OperationalError as error:
                self.assertIn(error.sqlite_errorcode,(sqlite3.SQLITE_BUSY,sqlite3.SQLITE_LOCKED))
                return None  # Existing bounded lock timeout: rejection, never retry.
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:attempt(),range(2)))
        self.assertEqual(1,sum(type(result) is issuer.IssuedAuthority for result in results))
        self.assertEqual(1,self.f.sql('SELECT count(*) FROM '+storage.AUTHORITIES)[0][0])

    def test_rollback_at_each_mutation_stage(self):
        before=self.dump();original_insert=issuer._insert;original_audit=a._audit
        for stage in ('before','consumed','authority','genesis','audit','final'):
            def insert(control,table,row):
                original_insert(control,table,row)
                if stage=='authority' and table==storage.AUTHORITIES or stage=='genesis' and table==storage.LIFECYCLE:
                    raise OSError(stage)
            def audit(control,action,*args):
                if stage=='consumed' and action==storage.CONSUME_ACTION:raise OSError(stage)
                if stage=='audit' and action==storage.ISSUE_ACTION:raise OSError(stage)
                return original_audit(control,action,*args)
            from contextlib import ExitStack
            with ExitStack() as stack:
                stack.enter_context(patch.object(issuer,'_insert',side_effect=insert))
                stack.enter_context(patch.object(a,'_audit',side_effect=audit))
                if stage=='before':stack.enter_context(patch.object(issuer,'_persist',side_effect=OSError(stage)))
                if stage=='final':stack.enter_context(patch.object(issuer,'_final_mutations',side_effect=OSError(stage)))
                with self.subTest(stage=stage),self.assertRaises(OSError):self.issue()
            self.assertEqual(before,self.dump())
        self.issue()

    def test_uncertain_commit_publishes_no_result(self):
        original=a.sqlite3.connect
        class Fault(sqlite3.Connection):
            def commit(conn):
                is_control=conn.execute('PRAGMA database_list').fetchone()[2]==str(self.config.control)
                value=super(Fault,conn).commit()
                if is_control:raise OSError('acknowledgement lost')
                return value
        def connect(*args,**kwargs):kwargs['factory']=Fault;return original(*args,**kwargs)
        before=len(issuer._issued)
        with patch.object(a.sqlite3,'connect',side_effect=connect),self.assertRaises(OSError):self.issue()
        self.assertEqual(before,len(issuer._issued))
        self.assertEqual('PRESENT_EXACT',self.inspect()['status'])
        self.assertIsNot(type(self.issue()),issuer.IssuedAuthority)

    def test_wrong_lookup_scope_and_confirmation(self):
        before=self.dump()
        for key,value in (('activation_sha256','a'*64),('approval_sha256','a'*64),('reason','another reason'),
                          ('reference',dict(self.scope['reference'],acknowledgement_sha256='a'*64))):
            with self.subTest(key=key),self.assertRaises(ValueError):self.issue(**{key:value})
        with self.assertRaises(ValueError):
            issuer.issue(self.config,self.session,'x'*40,self.approval_id,**self.scope)
        self.assertEqual(before,self.dump())

    def test_opaque_process_thread_lifetime_and_no_token_leak(self):
        result=self.issue()
        with self.assertRaises(TypeError):pickle.dumps(result)
        with self.assertRaises(TypeError):issuer.IssuedAuthority()
        with patch.object(os,'getpid',return_value=os.getpid()+1),self.assertRaises(ValueError):_=result.snapshot
        def wrong_thread():
            with self.assertRaises(ValueError):_=result.snapshot
        with ThreadPoolExecutor(max_workers=1) as pool:pool.submit(wrong_thread).result()
        serialized=repr(result.snapshot)
        for forbidden in ('seed_ciphertext','owner_key_sha256','key_hash',self.primary,self.session,self.confirmation['token']):
            self.assertNotIn(forbidden,serialized)
        self.assertNotIn(self.confirmation['token'],self.dump())

    def test_subject_change_before_final_commit_rolls_back(self):
        before=self.dump();original=issuer._subject;calls=[]
        changes=[('runtime_target',key) for key in ('auth_epoch','mfa_epoch','generation','owner_id','installation_id','target_id','runtime_profile_sha256')]
        changes += [('activation','sequence'),('activation','event_sha256'),('approval','approval_sha256'),
                    ('operation_reference','operation_sha256'),('dependencies','snapshot_sha256')]
        for section,key in changes:
            calls.clear()
            def changed(state):
                subject=original(state);calls.append(True)
                if len(calls)>1:
                    value=subject[section][key]
                    subject[section][key]=value+1 if type(value) is int else 'changed'
                return subject
            with self.subTest(field=(section,key)),patch.object(issuer,'_subject',side_effect=changed),self.assertRaisesRegex(ValueError,'scope_changed'):self.issue()
            self.assertEqual(before,self.dump())

    def test_actual_schema_and_auth_mfa_epoch_changes_fail_closed(self):
        self.f.sql('CREATE TABLE changed_schema(value)',target=True)
        with self.assertRaises(ValueError):self.issue()
        self.f.sql('DROP TABLE changed_schema',target=True)
        self.f.sql('UPDATE recognition_admin_mfa SET epoch=epoch+1')
        with self.assertRaises(ValueError):self.issue()
        self.assertEqual(0,self.f.sql('SELECT count(*) FROM '+storage.AUTHORITIES)[0][0])

    def test_consumed_without_authority_is_not_reconstructed(self):
        self.f.sql('UPDATE recognition_admin_confirmations SET used=1 WHERE token_hash=?',(a.token_hash(self.confirmation['token']),))
        self.assertEqual('UNKNOWN',self.inspect()['status'])
        with self.assertRaises(ValueError):self.issue()
        self.assertEqual(0,self.f.sql('SELECT count(*) FROM '+storage.AUTHORITIES)[0][0])

    def test_short_original_deadline_no_renewal_and_expiry(self):
        self.f.clock.return_value=(utc(self.f.clock.return_value)+timedelta(seconds=550)).strftime('%Y-%m-%dT%H:%M:%SZ')
        result=self.issue()
        self.assertEqual(self.confirmation['artifact']['expires_at_utc'],result.snapshot['expires_at_utc'])
        remaining=a.timestamp(result.snapshot['expires_at_utc'])-a.timestamp(result.snapshot['issued_at_utc'])
        self.assertGreater(remaining,0);self.assertLessEqual(remaining,50)
        self.f.clock.return_value=self.confirmation['artifact']['expires_at_utc']
        with self.assertRaises(ValueError):_=result.snapshot
        duplicate=self.issue()
        self.assertIsNot(type(duplicate),issuer.IssuedAuthority)
        self.assertFalse(duplicate['retry_authorized'])

    def test_actual_owner_install_target_physical_identity_mismatches(self):
        observe=a.target_identity.side_effect
        for which in ('control','target'):
            for key,value in (('hostname','wrong-host'),('device',999),('inode',999),('database',str(self.config.target.parent/'other.db'))):
                def changed(subject):
                    current=observe(subject)
                    return replace(current,**{key:value}) if current.database==str(getattr(self.config,which)) else current
                with self.subTest(which=which,key=key),patch.object(a,'target_identity',side_effect=changed),self.assertRaises(ValueError):self.issue()
        for key,value in (('installation_id',str(uuid4())),('target_id',str(uuid4())),('owner_id',999)):
            old=self.f.sql('SELECT '+key+' FROM recognition_local_installation',target=True)[0][0]
            self.f.sql('UPDATE recognition_local_installation SET '+key+'=?',(value,),target=True)
            with self.subTest(key=key),self.assertRaises(ValueError):self.issue()
            self.f.sql('UPDATE recognition_local_installation SET '+key+'=?',(old,),target=True)

    def test_actual_auth_epoch_and_stale_generation(self):
        self.f.sql('UPDATE recognition_local_installation SET auth_epoch=auth_epoch+1',target=True)
        with self.assertRaises(ValueError):self.issue()
        with a.connect(self.config.control,write=True) as control:
            row=control.execute('SELECT * FROM recognition_admin_bindings ORDER BY generation DESC LIMIT 1').fetchone()
            body=load(row['body_json']);body.update(generation=body['generation']+1,runtime_profile_sha256=None,
                previous_sha256=row['body_sha256'],at_utc=runtime._utc_now())
            control.execute('INSERT INTO recognition_admin_bindings VALUES(?,?,?)',(body['generation'],canonical(body),digest(body)))
            a._audit(control,'test_generation_fenced',1,runtime._utc_now(),dict(generation=body['generation']));control.commit()
        with self.assertRaises(ValueError):self.issue()

    def test_stale_approval_stop_and_activation_reject(self):
        from src.review.recognition import execution,events
        with a.connect(self.config.control,write=True) as control:
            previous=execution._stop(control)
            body=dict(sequence=previous['sequence']+1,active=True,reason='test stop',actor='owner',
                      recorded_at_utc=runtime._utc_now(),previous_sha256=digest(previous))
            events._insert(control,'recognition_execution_stops','sequence',(body['sequence'],),body);control.commit()
        with self.assertRaises(ValueError):self.issue()
        with a.connect(self.config.control,write=True) as control:
            approvals._invalidate_all(control,'owner',runtime._utc_now(),'test invalidation');control.commit()
        with self.assertRaisesRegex(ValueError,'runtime_approval_not_current'):self.issue()
        with a.connect(self.config.control,write=True) as control:
            binding,_,_=runtime._history(control)
            local_readiness._append(control,binding,'SUSPENDED',1,'test suspend',runtime._utc_now());control.commit()
        with self.assertRaises(ValueError):self.issue()

    def test_no_target_dml_ddl_commit_and_reservation_held(self):
        original=a.sqlite3.connect;target_commits=[];control_commits=[];target_writes=[]
        class Probe(sqlite3.Connection):
            def execute(conn,sql,*args):
                if getattr(conn,'is_target',False) and sql.lstrip().split()[0].upper() in ('INSERT','UPDATE','DELETE','CREATE','DROP','ALTER','REPLACE'):
                    target_writes.append(sql);raise AssertionError('target write')
                return super(Probe,conn).execute(sql,*args)
            def commit(conn):
                if conn.is_target:target_commits.append(True);raise AssertionError('target commit')
                if conn.is_control:
                    with closing(original(self.config.target,timeout=0)) as competitor:
                        with self.assertRaises(sqlite3.OperationalError):competitor.execute('BEGIN IMMEDIATE')
                    control_commits.append(True)
                return super(Probe,conn).commit()
        def connect(path,*args,**kwargs):
            kwargs['factory']=Probe;conn=original(path,*args,**kwargs)
            conn.is_target=str(path).startswith(self.config.target.resolve().as_uri()+'?')
            conn.is_control=str(path).startswith(self.config.control.resolve().as_uri()+'?')
            return conn
        target=self.dump(True)
        with patch.object(a.sqlite3,'connect',side_effect=connect):self.issue()
        self.assertEqual(target,self.dump(True));self.assertFalse(target_writes);self.assertFalse(target_commits);self.assertEqual(1,len(control_commits))

    def test_before_silent_commit_and_target_cleanup_failure(self):
        original=a.sqlite3.connect;before=self.dump()
        for stage in ('before','silent','cleanup'):
            class Fault(sqlite3.Connection):
                def commit(conn):
                    if conn.execute('PRAGMA database_list').fetchone()[2]==str(self.config.control):
                        if stage=='before':raise OSError('before commit')
                        if stage=='silent':return None
                    return super(Fault,conn).commit()
                def rollback(conn):
                    target=conn.execute('PRAGMA database_list').fetchone()[2]==str(self.config.target)
                    super(Fault,conn).rollback()
                    if target and stage=='cleanup':raise OSError('cleanup')
            def connect(*args,**kwargs):kwargs['factory']=Fault;return original(*args,**kwargs)
            count=len(issuer._issued)
            with self.subTest(stage=stage),patch.object(a.sqlite3,'connect',side_effect=connect),self.assertRaises((OSError,a.AdminError)):self.issue()
            self.assertEqual(count,len(issuer._issued))
            if stage!='cleanup':self.assertEqual(before,self.dump())
            else:self.assertEqual('PRESENT_EXACT',self.inspect()['status'])

    def _process_interruption(self, mode):
        for target in (False,True):self.f.sql('PRAGMA journal_mode='+mode,target=target)
        hostname=self.f.sql('SELECT hostname FROM recognition_runtime_profiles')[0][0]
        payload=dict(target=str(self.config.target),control=str(self.config.control),key=str(self.config.key_file),
                     session=self.session,confirmation=self.confirmation['token'],approval_id=self.approval_id,
                     scope=self.scope,now=runtime._utc_now(),hostname=hostname)
        script=r'''
import json,sys,sqlite3,time
from pathlib import Path
from dataclasses import replace
from datetime import timedelta
from unittest.mock import patch
payload=json.loads(sys.stdin.readline())
allowed={str(Path(payload[k]).resolve()).casefold() for k in ('target','control')}
def guard(event,args):
    if event=='sqlite3.connect':
        name=str(args[0])
        if name==':memory:':return
        path=Path.from_uri(name.split('?')[0]) if name.startswith('file:') else Path(name)
        if str(path.resolve()).casefold() not in allowed:raise PermissionError('nonfixture database')
    if event in ('socket.connect','socket.bind','socket.getaddrinfo'):raise PermissionError('network disabled')
sys.addaudithook(guard)
from src.review.recognition import administration as a,authorization,dependencies,runtime_validation as runtime
from src.review.recognition import runtime_activation_authority_issuance as issuer
from src.review.recognition.trust import utc
config=a.LocalAdministration(Path(payload['target']),Path(payload['control']),Path(payload['key']))
identity=authorization.target_identity
def observed(subject):
    current=identity(subject)
    return replace(current,hostname=payload['hostname'],device=current.device+1)
origin=utc(payload['now']);anchor=time.monotonic_ns()
def now():return (origin+timedelta(seconds=(time.monotonic_ns()-anchor)//1_000_000_000)).strftime('%Y-%m-%dT%H:%M:%SZ')
def pause():
    print('READY',flush=True)
    time.sleep(300)
original_insert=issuer._insert
def insert(control,table,row):
    original_insert(control,table,row)
    if payload['stage']=='authority' and table==issuer.storage.AUTHORITIES:pause()
original_audit=a._audit
def audit(control,action,*args):
    result=original_audit(control,action,*args)
    if payload['stage']=='consumed' and action==issuer.storage.CONSUME_ACTION:pause()
    return result
connect=sqlite3.connect
class Probe(sqlite3.Connection):
    def execute(conn,sql,*args):
        if getattr(conn,'target',False) and sql.lstrip().split()[0].upper() in ('INSERT','UPDATE','DELETE','CREATE','ALTER','DROP','REPLACE'):
            raise AssertionError('target DML or DDL')
        return super().execute(sql,*args)
    def commit(conn):
        if conn.target:raise AssertionError('target COMMIT')
        return super().commit()
def factory(path,*args,**kwargs):
    kwargs['factory']=Probe
    conn=connect(path,*args,**kwargs)
    conn.target=str(path).startswith(config.target.resolve().as_uri()+'?')
    return conn
with patch.object(a,'target_identity',side_effect=observed),patch.object(dependencies,'target_identity',side_effect=observed),patch.object(runtime,'_utc_now',side_effect=now),patch.object(a.sqlite3,'connect',side_effect=factory),patch.object(issuer,'_insert',side_effect=insert),patch.object(a,'_audit',side_effect=audit):
    result=issuer.issue(config,payload['session'],payload['confirmation'],payload['approval_id'],**payload['scope'])
    if payload['stage']!='committed':raise AssertionError('expected interruption not reached')
    pause()
'''
        target=self.dump(True)
        for stage in ('consumed','authority','committed'):
            child=subprocess.Popen([sys.executable,'-B','-c',script],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            messages=Queue()
            try:
                child.stdin.write(json.dumps(dict(payload,stage=stage))+'\n');child.stdin.flush()
                thread=threading.Thread(target=lambda:messages.put(child.stdout.readline()),daemon=True);thread.start()
                line=messages.get(timeout=45)
                if line.strip()!='READY':
                    child.wait(timeout=5)
                    self.fail('child did not reach reserved stage: '+child.stderr.read())
            finally:
                if child.poll() is None:child.kill()
                child.communicate(timeout=30)
            status=self.inspect()['status']
            self.assertEqual('PRESENT_EXACT' if stage=='committed' else 'ABSENT_AT_SNAPSHOT',status)
            self.assertEqual(target,self.dump(True))
        # The child registry died. Durable JSON/UUID does not recreate it.
        forged=object.__new__(issuer.IssuedAuthority)
        with self.assertRaises(ValueError):_=forged.snapshot
        self.assertIsNot(type(self.issue()),issuer.IssuedAuthority)

    def test_process_interruption_delete(self):self._process_interruption('DELETE')

    def test_process_interruption_wal(self):self._process_interruption('WAL')

    def test_construction_follows_consumption_and_authority_insertion(self):
        body=issuer._body;genesis=issuer._genesis;seen=[];states=[]
        def construct(state,artifact):
            self.assertEqual(1,state.control.execute('SELECT used FROM recognition_admin_confirmations WHERE token_hash=?',
                (artifact['token_sha256'],)).fetchone()[0])
            self.assertEqual(0,state.control.execute('SELECT count(*) FROM '+storage.AUTHORITIES).fetchone()[0])
            states.append(state);seen.append('body');return body(state,artifact)
        def evidence(authority):
            state=states[0]
            self.assertEqual(1,state.control.execute('SELECT count(*) FROM '+storage.AUTHORITIES).fetchone()[0])
            self.assertEqual(0,state.control.execute('SELECT count(*) FROM '+storage.LIFECYCLE).fetchone()[0])
            seen.append('genesis');return genesis(authority)
        with patch.object(issuer,'_body',side_effect=construct),patch.object(issuer,'_genesis',side_effect=evidence):self.issue()
        self.assertEqual(['body','genesis'],seen)
