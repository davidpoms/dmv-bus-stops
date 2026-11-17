"""Trusted-host recording only; all evidence here is explicitly synthetic."""

from copy import deepcopy
from dataclasses import replace
import io
import unittest
from unittest.mock import patch

from src.review.recognition import administration as a, authorization, local_readiness as ready
from src.review.recognition import runtime_activation as owner, runtime_validation as runtime, production_operations
from src.review.recognition import runtime_target_schema_completion as foundation
from src.review.recognition.rules import canonical, digest
from src.review.recognition.trust import load
from tests import test_recognition_target_schema_completion as fixture


class RuntimeDeploymentRehearsalTests(unittest.TestCase):
    def setUp(self):
        self.f = fixture.TargetSchemaCompletionTests()
        self.f.missing_runtime_prerequisites = True
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.config = self.f.config
        self.evidence = {name:digest(dict(synthetic_fixture_check=name)) for name in ready.REHEARSAL_CHECKS}

    def snapshot(self):
        return self.f.dump(self.config.target), self.f.dump(self.config.control)

    def record(self, **changes):
        options = dict(operator='synthetic-host-operator',reason='synthetic fixture rehearsal only',
                       evidence=self.evidence,now=fixture.base.at(1),expected_generation=5)
        options.update(changes)
        return ready.record_deployment_rehearsal(self.config,**options)

    def test_v3_records_existing_format_without_readiness_foundation_or_activation(self):
        protected = self.f.protected(); target = self.f.dump(self.config.target)
        with a.connect(self.config.control) as c:
            before = c.execute('SELECT COUNT(*) FROM recognition_admin_audit').fetchone()[0]
            binding, profile, _ = runtime._history(c)
        with patch.object(a,'transaction',side_effect=AssertionError('legacy path')), \
             patch.object(ready,'assess',side_effect=AssertionError('readiness invoked')), \
             patch.object(owner,'assess',side_effect=AssertionError('runtime readiness invoked')), \
             patch.object(foundation,'preview',side_effect=AssertionError('foundation invoked')), \
             patch.object(foundation,'complete',side_effect=AssertionError('completion invoked')):
            self.assertIsNone(self.record())
        self.assertEqual(target,self.f.dump(self.config.target))
        self.assertEqual(protected,self.f.protected())
        with a.connect(self.config.control) as c:
            self.assertEqual(before+1,c.execute('SELECT COUNT(*) FROM recognition_admin_audit').fetchone()[0])
            body = load(c.execute('SELECT body_json FROM recognition_admin_audit ORDER BY sequence DESC LIMIT 1').fetchone()[0])
            self.assertEqual(dict(action='local_deployment_rehearsal_recorded',actor='synthetic-host-operator',
                at_utc=runtime._utc_now(),subject=dict(target=production_operations.local_target(binding),
                evidence=self.evidence,reason='synthetic fixture rehearsal only',
                backup=dict(frequency='daily',retention_days=30,restore_verified=True)),previous_sha256=body['previous_sha256']),body)
            current, current_profile, _ = runtime._history(c)
            self.assertEqual(binding,current);self.assertEqual(profile,current_profile)
            self.assertEqual('NOT_ACTIVATED',ready._state(c,current)['state'])

    def test_exact_twelve_evidence_hashes_operator_reason_and_generation_required(self):
        before = self.snapshot()
        missing = dict(self.evidence);missing.pop(next(iter(missing)))
        extra = dict(self.evidence,unapproved='a'*64)
        invalid = dict(self.evidence);invalid['backup_creation']='not-a-sha256'
        cases = [dict(evidence=missing),dict(evidence=extra),dict(evidence=invalid),dict(evidence=[]),
                 dict(operator=''),dict(reason=' '),dict(expected_generation=6)]
        for values in cases:
            with self.subTest(values=list(values)),self.assertRaises(ValueError):self.record(**values)
            self.assertEqual(before,self.snapshot())

    def test_evidence_mutation_before_commit_rolls_back(self):
        before = self.snapshot(); original = a._audit
        def mutate(*args, **kwargs):
            original(*args,**kwargs)
            self.evidence['backup_restoration'] = 'f'*64
        with patch.object(a,'_audit',side_effect=mutate),self.assertRaisesRegex(ValueError,'deployment_rehearsal_evidence_changed'):
            self.record()
        self.assertEqual(before,self.snapshot())

    def test_frozen_evidence_mutation_before_commit_rolls_back(self):
        before = self.snapshot(); original = a._audit
        def mutate(control, action, actor, now, subject=None):
            original(control,action,actor,now,subject)
            subject['evidence']['backup_restoration'] = 'f'*64
        with patch.object(a,'_audit',side_effect=mutate),self.assertRaises(ValueError):self.record()
        self.assertEqual(before,self.snapshot())

    def test_scope_mutation_before_commit_rolls_back(self):
        before = self.snapshot(); original = owner._read_parts; calls = []
        def changed(context):
            parts = original(context)
            calls.append(None)
            if len(calls) >= 3:
                binding = deepcopy(parts[2]);binding['target_id']='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
                return parts[0],parts[1],binding,parts[3]
            return parts
        with patch.object(owner,'_read_parts',side_effect=changed),self.assertRaisesRegex(ValueError,'deployment_rehearsal_scope_changed'):
            self.record()
        self.assertEqual(before,self.snapshot())

    def test_audit_and_commit_failures_leave_no_partial_record(self):
        before = self.snapshot(); original = a._audit
        def failed_audit(*args, **kwargs):
            original(*args,**kwargs)
            raise RuntimeError('synthetic audit failure')
        for module, name, fail in ((a,'_audit',failed_audit),(owner,'_commit',RuntimeError('synthetic commit failure'))):
            with self.subTest(name=name),patch.object(module,name,side_effect=fail),self.assertRaises(RuntimeError):
                self.record()
            self.assertEqual(before,self.snapshot())
        self.record()  # A rollback does not disable a legitimate later attempt.

    def test_identity_profile_failures_do_not_fall_back_or_record(self):
        before = self.snapshot()
        original = authorization.target_identity
        with patch.object(a,'target_identity',side_effect=lambda path:replace(original(path),device=original(path).device+1)), \
             patch.object(a,'transaction',side_effect=AssertionError('legacy fallback')),self.assertRaises(ValueError):
            self.record()
        with patch.object(runtime,'_history',side_effect=a.AdminError('runtime_profile_not_enrolled',503)), \
             patch.object(a,'transaction',side_effect=AssertionError('legacy fallback')),self.assertRaises(ValueError):
            self.record()
        self.assertEqual(before,self.snapshot())

    def test_lost_commit_acknowledgement_leaves_one_complete_durable_record(self):
        protected=self.f.protected(); target=self.f.dump(self.config.target)
        with a.connect(self.config.control) as c:
            count=c.execute('SELECT COUNT(*) FROM recognition_admin_audit').fetchone()[0]
        original=owner._commit
        def lost(state):
            original(state)
            raise RuntimeError('synthetic lost acknowledgement')
        with patch.object(owner,'_commit',side_effect=lost),self.assertRaises(RuntimeError):self.record()
        self.assertEqual(protected,self.f.protected());self.assertEqual(target,self.f.dump(self.config.target))
        with a.connect(self.config.control) as c:
            self.assertEqual(count+1,c.execute('SELECT COUNT(*) FROM recognition_admin_audit').fetchone()[0])
            head=a._audit_head(c)
            record=load(head['body_json'])
            self.assertEqual('local_deployment_rehearsal_recorded',record['action'])
            self.assertEqual(self.evidence,record['subject']['evidence'])

    def test_final_manager_identity_check_failure_rolls_back(self):
        before = self.snapshot(); original = owner._read_parts; calls = []
        def changed(context):
            calls.append(None)
            if len(calls) >= 4:raise a.AdminError('runtime_validation_changed',503)
            return original(context)
        with patch.object(owner,'_read_parts',side_effect=changed),self.assertRaises(ValueError):self.record()
        self.assertEqual(before,self.snapshot())

    def cli(self, path, **changes):
        with patch('src.api.sqlite_runtime.load_production_sqlite'):
            from scripts.active import manage_recognition_administration as cli
        args = ['record-deployment-rehearsal','--target',str(self.config.target),'--control',str(self.config.control),
                '--key-file',str(self.config.key_file),'--operator','synthetic-host-operator','--reason','synthetic fixture only',
                '--expected-generation',str(changes.get('generation',5)),'--evidence-file',str(path)]
        with patch('sys.stdout',new_callable=io.StringIO) as out,patch('sys.stderr',new_callable=io.StringIO) as err:
            try:
                cli.main(args); status=0
            except SystemExit as error:
                status=error.code
            return status,out.getvalue(),err.getvalue()

    def test_cli_delegates_to_recorder_and_rejects_bad_files_without_leaks(self):
        path = self.config.target.parent/'synthetic-rehearsal-evidence.json'
        before = self.snapshot()
        path.write_text(canonical(dict(self.evidence,private_value='SENTINEL_PRIVATE_VALUE')))
        status,out,err = self.cli(path)
        self.assertEqual(1,status);self.assertNotIn('SENTINEL_PRIVATE_VALUE',out+err)
        self.assertEqual(before,self.snapshot())
        status,out,err = self.cli(self.config.key_file)
        self.assertEqual(1,status);self.assertEqual(before,self.snapshot())
        path.write_text(canonical(self.evidence))
        self.assertNotEqual(0,self.cli(path,generation=6)[0])
        self.assertEqual(before,self.snapshot())
        original = ready.record_deployment_rehearsal
        with patch.object(ready,'record_deployment_rehearsal',wraps=original) as record:
            status,out,err = self.cli(path)
        self.assertEqual(0,status,err);record.assert_called_once()
        self.assertEqual(dict(state='RECORDED',generation=5,evidence_checks=12,execution_authority=False),load(out))
        for secret in (self.f.primary,self.f.session,'SENTINEL_PRIVATE_VALUE'):
            self.assertNotIn(secret,out+err)

    def test_existing_owner_csrf_route_runs_in_runtime_context_and_rechecks_session(self):
        from flask import Flask
        from src.review.recognition import admin_routes
        app = Flask(__name__)
        app.config.update(TESTING=True,SECRET_KEY='disposable-rehearsal-route-test')
        admin_routes.register_admin_routes(app)
        client=app.test_client(); guest=app.test_client()
        with client.session_transaction() as browser:
            browser.update(authenticated_reviewer_id=1,reviewer_key='owner-key',auth_csrf='test-csrf',
                           recognition_primary=self.f.primary,recognition_admin=self.f.session)
        with guest.session_transaction() as browser:browser['auth_csrf']='test-csrf'
        path='/api/admin/recognition-control/runtime-activation/rehearsal'
        body=dict(csrf_token='test-csrf',operator='synthetic-owner',reason='synthetic fixture only',
                  generation=5,evidence=self.evidence)
        before=self.snapshot()
        with patch.object(admin_routes,'configuration',return_value=self.config):
            self.assertEqual(400,client.post(path,json=dict(body,csrf_token='wrong')).status_code)
            self.assertEqual(403,guest.post(path,json=body).status_code)
            self.assertEqual(400,client.post(path,json=dict(body,generation=6)).status_code)
            self.assertEqual(before,self.snapshot())
            with patch.object(owner,'_view',wraps=owner._view) as view:
                response=client.post(path,json=body)
            self.assertEqual(200,response.status_code,response.get_json())
            self.assertGreaterEqual(view.call_count,2)  # Route check and reserved recorder check.
            self.assertEqual('no-store',response.headers['Cache-Control'])
            self.assertEqual(dict(state='RECORDED',generation=5,evidence_checks=12,execution_authority=False),response.get_json())
            for token in (self.f.primary,self.f.session):self.assertNotIn(token,response.get_data(as_text=True))
            # Even a passed earlier route check cannot substitute for current session authority.
            with client.session_transaction() as browser:browser['recognition_admin']='invalid-session-reference-123456'
            with a.connect(self.config.control) as c:
                count=c.execute("SELECT COUNT(*) FROM recognition_admin_audit WHERE json_extract(body_json,'$.action')='local_deployment_rehearsal_recorded'").fetchone()[0]
            with patch.object(owner,'require_recognition_admin',return_value=None):
                self.assertEqual(401,client.post(path,json=body).status_code)
            with a.connect(self.config.control) as c:
                self.assertEqual(count,c.execute("SELECT COUNT(*) FROM recognition_admin_audit WHERE json_extract(body_json,'$.action')='local_deployment_rehearsal_recorded'").fetchone()[0])

    def test_reserved_http_session_expiry_rolls_back_record(self):
        before=self.snapshot(); original=a._audit
        def expire(*args,**kwargs):
            original(*args,**kwargs)
            self.f.f.clock.return_value=fixture.base.at(100000)
        with patch.object(a,'_audit',side_effect=expire),self.assertRaises(ValueError):
            self.record(session_token=self.f.session,primary_token=self.f.primary)
        self.assertEqual(before,self.snapshot())

    def test_v3_recorder_rejects_nonpreactivation_state(self):
        before=self.snapshot()
        with patch.object(ready,'_state',return_value=dict(state='SUSPENDED')),self.assertRaisesRegex(
                ValueError,'deployment_rehearsal_requires_not_activated'):
            self.record()
        self.assertEqual(before,self.snapshot())

