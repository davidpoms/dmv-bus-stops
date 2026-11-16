"""Synthetic generation-5 bootstrap with real enrollment, credentials and signatures."""

import base64
from copy import deepcopy
from dataclasses import asdict, replace
from pathlib import Path
import sqlite3
import subprocess
import sys
import queue
import threading
import time
from uuid import uuid4
from datetime import timedelta
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from src.review.recognition import administration as a, authorization, approval_schema, production_operations
from src.review.recognition import event_schema, operation_schema, execution as journal, local_readiness as readiness
from src.review.recognition import runtime_validation as runtime, runtime_activation as owner
from src.review.recognition import runtime_execution_claim_schema as claims, runtime_production_governance as governance
from src.review.recognition import runtime_target_schema_completion as completion, runtime_target_schema_lineage as lineage
from src.review.recognition.rules import canonical, digest
from src.review.recognition.trust import load
from tests import test_recognition_deployment_claim_recovery as source_fixture
from tests import test_recognition_administration as base


class TargetSchemaCompletionTests(unittest.TestCase):
    def setUp(self):
        self.f = source_fixture.DeploymentClaimRecoveryTests()
        install = a.install
        def incomplete_target(config, **options):
            with a.connect(config.target,write=True) as target:
                target.execute('PRAGMA foreign_keys=OFF')
                target.execute('BEGIN IMMEDIATE')
                # Use the fixed definitions to complete all OTHER prerequisites
                # before initial binding. Remove the fixture's old event graph.
                from src.review.recognition import permanent_schema, execution_schema
                for name, sql in {**permanent_schema.definitions(),**execution_schema.definitions()}.items():
                    if not target.execute('SELECT 1 FROM sqlite_master WHERE name=?',(name,)).fetchone():
                        target.execute(sql)
                for module in (operation_schema,event_schema):
                    for name, in target.execute("SELECT name FROM sqlite_master WHERE type='trigger'").fetchall():
                        if name in module.definitions():target.execute('DROP TRIGGER '+name)
                for name in ('recognition_operation_executions','recognition_operation_decisions',
                             'recognition_operation_contracts','recognition_event_history','recognition_frozen_events','recognition_preparations'):
                    target.execute('DELETE FROM '+name)
                for name, sql in operation_schema.definitions().items():
                    if sql.startswith('CREATE TRIGGER '):target.execute(sql)
                for name in event_schema.TABLES:target.execute('DROP TABLE '+name)
                if getattr(self, 'missing_runtime_prerequisites', False):
                    for module in (execution_schema, operation_schema):
                        for name, sql in module.definitions().items():
                            if sql.startswith('CREATE TRIGGER '):
                                target.execute('DROP TRIGGER '+name)
                        for name in module.TABLES:
                            target.execute('DROP TABLE '+name)
                    variant = getattr(self, 'runtime_source_variant', None)
                    if variant == 'partial':
                        target.execute(operation_schema.definitions()['recognition_operation_contracts'])
                    elif variant == 'mismatched':
                        target.execute('CREATE TABLE recognition_execution_storage(unapproved TEXT)')
                    elif variant == 'existing':
                        target.execute(execution_schema.definitions()['recognition_execution_storage'])
                    elif variant == 'missing_private':
                        trigger = next(name for name, sql in permanent_schema.definitions().items() if sql.startswith('CREATE TRIGGER '))
                        target.execute('DROP TRIGGER '+trigger)
                if self._testMethodName == 'test_other_missing_schema_already_absent_at_enrollment_rejects':
                    trigger = next(name for name,sql in operation_schema.definitions().items() if sql.startswith('CREATE TRIGGER '))
                    target.execute('DROP TRIGGER '+trigger)
                target.execute('CREATE TABLE preserved_data(id INTEGER PRIMARY KEY, payload BLOB, number REAL)')
                target.execute('INSERT INTO preserved_data VALUES(1,?,?)',(b'\x00\xff',1.25))
                target.commit()
            return install(config,**options)
        with patch.object(a,'install',side_effect=incomplete_target):self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.config=self.f.config
        self.enterContext(patch.object(a,'target_identity',side_effect=authorization.target_identity))
        with a.connect(self.config.control,write=True) as control:
            control.execute('BEGIN IMMEDIATE')
            approval_schema.install(control)
            for sql in readiness.definitions().values():control.execute(sql)
            binding,_,_=runtime._history(control)
            readiness._append(control,binding,'NOT_ACTIVATED',1,'synthetic genesis',runtime._utc_now())
            body=dict(sequence=1,active=False,reason='synthetic stop',actor=1,recorded_at_utc=runtime._utc_now(),previous_sha256=None)
            from src.review.recognition import events
            events._insert(control,'recognition_execution_stops','sequence',(1,),body)
            a._audit(control,'local_deployment_rehearsal_recorded','fixture',runtime._utc_now(),
                dict(target=production_operations.local_target(binding),evidence={key:digest(key) for key in readiness.REHEARSAL_CHECKS},
                     reason='synthetic observations',backup=dict(frequency='daily',retention_days=30,restore_verified=True)))
            control.commit()
        claims.migrate(self.config,expected_generation=5,operator='fixture',reason='test')
        self.primary=owner.record_primary_authentication(self.config,actor_id=1,reviewer_key='owner-key')
        self.session=owner.open_admin_session(self.config,self.primary,base.independent_code(runtime._utc_now()))
        self.key=Ed25519PrivateKey.generate() # Synthetic signing only; production never generates keys.
        public=base64.b64encode(self.key.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)).decode()
        root=dict(format=governance.FORMAT,mandate=governance.contract.MANDATE,installation_id=binding['installation_id'],owner_id=1,public_key=public)
        governance.trust_path(self.config).write_text(canonical(root),encoding='utf-8')
        governance.trust_path(self.config).chmod(0o600)

    def preview(self):
        return completion.preview(self.config,self.session,primary_token=self.primary,operator='fixture-owner',reason='explicit fixture completion')

    def approval(self,plan=None,**changes):
        plan=self.preview()['plan'] if plan is None else plan
        grant=authorization.Authorization(target=authorization.Target(**plan['physical']['target']),environment='production',
            expires_at_utc=base.at(300),reference=governance.contract.MANDATE,
            **authorization.migration_binding(lineage.PACKAGE,event_schema.definitions()))
        body=dict(format=governance.FORMAT,mandate=governance.contract.MANDATE,installation_id=plan['installation_id'],
            binding_sha256=plan['binding_sha256'],holder=dict(actor_id=1,primary_sha256=a.token_hash(self.primary),session_sha256=a.token_hash(self.session)),
            subject=dict(kind=lineage.KIND,plan=plan),target=plan['physical']['target'],control=plan['physical']['control'],
            issued_at_utc=runtime._utc_now(),expires_at_utc=base.at(300),approvals=[asdict(grant)])
        body.update(changes)
        encoded=canonical(body)
        return encoded,base64.b64encode(self.key.sign(governance.DOMAIN+encoded.encode())).decode()

    def apply(self,approval=None):
        encoded,signature=self.approval() if approval is None else approval
        return completion.complete(self.config,self.session,primary_token=self.primary,serialized_approval=encoded,signature=signature)

    def protected(self):
        with a.connect(self.config.control) as control:
            tables=[row[0] for row in control.execute("SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name NOT LIKE 'sqlite_%' AND name!='recognition_admin_audit' ORDER BY name")]
            return {name:[tuple(row) for row in control.execute('SELECT * FROM "'+name.replace('"','""')+'"')]
                    for name in tables}

    def dump(self,path):
        with a.connect(path) as connection:return '\n'.join(connection.iterdump())

    def test_preview_deterministic_readonly_and_successful_same_generation_completion(self):
        before=self.protected(),self.dump(self.config.target),self.dump(self.config.control)
        first,second=self.preview(),self.preview()
        self.assertEqual(first,second)
        self.assertEqual(before,(self.protected(),self.dump(self.config.target),self.dump(self.config.control)))
        plan=first['plan'];self.assertNotEqual(plan['h0'],plan['h1'])
        target_data=completion._data
        with a.connect(self.config.target) as target:data=target_data(target)
        result=self.apply(self.approval(plan))
        self.assertEqual(5,result['generation']);self.assertFalse(result['execution_authority'])
        self.assertEqual(before[0],self.protected())
        with a.connect(self.config.control) as control,a.connect(self.config.target) as target:
            self.assertEqual(data,target_data(target))
            self.assertEqual(plan['h1'],a.observe_target(target)['schema_sha256'])
            binding,profile,_=runtime._history(control)
            self.assertEqual(plan['h0'],binding['target']['schema_sha256'])
            self.assertEqual(plan['h0'],profile['target_schema_sha256'])
            runtime._identity_snapshot(self.config,control,target,runtime._utc_now())
        ready=owner.assess(self.config,self.session,primary_token=self.primary)
        self.assertTrue(ready['activation_ready'],ready)
        self.assertEqual('NOT_ACTIVATED',ready['activation_state'])
        self.assertEqual('BLOCKED',ready['production_execution'])
        self.assertEqual('COMPLETED',completion.inspect(self.config)['state'])

    def test_wrong_plan_fields_rejected_even_with_valid_signature(self):
        plan=self.preview()['plan']
        cases=dict(installation_id='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',target_id='bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
                   generation=6,profile_sha256='a'*64,binding_sha256='b'*64,h0='c'*64,h1='d'*64,
                   package='arbitrary-schema',definitions_sha256='e'*64,auth_epoch=99,mfa_epoch=99,
                   target_data_sha256='f'*64,readiness_sha256='a'*64,source_audit_sha256='b'*64)
        before=self.dump(self.config.target),self.dump(self.config.control)
        for field,value in cases.items():
            with self.subTest(field=field):
                changed=deepcopy(plan);changed[field]=value
                with self.assertRaises((ValueError,a.AdminError)):
                    self.apply(self.approval(changed))
        self.assertEqual(before,(self.dump(self.config.target),self.dump(self.config.control)))

    def test_unsigned_modified_expired_wrong_holder_and_purpose_approval_rejected(self):
        encoded,signature=self.approval()
        changed=load(encoded);changed['subject']['plan']['reason']='modified after signature'
        with self.assertRaises(ValueError):self.apply((canonical(changed),signature))
        with self.assertRaises(ValueError):self.apply((encoded,'A'*88))
        for changes in (dict(holder=dict(actor_id=1,primary_sha256='a'*64,session_sha256='b'*64)),
                        dict(subject=dict(kind='journal_install')),dict(expires_at_utc=base.at(182))):
            with self.subTest(changes=changes),self.assertRaises(ValueError):self.apply(self.approval(**changes))
        self.f.clock.return_value=base.at(301)
        with self.assertRaises(ValueError):self.apply((encoded,signature))

    def test_approval_cannot_be_repurposed_or_provision_general_authority(self):
        encoded,signature=self.approval()
        wrong=load(encoded)['approvals'];wrong[0]['operation_sha256']='a'*64
        with self.assertRaises(ValueError):self.apply(self.approval(approvals=wrong))
        with self.assertRaisesRegex(ValueError,'foundation_original_maintenance_owner_required'):
            governance.provision(self.config,self.session,primary_token=self.primary,serialized=encoded,signature=signature)

    def test_rehashed_completion_audit_does_not_replace_signature_verification(self):
        self.apply()
        with a.connect(self.config.control,write=True) as control:
            # Deliberately model offline modification with a coherent audit hash.
            guards={name:sql for name,sql in a.schema.definitions().items()
                    if sql.startswith('CREATE TRIGGER ') and 'BEFORE UPDATE ON recognition_admin_audit' in sql}
            self.assertTrue(guards)
            for name in guards:control.execute('DROP TRIGGER '+name)
            row=control.execute('SELECT * FROM recognition_admin_audit ORDER BY sequence DESC LIMIT 1').fetchone()
            body=load(row['body_json']);body['subject']['signature']='A'*88
            control.execute('UPDATE recognition_admin_audit SET body_json=?,body_sha256=? WHERE sequence=?',
                            (canonical(body),digest(body),row['sequence']))
            for sql in guards.values():control.execute(sql)
            control.commit()
        with self.assertRaises(ValueError):completion.inspect(self.config)

    def test_physical_identity_fields_not_tolerated(self):
        grant=self.approval()
        for field,value in (('hostname','other-runtime'),('device',999),('inode',999),('database',str(self.config.target.parent/'other.db'))):
            def changed(subject):return replace(authorization.target_identity(subject),**{field:value})
            with self.subTest(field=field),patch.object(a,'target_identity',side_effect=changed),self.assertRaises(ValueError):
                self.apply(grant)

    def test_delete_mode_is_required_without_silent_mode_change(self):
        for path in (self.config.control,self.config.target):
            with self.subTest(path=path):
                with a.connect(path,write=True) as connection:
                    self.assertEqual('wal',connection.execute('PRAGMA journal_mode=WAL').fetchone()[0])
                with self.assertRaisesRegex(ValueError,'foundation_delete_journal_required'):self.preview()
                with a.connect(path,write=True) as connection:
                    self.assertEqual('wal',connection.execute('PRAGMA journal_mode').fetchone()[0])
                    connection.execute('PRAGMA journal_mode=DELETE')

    def test_partial_event_package_and_other_readiness_schema_missing_reject(self):
        with a.connect(self.config.target,write=True) as target:
            target.execute(event_schema.definitions()['recognition_preparations'])
            target.commit()
        with self.assertRaises(ValueError):self.preview()

    def test_other_non_schema_readiness_prerequisites_are_mandatory(self):
        with a.connect(self.config.control,write=True) as control:
            body=journal._stop(control)
            changed=dict(body,sequence=2,active=True,previous_sha256=digest(body))
            from src.review.recognition.events import _insert
            _insert(control,'recognition_execution_stops','sequence',(2,),changed)
            control.commit()
        with self.assertRaisesRegex(ValueError,'foundation_other_readiness_prerequisites'):self.preview()

    def test_other_missing_schema_already_absent_at_enrollment_rejects(self):
        # H0 genuinely includes this incomplete schema: this is not schema drift.
        with a.connect(self.config.control) as control,a.connect(self.config.target) as target:
            runtime._identity_snapshot(self.config,control,target,runtime._utc_now())
        before=self.dump(self.config.target),self.dump(self.config.control)
        with self.assertRaises(ValueError):self.preview()
        self.assertEqual(before,(self.dump(self.config.target),self.dump(self.config.control)))

    def test_stale_plan_rejected_after_audit_change(self):
        grant=self.approval()
        with a.connect(self.config.control,write=True) as control:
            a._audit(control,'unrelated_operator_event',1,runtime._utc_now(),dict(reason='test'))
            control.commit()
        with self.assertRaisesRegex(ValueError,'foundation_plan_changed'):self.apply(grant)

    def test_rollback_on_ddl_validation_audit_and_commit_failure(self):
        grant=self.approval()
        before=self.dump(self.config.target),self.dump(self.config.control)
        def partial(db):
            name='recognition_preparations'
            db.execute(event_schema.definitions()[name].replace('CREATE TABLE '+name,'CREATE TABLE '+completion.ALIAS+'.'+name,1))
            raise RuntimeError('injected partial DDL')
        for module,name,effect in ((completion,'_install',partial),(completion,'_validate_after',RuntimeError('validation')),
                                   (a,'_audit',RuntimeError('audit')),(completion,'_commit',RuntimeError('commit'))):
            with self.subTest(name=name),patch.object(module,name,side_effect=effect),self.assertRaises(RuntimeError):
                self.apply(grant)
            self.assertEqual(before,(self.dump(self.config.target),self.dump(self.config.control)))
        with patch.object(completion,'_commit',return_value=None),self.assertRaisesRegex(ValueError,'foundation_commit_unconfirmed'):
            self.apply(grant)
        self.assertEqual(before,(self.dump(self.config.target),self.dump(self.config.control)))
        self.assertEqual('COMPLETED',self.apply(grant)['state'])

    def test_one_time_consumption_and_expired_approval_is_valid_history(self):
        grant=self.approval();self.apply(grant)
        with self.assertRaisesRegex(ValueError,'foundation_already_completed'):self.apply(grant)
        self.f.clock.return_value=base.at(10000)
        with a.connect(self.config.control) as control,a.connect(self.config.target) as target:
            binding,profile,_=runtime._history(control)
            self.assertEqual(lineage.verify(control)['h1'],a.observe_target(target)['schema_sha256'])
            runtime._identity_snapshot(self.config,control,target,runtime._utc_now())

    def test_missing_altered_extra_schema_and_original_h0_after_completion_reject(self):
        plan=self.preview()['plan'];self.apply(self.approval(plan))
        with a.connect(self.config.target,write=True) as target:
            target.execute('CREATE TABLE unauthorized(value TEXT)');target.commit()
        with self.assertRaises(ValueError):
            owner.inspect(self.config,self.session,primary_token=self.primary)
        with a.connect(self.config.target,write=True) as target:
            target.execute('DROP TABLE unauthorized')
            target.execute('DROP TRIGGER recognition_preparations_immutable_update');target.commit()
        with self.assertRaises(ValueError):owner.inspect(self.config,self.session,primary_token=self.primary)
        with a.connect(self.config.target,write=True) as target:
            target.execute('PRAGMA foreign_keys=OFF')
            for name,sql in event_schema.definitions().items():
                if sql.startswith('CREATE TRIGGER ') and target.execute('SELECT 1 FROM sqlite_master WHERE name=?',(name,)).fetchone():
                    target.execute('DROP TRIGGER '+name)
            for name in event_schema.TABLES:target.execute('DROP TABLE '+name)
            target.commit()
        with a.connect(self.config.target) as target:self.assertEqual(plan['h0'],a.observe_target(target)['schema_sha256'])
        with self.assertRaises(ValueError):owner.inspect(self.config,self.session,primary_token=self.primary)

    def test_ordinary_connections_still_reject_attachments(self):
        with a.connect(self.config.control) as control:
            control.execute('ATTACH DATABASE ? AS other',(str(self.config.target),))
            with self.assertRaisesRegex(ValueError,'isolated_admin_control_required'):runtime._history(control)

    def test_restricted_owner_rejects_nonpackage_dml_and_attach(self):
        with completion._attached(self.config) as db:
            db.set_authorizer(completion._authorizer)
            for sql in ('UPDATE completion_target.community_reviewers SET role=role',
                        'DELETE FROM recognition_admin_mfa','CREATE TABLE completion_target.unapproved(x)',
                        "ATTACH DATABASE ':memory:' AS arbitrary"):
                with self.subTest(sql=sql),self.assertRaises(sqlite3.DatabaseError):db.execute(sql)

    def test_protected_root_and_explicit_owner_are_required(self):
        grant=self.approval()
        with self.assertRaises(ValueError):
            completion.complete(self.config,'not-a-session',primary_token=self.primary,serialized_approval=grant[0],signature=grant[1])
        governance.trust_path(self.config).unlink()
        with self.assertRaises(OSError):self.apply(grant)

    def test_downstream_guard_and_historical_claim_manifest_compatibility(self):
        from src.review.recognition import runtime_activation_authority_schema as authority
        plan=self.preview()['plan'];self.apply(self.approval(plan))
        with a.connect(self.config.control) as control:
            claims.check_rows(control)
            self.assertEqual(plan['control_before_sha256'],authority.historical_claim_manifest(control))
            binding,profile,_=runtime._history(control)
            self.assertEqual(plan['h1'],lineage.expected_schema(control,binding,profile))
        old=authority.definitions();new=lineage.upgrade_definitions(old)
        guard=authority.AUTHORITIES+'_scope_guard'
        self.assertNotEqual(old[guard],new[guard])
        self.assertIn(lineage.ACTION,new[guard])

    def test_lost_commit_acknowledgement_has_durable_atomic_status(self):
        original=completion._commit
        def lost(db):original(db);raise RuntimeError('lost acknowledgement')
        with patch.object(completion,'_commit',side_effect=lost),self.assertRaises(RuntimeError):self.apply()
        self.assertEqual('COMPLETED',completion.inspect(self.config)['state'])

    def test_real_post_completion_proposal_approval_and_claim_use_h1(self):
        from src.review.recognition import runtime_proposals, runtime_approval_ceremony as ceremony
        from src.review.recognition import runtime_approvals, runtime_execution_admission, runtime_execution_claims
        self.apply()
        origin=time.monotonic_ns()
        self.f.clock.side_effect=lambda:(base.datetime.strptime(base.at(213),'%Y-%m-%dT%H:%M:%SZ')+
            timedelta(seconds=(time.monotonic_ns()-origin)//1_000_000_000)).strftime('%Y-%m-%dT%H:%M:%SZ')
        source=self.f.f.fixture.request()
        request=dict(request_id=str(uuid4()),family=source['family'],inputs=source['inputs'],
            evaluation_at_utc=source['evaluation_at_utc'],review_reference=source['review_reference'],parent_operation_id=None)
        pair=runtime_proposals.create_proposal(self.config,self.session,request,primary_token=self.primary)
        reference=pair['reference']
        step=ceremony.issue_step_up(self.config,self.session,base.independent_code(runtime._utc_now()),reference,primary_token=self.primary)
        confirmation=ceremony.begin_confirmation(self.config,self.session,step['token'],reference,
            canonical(dict(decision='approve',reason='synthetic downstream review',confirm=True)),primary_token=self.primary)
        approval_id=str(uuid4())
        approved=runtime_approvals.issue_approval(self.config,self.session,confirmation['token'],
            canonical(dict(approval_id=approval_id,reference=reference)),primary_token=self.primary)
        admission=runtime_execution_admission.assess(self.config,self.session,approval_id,
            approval_sha256=approved['approval_sha256'],reference=reference,primary_token=self.primary)
        runtime_execution_claims.acquire(self.config,admission,self.session,primary_token=self.primary)
        with a.connect(self.config.control) as control:
            claims.check_rows(control)
            row=control.execute('SELECT body_json FROM '+claims.CLAIMS).fetchone()
            body=load(row[0]);plan=lineage.verify(control)
            self.assertEqual(plan['h1'],body['target_snapshot']['target']['schema_sha256'])
            self.assertEqual(plan['profile_sha256'],body['runtime_scope']['runtime_profile_sha256'])

    def test_later_authority_storage_preserves_original_claim_manifest(self):
        from src.review.recognition import runtime_activation_authority_schema as authority
        self.apply()
        with a.connect(self.config.control,write=True) as control:
            control.execute('BEGIN IMMEDIATE')
            before=claims.manifest(control)
            for sql in lineage.upgrade_definitions(authority.definitions()).values():control.execute(sql)
            a._audit(control,authority.ACTION,'fixture',runtime._utc_now(),dict(migration_id=authority.MIGRATION,
                previous_schema_sha256=before,installed_schema_sha256=claims.manifest(control),
                installation_id=lineage.verify(control)['installation_id'],generation=5,reason='synthetic successor storage'))
            a.schema.check_control(control)
            self.assertEqual(lineage.verify(control)['control_before_sha256'],authority.historical_claim_manifest(control))
            control.commit()
        self.assertEqual('COMPLETED',completion.inspect(self.config)['state'])

    def test_completion_precedes_verified_authority_lifetime_control_lineage(self):
        from src.review.recognition import runtime_activation_authority_schema as authority
        from src.review.recognition import runtime_schema_package_lineage as packages
        self.apply()
        with a.connect(self.config.control,write=True) as control:
            control.execute('BEGIN IMMEDIATE')
            before=claims.manifest(control)
            source=lineage.upgrade_definitions(authority.definitions())
            successor=lineage.upgrade_definitions(packages.successor_definitions())
            old={row[0]:' '.join(row[1].split()) for row in control.execute(
                "SELECT name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'")}
            intermediate={**old,**{name:' '.join(sql.split()) for name,sql in source.items()}}
            for sql in successor.values():control.execute(sql)
            installation=lineage.verify(control)['installation_id']
            a._audit(control,authority.ACTION,'fixture',runtime._utc_now(),dict(migration_id=authority.MIGRATION,
                previous_schema_sha256=before,installed_schema_sha256=digest(intermediate),
                installation_id=installation,generation=5,reason='synthetic authority predecessor'))
            a._audit(control,packages.ACTION,'fixture',runtime._utc_now(),dict(migration_id=packages.MIGRATION,
                previous_schema_sha256=digest(intermediate),installed_schema_sha256=claims.manifest(control),
                installation_id=installation,generation=5,reason='synthetic lifetime successor'))
            edges=packages.verify(control)
            self.assertEqual({'A','L'},set(edges))
            a.schema.check_control(control)
            self.assertEqual(lineage.verify(control)['control_before_sha256'],authority.historical_claim_manifest(control))
            control.commit()
        self.assertEqual('COMPLETED',completion.inspect(self.config)['state'])

    def test_http_preview_diagnostic_survives_error_handler_without_state_changes(self):
        import json
        from flask import Flask
        from src.review import admin_dashboard
        from src.review.recognition import admin_routes, readiness_diagnostics as diagnostics
        from src.review.recognition.qualification import Quarantined
        from src.review.recognition.trust import TrustError
        app = Flask(__name__)
        app.config.update(TESTING=True, SECRET_KEY='synthetic-preview-diagnostic')
        admin_routes.register_admin_routes(app)
        client = app.test_client()
        with client.session_transaction() as browser:
            browser.update(authenticated_reviewer_id=1, reviewer_key='owner-key',
                           recognition_primary=self.primary, recognition_admin=self.session,
                           auth_csrf='synthetic-csrf')
        secret = '/secret/path nonce=secret-nonce token=secret-token approval=secret-approval'
        cases = [
            (admin_routes, 'configuration', OSError(secret), 'configuration', 'filesystem_access_failed'),
            (admin_dashboard, 'owner_access', sqlite3.DatabaseError(secret), 'owner_access', 'database_access_failed'),
            (owner, 'get_admin_identity', ImportError(secret), 'authentication', 'dependency_import_failed'),
            (owner, 'get_admin_identity', a.AdminError('primary_authentication_required', 401),
             'authentication', 'primary_authentication_required'),
            (completion, 'preview', ImportError(secret), 'foundation_plan', 'dependency_import_failed'),
            (completion, 'preview', ValueError(secret), 'foundation_plan', 'validation_failed'),
            (completion, '_journal', TrustError(secret), 'foundation_prerequisites', 'trust_validation_failed'),
            (completion.tempfile, 'TemporaryDirectory', OSError(secret), 'foundation_copy', 'filesystem_access_failed'),
            (completion.execution_schema, 'check_schema', Quarantined(secret), 'foundation_schema', 'recognition_inventory_rejected'),
            (readiness, '_assess_inventory', TrustError(secret), 'foundation_inventory', 'trust_validation_failed'),
        ]
        before = self.dump(self.config.target), self.dump(self.config.control)
        with patch.object(admin_routes, 'configuration', return_value=self.config):
            for module, name, error, stage, classification in cases:
                for broken_sink in (False, True):
                    with self.subTest(stage=stage, broken_sink=broken_sink), \
                         patch.object(module, name, side_effect=error), \
                         patch.object(diagnostics._logger, 'warning',
                                      side_effect=RuntimeError(secret) if broken_sink else None) as log:
                        response = client.post('/api/admin/recognition-control/runtime-foundation/preview',
                            json=dict(csrf_token='synthetic-csrf', operator='fixture', reason='review'))
                        status = error.status if isinstance(error, a.AdminError) else 503
                        code = error.code if isinstance(error, a.AdminError) else 'administrative_control_unavailable'
                        self.assertEqual(status, response.status_code)
                        expected = dict(stage=stage, failure_class=classification)
                        self.assertEqual({'error': code,
                                          'diagnostic': expected}, response.get_json())
                        self.assertNotIn(secret, response.get_data(as_text=True))
                        self.assertIsNone(diagnostics._scope.get())
                        self.assertEqual('no-store', response.headers['Cache-Control'])
                        log.assert_called_once()
                        record = json.loads(log.call_args.args[1])
                        self.assertEqual(stage, record['stage'])
                        self.assertEqual(classification, record['failure_class'])
                        self.assertNotIn(secret, repr(log.call_args))
                        self.assertNotIn('exc_info', log.call_args.kwargs)
                    self.assertEqual(before, (self.dump(self.config.target), self.dump(self.config.control)))
            # A different request must never inherit the Preview diagnostic.
            with patch.object(owner, 'get_admin_identity', side_effect=ValueError(secret)):
                response = client.get('/api/admin/recognition-control/identity')
                self.assertEqual({'error': 'administrative_control_unavailable'}, response.get_json())
            response = client.post('/api/admin/recognition-control/runtime-foundation/preview',
                json=dict(csrf_token='wrong', operator='fixture', reason='review'))
            self.assertEqual(400, response.status_code)
            self.assertEqual({'error': 'invalid_request_token', 'diagnostic': dict(
                stage='foundation_request', failure_class='administration_denied')}, response.get_json())
            with patch.object(diagnostics._logger, 'warning') as log:
                response = client.post('/api/admin/recognition-control/runtime-foundation/preview',
                    json=dict(csrf_token='synthetic-csrf', operator='fixture', reason='review'))
                self.assertEqual(200, response.status_code)
                self.assertFalse(response.get_json()['execution_authority'])
                log.assert_not_called()
            self.assertEqual(before, (self.dump(self.config.target), self.dump(self.config.control)))

    def test_protected_http_csrf_preview_apply_and_status(self):
        from flask import Flask
        from src.review.recognition import admin_routes
        app=Flask(__name__);app.config.update(TESTING=True,SECRET_KEY='synthetic-completion')
        admin_routes.register_admin_routes(app);client=app.test_client()
        with client.session_transaction() as browser:
            browser.update(authenticated_reviewer_id=1,reviewer_key='owner-key',recognition_primary=self.primary,
                           recognition_admin=self.session,auth_csrf='synthetic-csrf')
        prefix='/api/admin/recognition-control/runtime-foundation/'
        with patch.object(admin_routes,'configuration',return_value=self.config):
            self.assertEqual(400,client.post(prefix+'preview',json=dict(operator='fixture',reason='review')).status_code)
            response=client.post(prefix+'preview',json=dict(operator='fixture',reason='review',csrf_token='synthetic-csrf'))
            self.assertEqual(200,response.status_code,response.get_json())
            grant=self.approval(response.get_json()['plan'])
            response=client.post(prefix+'complete',json=dict(serialized_approval=grant[0],signature=grant[1],csrf_token='synthetic-csrf'))
            self.assertEqual(200,response.status_code,response.get_json())
            status=client.get(prefix+'status')
            self.assertEqual('COMPLETED',status.get_json()['state'])
            self.assertEqual('NOT_ACTIVATED',status.get_json()['activation_state'])

    def test_foundation_owner_page_preview_authentication_csrf_and_readonly(self):
        from flask import Flask
        from src.review.recognition import admin_routes
        app=Flask(__name__,template_folder=str(Path(__file__).resolve().parents[1]/'src/dashboard/templates'))
        app.config.update(TESTING=True,SECRET_KEY='synthetic-foundation-ui')
        admin_routes.register_admin_routes(app)
        prefix='/api/admin/recognition-control/'
        client=app.test_client();guest=app.test_client()
        with client.session_transaction() as browser:
            browser.update(authenticated_reviewer_id=1,reviewer_key='owner-key',recognition_primary=self.primary,
                           recognition_admin=self.session,auth_csrf='synthetic-csrf')
        with guest.session_transaction() as browser:browser['auth_csrf']='synthetic-csrf'
        with patch.object(admin_routes,'configuration',return_value=self.config):
            self.assertEqual(403,guest.get(prefix+'owner-activation').status_code)
            self.assertEqual(403,guest.post(prefix+'runtime-foundation/preview',json=dict(
                csrf_token='synthetic-csrf',operator='fixture',reason='review')).status_code)
            page=client.get(prefix+'owner-activation')
            self.assertEqual(200,page.status_code)
            html=page.get_data(as_text=True)
            for control in ('foundation-preview','foundation-digest','foundation-plan','foundation-complete',
                            'authenticate','status','readiness','activate','suspend','deactivate'):
                self.assertIn('id="'+control+'"',html)
            self.assertIn('Preview is read-only',html)
            self.assertNotIn(self.primary,html);self.assertNotIn(self.session,html)
            self.assertEqual('no-store',page.headers['Cache-Control'])
            for payload in (dict(operator='fixture',reason='review'),
                            dict(csrf_token='wrong',operator='fixture',reason='review'),
                            dict(csrf_token='synthetic-csrf',operator='fixture',reason='review',session_token=self.session)):
                self.assertEqual(400,client.post(prefix+'runtime-foundation/preview',json=payload).status_code)
            before=self.dump(self.config.target),self.dump(self.config.control)
            with patch.object(completion,'complete',side_effect=AssertionError('Preview must never complete')):
                response=client.post(prefix+'runtime-foundation/preview',json=dict(
                    csrf_token='synthetic-csrf',operator='fixture',reason='read-only review'))
            self.assertEqual(200,response.status_code,response.get_json())
            self.assertEqual(digest(response.get_json()['plan']),response.get_json()['plan_sha256'])
            self.assertEqual(before,(self.dump(self.config.target),self.dump(self.config.control)))
            with client.session_transaction() as browser:browser.pop('recognition_admin')
            self.assertEqual(401,client.post(prefix+'runtime-foundation/preview',json=dict(
                csrf_token='synthetic-csrf',operator='fixture',reason='review')).status_code)

    def test_crash_atomicity_delete_journals_before_and_after_commit(self):
        grant=self.approval()
        options=dict(paths=[str(self.config.target),str(self.config.control),str(self.config.key_file)],
                     session=self.session,primary=self.primary,approval=grant[0],signature=grant[1],now=runtime._utc_now())
        for phase in ('before_ddl','after_ddl','before_commit','after_commit'):
            with self.subTest(phase=phase):
                options['phase']=phase
                child=subprocess.Popen([sys.executable,'-B','-c',CHILD],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,text=True,cwd=Path(__file__).resolve().parents[1])
                child.stdin.write(canonical(options)+'\n');child.stdin.flush()
                lines=queue.Queue()
                reader=threading.Thread(target=lambda:lines.put(child.stdout.readline()),daemon=True);reader.start()
                try:
                    line=lines.get(timeout=45)
                    self.assertEqual('PAUSED',line.strip(),line)
                finally:
                    if child.poll() is None:child.kill()
                    child.wait(timeout=15)
                    child.stdin.close();child.stdout.close();child.stderr.close()
                    reader.join(timeout=5)
                # Ordinary SQLite rollback-journal recovery only, owned fixture.
                with a.connect(self.config.control,write=True) as control:
                    control.execute('BEGIN IMMEDIATE');a.schema.check_control(control)
                result=completion.inspect(self.config)
                self.assertEqual('COMPLETED' if phase=='after_commit' else 'NOT_COMPLETED',result['state'])


CHILD = r'''
import json,sys,time,tempfile
from pathlib import Path
from datetime import timedelta
from src.review.recognition import administration as a, runtime_validation as runtime
from src.review.recognition import runtime_target_schema_completion as completion
from src.review.recognition.trust import utc
options=json.loads(sys.stdin.readline())
assert all(Path(p).resolve().is_relative_to(Path(tempfile.gettempdir()).resolve()) for p in options['paths'])
config=a.LocalAdministration(*(Path(p) for p in options['paths']))
anchor=time.monotonic_ns();origin=utc(options['now'])
runtime._utc_now=lambda:(origin+timedelta(seconds=(time.monotonic_ns()-anchor)//1_000_000_000)).strftime('%Y-%m-%dT%H:%M:%SZ')
install,validate,commit=completion._install,completion._validate_after,completion._commit
def pause():
    print('PAUSED',flush=True);sys.stdin.readline()
def install_hook(db):
    if options['phase']=='before_ddl':pause()
    install(db)
def validate_hook(db,plan):
    validate(db,plan)
    if options['phase']=='after_ddl':pause()
def commit_hook(db):
    if options['phase']=='before_commit':pause()
    commit(db)
    if options['phase']=='after_commit':pause()
completion._install,completion._validate_after,completion._commit=install_hook,validate_hook,commit_hook
completion.complete(config,options['session'],primary_token=options['primary'],serialized_approval=options['approval'],signature=options['signature'])
'''
