"""Slice 3b: disposable real migration/enrollment, real owner/MFA primitives."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from contextlib import contextmanager
import json
import sqlite3
import threading
import unittest
from unittest.mock import patch

from src.review.recognition import administration as a, admin_auth as auth, runtime_auth as ra
from src.review.recognition import runtime_validation as v, runtime_profile_schema as r
from src.review.recognition import runtime_enrollment as n, runtime_evidence as e
from src.review.recognition.rules import canonical, digest
from tests import test_recognition_administration as f
from tests import test_recognition_runtime_challenges as challenges


class RuntimeAuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = challenges.RuntimeChallengeTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.f = self.fixture.f
        self.config = self.f.config
        self.original_identity = a.target_identity
        issued = self.fixture.issue()
        self.issued = issued
        with patch.object(a, 'target_identity', side_effect=self.runtime_identity):
            record = e._collect(self.config.target, self.config.control,
                challenge_id=issued['challenge']['challenge_id'], challenge_sha256=issued['challenge']['challenge_sha256'], now=f.at(181))
        review = dict(format=n.REVIEW_FORMAT, observations=[record], selected_observation_sha256=record['observation_sha256'])
        self.record, self.review = record, review
        options = {key:value for key,value in self.fixture.options.items() if key != 'now'}
        with patch.object(n, '_utc_now', return_value=f.at(182)):
            self.enrollment = n.enroll_runtime_profile(self.config, canonical(review), issued['nonce'], **options,
                challenge_id=issued['challenge']['challenge_id'], challenge_sha256=issued['challenge']['challenge_sha256'],
                approved_review_sha256=digest(review), approved_observation_sha256=record['observation_sha256'],
                confirm_private_log_review=True, confirm_enroll_runtime_profile=True)
        self.assertEqual(3, self.enrollment['generation'])
        identity_patch = patch.object(a, 'target_identity', side_effect=self.runtime_identity)
        identity_patch.start(); self.addCleanup(identity_patch.stop)
        clock_patch = patch.object(v, '_utc_now', return_value=f.at(900))
        self.clock = clock_patch.start(); self.addCleanup(clock_patch.stop)

    def runtime_identity(self, subject):
        observed = self.original_identity(subject)
        return replace(observed, hostname='synthetic-web', device=observed.device+1)

    def primary(self):
        return ra.record_primary_authentication(self.config, actor_id=1, reviewer_key='owner-key')

    def session(self, primary):
        return ra.open_admin_session(self.config, primary, f.independent_code(self.clock.return_value))

    def validate(self, primary, session):
        return ra.require_recognition_admin(self.config, session, primary_token=primary)

    def sql(self, statement, values=(), *, target=False):
        with a.connect(self.config.target if target else self.config.control, write=True) as conn:
            result = conn.execute(statement, values).fetchall()
            conn.commit()
            return result

    def scope_count(self):
        with a.connect(self.config.control) as conn:
            return conn.execute(f'SELECT count(*) FROM {r.AUTH}').fetchone()[0]

    def test_primary_and_session_exact_scopes_no_plaintext_persistence(self):
        primary = self.primary()
        session = self.session(primary)
        self.assertEqual(1, self.validate(primary, session).actor_id)
        with a.connect(self.config.control) as conn:
            scopes = [dict(row) for row in conn.execute(f'SELECT * FROM {r.AUTH} ORDER BY token_kind')]
            self.assertEqual(['primary','session'], [row['token_kind'] for row in scopes])
            for scope, token, table in zip(scopes, (primary,session), ('recognition_admin_primary','recognition_admin_sessions')):
                self.assertEqual(a.token_hash(token), scope['token_hash'])
                self.assertEqual(self.enrollment['profile_sha256'], scope['profile_sha256'])
                proof = conn.execute(f'SELECT * FROM {table} WHERE token_hash=?',(scope['token_hash'],)).fetchone()
                self.assertEqual((3,1,proof['created']), (proof['generation'],proof['actor'],scope['created_at']))
                self.assertEqual(auth.PRIMARY_SECONDS if table.endswith('primary') else auth.SESSION_SECONDS,
                                 proof['expires']-proof['created'])
            dump = '\n'.join(conn.iterdump())
            self.assertNotIn(primary,dump); self.assertNotIn(session,dump)

    def test_wrong_owner_or_key_creates_no_auth(self):
        for actor,key in ((2,'reviewer-key'),(1,'wrong'),(True,'owner-key')):
            before = self.scope_count()
            with self.subTest(actor=actor,key=key), self.assertRaises(a.AdminError):
                ra.record_primary_authentication(self.config, actor_id=actor, reviewer_key=key)
            self.assertEqual(before,self.scope_count())

    def test_missing_scope_and_wrong_token_kind_denied(self):
        primary = self.primary()
        session = self.session(primary)
        with self.assertRaises(a.AdminError): ra.get_admin_identity(self.config,session)
        with self.assertRaises(a.AdminError): self.validate(primary,primary)
        self.sql('DROP TRIGGER '+r.AUTH+'_immutable_delete')
        self.sql(f"DELETE FROM {r.AUTH} WHERE token_kind='session'")
        self.sql(r.definitions()[r.AUTH+'_immutable_delete'])
        with self.assertRaisesRegex(a.AdminError,'runtime_authentication_scope_required'):
            self.validate(primary,session)

    def test_wrong_browser_parent_primary_denied(self):
        first = self.primary()
        session = self.session(first)
        second = self.primary()
        with self.assertRaisesRegex(a.AdminError,'browser_session_mismatch'):
            self.validate(second,session)
        self.assertEqual(1,self.validate(first,session).actor_id)

    def test_parent_actor_and_generation_are_explicitly_checked(self):
        primary = self.primary(); session = self.session(primary)
        for field,value in (('actor',2),('generation',1)):
            self.sql(f'UPDATE recognition_admin_primary SET {field}=? WHERE token_hash=?',(value,a.token_hash(primary)))
            with self.subTest(field=field), self.assertRaises((a.AdminError,ValueError)):
                self.validate(primary,session)
            self.sql(f'UPDATE recognition_admin_primary SET {field}=? WHERE token_hash=?',
                     (1 if field=='actor' else 3,a.token_hash(primary)))

    def test_logout_and_direct_revocation(self):
        primary=self.primary(); session=self.session(primary)
        ra.invalidate_primary(self.config,primary,now=f.at(900))
        with self.assertRaises(a.AdminError): self.validate(primary,session)
        primary=self.primary()
        self.clock.return_value=f.at(930)
        session=self.session(primary)
        self.sql('UPDATE recognition_admin_sessions SET revoked=1 WHERE token_hash=?',(a.token_hash(session),))
        with self.assertRaises(a.AdminError): self.validate(primary,session)

    def test_owner_epoch_key_and_mfa_epoch_changes_invalidate(self):
        primary=self.primary(); session=self.session(primary)
        self.sql('UPDATE recognition_admin_mfa SET epoch=epoch+1 WHERE actor=1')
        with self.assertRaisesRegex(a.AdminError,'expired_or_revoked'): self.validate(primary,session)
        self.sql("UPDATE community_reviewers SET reviewer_key='new-owner-key' WHERE id=1",target=True)
        with self.assertRaises(a.AdminError): ra.get_admin_identity(self.config,primary)
        self.sql("UPDATE community_reviewers SET role='reviewer' WHERE id=1",target=True)
        with self.assertRaisesRegex(a.AdminError,'recognition_owner_required'):
            ra.record_primary_authentication(self.config,actor_id=1,reviewer_key='new-owner-key')

    def test_authentication_epoch_change_even_without_key_change(self):
        primary=self.primary(); session=self.session(primary)
        self.sql('UPDATE recognition_local_installation SET auth_epoch=auth_epoch+1',target=True)
        with self.assertRaises(a.AdminError): self.validate(primary,session)

    def test_totp_replay_throttle_and_no_failed_sessions(self):
        primary=self.primary(); self.session(primary)
        for attempt in range(5):
            with self.assertRaisesRegex(a.AdminError,'invalid_or_replayed_totp'):
                self.session(primary)
        with self.assertRaisesRegex(a.AdminError,'mfa_rate_limited') as failure:
            self.session(primary)
        self.assertEqual(429,failure.exception.status)
        self.assertEqual(2,self.scope_count())
        self.assertEqual(5,self.sql('SELECT failures FROM recognition_admin_attempts WHERE actor=1')[0][0])

    def test_failed_totp_crossing_second_preserves_throttle(self):
        primary = self.primary()
        sessions = [tuple(row) for row in self.sql('SELECT * FROM recognition_admin_sessions')]
        original = auth._cipher
        def delayed(config):
            cipher = original(config)
            self.clock.return_value = f.at(901)
            return cipher
        with patch.object(auth, '_cipher', side_effect=delayed):
            with self.assertRaisesRegex(a.AdminError, 'invalid_or_replayed_totp'):
                ra.open_admin_session(self.config, primary, 'bad')
        self.assertEqual([(a.timestamp(f.at(900)), 1)], [tuple(row) for row in self.sql(
            'SELECT window_start,failures FROM recognition_admin_attempts WHERE actor=1')])
        self.assertEqual(1, self.scope_count())
        self.assertEqual(sessions, [tuple(row) for row in self.sql('SELECT * FROM recognition_admin_sessions')])

    def test_concurrent_totp_only_one_session_and_atomic_scopes(self):
        primary=self.primary()
        barrier=threading.Barrier(3)
        def attempt(_):
            barrier.wait()
            try: return self.session(primary)
            except a.AdminError as error: return error.code
        with ThreadPoolExecutor(max_workers=3) as pool: results=list(pool.map(attempt,range(3)))
        self.assertEqual(2,results.count('invalid_or_replayed_totp'))
        self.assertEqual(2,self.scope_count())

    def test_expiry_recent_primary_and_fresh_server_clock(self):
        primary=self.primary()
        self.clock.return_value=f.at(1500)
        with self.assertRaisesRegex(a.AdminError,'recent_primary_authentication_required'):
            self.session(primary)
        self.clock.return_value=f.at(900+auth.PRIMARY_SECONDS)
        with self.assertRaisesRegex(a.AdminError,'primary_authentication_required'):
            ra.get_admin_identity(self.config,primary,now=f.at(900))

    def test_session_exact_eight_hour_boundary(self):
        primary=self.primary(); session=self.session(primary)
        self.clock.return_value=f.at(900+auth.SESSION_SECONDS-1)
        self.assertEqual(1,self.validate(primary,session).actor_id)
        self.clock.return_value=f.at(900+auth.SESSION_SECONDS)
        with self.assertRaisesRegex(a.AdminError,'expired_or_revoked'): self.validate(primary,session)

    def test_scope_insert_and_final_identity_failures_roll_back_everything(self):
        before=self.scope_count()
        original=ra._insert_scope
        def fail(*args):
            original(*args)
            raise RuntimeError('after scope insert')
        with patch.object(ra,'_insert_scope',side_effect=fail),self.assertRaises(RuntimeError): self.primary()
        self.assertEqual(before,self.scope_count())
        def drift(*args):
            original(*args)
            self.identity_drift=True
        self.identity_drift=False
        with patch.object(a,'target_identity',side_effect=lambda subject:
                          self.original_identity(subject) if self.identity_drift else self.runtime_identity(subject)), \
             patch.object(ra,'_insert_scope',side_effect=drift), self.assertRaisesRegex(a.AdminError,'identity_mismatch'):
            self.primary()
        self.assertEqual(before,self.scope_count())

    def test_missing_and_changed_current_profile_after_authentication(self):
        primary=self.primary(); session=self.session(primary)
        with a.connect(self.config.control) as conn:
            body=json.loads(conn.execute('SELECT body_json FROM recognition_admin_bindings ORDER BY generation DESC LIMIT 1').fetchone()[0])
        for pointer in (None,'0'*64):
            changed=dict(body,runtime_profile_sha256=pointer)
            self.sql('DROP TRIGGER recognition_admin_bindings_immutable_update')
            self.sql('UPDATE recognition_admin_bindings SET body_json=?,body_sha256=? WHERE generation=3',(canonical(changed),digest(changed)))
            self.sql(a.schema.definitions()['recognition_admin_bindings_immutable_update'])
            with self.subTest(pointer=pointer),self.assertRaises((a.AdminError,ValueError)):
                self.validate(primary,session)

    def test_generation_change_after_primary_and_after_session(self):
        primary=self.primary(); session=self.session(primary)
        with a.connect(self.config.control,write=True) as conn:
            old=json.loads(conn.execute('SELECT body_json FROM recognition_admin_bindings ORDER BY generation DESC LIMIT 1').fetchone()[0])
            body=dict(old,generation=4,previous_sha256=digest(old),runtime_profile_sha256=None,at_utc=f.at(901))
            conn.execute('INSERT INTO recognition_admin_bindings VALUES(?,?,?)',(4,canonical(body),digest(body)))
            conn.commit()
        with self.assertRaises(a.AdminError): ra.get_admin_identity(self.config,primary)
        with self.assertRaises(a.AdminError): self.validate(primary,session)

    def test_restart_and_thread_context_checks_are_not_cached(self):
        primary=self.primary(); session=self.session(primary)
        self.assertEqual(1,self.validate(primary,session).actor_id)
        # A new worker PID observes itself and reuses only durable scoped tokens.
        real_pid=v.os.getpid()
        with patch.object(v.os,'getpid',return_value=real_pid+1):
            self.assertEqual(1,self.validate(primary,session).actor_id)
        with patch.object(a,'target_identity',side_effect=self.original_identity):
            with self.assertRaisesRegex(a.AdminError,'identity_mismatch'): self.validate(primary,session)

    def test_session_scope_failure_rolls_back_totp_and_session(self):
        primary=self.primary()
        counter=self.sql('SELECT last_counter FROM recognition_admin_mfa WHERE actor=1')[0][0]
        original=ra._insert_scope
        def fail(context,kind,token,now):
            original(context,kind,token,now)
            if kind=='session': raise RuntimeError('after session scope')
        with patch.object(ra,'_insert_scope',side_effect=fail),self.assertRaises(RuntimeError): self.session(primary)
        self.assertEqual(1,self.scope_count())
        self.assertEqual(counter,self.sql('SELECT last_counter FROM recognition_admin_mfa WHERE actor=1')[0][0])
        self.assertEqual(1,self.validate(primary,self.session(primary)).actor_id)

    def test_final_recent_primary_expiry_aborts_issuance_and_counter(self):
        primary=self.primary()
        counter=self.sql('SELECT last_counter FROM recognition_admin_mfa WHERE actor=1')[0][0]
        original=auth._code
        def delayed(*args,**kwargs):
            original(*args,**kwargs)
            self.clock.return_value=f.at(1500)
        with patch.object(auth,'_code',side_effect=delayed),self.assertRaisesRegex(a.AdminError,'recent_primary_authentication_required'):
            self.session(primary)
        self.assertEqual(1,self.scope_count())
        self.assertEqual(counter,self.sql('SELECT last_counter FROM recognition_admin_mfa WHERE actor=1')[0][0])

    def test_wrong_installation_target_and_runtime_profile_digest(self):
        primary=self.primary()
        for column in ('installation_id','target_id'):
            old=self.sql(f'SELECT {column} FROM recognition_local_installation',target=True)[0][0]
            self.sql(f'UPDATE recognition_local_installation SET {column}=?',('00000000-0000-0000-0000-000000000000',),target=True)
            with self.subTest(column=column),self.assertRaisesRegex(a.AdminError,'scope_mismatch'):
                ra.get_admin_identity(self.config,primary)
            self.sql(f'UPDATE recognition_local_installation SET {column}=?',(old,),target=True)
        self.sql('DROP TRIGGER '+r.PROFILES+'_immutable_update')
        self.sql(f"UPDATE {r.PROFILES} SET hostname='wrong-worker'")
        self.sql(r.definitions()[r.PROFILES+'_immutable_update'])
        with self.assertRaisesRegex(ValueError,'digest_mismatch'): ra.get_admin_identity(self.config,primary)

    def test_corrupt_foreign_stale_and_wrong_kind_scope_rows_fail_read_validation(self):
        primary=self.primary(); session=self.session(primary)
        with a.connect(self.config.control) as conn:
            original=dict(conn.execute(f"SELECT * FROM {r.AUTH} WHERE token_kind='session'").fetchone())
        # Deliberately simulate a restored store that previously bypassed CHECK/FK
        # enforcement. No verification function is mocked or bypassed on read.
        for column,value in (('profile_sha256','0'*64),('created_at',original['created_at']+1),('token_kind','primary')):
            with sqlite3.connect(self.config.control) as conn:
                conn.execute('DROP TRIGGER '+r.AUTH+'_immutable_update')
                conn.execute(f'UPDATE {r.AUTH} SET {column}=? WHERE token_hash=?',(value,a.token_hash(session)))
                conn.execute(r.definitions()[r.AUTH+'_immutable_update'])
            with self.subTest(column=column),self.assertRaises((a.AdminError,ValueError)):
                self.validate(primary,session)
            with sqlite3.connect(self.config.control) as conn:
                conn.execute('DROP TRIGGER '+r.AUTH+'_immutable_update')
                conn.execute(f"UPDATE {r.AUTH} SET {','.join(k+'=?' for k in original)} WHERE token_hash=?",
                             (*original.values(),a.token_hash(session)))
                conn.execute(r.definitions()[r.AUTH+'_immutable_update'])

    def test_concurrent_owner_epoch_and_demotion_rechecked_before_issuance(self):
        from concurrent.futures import TimeoutError
        original_connect=a.connect
        for mutation in ('UPDATE recognition_local_installation SET auth_epoch=auth_epoch+1',
                         "UPDATE community_reviewers SET role='reviewer' WHERE id=1"):
            opened=threading.Event()
            @contextmanager
            def connected(path,**kwargs):
                with original_connect(path,**kwargs) as conn:
                    if path==self.config.target and kwargs.get('write'): opened.set()
                    yield conn
            before=self.scope_count()
            with sqlite3.connect(self.config.target) as held, patch.object(a,'connect',side_effect=connected), ThreadPoolExecutor(max_workers=1) as pool:
                held.execute('BEGIN IMMEDIATE')
                future=pool.submit(self.primary)
                self.assertTrue(opened.wait(3))
                with self.assertRaises(TimeoutError): future.result(timeout=0.05)
                held.execute(mutation); held.commit()
                if mutation.startswith('UPDATE community'):
                    with self.assertRaisesRegex(a.AdminError,'recognition_owner_required'): future.result(timeout=5)
                    self.assertEqual(before,self.scope_count())
                else:
                    primary=future.result(timeout=5)
                    self.assertEqual(self.sql('SELECT auth_epoch FROM recognition_local_installation',target=True)[0][0],
                                     self.sql('SELECT auth_epoch FROM recognition_admin_primary WHERE token_hash=?',(a.token_hash(primary),))[0][0])

    def test_authenticated_owner_still_cannot_enter_downstream_admission(self):
        from src.review.recognition import production_operations as p, approvals, local_execution as execution, local_readiness, writer_boundary
        from src.review.recognition.authorization import AuthorizationError
        primary=self.primary(); session=self.session(primary)
        identity=self.validate(primary,session)
        before=self.config.target.read_bytes()
        with a.connect(self.config.control) as conn:
            protected={table:[tuple(row) for row in conn.execute('SELECT * FROM '+table)]
                       for table in (r.PROFILES,'recognition_admin_bindings','recognition_approvals','recognition_approval_history')}
        request=dict(request_id='11111111-1111-4111-8111-111111111111',family='first_look',inputs={},
                     evaluation_at_utc=f.at(900),review_reference='fixture',parent_operation_id=None)
        for call in (lambda:p.create_operation(self.config,session,request,now=f.at(900)),
                     lambda:p.load_context(self.config,self.f.oid),
                     lambda:approvals.create_approval(self.config,session,'unused','unused',operation_id=self.f.oid,reason='fixture',now=f.at(900)),
                     lambda:local_readiness.change_state(self.config,session,'unused',state='ACTIVATED',reason='fixture',now=f.at(900))):
            with self.assertRaisesRegex(a.AdminError,'runtime_profile_contract_not_enabled'): call()
        result=execution.execute_approved_operation(identity,session,'unused',now=f.at(900))
        self.assertEqual(('BLOCKED','NOT_STARTED'),(result.admission,result.state))
        with self.assertRaises(AuthorizationError): writer_boundary.acquire(identity,self.config.target,{})
        readiness=local_readiness.assess(self.config,now=f.at(900))
        self.assertFalse(readiness['activation_ready'])
        self.assertEqual(before,self.config.target.read_bytes())  # No awards, claims, seals or receipts.
        with a.connect(self.config.control) as conn:
            for table,rows in protected.items(): self.assertEqual(rows,[tuple(row) for row in conn.execute('SELECT * FROM '+table)])

    def test_real_subprocess_restart_validates_durable_session_without_key_read(self):
        import subprocess
        import sys
        primary=self.primary(); session=self.session(primary)
        code='''import json,sys,socket
from pathlib import Path
from dataclasses import replace,asdict
from src.review.recognition import administration as a,runtime_auth as ra,runtime_validation as v
value=json.load(sys.stdin)
paths=[Path(value[k]).resolve() for k in ('target','control','key')]
assert paths[0].parent==paths[1].parent==paths[2].parent
assert paths[0].parent.name.startswith('recognition-disposable-')
def guard(event,args):
 if event in ('socket.connect','socket.getaddrinfo'): raise RuntimeError('external access forbidden')
 if event=='sqlite3.connect' and not any(str(path) in str(args[0]) or path.as_uri() in str(args[0]) for path in paths[:2]): raise RuntimeError('unregistered database')
 if event=='open' and str(args[0])==str(paths[2]): raise RuntimeError('key read forbidden')
sys.addaudithook(guard)
original=a.target_identity
a.target_identity=lambda subject:replace(original(subject),hostname='synthetic-web',device=original(subject).device+1)
v._utc_now=lambda:'2099-01-01T00:15:00Z'
identity=ra.require_recognition_admin(a.LocalAdministration(*paths),value['session'],primary_token=value['primary'])
print(json.dumps(asdict(identity)))
'''
        result=subprocess.run([sys.executable,'-B','-c',code],input=json.dumps(dict(target=str(self.config.target),
            control=str(self.config.control),key=str(self.config.key_file),primary=primary,session=session)),
            capture_output=True,text=True,timeout=20)
        self.assertEqual(0,result.returncode,result.stderr)
        self.assertEqual(1,json.loads(result.stdout)['actor_id'])
        self.assertNotIn(primary,result.stdout+result.stderr); self.assertNotIn(session,result.stdout+result.stderr)

    def test_concurrent_stale_enrollment_cannot_change_authentication_scope(self):
        from concurrent.futures import TimeoutError
        entered,proceed=threading.Event(),threading.Event()
        original=ra._insert_scope
        def held(*args):
            original(*args)
            entered.set()
            if not proceed.wait(5): raise RuntimeError('test synchronization timeout')
        issued=self.issued
        options={k:value for k,value in self.fixture.options.items() if k!='now'}
        # The old source generation cannot enroll again, including while primary
        # issuance owns control. No rotation/recovery mechanism is manufactured.
        def stale():
            return n.enroll_runtime_profile(self.config,canonical(dict(format=n.REVIEW_FORMAT,
                observations=[self.record],selected_observation_sha256=self.record['observation_sha256'])),issued['nonce'],**options,
                challenge_id=issued['challenge']['challenge_id'],challenge_sha256=issued['challenge']['challenge_sha256'],
                approved_review_sha256=digest(self.review),approved_observation_sha256=self.record['observation_sha256'],
                confirm_private_log_review=True,confirm_enroll_runtime_profile=True)
        with patch.object(ra,'_insert_scope',side_effect=held),ThreadPoolExecutor(max_workers=2) as pool:
            authenticating=pool.submit(self.primary)
            self.assertTrue(entered.wait(3))
            enrolling=pool.submit(stale)
            try:
                with self.assertRaises(TimeoutError): enrolling.result(timeout=0.05)
            finally: proceed.set()
            primary=authenticating.result(timeout=5)
            with self.assertRaisesRegex(a.AdminError,'generation_or_binding_conflict'): enrolling.result(timeout=5)
        self.assertEqual(3,ra.get_admin_identity(self.config,primary).generation)

    def test_runtime_auth_context_access_rejects_other_thread_and_retired_context(self):
        with v.authentication_transaction(self.config) as context:
            self.assertEqual(3,ra._parts(context)[3]['generation'])
            def foreign():
                with self.assertRaisesRegex(a.AdminError,'runtime_context_invalid'): ra._parts(context)
            with ThreadPoolExecutor(max_workers=1) as pool: pool.submit(foreign).result()
        with self.assertRaisesRegex(a.AdminError,'runtime_context_invalid'): ra._parts(context)

    def test_generation_change_between_primary_and_mfa_blocks_session_without_revocation(self):
        primary=self.primary()
        counter=self.sql('SELECT last_counter FROM recognition_admin_mfa WHERE actor=1')[0][0]
        with a.connect(self.config.control,write=True) as conn:
            old=json.loads(conn.execute('SELECT body_json FROM recognition_admin_bindings ORDER BY generation DESC LIMIT 1').fetchone()[0])
            body=dict(old,generation=4,previous_sha256=digest(old),runtime_profile_sha256=None,at_utc=f.at(900))
            conn.execute('INSERT INTO recognition_admin_bindings VALUES(?,?,?)',(4,canonical(body),digest(body))); conn.commit()
        self.assertEqual(0,self.sql('SELECT revoked FROM recognition_admin_primary WHERE token_hash=?',(a.token_hash(primary),))[0][0])
        with self.assertRaisesRegex(a.AdminError,'runtime_profile_not_enrolled'): self.session(primary)
        self.assertEqual(1,self.scope_count())
        self.assertEqual(counter,self.sql('SELECT last_counter FROM recognition_admin_mfa WHERE actor=1')[0][0])


if __name__ == '__main__':
    unittest.main()
