"""Disposable G5/G6 fixtures only. No hosted evidence or production keys."""
import base64
from copy import deepcopy
from dataclasses import asdict, replace
from datetime import timedelta
import unittest
import subprocess
import sys
import importlib.util
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from uuid import uuid4

from flask import Flask
from src.review.recognition import administration as a, authorization, runtime_validation as runtime
from src.review.recognition import runtime_profile_successor as successor, runtime_profile_successor_contract as contract
from src.review.recognition import runtime_production_governance as governance, runtime_enrollment as enrollment
from src.review.recognition.rules import canonical, digest
from src.review.recognition.trust import load, utc
from tests import test_recognition_target_schema_completion as fixture
from tests.recognition_deployment_qualification_fixture import prepare as backups


class SuccessorTests(unittest.TestCase):
    def setUp(self):
        actual = authorization.target_identity
        identity = lambda value: replace(actual(value), hostname='synthetic-web', device=57)
        self.enterContext(patch.object(authorization, 'target_identity', side_effect=identity))
        self.enterContext(patch.object(a, 'target_identity', side_effect=identity))
        self.f = fixture.TargetSchemaCompletionTests()
        self.f.omit_qualification = True
        self.f.omit_rehearsal = True
        self.f.missing_runtime_prerequisites = self._testMethodName == 'test_g6_v2_missing_prerequisites_foundation'
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.config = self.f.config
        self.app = Flask(__name__)
        self.enterContext(self.app.test_request_context('/maintenance'))
        with a.connect(self.config.control) as control:
            binding, profile, _ = runtime._history(control)
        original = {key: dict(hostname=profile['hostname'], database=profile[key+'_path'],
                             device=int(profile[key+'_device']), inode=int(profile[key+'_inode']))
                    for key in ('target', 'control')}
        self.enterContext(patch.object(contract, 'SOURCE', original))
        self.enterContext(patch.object(contract, 'SOURCE_BINDING', digest(binding)))
        self.enterContext(patch.object(contract, 'SOURCE_PROFILE', profile['profile_sha256']))
        self.current_device = 49
        self.identity = lambda value: replace(actual(value), hostname='synthetic-web', device=self.current_device)
        self.enterContext(patch.object(a, 'target_identity', side_effect=self.identity))
        self.enterContext(patch.object(authorization, 'target_identity', side_effect=self.identity))
        for path in (self.config.target, self.config.control, self.config.key_file):
            path.chmod(0o600); path.parent.chmod(0o700)
        self.recorded = []
        self.enterContext(patch.object(successor.evidence, '_log_record', side_effect=lambda app, record: self.recorded.append(record)))
        self.root = governance._root(self.config)
        self.identifier = str(uuid4())

    def envelope(self, kind, **values):
        subject = dict(kind=kind, **values)
        body = dict(format=governance.FORMAT, mandate=self.root['mandate'], installation_id=self.root['installation_id'],
            binding_sha256=contract.SOURCE_BINDING, holder=dict(kind='governance_custodian', actor_id=self.root['owner_id']),
            subject=subject, target=contract.destination()['target'], control=contract.destination()['control'],
            issued_at_utc=runtime._utc_now(),
            expires_at_utc=(utc(runtime._utc_now())+timedelta(seconds=300)).strftime('%Y-%m-%dT%H:%M:%SZ'))
        body['approvals'] = [contract.approval(subject, body['target'], body['expires_at_utc'], body['mandate'])]
        encoded = canonical(body)
        return dict(serialized_approval=encoded, signature=base64.b64encode(self.f.key.sign(governance.DOMAIN+encoded.encode())).decode())

    def prepare(self):
        scope = successor.describe(self.config)['scope']
        envelope = self.envelope(contract.PREPARE, authorization_id=self.identifier, scope=scope,
                                 operator='fixture-owner', reason='synthetic device transition')
        self.prepared = successor.prepare(self.config, envelope)
        return envelope

    def plan(self):
        review = dict(format=enrollment.REVIEW_FORMAT, observations=self.recorded,
                      selected_observation_sha256=self.recorded[0]['observation_sha256'])
        self.paths = backups(self, self.config, record=False)['backups']
        return successor.plan(self.config, self.envelope(contract.INSPECT, authorization_id=self.identifier), review, self.paths)['plan']

    def snapshot(self):
        return self.config.target.read_bytes(), self.config.control.read_bytes()

    def test_exact_transition_no_ddl_strict_validation_and_preservation(self):
        before_target = self.config.target.read_bytes()
        with a.connect(self.config.control) as control:
            ddl = [tuple(row) for row in control.execute('SELECT * FROM sqlite_master ORDER BY name')]
            g5 = [tuple(row) for row in control.execute('SELECT * FROM recognition_runtime_profiles')]
            mfa = [tuple(row) for row in control.execute('SELECT * FROM recognition_admin_mfa')]
        self.prepare()
        plan = self.plan()
        with a.connect(self.config.control) as control:
            self.assertNotIn(self.prepared['nonce'],'\n'.join(control.iterdump()))
        before = self.snapshot()
        repeated = successor.plan(self.config, self.envelope(contract.INSPECT, authorization_id=self.identifier), plan['review'], self.paths)
        self.assertEqual(plan, repeated['plan'])
        self.assertEqual(before, self.snapshot())
        result = successor.complete(self.config, self.envelope(contract.COMPLETE, plan=plan), self.prepared['nonce'])
        self.assertEqual(('COMMITTED', 6, False), (result['state'], result['generation'], result['execution_authority']))
        self.assertEqual(before_target, self.config.target.read_bytes())
        with a.connect(self.config.control) as control:
            self.assertEqual(ddl, [tuple(row) for row in control.execute('SELECT * FROM sqlite_master ORDER BY name')])
            self.assertEqual(g5, [tuple(row) for row in control.execute('SELECT * FROM recognition_runtime_profiles WHERE generation=5')])
            self.assertEqual(mfa, [tuple(row) for row in control.execute('SELECT * FROM recognition_admin_mfa')])
            self.assertFalse(control.execute('SELECT 1 FROM recognition_admin_sessions WHERE revoked=0').fetchone())
        self.assertEqual(6, runtime.validate_runtime_snapshot(self.config)['generation'])
        self.current_device = 63
        with self.assertRaisesRegex(a.AdminError, 'runtime_profile_identity_mismatch'):
            runtime.validate_runtime_snapshot(self.config)
        self.current_device = 49
        status = successor.inspect(self.config, self.envelope(contract.INSPECT, authorization_id=self.identifier))
        self.assertEqual('COMMITTED', status['state'])
        with self.assertRaises(ValueError):
            successor.complete(self.config, self.envelope(contract.COMPLETE, plan=plan), self.prepared['nonce'])

    def test_wrong_devices_reject_without_writes(self):
        before = self.snapshot()
        for device in (48, 50, 57):
            self.current_device = device
            with self.subTest(device=device), self.assertRaisesRegex(a.AdminError, 'physical_identity'):
                successor.describe(self.config)
        self.assertEqual(before, self.snapshot())

    def test_signature_purpose_scope_and_replay(self):
        scope = successor.describe(self.config)['scope']
        envelope = self.envelope(contract.PREPARE, authorization_id=self.identifier, scope=scope, operator='fixture', reason='test')
        bad = dict(envelope, signature=base64.b64encode(b'X'*64).decode())
        before = self.snapshot()
        with self.assertRaisesRegex(a.AdminError, 'signature'):
            successor.prepare(self.config, bad)
        with self.assertRaises(ValueError):
            successor.prepare(self.config, self.envelope(contract.INSPECT, authorization_id=self.identifier))
        self.assertEqual(before, self.snapshot())
        self.prepare()
        with self.assertRaises(ValueError):
            successor.prepare(self.config, envelope)

    def test_failed_commit_rolls_back_successor_and_revocation(self):
        self.prepare()
        plan = self.plan()
        envelope = self.envelope(contract.COMPLETE, plan=plan)
        before = self.snapshot()
        with patch.object(successor, '_commit', side_effect=RuntimeError('synthetic interruption')):
            with self.assertRaises(RuntimeError):
                successor.complete(self.config, envelope, self.prepared['nonce'])
        self.assertEqual(before, self.snapshot())
        self.assertEqual('COMMITTED', successor.complete(self.config, envelope, self.prepared['nonce'])['state'])

    def test_bad_plan_and_nonce_do_not_mutate(self):
        self.prepare()
        plan = self.plan()
        before = self.snapshot()
        altered = deepcopy(plan); altered['template_sha256'] = '0'*64
        with self.assertRaises(ValueError):
            successor.complete(self.config, self.envelope(contract.COMPLETE, plan=altered), self.prepared['nonce'])
        with self.assertRaisesRegex(a.AdminError, 'nonce_mismatch'):
            successor.complete(self.config, self.envelope(contract.COMPLETE, plan=plan), 'wrong')
        self.assertEqual(before, self.snapshot())

    def test_physical_and_signed_scope_rejections(self):
        scope = successor.describe(self.config)['scope']
        before = self.snapshot()
        for key, value in (('binding_sha256','0'*64), ('profile_sha256','0'*64), ('source_generation',4),
                           ('destination_generation',7), ('owner_id',2), ('installation_id',str(uuid4())),
                           ('target_id',str(uuid4())), ('target_schema_sha256','0'*64),
                           ('control_schema_sha256','0'*64), ('auth_epoch',999), ('mfa_epoch',999)):
            bad = deepcopy(scope);bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                successor.prepare(self.config,self.envelope(contract.PREPARE,authorization_id=self.identifier,
                    scope=bad,operator='fixture',reason='test'))
        for side in ('target','control'):
            for field, value in (('hostname','other'),('database',str(self.config.target.parent/'other.db')),
                                 ('inode',999),('device',57)):
                original = self.identity
                def observed(path):
                    result = original(path)
                    expected = str(self.config.target if side == 'target' else self.config.control)
                    return replace(result,**{field:value}) if result.database == expected else result
                with self.subTest(side=side,field=field), patch.object(a,'target_identity',side_effect=observed), self.assertRaises(ValueError):
                    successor.describe(self.config)
        self.assertEqual(before,self.snapshot())

    def test_expiry_worker_disagreement_and_pending_preparation(self):
        envelope = self.prepare()
        with patch.object(runtime,'_utc_now',return_value=(utc(runtime._utc_now())+timedelta(seconds=601)).strftime('%Y-%m-%dT%H:%M:%SZ')):
            with self.assertRaises(ValueError):successor.plan(self.config,self.envelope(contract.INSPECT,authorization_id=self.identifier),{}, {})
        scope = successor.describe(self.config)['scope']
        with self.assertRaisesRegex(ValueError,'pending_preparation'):
            successor.prepare(self.config,self.envelope(contract.PREPARE,authorization_id=str(uuid4()),scope=scope,operator='fixture',reason='test'))
        plan = self.plan()
        review = deepcopy(plan['review']);record = deepcopy(review['observations'][0])
        record['observation']['target_device'] = '50';record['observation_sha256'] = digest(record['observation'])
        review['observations'].append(record)
        with self.assertRaises(ValueError):
            successor.plan(self.config,self.envelope(contract.INSPECT,authorization_id=self.identifier),review,self.paths)

    def test_wrong_purpose_holder_and_console_rejected(self):
        envelope = self.envelope(contract.INSPECT,authorization_id=self.identifier)
        from flask import request
        with patch.dict(request.environ,{'wsgi.version':(2,0)}), self.assertRaisesRegex(ValueError,'wsgi_required'):
            successor.inspect(self.config,envelope)
        body = load(envelope['serialized_approval'])
        body['holder'] = dict(actor_id=1,primary_sha256='0'*64,session_sha256='0'*64)
        with self.assertRaises(ValueError):contract.validate_envelope(body,self.root)

    def test_failure_at_each_mutation_rolls_back(self):
        self.prepare();plan=self.plan();envelope=self.envelope(contract.COMPLETE,plan=plan)
        before=self.snapshot()
        for stage in ('profile','binding','invalidation','audit','validation'):
            original=successor._insert
            def insert(control,table,value):
                if table == (successor.profiles.PROFILES if stage == 'profile' else 'recognition_admin_bindings'):
                    raise RuntimeError('synthetic interrupted insert')
                return original(control,table,value)
            from src.review.recognition import approvals
            selected = (patch.object(successor,'_insert',side_effect=insert) if stage in ('profile','binding') else
                        patch.object(approvals,'_invalidate_all',side_effect=RuntimeError('synthetic')) if stage == 'invalidation' else
                        patch.object(a,'_audit',side_effect=RuntimeError('synthetic')) if stage == 'audit' else
                        patch.object(runtime,'_identity_snapshot',side_effect=RuntimeError('synthetic')))
            with self.subTest(stage=stage), selected, self.assertRaises(RuntimeError):
                successor.complete(self.config,envelope,self.prepared['nonce'])
            self.assertEqual(before,self.snapshot())

    def test_real_process_crash_before_commit_and_lost_response_after_commit(self):
        self.prepare();plan=self.plan();envelope=self.envelope(contract.COMPLETE,plan=plan)
        before=self.snapshot()
        program = '''
import sys,os,json
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
from flask import Flask
from src.review.recognition import administration as a,authorization,runtime_validation as runtime
from src.review.recognition import runtime_profile_successor as successor,runtime_profile_successor_contract as contract
p=json.load(sys.stdin)
config=a.LocalAdministration(*(Path(p[k]) for k in ('target','control','key')))
original=authorization.target_identity
commit=successor._commit
def interrupted(control):
    if p['phase']=='after':commit(control)
    os._exit(71 if p['phase']=='before' else 72)
with patch.object(contract,'SOURCE',p['source']),patch.object(contract,'SOURCE_BINDING',p['binding']),patch.object(contract,'SOURCE_PROFILE',p['profile']),patch.object(runtime,'_utc_now',return_value=p['now']),patch.object(a,'target_identity',side_effect=lambda value:replace(original(value),hostname='synthetic-web',device=49)),patch.object(successor,'_commit',side_effect=interrupted),Flask(__name__).test_request_context('/maintenance'):
    successor.complete(config,p['envelope'],p['nonce'])
'''
        data=dict(target=str(self.config.target),control=str(self.config.control),key=str(self.config.key_file),
                  source=contract.SOURCE,binding=contract.SOURCE_BINDING,profile=contract.SOURCE_PROFILE,
                  now=runtime._utc_now(),envelope=envelope,nonce=self.prepared['nonce'])
        for phase,code in (('before',71),('after',72)):
            result=subprocess.run([sys.executable,'-B','-c',program],input=canonical(dict(data,phase=phase)),
                                  capture_output=True,text=True,timeout=45)
            self.assertEqual(code,result.returncode,'child did not reach expected commit boundary')
            # Ordinary SQLite read/write reopen performs hot-journal recovery.
            with a.connect(self.config.control,write=True) as control:
                control.execute('SELECT count(*) FROM recognition_admin_bindings').fetchone()
            if phase=='before':self.assertEqual(before,self.snapshot())
        self.assertEqual('COMMITTED',successor.inspect(self.config,self.envelope(contract.INSPECT,authorization_id=self.identifier))['state'])

    def test_g6_qualification_foundation_readiness_and_normal_activation(self):
        # This fixture freezes UTC for independent TOTP vectors. Pair its clock
        # with deterministic monotonic samples; do not relax production clocks.
        import itertools
        self.enterContext(patch('src.review.recognition.runtime_execution_claims.time.monotonic_ns',
                                side_effect=itertools.count(1_000_000_000,1000).__next__))
        self.prepare();plan=self.plan()
        successor.complete(self.config,self.envelope(contract.COMPLETE,plan=plan),self.prepared['nonce'])
        from src.review.recognition import runtime_activation as owner, deployment_qualification as qualification
        from src.review.recognition import runtime_target_schema_completion as completion
        from tests import test_recognition_administration as base
        self.f.f.clock.return_value=base.at(240)
        self.f.primary=owner.record_primary_authentication(self.config,actor_id=1,reviewer_key='owner-key')
        self.f.session=owner.open_admin_session(self.config,self.f.primary,base.independent_code(runtime._utc_now()))
        backups(self,self.config)
        preview=self.f.preview();self.assertEqual(6,preview['plan']['generation'])
        signed=self.f.approval(preview['plan'])
        if self.f.missing_runtime_prerequisites:
            from src.review.recognition import runtime_target_schema_lineage as lineage
            self.assertEqual(lineage.RUNTIME_PACKAGE,preview['plan']['package'])
            body=load(signed[0])
            body['approvals']=[asdict(authorization.Authorization(
                target=authorization.Target(**body['target']),environment='production',expires_at_utc=body['expires_at_utc'],
                reference=body['mandate'],**authorization.migration_binding(lineage.RUNTIME_PACKAGE,
                    lineage.package_definitions(lineage.RUNTIME_PACKAGE))))]
            encoded=canonical(body)
            signed=(encoded,base64.b64encode(self.f.key.sign(governance.DOMAIN+encoded.encode())).decode())
        from pathlib import Path
        spec=importlib.util.spec_from_file_location('g6_foundation_signer',
            Path(__file__).resolve().parents[1]/'scripts/operator/recognition_governance.py')
        signer=importlib.util.module_from_spec(spec);spec.loader.exec_module(signer)
        payload=self.config.target.parent/'synthetic-g6-foundation-approval.json'
        payload.write_text(signed[0],encoding='utf-8')
        with patch.object(signer,'_fresh'):
            self.assertEqual(6,signer._payload(payload,self.root)['subject']['plan']['generation'])
        result=self.f.apply(signed)
        self.assertEqual((6,'COMPLETED',False),(result['generation'],result['state'],result['execution_authority']))
        status=completion.inspect(self.config)
        self.assertEqual('COMPLETED',status['state'])
        assessment=owner.assess(self.config,self.f.session,primary_token=self.f.primary)
        self.assertTrue(assessment['activation_ready'])
        with self.assertRaises(ValueError):
            owner.change_state(self.config,self.f.session,'missing',primary_token=self.f.primary,state='ACTIVATED',reason='test')
        self.f.f.clock.return_value=base.at(270)
        step=owner.create_step_up(self.config,self.f.session,base.independent_code(runtime._utc_now()),
            primary_token=self.f.primary,action='activate',installation_id=self.root['installation_id'],generation=6)
        confirmation=owner.begin_confirmation(self.config,self.f.session,step,primary_token=self.f.primary)
        with patch.object(qualification,'qualify_locking'):
            activated=owner.change_state(self.config,self.f.session,step,primary_token=self.f.primary,state='ACTIVATED',
                                        reason='synthetic activation only',confirmation_token=confirmation['confirmation_token'])
        self.assertEqual('ACTIVATED',activated['state'])
        from src.review.recognition import writer_boundary
        with self.assertRaises(ValueError):writer_boundary.acquire(None,self.config.target,{})
        with a.connect(self.config.control) as control:
            self.assertFalse(control.execute('SELECT 1 FROM recognition_runtime_execution_claims').fetchone())

    def test_g6_v2_missing_prerequisites_foundation(self):
        self.test_g6_qualification_foundation_readiness_and_normal_activation()

    def test_http_requires_signature_not_browser_session_and_never_grants_login(self):
        from src.review.recognition import admin_routes
        app=Flask(__name__);app.secret_key='synthetic-route-test'
        admin_routes.register_admin_routes(app)
        path='/api/admin/recognition-control/runtime-profile-successor/'
        with patch.object(admin_routes,'configuration',return_value=self.config), app.test_client() as client:
            response=client.post(path+'describe',json={})
            self.assertEqual(400,response.status_code)
            signed=self.envelope(contract.INSPECT,authorization_id=self.identifier)
            bad=dict(signed,signature=base64.b64encode(b'X'*64).decode())
            self.assertEqual(403,client.post(path+'describe',json=dict(authorization=bad)).status_code)
            before=self.snapshot()
            response=client.post(path+'describe',json=dict(authorization=signed))
            self.assertEqual(200,response.status_code)
            self.assertTrue(response.get_json()['read_only'])
            self.assertEqual(before,self.snapshot())
            self.assertEqual('no-store',response.headers['Cache-Control'])
            with client.session_transaction() as session:self.assertEqual({},dict(session))
        with self.assertRaises(ValueError):governance._verify(self.config,**dict(
            serialized=signed['serialized_approval'],signature=signed['signature']))

    def test_offline_signer_accepts_closed_custodian_payload_only(self):
        from pathlib import Path
        script=Path(__file__).resolve().parents[1]/'scripts/operator/recognition_governance.py'
        spec=importlib.util.spec_from_file_location('successor_operator_fixture',script)
        operator=importlib.util.module_from_spec(spec);spec.loader.exec_module(operator)
        envelope=self.envelope(contract.INSPECT,authorization_id=self.identifier)
        payload=self.config.target.parent/'synthetic-public-payload.json'
        payload.write_text(envelope['serialized_approval'],encoding='utf-8')
        with patch.object(operator,'_fresh'):
            self.assertEqual(load(envelope['serialized_approval']),operator._payload(payload,self.root))
            body=load(envelope['serialized_approval']);body['subject']['kind']='arbitrary'
            payload.write_text(canonical(body),encoding='utf-8')
            with self.assertRaises(ValueError):operator._payload(payload,self.root)

    def test_restricted_owner_forbids_ddl_and_target_writes(self):
        import sqlite3
        before=self.snapshot()
        with successor._reserved(self.config,write=True) as (control,target):
            for db,sql in ((control,'CREATE TABLE forbidden(x)'),(control,'DELETE FROM recognition_admin_mfa'),
                           (control,'PRAGMA journal_mode=WAL'),(target,'UPDATE preserved_data SET number=2')):
                with self.subTest(sql=sql),self.assertRaises(sqlite3.DatabaseError):db.execute(sql)
        self.assertEqual(before,self.snapshot())

    def test_concurrent_consumption_has_one_winner(self):
        self.prepare();plan=self.plan();envelope=self.envelope(contract.COMPLETE,plan=plan)
        def consume():
            with self.app.test_request_context('/maintenance'):
                try:return successor.complete(self.config,envelope,self.prepared['nonce'])['state']
                except ValueError:return 'REJECTED'
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:consume(),range(2)))
        self.assertEqual(['COMMITTED','REJECTED'],sorted(results))

    def test_tampered_history_fails_closed_and_inspection_is_inconsistent(self):
        self.prepare();plan=self.plan()
        successor.complete(self.config,self.envelope(contract.COMPLETE,plan=plan),self.prepared['nonce'])
        with a.connect(self.config.control,write=True) as control:
            control.execute('DROP TRIGGER recognition_admin_audit_immutable_update')
            row=control.execute('SELECT sequence,body_json FROM recognition_admin_audit ORDER BY sequence DESC LIMIT 1').fetchone()
            body=load(row['body_json']);body['subject']['plan_sha256']='0'*64
            control.execute('UPDATE recognition_admin_audit SET body_json=?,body_sha256=? WHERE sequence=?',
                            (canonical(body),digest(body),row['sequence']))
            control.execute(a.schema.definitions()['recognition_admin_audit_immutable_update'])
            control.commit()
        with self.assertRaises(ValueError):runtime.validate_runtime_snapshot(self.config)
        self.assertEqual('INCONSISTENT',successor.inspect(self.config,self.envelope(contract.INSPECT,authorization_id=self.identifier))['state'])

    def test_g6_cannot_hide_tampered_predecessor_binding(self):
        self.prepare();plan=self.plan()
        successor.complete(self.config,self.envelope(contract.COMPLETE,plan=plan),self.prepared['nonce'])
        with a.connect(self.config.control,write=True) as control:
            control.execute('DROP TRIGGER recognition_admin_bindings_immutable_update')
            row=control.execute('SELECT body_json FROM recognition_admin_bindings WHERE generation=3').fetchone()
            body=load(row[0]);body['owner_id']=2
            control.execute('UPDATE recognition_admin_bindings SET body_json=?,body_sha256=? WHERE generation=3',
                            (canonical(body),digest(body)))
            control.execute(a.schema.definitions()['recognition_admin_bindings_immutable_update'])
            control.commit()
        with self.assertRaises(ValueError):runtime.validate_runtime_snapshot(self.config)
        self.assertEqual('INCONSISTENT',successor.inspect(self.config,self.envelope(contract.INSPECT,authorization_id=self.identifier))['state'])

    def _assert_inconsistent_commit_evidence(self, mutation):
        self.prepare();plan=self.plan()
        successor.complete(self.config,self.envelope(contract.COMPLETE,plan=plan),self.prepared['nonce'])
        with a.connect(self.config.control,write=True) as control:
            row=control.execute('SELECT * FROM recognition_admin_audit ORDER BY sequence DESC LIMIT 1').fetchone()
            body=load(row['body_json'])
            if mutation == 'duplicate':
                a._audit(control,successor.COMMITTED,body['actor'],body['at_utc'],body['subject'])
            else:
                if mutation == 'missing':del body['action']
                elif mutation == 'rename':body['action']='unexpected_successor_action'
                elif mutation == 'identifier':body['subject']['authorization_id']=str(uuid4())
                control.execute('DROP TRIGGER recognition_admin_audit_immutable_update')
                control.execute('UPDATE recognition_admin_audit SET body_json=?,body_sha256=? WHERE sequence=?',
                                (canonical(body),digest(body),row['sequence']))
                control.execute(a.schema.definitions()['recognition_admin_audit_immutable_update'])
            control.commit()
        with self.assertRaises(ValueError):runtime.validate_runtime_snapshot(self.config)
        status=successor.inspect(self.config,self.envelope(contract.INSPECT,authorization_id=self.identifier))
        self.assertEqual('INCONSISTENT',status['state'])
        self.assertFalse(status['execution_authority'])

    def test_inspect_missing_commit_action_is_inconsistent(self):
        self._assert_inconsistent_commit_evidence('missing')

    def test_inspect_renamed_commit_action_with_valid_hash_is_inconsistent(self):
        self._assert_inconsistent_commit_evidence('rename')

    def test_inspect_altered_authorization_id_is_inconsistent(self):
        self._assert_inconsistent_commit_evidence('identifier')

    def test_inspect_duplicate_commit_is_inconsistent(self):
        self._assert_inconsistent_commit_evidence('duplicate')
