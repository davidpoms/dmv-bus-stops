"""R22 real disposable MFA/governance and exact original-source integration."""
from datetime import timedelta
import time
import unittest
from copy import deepcopy

from src.review.recognition import administration as a, runtime_validation as v
from src.review.recognition import runtime_finalization as finalization
from src.review.recognition import runtime_finalization_contract as contract
from src.review.recognition import runtime_operation_contract as operation, events
from src.review.recognition import runtime_scope_validation as shared
from src.review.recognition.rules import digest
from src.review.recognition.trust import utc, load
from tests import recognition_finalization_fixture as isolated
from tests import test_recognition_runtime_authority_owner_consent as fixture
from tests import test_recognition_administration as totp


class GovernanceIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.boot=isolated.bootstrap(); self.boot.__enter__(); self.addCleanup(self.boot.__exit__,None,None,None)
        self.f=fixture.AuthorityOwnerConsentTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.config,self.session,self.primary=self.f.config,self.f.session,self.f.primary
        origin=utc(self.f.clock.return_value); anchor=time.monotonic_ns()
        self.offset=[0]
        self.f.clock.side_effect=lambda:(origin+timedelta(seconds=self.offset[0]+(time.monotonic_ns()-anchor)//1_000_000_000)).strftime('%Y-%m-%dT%H:%M:%SZ')
        # Detached request DATA only. The new owner independently validates it;
        # the preactivation proposal owner must not be used on an active target.
        with a.connect(self.config.control) as conn,a.connect(self.config.target) as raw_target:
            binding,profile,_=v._history(conn)
            scope=v._identity_snapshot(self.config,conn,raw_target,v._utc_now())
            target=dict(format=operation.TARGET_FORMAT,installation_id=binding['installation_id'],
                target_id=binding['target_id'],generation=binding['generation'],owner_id=binding['owner_id'],
                binding_sha256=digest(binding),runtime_profile_sha256=profile['profile_sha256'],
                auth_epoch=scope['auth_epoch'],mfa_epoch=shared._mfa(conn,binding))
        with a.connect(self.config.target) as conn:
            op=load(conn.execute('SELECT body_json FROM recognition_operation_contracts WHERE operation_id=?',
                                 (self.f.scope['reference']['operation_id'],)).fetchone()[0])
            manifest=events.get_event(conn,op['event_id'])['preparation']['manifest']
        ref=self.f.scope['reference']
        self.intent=dict(operation_id=ref['operation_id'],operation_sha256=ref['operation_sha256'],
            writer_manifest_sha256=op['writer_manifest_sha256'],write_set_sha256=finalization._write_set(manifest),
            family=manifest['family'],runtime_target=target,action=contract.EFFECT)
        from src.review.recognition import runtime_activation_authority_schema as source
        self.policy=dict(format=contract.POLICY,policy_id=contract.ISSUER_ROLE,version=1,action=contract.EFFECT,
                         max_grants=1,lifetime_policy=source.LIFETIME)
        self.governance=isolated.governance(self.config,self.intent,self.policy)

    def authorize(self, **changes):
        args=dict(primary_token=self.primary,**self.governance); args.update(changes)
        return finalization.authorize_issuer(self.config,self.session,totp.independent_code(v._utc_now()),self.intent,**args)

    def test_real_mfa_and_four_distinct_governance_approvals(self):
        result=self.authorize()
        self.assertFalse(result['execution_authority'])
        self.assertEqual(self.intent,result['issuer']['intent'])
        with a.connect(self.config.control) as conn:
            self.assertEqual(result['issuer'],finalization._issuer(conn,result['issuer_sha256'],now=v._utc_now()))
            self.assertEqual(1,len(finalization._audits(conn,finalization.AUTHORIZE)))
        with self.assertRaisesRegex(ValueError,'finalization_issuer_already_authorized'):
            self.authorize()

    def test_wrong_issuer_provisioning_and_forged_attempt_rejected(self):
        with self.assertRaises(ValueError): self.authorize(authority=object())
        with self.assertRaises(ValueError): finalization.finalize(object(),object())
        proofs=dict(self.governance['approvals']);proofs['appoint_issuer']=proofs['adopt_policy']
        with self.assertRaises(ValueError):self.authorize(approvals=proofs)

    def test_changed_target_or_write_set_approval_rejected(self):
        old=deepcopy(self.intent)
        for key in ('operation_sha256','write_set_sha256'):
            self.intent=deepcopy(old);self.intent[key]='0'*64
            with self.subTest(key=key),self.assertRaises(ValueError):self.authorize()

    def test_v2_requires_its_own_exact_governance_approvals(self):
        from src.review.recognition import runtime_schema_package_lineage as lineage
        # Existing v1 approvals cannot authorize a different lifetime policy.
        with self.assertRaises(ValueError):self.authorize(lifetime_policy=lineage.V2)
        policy=dict(self.policy,lifetime_policy=lineage.V2)
        proofs=isolated.governance(self.config,self.intent,policy)
        receipt=self.authorize(lifetime_policy=lineage.V2,**proofs)
        self.assertEqual(policy,receipt['issuer']['policy'])
        with a.connect(self.config.control) as conn:
            self.assertEqual(receipt['issuer'],finalization._issuer(conn,receipt['issuer_sha256'],now=v._utc_now()))

    def test_authentication_denial_is_durable_and_never_issues(self):
        with self.assertRaises(a.AdminError):
            self.authorize(primary_token='invalid-primary-token-for-r22')
        with a.connect(self.config.control) as conn:
            self.assertFalse(finalization._audits(conn,finalization.AUTHORIZE))
            row=load(conn.execute('SELECT body_json FROM recognition_admin_audit ORDER BY sequence DESC LIMIT 1').fetchone()[0])
            self.assertEqual('administration_denied',row['action'])
            self.assertEqual('primary_authentication_required',row['subject']['code'])

    def test_original_source_binding_and_single_issuer_consumption(self):
        from src.review.recognition import runtime_authority_consent as consent
        from src.review.recognition import runtime_execution_coordinator as coordinator
        receipt=self.authorize()
        self.offset[0]+=30  # Before any original authority/clock exists; new MFA counter.
        step=consent.issue_step_up(self.config,self.session,totp.independent_code(v._utc_now()),self.f.approval_id,**self.f.scope)
        confirmation=consent.begin_confirmation(self.config,self.session,step['token'],self.f.approval_id,
            self.f.intent,**self.f.scope)
        with coordinator.coordinator(self.config,self.session,confirmation['token'],self.f.approval_id,
                **self.f.scope,finalization_issuer=receipt['issuer_sha256']) as owner:
            # Actual original source/private continuation, not synthetic source DATA.
            outer=coordinator._outer(owner)
            with a.connect(self.config.control) as conn:
                rows=finalization._audits(conn,finalization.ELIGIBILITY)
            self.assertEqual(1,len(rows))
            self.assertEqual(outer.authority_sha256,rows[0]['subject']['authority_sha256'])
            self.assertEqual(receipt['issuer_sha256'],rows[0]['subject']['issuer_sha256'])
            body=load(outer.authority_json); action=rows[0]['subject']
            self.assertEqual(120,a.timestamp(body['expires_at_utc'])-a.timestamp(body['issued_at_utc']))
            for field in ('authority_id','authority_sha256','intent','expires_at_utc'):
                changed=deepcopy(action)
                if field=='authority_id':
                    from uuid import uuid4
                    changed[field]=str(uuid4())
                elif field=='intent':changed['intent']['write_set_sha256']='0'*64
                elif field=='expires_at_utc':
                    changed[field]=(utc(body['expires_at_utc'])+timedelta(seconds=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
                else:changed[field]='0'*64
                with self.subTest(field=field),self.assertRaises(ValueError):
                    contract.validate_action(changed,issuer=receipt['issuer'],authority=body)
            # Unit ownership/binding adapter only: no business action or
            # reduced fresh-validation path is invoked. The complete ceremony
            # is measured separately by the bounded lifecycle diagnostic.
            with finalization._reserved(self.config,self.session,self.primary,outer=outer) as state:
                self.assertEqual(action,finalization._bound_action(state))
                finalization.p._rollback(state,state.control)

    def test_expired_revoked_and_cross_thread_issuer_rejected(self):
        from concurrent.futures import ThreadPoolExecutor
        from tests.recognition_authorization_fixture import approval
        receipt=self.authorize();sha=receipt['issuer_sha256']
        with a.connect(self.config.control) as conn:
            with self.assertRaisesRegex(ValueError,'finalization_issuer_expired'):
                finalization._issuer(conn,sha,now=receipt['issuer']['expires_at_utc'])
        with ThreadPoolExecutor(max_workers=1) as pool:
            result=pool.submit(finalization._require_entitlement_owner,self.config,sha,self.session,self.primary)
            with self.assertRaises(ValueError):result.result()
        proof=approval(self.config.target,family='runtime_finalization',permission='governance',action='revoke_issuer',
            operation_sha256=sha,policy_sha256=digest(self.policy),population_sha256=None,reference=contract.MANDATE)
        finalization.revoke_issuer(self.config,self.session,sha,primary_token=self.primary,
                                   approval=proof['authorization'],authority=proof['authority'])
        with a.connect(self.config.control) as conn:
            with self.assertRaisesRegex(ValueError,'finalization_issuer_revoked'):
                finalization._issuer(conn,sha,now=v._utc_now())


if __name__=='__main__':unittest.main()
