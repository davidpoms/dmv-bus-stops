"""G+1 -> G+2 with real disposable W/2a/2b stores; never runtime authority."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
import contextlib
import io
import sqlite3
import unittest
from unittest.mock import patch
from uuid import uuid4

from src.review.recognition import administration as a, administration_schema as base, authorization, admin_auth
from src.review.recognition import runtime_enrollment_transition as y, runtime_enrollment_transition_schema as s
from src.review.recognition import runtime_enrollment as codec, runtime_evidence, runtime_challenges, runtime_validation as runtime
from src.review.recognition import runtime_profile_schema as profiles, runtime_target_entry_storage as package
from src.review.recognition.rules import canonical,digest
from tests import test_recognition_runtime_enrollment_transition as fixtures
from tests.test_recognition_runtime_execution_attempt_creation import _cleanup_fixture_tree


class TransitionRuntimeProfileTests(unittest.TestCase):
    def test_real_transition_enrollment_atomicity_scope_and_no_authority(self):
        f=fixtures.EnrollmentTransitionTests();self.addCleanup(_cleanup_fixture_tree,f)
        f.setUp();f.migrate();config=f.config
        root=config.target.parent
        backups=(root/'y-old-target.db',root/'y-old-control.db')
        for source,path in zip((config.target,config.control),backups):
            with a.connect(source) as src,sqlite3.connect(path) as dst:src.backup(dst)
        with a.connect(config.control) as control:plan=f.plan(control)
        with a.connect(config.target) as target:
            plan['target_schema'].update(after_sha256=y._preview(target),added_definitions_sha256=digest(package.definitions()))
        now=plan['created_at_utc']
        with patch.object(a,'target_identity',side_effect=authorization.target_identity),patch.object(runtime,'_utc_now',return_value=now):
            y.transition(config,plan=plan,plan_sha256=digest(plan),target_backup=backups[0],control_backup=backups[1])
            with a.connect(config.control) as control:
                bound=s._binding(control,4)
                old_profile=dict(control.execute(f'SELECT * FROM {profiles.PROFILES} WHERE profile_sha256=?',(plan['source_profile_sha256'],)).fetchone())
            issued=runtime_challenges.issue_challenge(config,expected_generation=4,installation_id=bound['installation_id'],
                target_id=bound['target_id'],owner_id=bound['owner_id'],source_binding_sha256=digest(bound),
                operator='y-operator',reason='fresh transition observation',now=now)
            def worker_identity(subject):
                actual=authorization.target_identity(subject)
                prefix='target' if actual.database==str(config.target) else 'control'
                return replace(actual,hostname=old_profile['hostname'],device=int(old_profile[prefix+'_device']),inode=int(old_profile[prefix+'_inode']))
            with patch.object(a,'target_identity',side_effect=worker_identity):
                record=runtime_evidence._collect(config.target,config.control,challenge_id=issued['challenge']['challenge_id'],
                    challenge_sha256=issued['challenge']['challenge_sha256'],now=now)
            review=dict(format=codec.REVIEW_FORMAT,observations=[record],selected_observation_sha256=record['observation_sha256'])
            options=dict(plan_id=plan['plan_id'],plan_sha256=digest(plan),expected_generation=4,
                installation_id=bound['installation_id'],target_id=bound['target_id'],owner_id=bound['owner_id'],source_binding_sha256=digest(bound),
                challenge_id=issued['challenge']['challenge_id'],challenge_sha256=issued['challenge']['challenge_sha256'],
                approved_review_sha256=digest(review),approved_observation_sha256=record['observation_sha256'],
                operator='y-operator',reason='independently reviewed transition worker log',
                confirm_private_log_review=True,confirm_enroll_runtime_profile=True)
            baseline=root/'y-schema-bound-control.db'
            with a.connect(config.control) as src,sqlite3.connect(baseline) as dst:src.backup(dst)
            with a.connect(config.target) as target:target_data=y._data(target)
            with a.connect(config.control) as control:
                bindings=[tuple(r) for r in control.execute('SELECT * FROM recognition_admin_bindings')]
                approvals=[tuple(r) for r in control.execute('SELECT * FROM recognition_approvals')]
                old_profiles=[tuple(r) for r in control.execute(f'SELECT * FROM {profiles.PROFILES}')]
                auth=[tuple(r) for r in control.execute(f'SELECT * FROM {profiles.AUTH}')]

            def restore():
                with sqlite3.connect(baseline) as src,sqlite3.connect(config.control) as dst:src.backup(dst)

            def run(changes=None,body=None,nonce=None):
                return y.enroll_transition_runtime_profile(config,canonical(body or review),nonce or issued['nonce'],**dict(options,**(changes or {})))

            def state():
                with a.connect(config.control) as control:
                    base.check_control(control)
                    return (control.execute('SELECT max(generation) FROM recognition_admin_bindings').fetchone()[0],
                        control.execute(f'SELECT max(sequence) FROM {s.HISTORY} WHERE plan_id=?',(plan['plan_id'],)).fetchone()[0],
                        control.execute(f'SELECT count(*) FROM {profiles.PROFILES}').fetchone()[0])
            before=state()
            for key,value in [('plan_id',str(uuid4())),('plan_sha256','0'*64),('expected_generation',3),
                    ('source_binding_sha256','0'*64),('installation_id',str(uuid4())),('target_id',str(uuid4())),
                    ('owner_id',999),('challenge_sha256','0'*64),('confirm_private_log_review',False),('confirm_enroll_runtime_profile',False)]:
                with self.subTest(reject=key),self.assertRaises(ValueError):run({key:value})
                self.assertEqual(before,state())
            with self.assertRaises(ValueError):run(nonce='A'*43)
            with patch.object(runtime,'_utc_now',return_value=plan['deadline_at_utc']),self.assertRaises(ValueError):run()
            # The actual schema must still be H1, even when all supplied hashes match.
            with a.connect(config.target,write=True) as target:
                target.execute('CREATE INDEX synthetic_y_schema_drift ON community_reviewers(id)');target.commit()
            with self.assertRaises(ValueError):run()
            with a.connect(config.target,write=True) as target:
                target.execute('DROP INDEX synthetic_y_schema_drift');target.commit()
            self.assertEqual(before,state())
            with a.connect(config.control,write=True) as control:
                control.execute('UPDATE recognition_admin_mfa SET epoch=epoch+1');control.commit()
            with self.assertRaises(ValueError):run()
            restore()
            from src.review.recognition import local_readiness
            with a.connect(config.control,write=True) as control:
                control.execute('BEGIN IMMEDIATE')
                local_readiness._append(control,bound,'DEACTIVATED','y-test','changed activation head',now)
                control.commit()
            with self.assertRaises(ValueError):run()
            restore()
            # Approved but physically different evidence cannot rotate P0.
            for field in ('hostname','target_device','control_device','target_inode','control_inode'):
                bad=deepcopy(review);bad['observations'][0]['observation'][field]=('other-host' if field=='hostname' else '999')
                bad['observations'][0]['observation_sha256']=digest(bad['observations'][0]['observation'])
                bad['selected_observation_sha256']=bad['observations'][0]['observation_sha256']
                with self.subTest(physical=field),self.assertRaises(ValueError):
                    run(dict(approved_review_sha256=digest(bad),approved_observation_sha256=bad['selected_observation_sha256']),body=bad)
                self.assertEqual(before,state())
            with self.assertRaisesRegex(ValueError,'runtime_schema_transition_pending'):
                with patch.object(codec,'_utc_now',return_value=now):
                    initial={k:v for k,v in options.items() if k not in ('plan_id','plan_sha256')}
                    codec.enroll_runtime_profile(config,canonical(review),issued['nonce'],**initial)

            insert=y._insert
            def reject_profile(conn,table,row):
                if table==profiles.PROFILES:raise OSError('synthetic profile insertion failure')
                return insert(conn,table,row)
            with patch.object(y,'_insert',side_effect=reject_profile),self.assertRaises(OSError):run()
            self.assertEqual(before,state())
            commit=y._commit
            for after in (False,True):
                restore()
                def uncertain(conn,stage):
                    if after:commit(conn,stage)
                    raise OSError('synthetic uncertain commit')
                with patch.object(y,'_commit',side_effect=uncertain),self.assertRaises(OSError):run()
                self.assertEqual((5,4,before[2]+1) if after else before,state())
                result=y.inspect_runtime_profile_transition(config.control,plan_id=plan['plan_id'])
                self.assertEqual('FINALIZED' if after else 'SCHEMA_BOUND',result['status'])
                self.assertFalse(result['profile_result_authority'])
                if after:
                    with self.assertRaises(ValueError):run()

            restore()
            def contender():
                try:return run()
                except (ValueError,sqlite3.Error):return None
            with patch.object(admin_auth,'_cipher',side_effect=AssertionError('key-content read')):
                with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:contender(),range(2)))
            winners=[r for r in results if r is not None]
            self.assertEqual(1,len(winners));result=winners[0]
            self.assertEqual((5,4,before[2]+1),state())
            self.assertFalse(result['execution_authority']);self.assertFalse(result['runtime_authentication_issued'])
            self.assertEqual('NOT_ACTIVATED',result['production_state'])
            with self.assertRaises(ValueError):run()  # matching retry is inspection only
            with a.connect(config.control) as control,a.connect(config.target) as target:
                current,profile,_=runtime._history(control)
                self.assertEqual(5,current['generation']);self.assertEqual(result['profile_sha256'],profile['profile_sha256'])
                self.assertEqual(bindings,[tuple(r) for r in control.execute('SELECT * FROM recognition_admin_bindings WHERE generation<5')])
                self.assertEqual(approvals,[tuple(r) for r in control.execute('SELECT * FROM recognition_approvals')])
                self.assertEqual(old_profiles,[tuple(r) for r in control.execute(f'SELECT * FROM {profiles.PROFILES} WHERE generation<5')])
                self.assertEqual(auth,[tuple(r) for r in control.execute(f'SELECT * FROM {profiles.AUTH}')])
                self.assertEqual(target_data,y._data(target))
                self.assertEqual(0,target.execute(f'SELECT count(*) FROM {package.TABLE}').fetchone()[0])
                self.assertNotIn(issued['nonce'],'\n'.join(control.iterdump()))
                s.require_no_pending(control)
                from src.review.recognition import local_readiness
                with self.assertRaises(ValueError):local_readiness.require_activated(control,current)

    def test_cli_requires_scope_and_hidden_nonce_only(self):
        with patch('src.api.sqlite_runtime.load_production_sqlite'):
            from scripts.active.manage_recognition_administration import main
        with contextlib.redirect_stderr(io.StringIO()),patch('getpass.getpass',side_effect=AssertionError('must not prompt')):
            for args in (['enroll-transition-runtime-profile'],['enroll-transition-runtime-profile','--nonce','secret']):
                with self.subTest(args=args),self.assertRaises(SystemExit):main(args)


if __name__=='__main__':unittest.main()
