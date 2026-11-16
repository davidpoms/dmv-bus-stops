"""Real enrolled H0 missing runtime schemas; same signed atomic completion path."""

from copy import deepcopy
import base64
import io
import unittest
from unittest.mock import patch

from src.review.recognition import administration as a, authorization, event_schema, operation_schema, execution_schema
from src.review.recognition import runtime_target_schema_completion as completion, runtime_target_schema_lineage as lineage
from src.review.recognition import runtime_production_governance as governance, runtime_validation as runtime
from src.review.recognition.rules import canonical, digest
from src.review.recognition.trust import load
from tests import test_recognition_target_schema_completion as fixture


class RuntimeFoundationCompletionTests(unittest.TestCase):
    def setUp(self):
        self.f = fixture.TargetSchemaCompletionTests()
        self.f.missing_runtime_prerequisites = True
        variants = {'test_partial_prerequisite_source_rejected': 'partial',
                    'test_mismatched_existing_definition_rejected': 'mismatched',
                    'test_existing_canonical_objects_are_preserved_in_h0_projection': 'existing',
                    'test_missing_private_prerequisite_rejected': 'missing_private'}
        self.f.runtime_source_variant = variants.get(self._testMethodName)
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.config = self.f.config
        self.original_approval = self.f.approval

    def snapshot(self):
        return self.f.dump(self.config.target), self.f.dump(self.config.control)

    def sign(self, body):
        encoded = canonical(body)
        return dict(serialized_approval=encoded, signature=base64.b64encode(
            self.f.key.sign(governance.DOMAIN+encoded.encode())).decode())

    def approval(self, plan=None, preview=False):
        plan = self.f.preview()['plan'] if plan is None else plan
        body = load(self.original_approval(plan)[0])
        if preview:
            subject = dict(kind=completion.PREVIEW_KIND, operator=plan['operator'], reason=plan['reason'],
                           package=lineage.RUNTIME_PACKAGE)
            body['subject'] = subject
            binding = completion.preview_binding(subject)
        else:
            binding = authorization.migration_binding(plan['package'], lineage.package_definitions(plan['package']))
        body['approvals'][0].update(binding)
        return self.sign(body)

    def test_absent_source_deterministic_preview_and_signed_cli_completion(self):
        before = self.snapshot()
        protected = self.f.protected()
        first = self.f.preview()
        self.assertEqual(first, self.f.preview())
        self.assertEqual(before, self.snapshot())
        plan = first['plan']
        self.assertEqual(lineage.RUNTIME_PACKAGE, plan['package'])
        expected = lineage.package_definitions(lineage.RUNTIME_PACKAGE)
        self.assertEqual(sorted(expected), plan['added_objects'])
        self.assertEqual(digest(expected), plan['definitions_sha256'])
        signed_preview = completion.preview_approved(self.config, **self.approval(plan, preview=True))
        self.assertEqual(first['plan'], signed_preview['plan'])
        self.assertTrue(signed_preview['read_only'])
        self.assertEqual(before, self.snapshot())
        artifact = self.approval(plan)
        path = self.config.target.parent/'synthetic-runtime-foundation.json'
        path.write_text(canonical(artifact))
        with patch('src.api.sqlite_runtime.load_production_sqlite'):
            from scripts.active import complete_recognition_foundation as cli
        args = ['complete','--target',str(self.config.target),'--control',str(self.config.control),
                '--key-file',str(self.config.key_file),'--expected-generation','5',
                '--authorization',str(path),'--approved-plan-sha256',first['plan_sha256']]
        with patch('builtins.input', return_value=first['plan_sha256']), \
             patch('sys.stdout',new_callable=io.StringIO) as output:
            self.assertEqual(0, cli.main(args))
        result = load(output.getvalue())
        self.assertEqual(('COMPLETED',5,'NOT_ACTIVATED',False), tuple(result[k] for k in
                         ('state','generation','production_state','execution_authority')))
        self.assertEqual(protected, self.f.protected())
        with a.connect(self.config.control) as control, a.connect(self.config.target) as target:
            binding, profile, _ = runtime._history(control)
            self.assertEqual(plan['h0'], binding['target']['schema_sha256'])
            self.assertEqual(plan['h0'], profile['target_schema_sha256'])
            self.assertEqual(plan, lineage.verify(control))
            runtime._identity_snapshot(self.config,control,target,runtime._utc_now())
            execution_schema.check_schema(target)
            self.assertEqual([(1,b'\x00\xff',1.25)], [tuple(r) for r in target.execute('SELECT * FROM preserved_data')])
            for name, sql in expected.items():
                self.assertEqual(' '.join(sql.split()), ' '.join(target.execute(
                    'SELECT sql FROM sqlite_master WHERE name=?',(name,)).fetchone()[0].split()))
        ready = fixture.owner.assess(self.config,self.f.session,primary_token=self.f.primary)
        self.assertTrue(ready['activation_ready'], ready)
        self.assertEqual('NOT_ACTIVATED', ready['activation_state'])
        with self.assertRaises(ValueError):
            completion.complete_approved(self.config,approved_plan_sha256=first['plan_sha256'],**artifact)
        with self.assertRaises(ValueError):
            self.f.preview()

    def test_v1_preview_and_completion_authorizations_cannot_install_v2(self):
        plan = self.f.preview()['plan']
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.f.apply(self.f.approval(plan))  # v1 family/digest on a v2 plan.
        body = load(self.approval(plan,preview=True)['serialized_approval'])
        del body['subject']['package']
        body['approvals'][0].update(completion.preview_binding(body['subject']))
        with self.assertRaisesRegex(ValueError,'foundation_preview_package_mismatch'):
            completion.preview_approved(self.config,**self.sign(body))
        self.assertEqual(before,self.snapshot())

    def test_wrong_or_modified_plan_rejected_without_changes(self):
        plan = self.f.preview()['plan']
        before = self.snapshot()
        for field, value in [('h0','a'*64),('h1','b'*64),('generation',6),('target_id',str(fixture.uuid4())),
                             ('profile_sha256','c'*64),('added_objects',['unapproved_sql']),
                             ('added_objects',sorted(set(plan['added_objects'])-{'recognition_execution_seals'}))]:
            changed = deepcopy(plan); changed[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                completion.complete_approved(self.config,approved_plan_sha256=digest(changed),**self.approval(changed))
        artifact = self.approval(plan)
        body = load(artifact['serialized_approval']); body['subject']['plan']['reason'] = 'unsigned alteration'
        artifact['serialized_approval'] = canonical(body)
        with self.assertRaises(ValueError):
            completion.complete_approved(self.config,approved_plan_sha256=digest(body['subject']['plan']),**artifact)
        self.assertEqual(before,self.snapshot())

    def test_validation_audit_and_commit_failure_roll_back_and_allow_retry(self):
        plan = self.f.preview()['plan']; artifact = self.approval(plan); before = self.snapshot()
        for module, name in [(completion,'_validate_after'),(a,'_audit'),(completion,'_commit')]:
            with self.subTest(name=name), patch.object(module,name,side_effect=RuntimeError('synthetic failure')):
                with self.assertRaises(RuntimeError):
                    completion.complete_approved(self.config,approved_plan_sha256=digest(plan),**artifact)
            self.assertEqual(before,self.snapshot())
        self.assertEqual('COMPLETED',completion.complete_approved(
            self.config,approved_plan_sha256=digest(plan),**artifact)['state'])

    def test_ddl_failure_rolls_back_all_added_schemas(self):
        plan = self.f.preview()['plan']; artifact = self.approval(plan); before = self.snapshot()
        original = completion._authorizer
        def reject(action, first, *args, **kwargs):
            if first == 'recognition_execution_seals' and action == fixture.sqlite3.SQLITE_CREATE_TABLE:
                return fixture.sqlite3.SQLITE_DENY
            return original(action,first,*args,**kwargs)
        with patch.object(completion,'_authorizer',side_effect=reject), self.assertRaises(fixture.sqlite3.Error):
            completion.complete_approved(self.config,approved_plan_sha256=digest(plan),**artifact)
        self.assertEqual(before,self.snapshot())

    def test_unrelated_schema_drift_rejected(self):
        with a.connect(self.config.target,write=True) as target:
            target.execute('CREATE TABLE unauthorized_schema(value)');target.commit()
        before = self.snapshot()
        with self.assertRaises(ValueError):self.f.preview()
        self.assertEqual(before,self.snapshot())

    def test_partial_prerequisite_source_rejected(self):
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'foundation_partial_prerequisite_source'):
            self.f.preview()
        self.assertEqual(before, self.snapshot())

    def test_existing_canonical_objects_are_preserved_in_h0_projection(self):
        plan = self.f.preview()['plan']
        self.assertNotIn('recognition_execution_storage', plan['added_objects'])
        self.assertIn('recognition_execution_storage', lineage.package_definitions(plan['package']))
        completion.complete_approved(self.config,approved_plan_sha256=digest(plan),**self.approval(plan))
        with a.connect(self.config.control) as control, a.connect(self.config.target) as target:
            runtime._identity_snapshot(self.config,control,target,runtime._utc_now())
            binding, profile, _ = runtime._history(control)
            self.assertEqual(plan['h0'], profile['target_schema_sha256'])
            self.assertEqual(plan['h1'],lineage.expected_schema(control,binding,profile))

    def test_mismatched_existing_definition_rejected(self):
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'foundation_existing_definition_mismatch'):
            self.f.preview()
        self.assertEqual(before, self.snapshot())

    def test_missing_private_prerequisite_rejected(self):
        before = self.snapshot()
        with self.assertRaises(ValueError):self.f.preview()
        self.assertEqual(before, self.snapshot())

    def test_existing_physical_mfa_expiry_and_readiness_gates_remain_enforced(self):
        plan = self.f.preview()['plan']; before = self.snapshot(); artifact = self.approval(plan)
        for seconds in (301,):
            self.f.f.clock.return_value = fixture.base.at(seconds)
            with self.assertRaises(ValueError):
                completion.complete_approved(self.config,approved_plan_sha256=digest(plan),**artifact)
        self.f.f.clock.return_value = fixture.base.at(183)
        self.assertEqual(before,self.snapshot())
        original = authorization.target_identity
        with patch.object(a,'target_identity',side_effect=lambda value: fixture.replace(original(value),device=original(value).device+1)):
            with self.assertRaises(ValueError):self.f.preview()
        with patch.object(completion.local_readiness,'_assess_inventory',return_value=dict(activation_ready=False)):
            with self.assertRaisesRegex(ValueError,'foundation_other_readiness_prerequisites'):self.f.preview()
        self.assertEqual(before,self.snapshot())
        with a.connect(self.config.control,write=True) as control:
            control.execute("UPDATE recognition_admin_mfa SET state='UNENROLLED' WHERE actor=1")
            control.commit()
        protected = self.f.protected()
        with self.assertRaises(ValueError):self.f.preview()
        self.assertEqual(protected,self.f.protected())

    def test_offline_signer_accepts_only_the_exact_v2_completion_binding(self):
        from scripts.operator import recognition_governance as tool
        plan = self.f.preview()['plan']; body = load(self.approval(plan)['serialized_approval'])
        path = self.config.target.parent/'synthetic-offline-reviewed.json'
        path.write_text(canonical(body))
        root = governance._root(self.config)
        self.assertEqual(digest(lineage.package_definitions(lineage.RUNTIME_PACKAGE)),tool.RUNTIME_POLICY)
        with patch.object(tool,'_fresh') as freshness:
            self.assertEqual(body,tool._payload(path,root))
            freshness.assert_called_once_with(body)
        body['approvals'][0]['family'] = lineage.PACKAGE
        path.write_text(canonical(body))
        with self.assertRaises(ValueError):tool._payload(path,root)

    def test_process_interruption_preserves_atomic_v2_lineage(self):
        from tests import test_recognition_foundation_maintenance_cli as maintenance
        harness = maintenance.FoundationMaintenanceTests()
        harness.f, harness.config = self.f, self.config
        harness.preview = lambda: self.f.preview()
        harness.grant = lambda plan: self.approval(plan)
        harness.test_signed_completion_crash_rollback_and_commit()

    def approved_pair(self, plan=None):
        artifact = self.approval(plan)
        return artifact['serialized_approval'], artifact['signature']

    def test_historical_approval_remains_valid_after_expiry(self):
        with patch.object(self.f,'approval',side_effect=self.approved_pair):
            self.f.test_one_time_consumption_and_expired_approval_is_valid_history()

    def test_actual_downstream_proposal_approval_and_claim_use_v2_h1(self):
        with patch.object(self.f,'approval',side_effect=self.approved_pair):
            self.f.test_real_post_completion_proposal_approval_and_claim_use_h1()

    def test_authority_control_successor_preserves_v2_lineage(self):
        with patch.object(self.f,'approval',side_effect=self.approved_pair):
            self.f.test_completion_precedes_verified_authority_lifetime_control_lineage()

    def test_post_completion_additional_altered_and_missing_schema_reject(self):
        plan = self.f.preview()['plan']
        completion.complete_approved(self.config,approved_plan_sha256=digest(plan),**self.approval(plan))
        for sql in ('CREATE TABLE unauthorized_schema(value)',
                    'DROP TABLE recognition_operation_receipts',
                    'DROP TRIGGER recognition_execution_seals_immutable_update'):
            with a.connect(self.config.target,write=True) as target:
                target.execute('BEGIN'); target.execute(sql)
                with a.connect(self.config.control) as control, self.assertRaises(ValueError):
                    # The uncommitted mutation is inspected on this target handle.
                    runtime._identity_snapshot(self.config,control,target,runtime._utc_now())
                target.rollback()

    def test_authorizer_remains_closed_to_arbitrary_ddl_and_data_writes(self):
        plan = self.f.preview()['plan']; definitions = lineage.additions(plan); s = fixture.sqlite3
        for action, name in ((s.SQLITE_CREATE_TABLE,'arbitrary'),(s.SQLITE_CREATE_TRIGGER,'arbitrary'),
                             (s.SQLITE_INSERT,'recognition_operation_contracts')):
            self.assertEqual(s.SQLITE_DENY,completion._authorizer(action,name,None,completion.ALIAS,None,additions=definitions))

