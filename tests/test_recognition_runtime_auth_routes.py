"""Real login-token hook and existing HTTP authentication routes only."""

from dataclasses import asdict
import json
from unittest.mock import patch
import unittest

from src.api import app as api
from src.review.recognition import administration as a, admin_auth as auth, admin_routes, runtime_auth as ra
from src.review.recognition import runtime_profile_schema as r, runtime_validation as v
from tests import test_recognition_runtime_authentication as fixtures
from tests import test_recognition_administration as f


class RuntimeAuthRouteTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.RuntimeAuthenticationTests()
        self.fixture.setUp(); self.addCleanup(self.fixture.doCleanups)
        self.f=self.fixture.f
        self.config=self.fixture.config
        self.client=self.f.web()
        self.f.web_now=f.at(900)

    def login(self):
        self.f.login(self.client)  # Real issue/consume_login_token and unmodified app hook.
        with self.client.session_transaction() as browser:
            return browser['recognition_primary']

    def authenticated(self):
        primary=self.login()
        response=self.f.post(self.client,'session',code=f.independent_code(self.f.web_now))
        self.assertEqual(200,response.status_code,response.get_json())
        with self.client.session_transaction() as browser:
            return primary,browser['recognition_admin']

    def test_real_login_enrollment_runtime_primary_mfa_session_scope(self):
        primary,session=self.authenticated()
        self.assertEqual(1,ra.require_recognition_admin(self.config,session,primary_token=primary).actor_id)
        self.assertEqual(2,self.fixture.scope_count())
        with a.connect(self.config.target) as target:
            self.assertTrue(target.execute('SELECT used_at FROM reviewer_login_tokens ORDER BY id DESC LIMIT 1').fetchone()[0])
        for path in ('identity','session'):
            response=self.client.get('/api/admin/recognition-control/'+path)
            self.assertEqual(200,response.status_code)
            self.assertEqual({'actor_id','installation_id','generation'},set(response.get_json()))
            self.assertEqual(3,response.get_json()['generation'])
            self.assertEqual('no-store',response.headers['Cache-Control'])
            for value in ('hostname','device','inode','profile_sha256',primary,session):
                self.assertNotIn(value,response.get_data(as_text=True))

    def test_existing_mfa_enrollment_routes_reuse_same_crypto_and_counter(self):
        self.fixture.sql("UPDATE recognition_admin_mfa SET state='UNENROLLED',seed_ciphertext=NULL,last_counter=-1,epoch=epoch+1")
        self.login()
        with patch.object(auth.secrets,'token_bytes',return_value=f.SEED):
            response=self.f.post(self.client,'mfa/enrollment')
        self.assertEqual(200,response.status_code,response.get_json())
        self.assertIn('otpauth://',response.get_json()['provisioning_uri'])
        self.assertEqual(200,self.f.post(self.client,'mfa/verify',code=f.independent_code(f.at(900))).status_code)
        self.fixture.clock.return_value=f.at(930); self.f.web_now=f.at(930)
        self.assertEqual(200,self.f.post(self.client,'session',code=f.independent_code(f.at(930))).status_code)

    def test_no_browser_identity_claim_csrf_or_session_flag_authentication(self):
        self.assertEqual(403,self.client.get('/api/admin/recognition-control/identity').status_code)
        with self.client.session_transaction() as browser:
            browser.update(authenticated_reviewer_id=1,reviewer_key='owner-key',is_admin=True)
        self.assertEqual(401,self.client.get('/api/admin/recognition-control/identity').status_code)
        self.login()
        for field,value in (('hostname','synthetic-web'),('generation',3),('profile_sha256',self.fixture.enrollment['profile_sha256']),
                            ('installation_id',f.INSTALLATION),('device',1),('target_id','any'),('nonce','any')):
            with self.subTest(field=field):
                response=self.f.post(self.client,'session',code='000000',**{field:value})
                self.assertEqual(400,response.status_code)
        self.assertEqual(400,self.client.post('/api/admin/recognition-control/session',json={'code':'000000'}).status_code)

    def test_logout_revokes_copied_primary_and_session(self):
        primary,session=self.authenticated()
        with self.client.session_transaction() as browser: csrf=browser['auth_csrf']
        self.assertEqual(200,self.client.post('/reviewer/sign-out',json=dict(csrf_token=csrf)).status_code)
        with self.assertRaises(a.AdminError): ra.require_recognition_admin(self.config,session,primary_token=primary)

    def test_browser_primary_and_session_must_belong_together(self):
        primary,session=self.authenticated()
        other=self.fixture.primary()
        with self.client.session_transaction() as browser: browser['recognition_primary']=other
        response=self.client.get('/api/admin/recognition-control/session')
        self.assertEqual(403,response.status_code)
        self.assertEqual('administrative_browser_session_mismatch',response.get_json()['error'])

    def test_runtime_mismatch_keeps_reviewer_login_but_mints_no_primary(self):
        before=self.fixture.scope_count()
        with patch.object(a,'target_identity',side_effect=self.fixture.original_identity):
            self.f.login(self.client)
            with self.client.session_transaction() as browser:
                self.assertEqual(1,browser['authenticated_reviewer_id'])
                self.assertNotIn('recognition_primary',browser)
        self.assertEqual(before,self.fixture.scope_count())

    def test_authenticated_owner_downstream_routes_remain_blocked(self):
        self.authenticated()
        target_before=self.config.target.read_bytes()
        with a.connect(self.config.control) as conn:
            profile_before=tuple(conn.execute(f'SELECT * FROM {r.PROFILES}').fetchone())
            bindings_before=[tuple(row) for row in conn.execute('SELECT * FROM recognition_admin_bindings')]
        for path in ('readiness','installation','operations/'+self.f.oid,'operations/'+self.f.oid+'/approvals'):
            with self.subTest(path=path):
                response=self.client.get('/api/admin/recognition-control/'+path)
                self.assertEqual(503,response.status_code,response.get_json())
                self.assertEqual('runtime_profile_contract_not_enabled',response.get_json()['error'])
        request=dict(request_id='11111111-1111-4111-8111-111111111111',family='first_look',inputs={},
                     evaluation_at_utc=f.at(900),review_reference='fixture',parent_operation_id=None)
        for path,values in (('operations',request),('activation',dict(state='ACTIVATED',reason='fixture',step_up_token='unused',confirmation_token='unused')),
                            ('step-up',dict(code='000000',action='activate',operation_id=None)),
                            ('operations/'+self.f.oid+'/approve',dict(reason='fixture',step_up_token='unused',confirmation_token='unused')),
                            ('activation/confirmations',dict(step_up_token='unused'))):
            with self.subTest(path=path):
                response=self.f.post(self.client,path,**values)
                self.assertEqual(503,response.status_code,response.get_json())
                self.assertEqual('runtime_profile_contract_not_enabled',response.get_json()['error'])
        self.assertEqual(target_before,self.config.target.read_bytes())
        with a.connect(self.config.control) as conn:
            self.assertEqual(profile_before,tuple(conn.execute(f'SELECT * FROM {r.PROFILES}').fetchone()))
            self.assertEqual(bindings_before,[tuple(row) for row in conn.execute('SELECT * FROM recognition_admin_bindings')])


if __name__ == '__main__':
    unittest.main()
