"""Slice 2c: local synthetic enrollment only; ordinary authority remains blocked."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
import io
import json
import sqlite3
import threading
import unittest
from unittest.mock import patch

from src.review.recognition import administration as a, administration_schema as s
from src.review.recognition import runtime_enrollment as n, runtime_evidence as e, runtime_profile_schema as r
from src.review.recognition.rules import canonical, digest
from tests import test_recognition_runtime_challenges as fixture
from tests import test_recognition_administration as f


class RuntimeEnrollmentTests(unittest.TestCase):
    def setUp(self):
        # The existing synthetic v3 fixture retains live, current-generation
        # authentication and an APPROVED approval, so revocation is observable.
        self.fixture=fixture.RuntimeChallengeTests('test_success_exact_fields_digest_expiry_nonce_and_no_authority')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.f=self.fixture.f
        self.binding=self.fixture.binding
        self.issued=self.fixture.issue()
        self.challenge=self.issued['challenge']
        original=a.target_identity
        with patch.object(a,'target_identity',side_effect=lambda subject:replace(original(subject),hostname='synthetic-web',device=original(subject).device+1)):
            self.record=e._collect(self.f.path,self.f.control,challenge_id=self.challenge['challenge_id'],
                                  challenge_sha256=self.challenge['challenge_sha256'],now=f.at(181))
        self.review=dict(format=n.REVIEW_FORMAT,observations=[self.record],selected_observation_sha256=self.record['observation_sha256'])
        self.options=dict(expected_generation=self.binding['generation'],installation_id=self.binding['installation_id'],
            target_id=self.binding['target_id'],owner_id=self.binding['owner_id'],source_binding_sha256=digest(self.binding),
            challenge_id=self.challenge['challenge_id'],challenge_sha256=self.challenge['challenge_sha256'],
            approved_review_sha256=digest(self.review),approved_observation_sha256=self.record['observation_sha256'],
            operator='trusted-fixture-operator',reason='independently reviewed private worker log',
            confirm_private_log_review=True,confirm_enroll_runtime_profile=True)
        clock_patch=patch.object(n,'_utc_now',return_value=f.at(182))
        self.clock=clock_patch.start()
        self.addCleanup(clock_patch.stop)

    def enroll(self,review=None,**changes):
        options=dict(self.options,**changes)
        return n.enroll_runtime_profile(self.f.config,canonical(self.review if review is None else review),
            self.issued['nonce'],**options)

    def snapshot(self):
        return self.f.path.read_bytes(),self.f.control.read_bytes()

    def changed_review(self,**changes):
        review=json.loads(canonical(self.review))
        review['observations'][0]['observation'].update(changes)
        record=review['observations'][0]
        record['observation_sha256']=digest(record['observation'])
        review['selected_observation_sha256']=record['observation_sha256']
        return review

    def approved(self,review):
        return dict(approved_review_sha256=digest(review),approved_observation_sha256=review['selected_observation_sha256'])

    def test_success_exact_profile_audit_revocation_and_blocked_authority(self):
        from src.review.recognition import approvals, admin_auth
        before_target=self.f.path.read_bytes()
        with a.connect(self.f.control) as conn:
            self.assertGreater(conn.execute('SELECT count(*) FROM recognition_admin_primary WHERE revoked=0').fetchone()[0],0)
            self.assertGreater(conn.execute('SELECT count(*) FROM recognition_admin_sessions WHERE revoked=0').fetchone()[0],0)
            self.assertGreater(conn.execute('SELECT count(*) FROM recognition_admin_stepups').fetchone()[0],0)
            self.assertGreater(conn.execute('SELECT count(*) FROM recognition_admin_confirmations WHERE used=0').fetchone()[0],0)
            old_approvals=[tuple(row) for row in conn.execute('SELECT * FROM recognition_approvals')]
            old_history=[tuple(row) for row in conn.execute('SELECT * FROM recognition_approval_history')]
            old_bindings=[tuple(row) for row in conn.execute('SELECT * FROM recognition_admin_bindings')]
            old_challenges=[tuple(row) for row in conn.execute(f'SELECT * FROM {r.CHALLENGES}')]
        with patch.object(admin_auth,'_cipher',side_effect=AssertionError('key read')):
            result=self.enroll()
        self.assertEqual(self.binding['generation']+1,result['generation'])
        self.assertEqual('BLOCKED',result['runtime_access'])
        with a.connect(self.f.control) as conn:
            s.check_control(conn)
            row=dict(conn.execute(f'SELECT * FROM {r.PROFILES}').fetchone())
            self.assertEqual(digest({k:v for k,v in row.items() if k!='profile_sha256'}),row['profile_sha256'])
            self.assertEqual(result['profile_sha256'],row['profile_sha256'])
            for k in n.PHYSICAL_FIELDS:self.assertEqual(self.record['observation'][k],row[k])
            latest=json.loads(conn.execute('SELECT body_json FROM recognition_admin_bindings ORDER BY generation DESC LIMIT 1').fetchone()[0])
            for k in ('target','control_identity','installation_id','target_id','owner_id'):
                self.assertEqual(self.binding[k],latest[k])
            self.assertEqual('NOT_ACTIVATED',latest['production_state'])
            self.assertEqual(result['profile_sha256'],latest['runtime_profile_sha256'])
            self.assertEqual(old_bindings,[tuple(v) for v in conn.execute('SELECT * FROM recognition_admin_bindings ORDER BY generation')][:-1])
            self.assertEqual(old_challenges,[tuple(v) for v in conn.execute(f'SELECT * FROM {r.CHALLENGES}')])
            for table in ('recognition_admin_primary','recognition_admin_sessions'):
                self.assertEqual(0,conn.execute(f'SELECT count(*) FROM {table} WHERE revoked=0').fetchone()[0])
            self.assertEqual(0,conn.execute('SELECT count(*) FROM recognition_admin_stepups').fetchone()[0])
            self.assertEqual(0,conn.execute('SELECT count(*) FROM recognition_admin_confirmations WHERE used=0').fetchone()[0])
            self.assertEqual(old_approvals,[tuple(v) for v in conn.execute('SELECT * FROM recognition_approvals')])
            self.assertEqual(old_history,[tuple(v) for v in conn.execute('SELECT * FROM recognition_approval_history')][:-1])
            self.assertEqual('INVALIDATED',approvals._read(conn,self.fixture.approved['approval']['approval_id'])['state'])
            self.assertEqual(0,conn.execute(f'SELECT count(*) FROM {r.AUTH}').fetchone()[0])
            head=a._audit_head(conn)
            self.assertEqual(row['audit_sequence'],head['sequence'])
            audit=json.loads(head['body_json'])
            self.assertEqual('runtime_profile_enrolled',audit['action'])
            self.assertEqual(self.review,audit['subject']['review'])
            self.assertNotIn(self.issued['nonce'],'\n'.join(conn.iterdump()))
        self.assertEqual(before_target,self.f.path.read_bytes())
        with self.assertRaisesRegex(a.AdminError,'runtime_profile_contract_not_enabled'):
            a.get_installation_control(self.f.config)

    def test_strict_review_parsing_and_field_types(self):
        cases=[dict(format='wrong'),dict(extra='value'),dict(observations=[]),dict(observations=True),
               dict(selected_observation_sha256='0'*64)]
        for changes in cases:
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                n.parse_review(canonical(dict(self.review,**changes)))
        for key,value in (('owner_id',True),('source_generation',True),('pid',False),('pid',0),
                ('observed_at',True),('observed_at',-1),('observed_at',r.MAX_TIME+1),
                ('challenge_expires_at',True),('installation_id','ABC'),('target_id','a'*36),
                ('hostname','bad\x00host'),('target_device','01'),('control_device','-1'),('target_device',1),
                ('target_inode','0'),('control_inode','42\x00'),('target_path','relative'),
                ('control_path',str(self.f.control)+'\x00'),('python_version','x'*4097),('python_executable',''),
                ('provenance','APPROVED'),('evidence_channel','browser'),('role','deployment'),('format','other')):
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                n.parse_review(canonical(self.changed_review(**{key:value})))
        for serialized in ('{"format":1,"format":2}',canonical(self.review).replace('"pid":','"pid":0.5,"old_pid":'),
                           'x'*(n.MAX_REVIEW_BYTES+1),'[]'):
            with self.subTest(serialized=serialized[:80]),self.assertRaises(ValueError):n.parse_review(serialized)

    def test_tampering_and_selection_rejected(self):
        review=json.loads(canonical(self.review))
        review['observations'][0]['observation']['hostname']='tampered'
        with self.assertRaisesRegex(a.AdminError,'digest_mismatch'):self.enroll(review)
        for changes in (dict(approved_review_sha256='0'*64),dict(approved_observation_sha256='0'*64)):
            with self.subTest(changes=changes),self.assertRaises(a.AdminError):self.enroll(**changes)

    def test_envelope_limits_duplicates_and_extra_observation_fields(self):
        for count in (2,n.MAX_OBSERVATIONS+1):
            review=dict(self.review,observations=[self.record]*count)
            with self.subTest(count=count),self.assertRaises(a.AdminError):n.parse_review(canonical(review))
        for key,value in (('target_device','42\x00'),('control_path',str(self.f.control.parent/'..'/'x')),
                          ('hostname','x'*256),('python_executable','x'*4097),('unexpected','value')):
            with self.subTest(key=key),self.assertRaises(ValueError):n.parse_review(canonical(self.changed_review(**{key:value})))
        # Canonical ASCII escaping is bounded independently of input UTF-8 size.
        oversized=self.changed_review(python_version='\u0100'*(n.MAX_REVIEW_BYTES//4))
        with self.assertRaises(a.AdminError):n.parse_review(json.dumps(oversized,ensure_ascii=False))
        with patch('pathlib.Path.resolve',side_effect=AssertionError('must reject UNC before resolution')):
            with self.assertRaisesRegex(a.AdminError,'runtime_enrollment_path_invalid'):
                n._path('\\\\untrusted-host\\share\\db.sqlite')

    def test_approval_and_scope_failures_rollback(self):
        for changes in (dict(confirm_private_log_review=False),dict(confirm_private_log_review=1),
                dict(confirm_enroll_runtime_profile=False),dict(expected_generation=True),dict(expected_generation=99),
                dict(source_binding_sha256='0'*64),dict(owner_id=2),dict(owner_id=True),
                dict(installation_id='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'),
                dict(target_id='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'),
                dict(challenge_id='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'),dict(challenge_sha256='0'*64),
                dict(operator=''),dict(reason='x\x00y')):
            before=self.snapshot()
            with self.subTest(changes=changes),self.assertRaises(ValueError):self.enroll(**changes)
            self.assertEqual(before,self.snapshot())

    def test_each_observation_scope_mismatch_rejected(self):
        for key,value in (('installation_id','aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'),
                ('target_id','aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'),('owner_id',2),('source_generation',2),
                ('source_binding_sha256','0'*64),('challenge_id','aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'),
                ('challenge_sha256','0'*64),('nonce_sha256','0'*64),('challenge_expires_at',9999999999),
                ('target_path',str(self.f.path.parent/'other.db')),('control_path',str(self.f.control.parent/'other.db')),
                ('target_inode','999'),('control_inode','999'),('target_schema_sha256','0'*64),
                ('observed_at',a.timestamp(f.at(179))),('observed_at',a.timestamp(f.at(183)))):
            review=self.changed_review(**{key:value})
            before=self.snapshot()
            with self.subTest(key=key),self.assertRaises(a.AdminError):self.enroll(review,**self.approved(review))
            self.assertEqual(before,self.snapshot())

    def test_contradictory_workers_never_silently_selected(self):
        for key in n.PHYSICAL_FIELDS:
            review=json.loads(canonical(self.review))
            other=json.loads(canonical(self.record))
            if key.endswith(('device','inode')):other['observation'][key]='999'
            elif key.endswith('sha256'):other['observation'][key]='0'*64
            elif key.endswith('path'):other['observation'][key]=str(self.f.path.parent/'other.db')
            else:other['observation'][key]='other-host'
            other['observation_sha256']=digest(other['observation'])
            review['observations'].append(other)
            with self.subTest(key=key),self.assertRaisesRegex(a.AdminError,'worker_disagreement'):
                self.enroll(review,**self.approved(review))

    def test_matching_workers_audited_selected_exactly(self):
        review=json.loads(canonical(self.review))
        other=json.loads(canonical(self.record))
        other['observation']['pid']+=1
        other['observation_sha256']=digest(other['observation'])
        review['observations'].append(other)
        review['selected_observation_sha256']=other['observation_sha256']
        result=self.enroll(review,**self.approved(review))
        with a.connect(self.f.control) as conn:
            self.assertEqual(other['observation_sha256'],conn.execute(f'SELECT observation_sha256 FROM {r.PROFILES}').fetchone()[0])
            self.assertEqual(review,json.loads(a._audit_head(conn)['body_json'])['subject']['review'])
        self.assertEqual(self.binding['generation']+1,result['generation'])

    def test_expiry_and_clock_rollback_at_all_boundaries(self):
        for times in ([f.at(780)],[f.at(179)],[f.at(182),f.at(780)],[f.at(182),f.at(181)]):
            before=self.snapshot()
            with self.subTest(times=times),patch.object(n,'_utc_now',side_effect=times),self.assertRaises(a.AdminError):self.enroll()
            self.assertEqual(before,self.snapshot())

    def test_nonce_is_canonical_required_and_not_persisted_on_failure(self):
        for nonce in ('','x'*43,self.issued['nonce']+'\x00','A'*43):
            before=self.snapshot()
            with self.subTest(nonce=nonce),self.assertRaises(a.AdminError):
                n.enroll_runtime_profile(self.f.config,canonical(self.review),nonce,**self.options)
            self.assertEqual(before,self.snapshot())

    def test_nonce_cannot_be_smuggled_into_audited_metadata(self):
        before=self.snapshot()
        review=self.changed_review(python_version=self.issued['nonce'])
        with self.assertRaisesRegex(a.AdminError,'nonce_in_record'):
            self.enroll(review,**self.approved(review))
        with self.assertRaisesRegex(a.AdminError,'nonce_in_record'):
            self.enroll(reason='mistakenly pasted '+self.issued['nonce'])
        self.assertEqual(before,self.snapshot())

    def test_large_decimal_devices_preserved_and_process_metadata_not_resolved(self):
        huge=str(2**64-1)
        review=self.changed_review(target_device=huge,control_device=huge,
                                  python_executable='/worker-only-namespace/python-symlink')
        self.enroll(review,**self.approved(review))
        with a.connect(self.f.control) as conn:
            row=conn.execute(f'SELECT target_device,control_device,typeof(target_device) FROM {r.PROFILES}').fetchone()
            self.assertEqual((huge,huge,'text'),tuple(row))

    def test_collection_and_enrollment_never_grant_downstream_admission(self):
        from src.review.recognition import production_operations as p,local_execution as execution,writer_boundary as writer
        from src.review.recognition import admin_auth,local_readiness
        self.enroll()
        with self.assertRaisesRegex(a.AdminError,'runtime_profile_contract_not_enabled'):
            admin_auth.require_recognition_admin(self.f.config,self.fixture.session,now=f.at(182))
        readiness=local_readiness.assess(self.f.config,now=f.at(182))
        self.assertFalse(readiness['activation_ready'])
        self.assertIn('runtime_profile_contract_not_enabled',canonical(readiness))
        context=object.__new__(p.ProductionOperationContext)
        p._contexts[context]=dict(config=self.f.config,operation_id='synthetic',consumed=False)
        self.addCleanup(p._contexts.pop,context,None)
        with patch.object(execution.permanent,'finalize',side_effect=AssertionError('writer invoked')):
            result=execution.execute_approved_operation(context,'no-session','no-approval',now=f.at(182))
        self.assertEqual('runtime_profile_contract_not_enabled',result.reason)
        with a.connect(self.f.control,write=True) as control,a.connect(self.f.path,write=True) as target:
            control.execute('BEGIN IMMEDIATE')
            target.execute('BEGIN IMMEDIATE')
            manifest=dict(synthetic='admission denial')
            claim=dict(execution_scope='trusted-local-production')
            p._contexts[context].update(writer_admission=(target,digest(manifest),digest(claim)),
                                       writer_control=control,consumed=True)
            with self.assertRaisesRegex(a.AdminError,'runtime_profile_contract_not_enabled'):
                with writer._local_lease(context,target,manifest,claim):self.fail('writer lease issued')

    def test_concurrent_different_challenges_only_one_enrolls(self):
        issued=self.fixture.issue()
        original=a.target_identity
        with patch.object(a,'target_identity',side_effect=lambda subject:replace(original(subject),hostname='synthetic-web',device=original(subject).device+1)):
            record=e._collect(self.f.path,self.f.control,challenge_id=issued['challenge']['challenge_id'],
                              challenge_sha256=issued['challenge']['challenge_sha256'],now=f.at(181))
        review=dict(format=n.REVIEW_FORMAT,observations=[record],selected_observation_sha256=record['observation_sha256'])
        barrier=threading.Barrier(2)
        def finalize(index):
            barrier.wait()
            try:
                if index==0:return self.enroll()
                options=dict(self.options,challenge_id=issued['challenge']['challenge_id'],
                             challenge_sha256=issued['challenge']['challenge_sha256'],**self.approved(review))
                return n.enroll_runtime_profile(self.f.config,canonical(review),issued['nonce'],**options)
            except a.AdminError as error:return error.code
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(finalize,range(2)))
        self.assertEqual(1,sum(type(result) is dict for result in results))
        self.assertIn('runtime_enrollment_generation_or_binding_conflict',results)

    def test_replay_and_rotation_denied(self):
        self.enroll()
        before=self.snapshot()
        with self.assertRaisesRegex(a.AdminError,'generation_or_binding_conflict'):self.enroll()
        with a.connect(self.f.control) as conn:
            latest=json.loads(conn.execute('SELECT body_json FROM recognition_admin_bindings ORDER BY generation DESC LIMIT 1').fetchone()[0])
        with self.assertRaisesRegex(a.AdminError,'already_enrolled'):
            self.enroll(expected_generation=latest['generation'],source_binding_sha256=digest(latest))
        self.assertEqual(before,self.snapshot())

    def test_concurrent_same_generation_exactly_once(self):
        barrier=threading.Barrier(2)
        def enroll(_):
            barrier.wait()
            try:return self.enroll()
            except a.AdminError as error:return error.code
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(enroll,range(2)))
        self.assertEqual(1,sum(type(result) is dict for result in results))
        self.assertIn('runtime_enrollment_generation_or_binding_conflict',results)
        with a.connect(self.f.control) as conn:
            s.check_control(conn)
            a._audit_head(conn)
            self.assertEqual(1,conn.execute(f'SELECT count(*) FROM {r.PROFILES}').fetchone()[0])

    def test_expiry_is_read_after_waiting_for_control_lock(self):
        before=self.snapshot()
        original=a.connect
        opened=threading.Event()
        @contextmanager
        def connected(path,**kwargs):
            with original(path,**kwargs) as conn:
                if path==self.f.control:opened.set()
                yield conn
        with original(self.f.control,write=True) as held,ThreadPoolExecutor(max_workers=1) as pool:
            held.execute('BEGIN IMMEDIATE')
            with patch.object(a,'connect',side_effect=connected):
                future=pool.submit(self.enroll)
                self.assertTrue(opened.wait(2),'worker did not open control')
                self.clock.assert_not_called()
                self.clock.return_value=f.at(780)
                held.rollback()
                with self.assertRaisesRegex(a.AdminError,'runtime_challenge_expired_or_not_yet_valid'):
                    future.result(timeout=5)
        self.assertEqual(before,self.snapshot())

    def test_durable_target_metadata_mismatch_rejected(self):
        for key,value in (('installation_id','aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'),
                          ('target_id','aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'),('owner_id',2)):
            with a.connect(self.f.path,write=True) as conn:
                conn.execute(f'UPDATE {s.TARGET_TABLE} SET {key}=?',(value,))
                conn.commit()
            with self.subTest(key=key),self.assertRaisesRegex(a.AdminError,'installation_target_mismatch'):self.enroll()
            with a.connect(self.f.path,write=True) as conn:
                conn.execute(f'UPDATE {s.TARGET_TABLE} SET {key}=?',(self.binding[key],))
                conn.commit()

    def test_deployment_identity_and_owner_fail_closed(self):
        original=a.target_identity
        for key,value in (('hostname','wrong'),('device',999),('inode',999),('database','/wrong/path')):
            with self.subTest(key=key),patch.object(a,'target_identity',side_effect=lambda subject:replace(original(subject),**{key:value})),self.assertRaises(a.AdminError):self.enroll()
        with patch.object(a,'observe_target',return_value={}),self.assertRaises(a.AdminError):self.enroll()
        with a.connect(self.f.path,write=True) as conn:
            conn.execute("UPDATE community_reviewers SET role='reviewer' WHERE id=1")
            conn.commit()
        with self.assertRaisesRegex(a.AdminError,'verified_project_owner_required'):self.enroll()

    def test_missing_genesis_and_partial_schema_fail_closed(self):
        with a.connect(self.f.control,write=True) as conn:
            conn.execute('DROP TRIGGER recognition_admin_bindings_immutable_update')
            body=dict(self.binding)
            del body['previous_sha256']
            conn.execute('UPDATE recognition_admin_bindings SET body_json=?,body_sha256=?',(canonical(body),digest(body)))
            conn.execute(s.definitions()['recognition_admin_bindings_immutable_update'])
            conn.commit()
        with self.assertRaisesRegex(a.AdminError,'history_integrity_failure'):
            self.enroll(source_binding_sha256=digest(body))
        with a.connect(self.f.control,write=True) as conn:
            conn.execute('DROP TRIGGER '+r.PROFILES+'_immutable_update')
            conn.commit()
        with self.assertRaisesRegex(ValueError,'schema_mismatch'):self.enroll()

    def test_non_not_activated_readiness_rejected(self):
        from src.review.recognition import local_readiness
        with a.connect(self.f.control,write=True) as conn:
            conn.execute('BEGIN')
            for definition in local_readiness.definitions().values():conn.execute(definition)
            local_readiness._append(conn,self.binding,'NOT_ACTIVATED',1,'fixture',f.at(181))
            local_readiness._append(conn,self.binding,'ACTIVATED',1,'synthetic denial fixture',f.at(181))
            conn.commit()
        before=self.snapshot()
        with self.assertRaisesRegex(a.AdminError,'requires_not_activated'):self.enroll()
        self.assertEqual(before,self.snapshot())

    def test_target_connection_reserved_but_query_only(self):
        original=a.connect
        checked=[]
        @contextmanager
        def connected(path,**kwargs):
            with original(path,**kwargs) as conn:
                if path==self.f.path:
                    def authorize(action,*args):
                        if action in (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE):
                            return sqlite3.SQLITE_DENY
                        return sqlite3.SQLITE_OK
                    conn.set_authorizer(authorize)
                yield conn
                if path==self.f.path:
                    self.assertTrue(conn.in_transaction)
                    self.assertEqual(1,conn.execute('PRAGMA query_only').fetchone()[0])
                    checked.append(True)
        with patch.object(a,'connect',side_effect=connected):self.enroll()
        self.assertEqual([True],checked)

    def test_rollback_after_each_mutation(self):
        from src.review.recognition import approvals
        for stage in ('profile','after_profile','auth','approval','binding','after_binding','audit','validation','commit'):
            before=self.snapshot()
            original_connect=a.connect
            @contextmanager
            def connected(path,**kwargs):
                with original_connect(path,**kwargs) as conn:
                    if path==self.f.control:
                        if stage in ('profile','binding'):
                            table=r.PROFILES if stage=='profile' else 'recognition_admin_bindings'
                            # Authorizer exceptions abort the actual SQLite INSERT.
                            def deny(action,table_name,*args):
                                if action==sqlite3.SQLITE_INSERT and table_name==table:return sqlite3.SQLITE_DENY
                                return sqlite3.SQLITE_OK
                            conn.set_authorizer(deny)
                        if stage=='commit':
                            def deny_commit(action,arg,*args):
                                if action==sqlite3.SQLITE_TRANSACTION and arg=='COMMIT':return sqlite3.SQLITE_DENY
                                return sqlite3.SQLITE_OK
                            conn.set_authorizer(deny_commit)
                    yield conn
            def after(function):
                def injected(*args,**kwargs):
                    function(*args,**kwargs)
                    raise RuntimeError('injected')
                return injected
            from contextlib import ExitStack
            with ExitStack() as stack:
                stack.enter_context(patch.object(a,'connect',side_effect=connected))
                if stage=='after_profile':stack.enter_context(patch.object(a,'_invalidate',side_effect=RuntimeError('injected')))
                if stage=='auth':stack.enter_context(patch.object(a,'_invalidate',side_effect=after(a._invalidate)))
                if stage=='approval':stack.enter_context(patch.object(approvals,'_invalidate_all',side_effect=after(approvals._invalidate_all)))
                if stage=='audit':stack.enter_context(patch.object(a,'_audit',side_effect=after(a._audit)))
                if stage=='after_binding':stack.enter_context(patch.object(a,'_audit',side_effect=RuntimeError('injected')))
                if stage=='validation':
                    original=s.check_control
                    calls=[]
                    def check(conn):
                        original(conn)
                        calls.append(1)
                        if len(calls)==3:raise RuntimeError('injected')
                    stack.enter_context(patch.object(s,'check_control',side_effect=check))
                with self.subTest(stage=stage),self.assertRaises((RuntimeError,sqlite3.DatabaseError)):self.enroll()
            self.assertEqual(before,self.snapshot())

    def test_cli_requires_confirmation_hidden_nonce_and_sanitizes_failure(self):
        with patch('src.api.sqlite_runtime.load_production_sqlite'):
            from scripts.active.manage_recognition_administration import main
        path=self.f.path.parent/'review.json'
        path.write_text(canonical(self.review),encoding='utf-8')
        args=['enroll-runtime-profile','--target',str(self.f.path),'--control',str(self.f.control),
            '--key-file',str(self.f.key_file),'--operator','fixture','--reason','reviewed',
            '--installation-id',self.binding['installation_id'],'--target-id',self.binding['target_id'],
            '--owner-id','1','--expected-generation',str(self.binding['generation']),
            '--source-binding-sha256',digest(self.binding),'--challenge-id',self.challenge['challenge_id'],
            '--challenge-sha256',self.challenge['challenge_sha256'],'--evidence-file',str(path),
            '--approved-review-sha256',digest(self.review),'--approved-observation-sha256',self.record['observation_sha256']]
        with patch('sys.stderr',new_callable=io.StringIO),patch('getpass.getpass',side_effect=AssertionError('premature prompt')),self.assertRaises(SystemExit):main(args)
        args+=['--confirm-private-log-review','--confirm-enroll-runtime-profile']
        for protected in (self.f.key_file,self.f.control,self.f.path):
            protected_args=list(args)
            protected_args[protected_args.index('--evidence-file')+1]=str(protected)
            with patch('pathlib.Path.open',side_effect=AssertionError('protected input opened')) as opened, \
                 patch('getpass.getpass',side_effect=AssertionError('premature prompt')), \
                 patch('sys.stderr',new_callable=io.StringIO),self.assertRaises(SystemExit):main(protected_args)
            opened.assert_not_called()
        with patch('getpass.getpass',return_value='bad nonce') as prompt,patch('sys.stderr',new_callable=io.StringIO) as err,self.assertRaises(SystemExit):main(args)
        self.assertEqual(1,prompt.call_count)
        self.assertNotIn('bad nonce',err.getvalue())
        import getpass
        import warnings
        def echo_fallback(*args,**kwargs):
            warnings.warn('cannot disable echo',getpass.GetPassWarning)
            self.fail('must not fall back to echoed input')
        with patch('getpass.getpass',side_effect=echo_fallback),patch('sys.stderr',new_callable=io.StringIO),self.assertRaises(SystemExit):
            main(args)
        with patch('getpass.getpass',return_value=self.issued['nonce']),patch('sys.stdout',new_callable=io.StringIO) as out:
            main(args)
        self.assertNotIn(self.issued['nonce'],out.getvalue())
        self.assertEqual('BLOCKED',json.loads(out.getvalue())['runtime_access'])


if __name__ == '__main__':
    unittest.main()
