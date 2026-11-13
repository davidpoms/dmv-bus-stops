"""Real v3 enrollment/auth/readiness/activation; disposable files only."""

import json
import pickle
import sqlite3
import subprocess
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from src.review.recognition import administration as a, admin_auth as auth
from src.review.recognition import runtime_activation as owner, local_readiness as readiness
from src.review.recognition import runtime_validation as v, production_operations
from src.review.recognition.rules import digest
from tests import test_recognition_runtime_activated_owner as fixtures
from tests import test_recognition_administration as base
from tests.recognition_production_owner_fixture import allocation


class ActivationOwnerTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(allocation())
        self.f = fixtures.RuntimeActivatedOwnerTests()

        def preactivation(fixture):
            with a.connect(fixture.config.control, write=True) as control:
                binding, _, _ = v._history(control)
                a._audit(control, 'local_deployment_rehearsal_recorded', 'disposable-test', v._utc_now(),
                    dict(target=production_operations.local_target(binding),
                         evidence={key:digest(dict(disposable=key)) for key in readiness.REHEARSAL_CHECKS},
                         reason='isolated activation test', backup=dict(frequency='daily', retention_days=30, restore_verified=True)))
                result = readiness._state(control, binding)
                control.commit()
                return result

        with patch.object(fixtures.RuntimeActivatedOwnerTests, 'activate_fixture', preactivation):
            self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.config, self.primary, self.session = self.f.config, self.f.primary, self.f.session
        self.clock = self.f.clock
        self.tick()

    def tick(self):
        self.clock.return_value = base.at(a.timestamp(self.clock.return_value) - a.timestamp(base.NOW) + 30)

    def status(self):
        return owner.inspect(self.config, self.session, primary_token=self.primary)

    def step(self, action='activate', **changes):
        self.tick()
        status = self.status()
        values = dict(primary_token=self.primary, action=action,
                      installation_id=status['installation_id'], generation=status['generation'])
        values.update(changes)
        return owner.create_step_up(self.config, self.session, base.independent_code(v._utc_now()), **values)

    def prepare(self):
        self.token = self.step()
        self.confirmation = owner.begin_confirmation(self.config, self.session, self.token, primary_token=self.primary)

    def activate(self):
        return owner.change_state(self.config, self.session, self.token, primary_token=self.primary,
            state='ACTIVATED', reason='disposable owner activation', confirmation_token=self.confirmation['confirmation_token'])

    def fresh(self):
        self.tick()
        self.primary = owner.record_primary_authentication(self.config, actor_id=1, reviewer_key='owner-key')
        self.session = owner.open_admin_session(self.config, self.primary, base.independent_code(v._utc_now()))

    def durable(self):
        with a.connect(self.config.control) as control:
            binding, _, _ = v._history(control)
            return readiness._state(control, binding)

    def test_activation_fresh_authentication_status_and_suspension(self):
        with a.connect(self.config.target) as target:
            before = '\n'.join(target.iterdump())
        self.prepare()
        activated = self.activate()
        self.assertEqual('ACTIVATED', activated['state'])
        with self.assertRaises(a.AdminError): self.status()
        self.fresh()
        self.assertEqual(activated, self.status()['activation'])
        self.assertFalse(self.status()['execution_authority'])
        step = self.step('suspend')
        result = owner.change_state(self.config, self.session, step, primary_token=self.primary,
                                    state='SUSPENDED', reason='disposable rollback')
        self.assertEqual('SUSPENDED', result['state'])
        self.fresh()
        self.assertEqual('SUSPENDED', self.status()['activation']['state'])
        with a.connect(self.config.target) as target:
            self.assertEqual(before, '\n'.join(target.iterdump()))

    def test_wrong_installation_and_generation(self):
        for changes in (dict(installation_id='wrong'), dict(generation=999), dict(generation=True)):
            with self.subTest(changes=changes), self.assertRaises(a.AdminError): self.step(**changes)
        self.assertEqual('NOT_ACTIVATED', self.durable()['state'])

    def test_unauthorized_owner_and_invalid_credentials(self):
        with self.assertRaises(a.AdminError):
            owner.record_primary_authentication(self.config, actor_id=2, reviewer_key='reviewer-key')
        with self.assertRaises(a.AdminError):
            owner.inspect(self.config, 'invalid', primary_token=self.primary)

    def test_missing_or_invalid_step_and_replayed_totp(self):
        for token in ('missing', ''):
            with self.subTest(token=token), self.assertRaises(a.AdminError):
                owner.begin_confirmation(self.config, self.session, token, primary_token=self.primary)
        step = self.step()
        status = self.status()
        with self.assertRaises(a.AdminError):
            owner.create_step_up(self.config, self.session, base.independent_code(v._utc_now()),
                primary_token=self.primary, action='activate', installation_id=status['installation_id'], generation=status['generation'])
        self.assertTrue(step)

    def test_readiness_failure(self):
        token = self.step()
        with patch.object(readiness, '_assess_activation', return_value=dict(activation_ready=False)):
            with self.assertRaises(a.AdminError):
                owner.begin_confirmation(self.config, self.session, token, primary_token=self.primary)
        self.assertEqual('NOT_ACTIVATED', self.durable()['state'])

    def test_confirmation_replay_and_already_active(self):
        self.prepare(); self.activate(); self.fresh()
        self.token = self.step()
        with self.assertRaises(a.AdminError): self.activate()
        with self.assertRaises(a.AdminError):
            owner.begin_confirmation(self.config, self.session, self.token, primary_token=self.primary)
        self.assertEqual('ACTIVATED', self.durable()['state'])

    def test_confirmation_cannot_outlive_its_step_up(self):
        self.prepare()
        with a.connect(self.config.control, write=True) as control:
            control.execute('UPDATE recognition_admin_confirmations SET expires=expires+1 WHERE token_hash=?',
                            (a.token_hash(self.confirmation['confirmation_token']),))
            control.commit()
        with self.assertRaises(a.AdminError) as error:
            self.activate()
        self.assertEqual('invalid_or_stale_activation_confirmation', error.exception.code)
        self.assertEqual('NOT_ACTIVATED', self.durable()['state'])

    def test_failure_before_commit_rolls_back_transition_and_fence(self):
        self.prepare()
        with patch.object(owner, '_commit', side_effect=SystemExit('simulated precommit termination')):
            with self.assertRaises(SystemExit): self.activate()
        self.assertEqual('NOT_ACTIVATED', self.status()['activation']['state'])
        with a.connect(self.config.control) as control:
            row = control.execute('SELECT used FROM recognition_admin_confirmations WHERE token_hash=?',
                (a.token_hash(self.confirmation['confirmation_token']),)).fetchone()
            self.assertEqual(0, row[0])

    def test_failure_after_commit_has_durable_activation_and_no_old_session(self):
        self.prepare()
        real = owner._commit
        def committed(state):
            real(state)
            raise SystemExit('simulated lost response after commit')
        with patch.object(owner, '_commit', side_effect=committed):
            with self.assertRaises(SystemExit): self.activate()
        self.assertEqual('ACTIVATED', self.durable()['state'])
        with self.assertRaises(a.AdminError): self.status()
        self.fresh()
        self.assertEqual('ACTIVATED', self.status()['activation']['state'])

    def test_failed_postactivation_auth_does_not_undo_activation(self):
        self.prepare(); self.activate(); self.tick()
        primary = owner.record_primary_authentication(self.config, actor_id=1, reviewer_key='owner-key')
        with self.assertRaises(a.AdminError): owner.open_admin_session(self.config, primary, 'invalid')
        self.assertEqual('ACTIVATED', self.durable()['state'])

    def test_owner_lifetime_and_no_handoff(self):
        with owner._transaction(self.config) as context:
            with self.assertRaises(TypeError): pickle.dumps(context)
            self.assertFalse(hasattr(context, 'execute'))
        with self.assertRaises(a.AdminError): owner._read_parts(context)
        self.assertFalse(self.status()['execution_authority'])

    def test_authentication_scope_keeps_exact_kernel_creation_second(self):
        original = owner._scope
        def next_second(context, kind, raw, created_at):
            offset = a.timestamp(self.clock.return_value) - a.timestamp(base.NOW)
            self.clock.return_value = base.at(offset + 1)
            return original(context, kind, raw, created_at)
        with patch.object(owner, '_scope', side_effect=next_second):
            self.fresh()
        self.assertEqual('NOT_ACTIVATED', self.status()['activation']['state'])

    def test_query_only_cannot_be_disabled(self):
        with self.assertRaises(a.AdminError):
            with owner._transaction(self.config) as context:
                with self.assertRaises(sqlite3.DatabaseError):
                    owner._state(context).body_target.execute('PRAGMA query_only=OFF')
        self.assertEqual('NOT_ACTIVATED', self.status()['activation']['state'])

    def test_revoked_session_denied(self):
        with a.connect(self.config.control, write=True) as control:
            control.execute('UPDATE recognition_admin_sessions SET revoked=1'); control.commit()
        with self.assertRaises(a.AdminError): self.status()

    def test_fresh_process_durable_verification(self):
        self.prepare(); expected = self.activate()
        script = ('import json,sys; from src.review.recognition import administration as a,local_readiness as r; '
                  'from src.review.recognition.trust import load; '
                  'c=a.connect(sys.argv[1]); db=c.__enter__(); '
                  'b=load(db.execute("SELECT body_json FROM recognition_admin_bindings ORDER BY generation DESC LIMIT 1").fetchone()[0]); '
                  'print(json.dumps(r.require_activated(db,b))); c.__exit__(None,None,None)')
        result = subprocess.run([sys.executable, '-B', '-c', script, str(self.config.control)],
                                capture_output=True, text=True, timeout=30, check=True)
        self.assertEqual(expected, json.loads(result.stdout))

    def test_http_page_csrf_activation_and_fresh_session(self):
        fixture = self.f
        while not hasattr(fixture, 'web'):
            fixture = fixture.f if hasattr(fixture, 'f') else fixture.fixture
        client = fixture.web()
        prefix = '/api/admin/recognition-control/'
        with client.session_transaction() as browser:
            browser.update(authenticated_reviewer_id=1, reviewer_key='owner-key',
                           recognition_primary=self.primary, recognition_admin=self.session, auth_csrf='test-csrf')
        self.assertEqual(200, client.get(prefix+'owner-activation').status_code)
        status = client.get(prefix+'runtime-activation')
        self.assertEqual(200, status.status_code, status.get_json())
        self.assertEqual('no-store', status.headers['Cache-Control'])
        current = status.get_json()
        checked = client.get(prefix+'runtime-activation/readiness')
        self.assertEqual(200, checked.status_code, checked.get_json())
        self.assertTrue(checked.get_json()['activation_ready'])
        self.tick()
        values = dict(code=base.independent_code(v._utc_now()), action='activate',
                      installation_id=current['installation_id'], generation=current['generation'])
        self.assertEqual(400, client.post(prefix+'runtime-activation/step-up', json=values).status_code)
        def post(path, **data):
            return client.post(prefix+path, json=dict(data, csrf_token='test-csrf'))
        step = post('runtime-activation/step-up', **values)
        self.assertEqual(200, step.status_code, step.get_json())
        token = step.get_json()['step_up_token']
        confirmation = post('runtime-activation/confirmations', step_up_token=token)
        self.assertEqual(200, confirmation.status_code, confirmation.get_json())
        activated = post('runtime-activation', state='ACTIVATED', step_up_token=token,
            confirmation_token=confirmation.get_json()['confirmation_token'], reason='disposable HTTP activation')
        self.assertEqual(200, activated.status_code, activated.get_json())
        with client.session_transaction() as browser:
            self.assertNotIn('recognition_primary', browser)
            self.assertNotIn('recognition_admin', browser)
        self.tick()
        self.primary = owner.record_primary_authentication(self.config, actor_id=1, reviewer_key='owner-key')
        with client.session_transaction() as browser:
            browser['recognition_primary'] = self.primary
        authenticated = post('session', code=base.independent_code(v._utc_now()))
        self.assertEqual(200, authenticated.status_code, authenticated.get_json())
        self.assertEqual('ACTIVATED', client.get(prefix+'runtime-activation').get_json()['activation']['state'])

    def mfa_client(self, unenrolled=True):
        fixture=self.f
        while not hasattr(fixture,'web'):
            fixture=fixture.f if hasattr(fixture,'f') else fixture.fixture
        if unenrolled:
            # Disposable first-time setup fixture only; production reset is not involved.
            with a.connect(self.config.control,write=True) as control:
                reset=control.execute("UPDATE recognition_admin_mfa SET state='UNENROLLED',seed_ciphertext=NULL,"
                                      "pending_primary=NULL,pending_until=NULL,last_counter=-1 WHERE actor=?",(1,))
                self.assertEqual(1,reset.rowcount)
                control.commit()
        self.primary=owner.record_primary_authentication(self.config,actor_id=1,reviewer_key='owner-key')
        client=fixture.web()
        with client.session_transaction() as browser:
            browser.update(authenticated_reviewer_id=1,reviewer_key='owner-key',
                           recognition_primary=self.primary,auth_csrf='test-csrf')
        return client

    def test_first_time_mfa_ui_and_durable_setup_without_activation_or_secret_logging(self):
        client=self.mfa_client()
        prefix='/api/admin/recognition-control/'
        with a.connect(self.config.target) as target:
            before='\n'.join(target.iterdump())
        page=client.get(prefix+'owner-activation')
        self.assertEqual(200,page.status_code)
        html=page.get_data(as_text=True)
        self.assertIn('Set up MFA',html)
        self.assertIn('mfa/state',html)
        self.assertIn("mfaState !== 'UNENROLLED'",html)
        status=client.get(prefix+'mfa/state')
        self.assertEqual({'state':'UNENROLLED','pending_expired':False},status.get_json())
        self.assertEqual('no-store',status.headers['Cache-Control'])
        with patch.object(auth.secrets,'token_bytes',return_value=base.SEED), \
             patch('logging.Logger._log') as logged:
            begun=client.post(prefix+'mfa/enrollment',json={'csrf_token':'test-csrf'})
            self.assertEqual(200,begun.status_code,begun.get_json())
            uri=begun.get_json()['provisioning_uri']
            self.assertTrue(uri.startswith('otpauth://'))
            self.assertEqual({'state':'PENDING','pending_expired':False},client.get(prefix+'mfa/state').get_json())
            self.assertNotIn(uri,client.get(prefix+'owner-activation').get_data(as_text=True))
            good=base.independent_code(v._utc_now())
            bad=str((int(good[0])+1)%10)+good[1:]
            rejected=client.post(prefix+'mfa/verify',json={'csrf_token':'test-csrf','code':bad})
            self.assertEqual('invalid_or_replayed_totp',rejected.get_json()['error'])
            self.assertEqual({'state':'PENDING','pending_expired':False},client.get(prefix+'mfa/state').get_json())
            verified=client.post(prefix+'mfa/verify',json={'csrf_token':'test-csrf','code':good})
            self.assertEqual({'state':'ENROLLED'},verified.get_json())
            self.assertEqual({'state':'ENROLLED','pending_expired':False},client.get(prefix+'mfa/state').get_json())
            replay=client.post(prefix+'session',json={'csrf_token':'test-csrf','code':good})
            self.assertEqual('invalid_or_replayed_totp',replay.get_json()['error'])
            self.tick()
            authenticated=client.post(prefix+'session',json={'csrf_token':'test-csrf',
                                                            'code':base.independent_code(v._utc_now())})
            self.assertEqual(200,authenticated.status_code,authenticated.get_json())
            log_text=repr(logged.call_args_list)
            self.assertNotIn(uri,log_text)
            self.assertNotIn('otpauth://',log_text)
            from urllib.parse import urlparse,parse_qs
            self.assertNotIn(parse_qs(urlparse(uri).query)['secret'][0],log_text)
        self.assertEqual('NOT_ACTIVATED',self.durable()['state'])
        with a.connect(self.config.target) as target:
            self.assertEqual(before,'\n'.join(target.iterdump()))

    def test_mfa_setup_csrf_exact_payload_recent_primary_and_existing_enrollment(self):
        client=self.mfa_client()
        prefix='/api/admin/recognition-control/'
        for path,valid in (('mfa/enrollment',{}),('mfa/verify',{'code':'123456'})):
            for payload in (valid,dict(valid,csrf_token='wrong'),
                            dict(valid,csrf_token='test-csrf',actor_id=1)):
                with self.subTest(path=path,payload=payload):
                    self.assertEqual(400,client.post(prefix+path,json=payload).status_code)
        for _ in range(20):self.tick()
        self.assertEqual(200,client.get(prefix+'owner-activation').status_code)
        denied=client.post(prefix+'mfa/enrollment',json={'csrf_token':'test-csrf'})
        self.assertEqual('recent_primary_authentication_required',denied.get_json()['error'])
        self.assertEqual({'state':'UNENROLLED','pending_expired':False},client.get(prefix+'mfa/state').get_json())
        self.assertEqual('NOT_ACTIVATED',self.durable()['state'])
        fresh=owner.record_primary_authentication(self.config,actor_id=1,reviewer_key='owner-key')
        with client.session_transaction() as browser:browser['recognition_primary']=fresh
        self.assertEqual(200,client.post(prefix+'mfa/enrollment',json={'csrf_token':'test-csrf'}).status_code)
        for _ in range(20):self.tick()
        expired=client.post(prefix+'mfa/verify',json={'csrf_token':'test-csrf',
                                                   'code':base.independent_code(v._utc_now())})
        self.assertEqual('recent_primary_authentication_required',expired.get_json()['error'])
        self.assertEqual({'state':'PENDING','pending_expired':True},client.get(prefix+'mfa/state').get_json())
        self.assertEqual('NOT_ACTIVATED',self.durable()['state'])
        with client.session_transaction() as browser:browser.pop('recognition_primary')
        self.assertEqual(401,client.get(prefix+'mfa/state').status_code)

    def test_enrolled_owner_state_and_existing_authentication(self):
        client=self.mfa_client(unenrolled=False)
        prefix='/api/admin/recognition-control/'
        self.assertEqual({'state':'ENROLLED','pending_expired':False},client.get(prefix+'mfa/state').get_json())
        denied=client.post(prefix+'mfa/enrollment',json={'csrf_token':'test-csrf'})
        self.assertEqual('mfa_already_enrolled_or_pending',denied.get_json()['error'])
        self.tick()
        response=client.post(prefix+'session',json={'csrf_token':'test-csrf',
                                                  'code':base.independent_code(v._utc_now())})
        self.assertEqual(200,response.status_code,response.get_json())
        self.assertEqual('NOT_ACTIVATED',self.durable()['state'])

    def test_mfa_client_reset_preserves_second_actor_sentinel(self):
        with a.connect(self.config.control,write=True) as control:
            control.execute("INSERT INTO recognition_admin_mfa(actor,seed_ciphertext,state,epoch,last_counter) "
                            "VALUES(2,'second-actor-sentinel','ENROLLED',7,123)")
            sentinel=tuple(control.execute('SELECT * FROM recognition_admin_mfa WHERE actor=2').fetchone())
            control.commit()
        self.mfa_client()
        with a.connect(self.config.control) as control:
            self.assertEqual(sentinel,tuple(control.execute(
                'SELECT * FROM recognition_admin_mfa WHERE actor=2').fetchone()))
            self.assertEqual(('UNENROLLED',None,-1),tuple(control.execute(
                'SELECT state,seed_ciphertext,last_counter FROM recognition_admin_mfa WHERE actor=1').fetchone()))

    def test_expired_pending_setup_restarts_only_with_fresh_primary_and_new_seed(self):
        client=self.mfa_client()
        prefix='/api/admin/recognition-control/'
        def pending():
            with a.connect(self.config.control) as control:
                return dict(control.execute('SELECT * FROM recognition_admin_mfa WHERE actor=1').fetchone())
        with patch.object(auth.secrets,'token_bytes',return_value=base.SEED):
            begun=client.post(prefix+'mfa/enrollment',json={'csrf_token':'test-csrf'})
            self.assertEqual(200,begun.status_code)
        old=pending()
        self.assertEqual({'state':'PENDING','pending_expired':False},client.get(prefix+'mfa/state').get_json())
        early=client.post(prefix+'mfa/enrollment',json={'csrf_token':'test-csrf'})
        self.assertEqual('mfa_already_enrolled_or_pending',early.get_json()['error'])
        for _ in range(20):self.tick()
        self.assertEqual({'state':'PENDING','pending_expired':True},client.get(prefix+'mfa/state').get_json())
        self.assertEqual(old,pending())  # Inspection never rewrites expired PENDING.
        stale=client.post(prefix+'mfa/enrollment',json={'csrf_token':'test-csrf'})
        self.assertEqual('recent_primary_authentication_required',stale.get_json()['error'])
        fresh=owner.record_primary_authentication(self.config,actor_id=1,reviewer_key='owner-key')
        with client.session_transaction() as browser:browser['recognition_primary']=fresh
        with patch.object(auth.secrets,'token_bytes',return_value=b'Z'*20):
            restarted=client.post(prefix+'mfa/enrollment',json={'csrf_token':'test-csrf'})
        self.assertEqual(200,restarted.status_code,restarted.get_json())
        self.assertNotEqual(begun.get_json()['provisioning_uri'],restarted.get_json()['provisioning_uri'])
        new=pending()
        self.assertEqual('PENDING',new['state'])
        self.assertNotEqual(old['seed_ciphertext'],new['seed_ciphertext'])
        self.assertEqual(a.token_hash(fresh),new['pending_primary'])
        self.assertEqual(a.timestamp(v._utc_now())+auth.RECENT_SECONDS,new['pending_until'])
        self.assertEqual(old['epoch'],new['epoch'])
        self.assertEqual(-1,new['last_counter'])
        self.assertEqual({'state':'PENDING','pending_expired':False},client.get(prefix+'mfa/state').get_json())
        self.assertEqual('NOT_ACTIVATED',self.durable()['state'])

    def test_concurrent_activation_has_one_committed_transition(self):
        self.prepare()
        def attempt():
            try:
                return self.activate()['state']
            except a.AdminError:
                return 'REJECTED'
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: attempt(), range(2)))
        self.assertEqual(['ACTIVATED', 'REJECTED'], sorted(results))
        self.assertEqual('ACTIVATED', self.durable()['state'])
        with a.connect(self.config.control) as control:
            self.assertEqual(2, control.execute('SELECT count(*) FROM recognition_local_activation').fetchone()[0])

    def test_process_termination_immediately_before_and_after_commit(self):
        # One child per boundary; before-commit death leaves no committed change.
        self.prepare()
        script = '''
import json,os,sys,time
from pathlib import Path
from dataclasses import replace
from datetime import timedelta
from src.review.recognition import runtime_activation as o,administration as a,runtime_validation as v
from src.review.recognition.trust import utc
p=json.load(sys.stdin)
c=a.LocalAdministration(*map(Path,p['paths']))
original=a.target_identity
def observed(subject):
    value=original(subject)
    expected=p['identities'][str(Path(value.database))]
    return replace(value,hostname=expected['hostname'],device=expected['device'],inode=expected['inode'])
a.target_identity=observed
from src.review.recognition import dependencies
dependencies.target_identity=observed
anchor=time.monotonic()
v._utc_now=lambda:(utc(p['now'])+timedelta(seconds=int(time.monotonic()-anchor))).strftime('%Y-%m-%dT%H:%M:%SZ')
commit=o._commit
def terminate(state):
    if p['after']:commit(state)
    os._exit(79)
o._commit=terminate
o.change_state(c,p['session'],p['step'],primary_token=p['primary'],state='ACTIVATED',
               reason='disposable child crash boundary',confirmation_token=p['confirmation'])
'''
        from dataclasses import asdict
        paths = [self.config.target, self.config.control, self.config.key_file]
        identities = {str(path):asdict(a.target_identity(path)) for path in paths[:2]}
        for after in (False, True):
            payload = dict(paths=list(map(str, paths)), identities=identities, now=v._utc_now(),
                session=self.session, primary=self.primary, step=self.token,
                confirmation=self.confirmation['confirmation_token'], after=after)
            result = subprocess.run([sys.executable, '-B', '-c', script], input=json.dumps(payload),
                                    capture_output=True, text=True, timeout=90)
            self.assertEqual(79, result.returncode, result.stderr)
            self.assertEqual('ACTIVATED' if after else 'NOT_ACTIVATED', self.durable()['state'])
        with self.assertRaises(a.AdminError): self.status()
        self.fresh()
        step = self.step('deactivate')
        self.assertEqual('DEACTIVATED', owner.change_state(self.config, self.session, step,
            primary_token=self.primary, state='DEACTIVATED', reason='disposable revocation')['state'])
        self.fresh()
        step = self.step('activate')
        with self.assertRaises(a.AdminError):
            owner.begin_confirmation(self.config, self.session, step, primary_token=self.primary)


if __name__ == '__main__':
    unittest.main()
