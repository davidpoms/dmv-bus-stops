"""Trusted-local orchestration against real disposable 2c/auth/ACK/approval stores."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import pickle
import sqlite3
import subprocess
import sys
import unittest
from unittest.mock import patch
from uuid import uuid4

from src.review.recognition import administration as a, administration_schema as base, authorization
from src.review.recognition import runtime_enrollment_transition as w
from src.review.recognition import runtime_enrollment_transition_schema as s
from src.review.recognition import runtime_target_entry_storage as package
from src.review.recognition import runtime_validation as runtime
from src.review.recognition.rules import canonical,digest
from src.review.recognition.trust import utc
from tests import test_recognition_runtime_enrollment_transition as fixtures
from tests.test_recognition_runtime_execution_attempt_creation import _cleanup_fixture_tree


class TransitionOrchestrationTests(unittest.TestCase):
    def test_disposable_lifecycle_failures_concurrency_and_legacy_isolation(self):
        # One expensive real enrollment fixture; every case restores only these
        # disposable files into their original inodes. No runtime producer mock.
        f=fixtures.EnrollmentTransitionTests();self.addCleanup(_cleanup_fixture_tree,f)
        f.setUp();f.migrate();config=f.config
        root=config.target.parent
        target_backup=root/'w-target-backup.db';control_backup=root/'w-control-backup.db'
        for source,path in ((config.target,target_backup),(config.control,control_backup)):
            with a.connect(source) as src, sqlite3.connect(path) as dst:src.backup(dst)
        with a.connect(config.control) as control:
            plan=f.plan(control)
        with a.connect(config.target) as target:
            plan['target_schema'].update(after_sha256=w._preview(target),added_definitions_sha256=digest(package.definitions()))
        now=plan['created_at_utc']
        original_commit=w._commit

        def restore():
            for source,path in ((target_backup,config.target),(control_backup,config.control)):
                with sqlite3.connect(source) as src,sqlite3.connect(path) as dst:src.backup(dst)

        def run(body=None):
            body=body or plan
            return w.transition(config,plan=body,plan_sha256=digest(body),target_backup=target_backup,control_backup=control_backup)

        def counts():
            with a.connect(config.control) as control,a.connect(config.target) as target:
                return (control.execute(f'SELECT count(*) FROM {s.PLANS}').fetchone()[0],
                    control.execute(f'SELECT max(sequence) FROM {s.HISTORY}').fetchone()[0],
                    control.execute('SELECT max(generation) FROM recognition_admin_bindings').fetchone()[0],
                    bool(target.execute("SELECT 1 FROM sqlite_master WHERE name=?",(package.TABLE,)).fetchone()))

        with patch.object(a,'target_identity',side_effect=authorization.target_identity),patch.object(runtime,'_utc_now',return_value=now):
            for key,value in [('source_generation',2),('source_binding_sha256','0'*64),('source_profile_sha256','0'*64),
                              ('migration_id','unregistered'),('installation_id',str(uuid4())),('owner_id',999),
                              ('source_auth_epoch',99),('source_mfa_epoch',99)]:
                bad=deepcopy(plan);bad[key]=value
                with self.subTest(rejection=key),self.assertRaises(ValueError):run(bad)
                self.assertEqual((0,None,3,False),counts())
            for key in ('before_sha256','after_sha256','added_definitions_sha256'):
                bad=deepcopy(plan);bad['target_schema'][key]='0'*64
                with self.subTest(schema=key),self.assertRaises(ValueError):run(bad)
                self.assertEqual((0,None,3,False),counts())
            with patch.object(runtime,'_utc_now',return_value=plan['deadline_at_utc']),self.assertRaises(ValueError):run()
            self.assertEqual((0,None,3,False),counts())

            bad=deepcopy(plan);bad['activation_head']['sequence']+=1
            with self.assertRaises(ValueError):run(bad)
            # Incorrect/old backup cannot establish preparation.
            with self.assertRaises(ValueError):
                w.transition(config,plan=plan,plan_sha256=digest(plan),target_backup=control_backup,control_backup=target_backup)
            self.assertEqual((0,None,3,False),counts())

            # Simulated interrupted/uncertain commits on BOTH sides, with real
            # durable inspection after stack unwind. No automatic continuation.
            cases=[('prepared',False,(0,None,3,False)),('prepared',True,(1,1,3,False)),
                ('intent',False,(1,1,3,False)),('intent',True,(1,2,3,False)),
                ('target',False,(1,2,3,False)),('target',True,(1,2,3,True)),
                ('schema_bound',False,(1,2,3,True)),('schema_bound',True,(1,3,4,True))]
            for stage,after,expected in cases:
                restore()
                def interrupt(conn,actual):
                    if actual==stage:
                        if after:original_commit(conn,actual)
                        raise OSError('simulated commit uncertainty')
                    original_commit(conn,actual)
                with self.subTest(stage=stage,after=after),patch.object(w,'_commit',side_effect=interrupt),self.assertRaises(OSError):run()
                self.assertEqual(expected,counts())
                inspected=w.inspect_transition(config.control,plan_id=plan['plan_id'])
                self.assertFalse(inspected['execution_authority']);self.assertFalse(inspected['retry_authorized'])
                if expected[0]:
                    before=counts()
                    with self.assertRaises(ValueError):run()  # new call/restart never adopts
                    self.assertEqual(before,counts())

            # An actual terminated process leaves only durable INTENT. The
            # restarted caller cannot turn that prefix into a live continuation.
            restore()
            script = '''import os,sys
from pathlib import Path
from unittest.mock import patch
from src.review.recognition import administration as a, runtime_validation as runtime
from src.review.recognition import runtime_enrollment_transition as w
from src.review.recognition.trust import load
config=a.LocalAdministration(*(Path(x) for x in sys.argv[1:4]))
plan=load(sys.argv[4]);original=w._commit
def terminate(conn,stage):
    original(conn,stage)
    if stage=='intent':os._exit(77)
with patch.object(runtime,'_utc_now',return_value=plan['created_at_utc']),patch.object(w,'_commit',side_effect=terminate):
    w.transition(config,plan=plan,plan_sha256=w.digest(plan),target_backup=Path(sys.argv[5]),control_backup=Path(sys.argv[6]))
'''
            child=subprocess.run([sys.executable,'-B','-c',script,str(config.target),str(config.control),str(config.key_file),
                canonical(plan),str(target_backup),str(control_backup)],capture_output=True,text=True,timeout=120)
            self.assertEqual(77,child.returncode,child.stderr)
            self.assertEqual((1,2,3,False),counts())
            with self.assertRaises(ValueError):run()

            restore()
            # A poisoned original owner cannot be serialized or cross-threaded.
            owner=w._Owner(config,plan)
            with self.assertRaises(TypeError):pickle.dumps(owner)
            with ThreadPoolExecutor(max_workers=1) as pool:
                with self.assertRaises(ValueError):pool.submit(owner.now).result()
            owner.alive=False
            with self.assertRaises(ValueError):owner.now()

            # Two genuine competing ceremonies serialize through SQLite; only
            # one complete graph can win, with no process-local locking.
            def contender():
                try:return run()
                except (ValueError,sqlite3.Error):return None
            with ThreadPoolExecutor(max_workers=2) as pool:
                results=list(pool.map(lambda _:contender(),range(2)))
            winners=[r for r in results if r is not None]
            self.assertEqual(1,len(winners));result=winners[0]
            self.assertEqual((1,3,4,True),counts())
            self.assertEqual(len(package.definitions()),result['target_ddl_count'])
            self.assertEqual((0,1,0,0),(result['target_dml_count'],result['target_commit_count'],result['writer_capability_count'],result['execution_count']))
            with a.connect(config.control) as control,a.connect(config.target) as target:
                base.check_control(control);package.check_schema(target)
                bound=s._binding(control,4)
                self.assertEqual('NOT_ACTIVATED',bound['production_state']);self.assertIsNone(bound['runtime_profile_sha256'])
                self.assertEqual(plan['target_schema']['after_sha256'],a.observe_target(target)['schema_sha256'])
                self.assertEqual([],target.execute(f'SELECT * FROM {package.TABLE}').fetchall())
                for table in ('recognition_execution_claims','recognition_execution_seals','recognition_operation_receipts'):
                    self.assertEqual(0,target.execute('SELECT count(*) FROM '+table).fetchone()[0])
                self.assertEqual([],control.execute('PRAGMA foreign_key_check').fetchall())
                for table,column in (('recognition_admin_primary','revoked'),('recognition_admin_sessions','revoked'),('recognition_admin_confirmations','used')):
                    self.assertEqual(0,control.execute(f'SELECT count(*) FROM {table} WHERE {column}=0').fetchone()[0])
                with self.assertRaisesRegex(ValueError,'runtime_profile_not_enrolled'):runtime._history(control)
                with self.assertRaisesRegex(ValueError,'runtime_schema_transition_pending'):s.require_no_pending(control)
            self.assertFalse(result['execution_authority']);self.assertFalse(result['retry_authorized'])


if __name__=='__main__':unittest.main()
