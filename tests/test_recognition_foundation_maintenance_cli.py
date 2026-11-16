"""Signed maintenance on disposable generation-5 fixtures; no browser credentials."""

import base64
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict, replace
import io
import os
from pathlib import Path
import queue
import sqlite3
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch

from src.review.recognition import administration as a, authorization, event_schema
from src.review.recognition import runtime_target_schema_completion as completion
from src.review.recognition import runtime_target_schema_lineage as lineage
from src.review.recognition import runtime_production_governance as governance, runtime_validation as runtime
from src.review.recognition.rules import canonical,digest
from src.review.recognition.trust import load
from tests import test_recognition_target_schema_completion as fixture


class FoundationMaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.TargetSchemaCompletionTests('test_preview_deterministic_readonly_and_successful_same_generation_completion')
        self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.config=self.f.config
        with patch('src.api.sqlite_runtime.load_production_sqlite'):
            from scripts.active import complete_recognition_foundation as cli
        self.cli=cli

    def preview_approval(self, **changes):
        with a.connect(self.config.control) as control:
            binding,_,_=runtime._history(control)
        subject=dict(kind=completion.PREVIEW_KIND,operator='signed-owner',reason='read-only foundation inspection')
        grant=authorization.Authorization(target=authorization.target_identity(self.config.target),environment='production',
            expires_at_utc=fixture.base.at(300),**completion.preview_binding(subject))
        body=dict(format=governance.FORMAT,mandate=governance.contract.MANDATE,installation_id=binding['installation_id'],
            binding_sha256=digest(binding),holder=dict(actor_id=1,primary_sha256=a.token_hash(self.f.primary),
            session_sha256=a.token_hash(self.f.session)),subject=subject,
            target=asdict(authorization.target_identity(self.config.target)),control=asdict(authorization.target_identity(self.config.control)),
            issued_at_utc=runtime._utc_now(),expires_at_utc=fixture.base.at(300),approvals=[asdict(grant)])
        body.update(changes)
        return self.sign(body)

    def sign(self,body):
        encoded=canonical(body)
        return dict(serialized_approval=encoded,signature=base64.b64encode(
            self.f.key.sign(governance.DOMAIN+encoded.encode())).decode())

    def preview(self, artifact=None):
        return completion.preview_approved(self.config,**(artifact or self.preview_approval()))

    def grant(self,plan=None):
        plan=plan or self.preview()['plan']
        encoded,signature=self.f.approval(plan)
        return dict(serialized_approval=encoded,signature=signature)

    def complete(self,grant=None,plan=None):
        plan=plan or self.preview()['plan'];grant=grant or self.grant(plan)
        return completion.complete_approved(self.config,approved_plan_sha256=digest(plan),**grant)

    def snapshots(self):return self.f.dump(self.config.target),self.f.dump(self.config.control)

    def cli_run(self,action,artifact=None,approved=None,**options):
        path=self.config.target.parent/'synthetic-maintenance-approval.json'
        path.write_text(canonical(artifact or self.preview_approval()),encoding='utf-8')
        args=[action,'--target',str(self.config.target),'--control',str(self.config.control),
              '--key-file',str(self.config.key_file),'--expected-generation','5','--authorization',str(path)]
        if approved is not None:args+=['--approved-plan-sha256',approved]
        with (patch('sys.stdout',new_callable=io.StringIO) as output,patch('sys.stderr',new_callable=io.StringIO) as error,
              patch('builtins.input',return_value=options.get('confirmation',approved))):
            status=self.cli.main(args)
        return status,output.getvalue(),error.getvalue()

    def test_signed_preview_no_raw_tokens_is_deterministic_and_completely_nonmutating(self):
        artifact=self.preview_approval();before=self.snapshots()
        with (patch.object(completion,'_session',side_effect=AssertionError('Raw tokens not permitted')),
              patch.object(completion,'_commit',side_effect=AssertionError('Preview must not commit'))):
            first=self.preview(artifact);second=self.preview(artifact)
        self.assertEqual(first,second);self.assertEqual(before,self.snapshots())
        self.assertTrue(first['read_only']);self.assertFalse(first['source_databases_modified'])
        self.assertFalse(first['execution_authority']);self.assertNotEqual(first['h0'],first['h1'])
        self.assertEqual(digest(first['plan']),first['plan_sha256'])
        status,stdout,stderr=self.cli_run('preview',artifact)
        self.assertEqual(0,status,stderr);self.assertEqual(first,load(stdout))
        for secret in (self.f.primary,self.f.session,'seed_ciphertext'):
            self.assertNotIn(secret,stdout+stderr)
        self.assertEqual(before,self.snapshots())

    def test_cli_completion_existing_lineage_and_records_preserved(self):
        plan=self.preview()['plan'];grant=self.grant(plan);protected=self.f.protected()
        with a.connect(self.config.target) as target:original=completion._data(target)
        with patch.object(completion,'_session',side_effect=AssertionError('Raw tokens not permitted')):
            code,stdout,stderr=self.cli_run('complete',grant,digest(plan))
        self.assertEqual(0,code,stderr);result=load(stdout)
        self.assertEqual(('COMPLETED',5,'NOT_ACTIVATED',False),tuple(result[k] for k in
                         ('state','generation','production_state','execution_authority')))
        self.assertEqual(protected,self.f.protected())
        with a.connect(self.config.control) as control,a.connect(self.config.target) as target:
            self.assertEqual(plan,lineage.verify(control));self.assertEqual(original,completion._data(target))
            binding,profile,_=runtime._history(control)
            self.assertEqual(plan['h0'],binding['target']['schema_sha256']);self.assertEqual(plan['h0'],profile['target_schema_sha256'])
            runtime._identity_snapshot(self.config,control,target,runtime._utc_now())
        ready=fixture.owner.assess(self.config,self.f.session,primary_token=self.f.primary)
        self.assertTrue(ready['activation_ready']);self.assertEqual('NOT_ACTIVATED',ready['activation_state'])
        with self.assertRaises(ValueError):self.complete(grant,plan)

    def test_wrong_digest_confirmation_and_signature_fail_without_mutation(self):
        plan=self.preview()['plan'];grant=self.grant(plan);before=self.snapshots()
        with self.assertRaises(ValueError):completion.complete_approved(self.config,approved_plan_sha256='a'*64,**grant)
        self.assertEqual(1,self.cli_run('complete',grant,digest(plan),confirmation='wrong')[0])
        bad=dict(grant,signature='A'*88)
        self.assertEqual(1,self.cli_run('complete',bad,digest(plan))[0])
        with self.assertRaises(ValueError):self.preview(bad)
        self.assertEqual(before,self.snapshots())

    def test_preview_grant_cannot_install_or_provision_generic_authority(self):
        preview=self.preview_approval();plan=self.preview(preview)['plan']
        with self.assertRaises(ValueError):self.complete(preview,plan)
        with self.assertRaises(ValueError):self.preview(self.grant(plan))
        with self.assertRaises(ValueError):governance.provision(self.config,self.f.session,primary_token=self.f.primary,
                                                              serialized=preview['serialized_approval'],signature=preview['signature'])

    def test_wrong_signed_scopes_expiry_and_holder_reject(self):
        artifact=self.preview_approval();body=load(artifact['serialized_approval']);before=self.snapshots()
        for key,value in (('binding_sha256','a'*64),('installation_id','aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'),
                          ('holder',dict(actor_id=1,primary_sha256='a'*64,session_sha256='b'*64)),
                          ('expires_at_utc',fixture.base.at(182))):
            with self.subTest(key=key),self.assertRaises((ValueError,sqlite3.Error)):
                self.preview(self.sign(dict(body,**{key:value})))
        plan=self.preview()['plan']
        for key,value in (('generation',6),('profile_sha256','a'*64),('h0','b'*64),('target_id','aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa')):
            changed=dict(plan,**{key:value})
            with self.subTest(key=key),self.assertRaises(ValueError):self.complete(self.grant(changed),changed)
        self.assertEqual(before,self.snapshots())

    def test_physical_identity_and_no_legacy_recovery_fallback(self):
        artifact=self.preview_approval()
        for key,value in (('hostname','other'),('device',999),('inode',999),('database',str(self.config.target.parent/'other'))):
            def changed(subject):return replace(authorization.target_identity(subject),**{key:value})
            with self.subTest(key=key),patch.object(a,'target_identity',side_effect=changed),self.assertRaises(ValueError):
                self.preview(artifact)
        for option in ('--session-token','--primary-token','--force','--skip-readiness','--recovery-sha256'):
            with patch('sys.stderr',new_callable=io.StringIO) as error,self.assertRaises(SystemExit):
                self.cli.main([option,'SENTINEL-SECRET'])
            self.assertNotIn('SENTINEL-SECRET',error.getvalue())

    def test_revoked_mfa_and_profile_auth_records_rejected_without_repair(self):
        artifact=self.preview_approval()
        for table,column in (('recognition_admin_sessions','revoked'),('recognition_admin_primary','revoked')):
            with a.connect(self.config.control,write=True) as control:
                control.execute('UPDATE '+table+' SET '+column+'=1');control.commit()
            before=self.snapshots()
            with self.assertRaises((ValueError,sqlite3.Error)):self.preview(artifact)
            self.assertEqual(before,self.snapshots())
            with a.connect(self.config.control,write=True) as control:
                control.execute('UPDATE '+table+' SET '+column+'=0');control.commit()
        with a.connect(self.config.control,write=True) as control:
            control.execute("UPDATE recognition_admin_mfa SET state='UNENROLLED' WHERE actor=1");control.commit()
        with self.assertRaises((ValueError,sqlite3.Error)):self.preview(artifact)

    def test_delete_and_full_are_required_without_journal_switch(self):
        artifact=self.preview_approval()
        for path in (self.config.control,self.config.target):
            with a.connect(path,write=True) as db:db.execute('PRAGMA journal_mode=WAL')
            with self.assertRaisesRegex(ValueError,'foundation_delete_journal_required'):self.preview(artifact)
            with a.connect(path,write=True) as db:
                self.assertEqual('wal',db.execute('PRAGMA journal_mode').fetchone()[0]);db.execute('PRAGMA journal_mode=DELETE')
        original=a.connect
        @contextmanager
        def normal(path,**options):
            with original(path,**options) as db:
                if options.get('write'):db.execute('PRAGMA synchronous=NORMAL')
                yield db
        with patch.object(a,'connect',side_effect=normal),self.assertRaisesRegex(ValueError,'foundation_full_synchronization_required'):
            self.preview(artifact)
        check=completion._synchronization
        def wrong_target(db,namespace):
            if namespace==completion.ALIAS:db.execute('PRAGMA '+namespace+'.synchronous=NORMAL')
            check(db,namespace)
        with patch.object(completion,'_synchronization',side_effect=wrong_target),self.assertRaisesRegex(ValueError,'foundation_full_synchronization_required'):
            self.preview(artifact)

    def test_preview_owner_forbids_mutation_and_missing_root_rejects(self):
        with completion._attached(self.config) as reserved:
            reserved.execute('PRAGMA query_only=ON');reserved.set_authorizer(completion._preview_authorizer)
            for sql in ('CREATE TABLE completion_target.bad(x)','DELETE FROM recognition_admin_mfa',
                        'PRAGMA query_only=OFF',"ATTACH DATABASE ':memory:' AS arbitrary"):
                with self.subTest(sql=sql),self.assertRaises(sqlite3.Error):reserved.execute(sql)
        artifact=self.preview_approval();before=self.snapshots()
        governance.trust_path(self.config).unlink()
        with self.assertRaises(OSError):self.preview(artifact)
        self.assertEqual(before,self.snapshots())

    def test_cli_bootstrap_stops_before_sqlite_project_imports_if_loader_fails(self):
        source=r'''
import runpy,sys
from pathlib import Path
from src.api import sqlite_runtime
def stop():
 assert 'sqlite3' not in sys.modules
 assert 'src.review.recognition.runtime_target_schema_completion' not in sys.modules
 print('LOADER_FIRST',flush=True)
 raise RuntimeError('synthetic stop')
sqlite_runtime.load_production_sqlite=stop
try:runpy.run_path(str(Path('scripts/active/complete_recognition_foundation.py')),run_name='__main__')
except RuntimeError:pass
else:raise AssertionError('loader bypassed')
'''
        child=subprocess.run([sys.executable,'-B','-c',source],capture_output=True,text=True,timeout=30)
        self.assertEqual(0,child.returncode,child.stderr)
        self.assertEqual('LOADER_FIRST',child.stdout.strip())

    def test_unrelated_target_drift_and_other_readiness_fail_closed(self):
        artifact=self.preview_approval()
        with a.connect(self.config.target,write=True) as target:target.execute('CREATE TABLE unrelated(value)');target.commit()
        with self.assertRaises(ValueError):self.preview(artifact)
        with a.connect(self.config.target,write=True) as target:target.execute('DROP TABLE unrelated');target.commit()
        with (patch.object(completion.execution_schema,'check_schema',side_effect=ValueError('unrelated schema')),
              self.assertRaises(ValueError)):self.preview(artifact)

    def test_signed_completion_uses_existing_atomic_owner_and_rollback(self):
        plan=self.preview()['plan'];grant=self.grant(plan);before=self.snapshots()
        for module,name in ((completion,'_install'),(completion,'_validate_after'),(a,'_audit'),(completion,'_commit')):
            with (self.subTest(name=name),patch.object(module,name,side_effect=RuntimeError('injected')),
                  self.assertRaises(RuntimeError)):self.complete(grant,plan)
            self.assertEqual(before,self.snapshots())
        self.assertEqual('COMPLETED',self.complete(grant,plan)['state'])

    def test_parser_missing_artifact_and_bad_artifact_are_sanitized(self):
        with patch('sys.stderr',new_callable=io.StringIO),self.assertRaises(SystemExit):self.cli.main(['preview'])
        bad={'serialized_approval':'SENTINEL-SECRET','signature':'SENTINEL-SECRET'}
        code,stdout,stderr=self.cli_run('preview',bad)
        self.assertEqual(1,code);self.assertFalse(stdout);self.assertNotIn('SENTINEL-SECRET',stderr)

    def test_signed_completion_crash_rollback_and_commit(self):
        plan=self.preview()['plan'];grant=self.grant(plan)
        options=dict(paths=[str(self.config.target),str(self.config.control),str(self.config.key_file)],
                     grant=grant,plan=digest(plan),now=runtime._utc_now())
        for phase in ('after_ddl','before_commit','after_commit'):
            with self.subTest(phase=phase):
                options['phase']=phase
                child=subprocess.Popen([sys.executable,'-B','-c',CHILD],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,text=True)
                child.stdin.write(canonical(options)+'\n');child.stdin.flush()
                lines=queue.Queue();reader=threading.Thread(target=lambda:lines.put(child.stdout.readline()),daemon=True);reader.start()
                try:self.assertEqual('PAUSED',lines.get(timeout=45).strip())
                finally:
                    if child.poll() is None:child.kill()
                    child.wait(timeout=15);child.stdin.close();child.stdout.close();child.stderr.close();reader.join(timeout=5)
                with a.connect(self.config.control,write=True) as control:control.execute('BEGIN IMMEDIATE');a.schema.check_control(control)
                self.assertEqual('COMPLETED' if phase=='after_commit' else 'NOT_COMPLETED',completion.inspect(self.config)['state'])


CHILD=r'''
import json,sys,time,tempfile
from pathlib import Path
from datetime import timedelta
from src.review.recognition import administration as a,runtime_validation as runtime,runtime_target_schema_completion as c
from src.review.recognition.trust import utc
o=json.loads(sys.stdin.readline())
assert all(Path(p).resolve().is_relative_to(Path(tempfile.gettempdir()).resolve()) for p in o['paths'])
config=a.LocalAdministration(*(Path(p) for p in o['paths']))
anchor=time.monotonic_ns();origin=utc(o['now'])
runtime._utc_now=lambda:(origin+timedelta(seconds=(time.monotonic_ns()-anchor)//1_000_000_000)).strftime('%Y-%m-%dT%H:%M:%SZ')
validate,commit=c._validate_after,c._commit
def pause():print('PAUSED',flush=True);sys.stdin.readline()
def checked(db,plan):
 validate(db,plan)
 if o['phase']=='after_ddl':pause()
def committed(db):
 if o['phase']=='before_commit':pause()
 commit(db)
 if o['phase']=='after_commit':pause()
c._validate_after,c._commit=checked,committed
c.complete_approved(config,approved_plan_sha256=o['plan'],**o['grant'])
'''
