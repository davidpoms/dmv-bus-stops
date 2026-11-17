"""Reduced contract: real disposable stores; synthetic operator evidence only."""
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch, Mock
import subprocess
import unittest
from datetime import timedelta
from types import SimpleNamespace
import stat
import importlib.util
import io
from contextlib import redirect_stdout, redirect_stderr

from src.review.recognition import administration as a, local_readiness as ready
from src.review.recognition import deployment_qualification as q, runtime_validation as runtime
from src.review.recognition import runtime_target_schema_completion as completion
from tests import test_recognition_target_schema_completion as fixtures
from tests.recognition_deployment_qualification_fixture import prepare


class PermissionPolicyTests(unittest.TestCase):
    def test_posix_owner_modes_parent_and_links_are_enforced(self):
        info=SimpleNamespace(st_mode=stat.S_IFREG|0o600,st_nlink=1,st_uid=123)
        parent=SimpleNamespace(st_mode=stat.S_IFDIR|0o755)
        path=Mock();path.lstat.return_value=info;path.is_symlink.return_value=False
        path.parent.stat.return_value=parent
        config=SimpleNamespace(target=path,control=path,key_file=path)
        with patch.object(q.os,'name','posix'),patch.object(q.os,'geteuid',return_value=123,create=True):
            q.permissions(config)
            for field,value in (('st_mode',stat.S_IFREG|0o644),('st_uid',124),('st_nlink',2)):
                previous=getattr(info,field);setattr(info,field,value)
                with self.assertRaisesRegex(a.AdminError,'deployment_unsafe_permissions'):q.permissions(config)
                setattr(info,field,previous)
            parent.st_mode=stat.S_IFDIR|0o777
            with self.assertRaisesRegex(a.AdminError,'deployment_unsafe_permissions'):q.permissions(config)


class DeploymentQualificationTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.TargetSchemaCompletionTests()
        self.f.omit_rehearsal = True
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.config = self.f.config

    def qualification(self, **changes):
        with a.connect(self.config.control) as control, a.connect(self.config.target) as target:
            binding, _, _ = runtime._history(control)
            return q.assess(self.config,control,binding,runtime._utc_now(),target=target,**changes)

    def test_absent_rehearsal_preview_completion_readiness_but_no_activation(self):
        before = self.f.dump(self.config.control), self.f.dump(self.config.target), self.f.protected()
        preview = self.f.preview()
        self.assertEqual(['deployment_rehearsal_absent_or_expired'],preview['operational_assurance_warnings'])
        self.assertEqual(before,(self.f.dump(self.config.control),self.f.dump(self.config.target),self.f.protected()))
        self.f.apply(self.f.approval(preview['plan']))
        from src.review.recognition import runtime_activation as owner
        result = owner.assess(self.config,self.f.session,primary_token=self.f.primary)
        self.assertTrue(result['safety_ready']); self.assertTrue(result['activation_ready'])
        self.assertFalse(result['rehearsal_evidence_present']); self.assertFalse(result['deployment_verified'])
        self.assertEqual('NOT_ACTIVATED', result['activation_state'])
        self.assertEqual('BLOCKED',result['production_execution'])
        self.assertEqual(before[2],self.f.protected())

    def test_missing_qualification_preview_allowed_completion_blocked(self):
        with patch.object(q,'assess',return_value=dict(ready=False,issues=['deployment_qualification_missing'],qualification_sha256=None)):
            plan = self.f.preview()['plan']
            with self.assertRaisesRegex(ValueError,'foundation_deployment_qualification_required'):
                self.f.apply(self.f.approval(plan))

    def test_missing_or_modified_backup_blocks(self):
        with a.connect(self.config.control) as control:
            from src.review.recognition.trust import load
            value = load(control.execute("SELECT body_json FROM recognition_admin_audit WHERE json_extract(body_json,'$.action')=?",(q.ACTION,)).fetchone()[0])['subject']
        backup = Path(value['backups']['target']['path'])
        backup.write_bytes(backup.read_bytes()+b'tampered')
        self.assertFalse(self.qualification()['ready'])
        plan = self.f.preview()['plan']
        with self.assertRaisesRegex(ValueError,'foundation_deployment_qualification_required'):
            self.f.apply(self.f.approval(plan))

    def test_unsafe_permissions_blocks_safety_and_preview(self):
        with patch.object(q,'permissions',side_effect=a.AdminError('deployment_unsafe_permissions',503)):
            with self.assertRaisesRegex(ValueError,'foundation_other_readiness_prerequisites'):
                self.f.preview()

    def test_unsafe_locking_cannot_be_qualified(self):
        options = prepare(self,self.config,record=False)
        before = self.f.dump(self.config.control)
        with patch.object(q,'qualify_locking',side_effect=a.AdminError('deployment_unsafe_locking',503)):
            with self.assertRaisesRegex(a.AdminError,'deployment_unsafe_locking'):
                q.record(self.config,**options)
        self.assertEqual(before,self.f.dump(self.config.control))

    def test_actual_two_process_locking_on_disposable_files(self):
        before = self.f.dump(self.config.target),self.f.dump(self.config.control)
        q.qualify_locking(self.config)
        self.assertEqual(before,(self.f.dump(self.config.target),self.f.dump(self.config.control)))
        with patch.object(q.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'COMMITTED','')):
            with self.assertRaisesRegex(a.AdminError,'deployment_unsafe_locking'):
                q.qualify_locking(self.config)

    def test_missing_check_or_unverified_backup_rejected_without_audit(self):
        options = prepare(self,self.config,record=False)
        for change in (dict(evidence={}),dict(backups=dict(options['backups'],target=str(self.config.target)))):
            with self.subTest(change=tuple(change)):
                before = self.f.dump(self.config.control)
                with patch.object(q,'qualify_locking'), self.assertRaises(a.AdminError):
                    q.record(self.config,**dict(options,**change))
                self.assertEqual(before,self.f.dump(self.config.control))

    def test_rehearsal_expiry_not_in_safety_plan_or_authority_binding(self):
        report = dict(safety_ready=True,code_ready=True,activation_ready=True,
                      admission_state_sha256='a'*64,rehearsal_evidence_present=True,
                      operational_assurance=dict(status='CURRENT'),deployment_prerequisites=[],
                      deployment_verified=True,deployment_status='DEPLOYMENT_OBSERVATIONS_VERIFIED')
        expired = deepcopy(report)
        expired.update(rehearsal_evidence_present=False,operational_assurance=dict(status='ABSENT_OR_EXPIRED'),
                       deployment_prerequisites=sorted(ready.REHEARSAL_CHECKS),deployment_verified=False,
                       deployment_status='ASSURANCE_ADVISORY')
        self.assertEqual(ready._assessment_binding(report),ready._assessment_binding(expired))
        changed = dict(expired,admission_state_sha256='b'*64)
        self.assertNotEqual(ready._assessment_binding(report),ready._assessment_binding(changed))

    def test_qualification_scope_mismatch_is_not_authority(self):
        with patch.object(q,'_scope',return_value={}):
            self.assertFalse(self.qualification()['ready'])

    def test_failed_qualification_audit_rolls_back(self):
        options=prepare(self,self.config,record=False)
        before=self.f.dump(self.config.control),self.f.dump(self.config.target)
        audit=a._audit
        def failed(*args,**kwargs):
            audit(*args,**kwargs)
            raise RuntimeError('synthetic audit failure')
        with patch.object(q,'qualify_locking'),patch.object(a,'_audit',side_effect=failed):
            with self.assertRaises(RuntimeError):q.record(self.config,**options)
        self.assertEqual(before,(self.f.dump(self.config.control),self.f.dump(self.config.target)))

    def test_backup_changed_during_completion_rolls_back_entire_edge(self):
        from src.review.recognition.trust import load
        plan=self.f.preview()['plan'];approval=self.f.approval(plan)
        with a.connect(self.config.control) as control:
            value=load(control.execute("SELECT body_json FROM recognition_admin_audit WHERE json_extract(body_json,'$.action')=?",(q.ACTION,)).fetchone()[0])['subject']
        before=self.f.dump(self.config.target),self.f.dump(self.config.control),self.f.protected()
        install=completion._install
        def tamper(*args,**kwargs):
            install(*args,**kwargs)
            path=Path(value['backups']['control']['path'])
            path.write_bytes(path.read_bytes()+b'synthetic-tamper')
        with patch.object(completion,'_install',side_effect=tamper):
            with self.assertRaisesRegex(ValueError,'foundation_deployment_qualification_changed'):
                self.f.apply(approval)
        self.assertEqual(before,(self.f.dump(self.config.target),self.f.dump(self.config.control),self.f.protected()))

    def test_expired_actual_rehearsal_does_not_change_substantive_readiness(self):
        from src.review.recognition import production_operations
        from src.review.recognition.rules import digest
        from src.review.recognition.trust import utc
        with a.connect(self.config.control,write=True) as control:
            binding,_,_=runtime._history(control)
            a._audit(control,'local_deployment_rehearsal_recorded','synthetic-test',runtime._utc_now(),
                dict(target=production_operations.local_target(binding),
                     evidence={key:digest(dict(synthetic=key)) for key in ready.REHEARSAL_CHECKS},
                     reason='test-only observations',backup=dict(frequency='daily',retention_days=30,restore_verified=True)))
            control.commit()
        self.f.apply()
        with a.connect(self.config.control) as control,a.connect(self.config.target) as target:
            binding,_,_=runtime._history(control)
            current=runtime._utc_now()
            expired=(utc(current)+timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
            first=ready._assess_inventory(control,target,binding,current,config=self.config)
            second=ready._assess_inventory(control,target,binding,expired,config=self.config)
        self.assertTrue(first['rehearsal_evidence_present'])
        self.assertFalse(second['rehearsal_evidence_present'])
        self.assertTrue(second['safety_ready']); self.assertTrue(second['activation_ready'])
        self.assertEqual(ready._assessment_binding(first),ready._assessment_binding(second))

    def test_qualification_http_uses_existing_owner_mfa_and_csrf(self):
        from flask import Flask
        from src.review.recognition import admin_routes
        app=Flask(__name__);app.config.update(TESTING=True,SECRET_KEY='synthetic-test-key')
        admin_routes.register_admin_routes(app)
        client=app.test_client();guest=app.test_client()
        with client.session_transaction() as browser:
            browser.update(authenticated_reviewer_id=1,reviewer_key='owner-key',auth_csrf='fixture-csrf',
                           recognition_primary=self.f.primary,recognition_admin=self.f.session)
        options=prepare(self,self.config,record=False)
        value=dict(csrf_token='fixture-csrf',generation=5,operator=options['operator'],reason=options['reason'],
                   evidence=options['evidence'],backups=options['backups'])
        path='/api/admin/recognition-control/runtime-activation/qualification'
        before=self.f.dump(self.config.target)
        with patch.object(admin_routes,'configuration',return_value=self.config),patch.object(q,'qualify_locking'):
            self.assertEqual(400,client.post(path,json=dict(value,csrf_token='wrong')).status_code)
            self.assertNotEqual(200,guest.post(path,json=value).status_code)
            self.assertEqual(400,client.post(path,json=dict(value,generation=6)).status_code)
            response=client.post(path,json=value)
            self.assertEqual(200,response.status_code,response.get_json())
            with client.session_transaction() as browser:browser['recognition_admin']='invalid-fixture-token-12345'
            self.assertNotEqual(200,client.post(path,json=value).status_code)
        self.assertEqual(before,self.f.dump(self.config.target))
        self.assertFalse(response.get_json()['execution_authority'])

    def test_existing_administration_cli_records_only_focused_metadata(self):
        from src.api import sqlite_runtime
        from src.review.recognition.rules import canonical
        from src.review.recognition.trust import load
        options=prepare(self,self.config,record=False)
        payload=self.config.target.parent/'synthetic-qualification-input.json'
        payload.write_text(canonical(dict(evidence=options['evidence'],backups=options['backups'])),encoding='utf-8')
        payload.chmod(0o600)
        script=Path(__file__).resolve().parents[1]/'scripts/active/manage_recognition_administration.py'
        spec=importlib.util.spec_from_file_location('qualification_cli_test',script)
        cli=importlib.util.module_from_spec(spec)
        before=self.f.protected(),self.f.dump(self.config.target)
        output,errors=io.StringIO(),io.StringIO()
        with patch.object(sqlite_runtime,'load_production_sqlite') as loader:
            spec.loader.exec_module(cli)
        loader.assert_called_once_with()
        with patch.object(q,'qualify_locking'),redirect_stdout(output),redirect_stderr(errors):
            cli.main(['record-deployment-qualification','--target',str(self.config.target),
                '--control',str(self.config.control),'--key-file',str(self.config.key_file),
                '--expected-generation','5','--operator',options['operator'],'--reason',options['reason'],
                '--evidence-file',str(payload)])
        self.assertEqual(dict(state='RECORDED',generation=5,evidence_checks=4,execution_authority=False),load(output.getvalue()))
        self.assertEqual(before,(self.f.protected(),self.f.dump(self.config.target)))
        self.assertEqual('',errors.getvalue())
        for secret in (self.f.primary,self.f.session,self.config.key_file.read_text().strip()):
            self.assertNotIn(secret,output.getvalue())
