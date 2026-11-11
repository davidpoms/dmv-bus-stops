"""R26-FIX closed policy compatibility; detached DATA, no issuance or execution."""
from copy import deepcopy
from datetime import timedelta
import inspect
import unittest

from src.review.recognition import runtime_finalization_contract as c
from src.review.recognition import runtime_finalization as owner
from src.review.recognition import runtime_activation_authority_schema as source
from src.review.recognition import runtime_schema_package_lineage as lineage
from src.review.recognition.runtime_authority_lifetime_policy import seconds
from src.review.recognition.rules import canonical, digest
from src.review.recognition.trust import utc
from tests.test_recognition_runtime_decision_outcome_journal_schema import data


class FinalizationLifetimeTests(unittest.TestCase):
    def values(self, policy=source.LIFETIME):
        authority=deepcopy(data()[0]['authority'])
        authority.update(lifetime_policy=policy,expires_at_utc=(utc(authority['issued_at_utc'])+
            timedelta(seconds=seconds(policy))).strftime('%Y-%m-%dT%H:%M:%SZ'))
        ref=authority['operation_reference']
        issuer=dict(format=c.ISSUER,mandate=c.MANDATE,governance_binding_sha256='a'*64,
            adoption_sha256='b'*64,appointment_sha256='c'*64,approval_sha256='d'*64,
            issuer_role=c.ISSUER_ROLE,holder=deepcopy(authority['authentication']),
            intent=dict(operation_id=ref['operation_id'],operation_sha256=ref['operation_sha256'],
                writer_manifest_sha256=ref['writer_manifest_sha256'],write_set_sha256='e'*64,
                family=ref['writer_family'],runtime_target=deepcopy(authority['runtime_target']),action=c.EFFECT),
            policy=dict(format=c.POLICY,policy_id=c.ISSUER_ROLE,version=1,action=c.EFFECT,
                max_grants=1,lifetime_policy=policy),issued_at_utc=authority['issued_at_utc'],
            expires_at_utc=authority['expires_at_utc'])
        action=dict(format=c.ACTION,issuer_sha256=digest(issuer),authority_id=authority['authority_id'],
            authority_sha256=digest(authority),holder=deepcopy(issuer['holder']),intent=deepcopy(issuer['intent']),
            policy=deepcopy(issuer['policy']),issued_at_utc=authority['issued_at_utc'],
            expires_at_utc=authority['expires_at_utc'])
        return issuer,authority,action

    def test_v1_historical_canonical_records_unchanged(self):
        issuer,authority,action=self.values()
        before=canonical(dict(issuer=issuer,authority=authority,action=action))
        self.assertEqual(issuer,c.parse_issuer(canonical(issuer),expected_sha256=digest(issuer)))
        self.assertEqual(action,c.parse_action(canonical(action),expected_sha256=digest(action),issuer=issuer,authority=authority))
        self.assertEqual(before,canonical(dict(issuer=issuer,authority=authority,action=action)))
        self.assertEqual(120,seconds(authority['lifetime_policy']))

    def test_v2_exact_300_second_authority_and_action(self):
        issuer,authority,action=self.values(lineage.V2)
        self.assertEqual(300,int((utc(authority['expires_at_utc'])-utc(authority['issued_at_utc'])).total_seconds()))
        self.assertEqual(action,c.parse_action(canonical(action),expected_sha256=digest(action),issuer=issuer,authority=authority))

    def test_unknown_policy_and_policy_versions_rejected(self):
        for key,value in [('lifetime_policy','recognition-runtime-authority-lifetime-600s-v3'),
                          ('lifetime_policy',300),('version',2),('version',True)]:
            issuer,_,_=self.values()
            issuer['policy'][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):c.validate_issuer(issuer)

    def test_arbitrary_duration_and_extension_rejected(self):
        issuer,authority,action=self.values(lineage.V2)
        issuer['policy']['seconds']=600
        with self.assertRaises(ValueError):c.validate_issuer(issuer)
        issuer,authority,action=self.values(lineage.V2)
        authority['expires_at_utc']='2099-01-01T00:05:01Z'
        with self.assertRaises(ValueError):source.validate_authority(authority)

    def test_policy_mismatch_never_upgrades_v1_or_downgrades_v2(self):
        for policy,other in [(source.LIFETIME,lineage.V2),(lineage.V2,source.LIFETIME)]:
            issuer,authority,action=self.values(policy)
            issuer['policy']['lifetime_policy']=other
            action.update(policy=deepcopy(issuer['policy']),issuer_sha256=digest(issuer))
            with self.subTest(policy=policy),self.assertRaisesRegex(ValueError,'finalization_policy'):
                c.validate_action(action,issuer=issuer,authority=authority)

    def test_issue_time_authority_digest_cannot_be_reinterpreted(self):
        issuer,authority,action=self.values()
        authority.update(lifetime_policy=lineage.V2,expires_at_utc='2099-01-01T00:05:00Z')
        with self.assertRaisesRegex(ValueError,'finalization_decision_mismatch'):
            c.validate_action(action,issuer=issuer,authority=authority)

    def test_exact_action_target_and_policy_binding(self):
        for key in ('action','write_set_sha256','runtime_target'):
            issuer,authority,action=self.values(lineage.V2)
            if key=='runtime_target':action['intent'][key]['generation']+=1
            else:action['intent'][key]='f'*64
            with self.subTest(key=key),self.assertRaises(ValueError):
                c.validate_action(action,issuer=issuer,authority=authority)

    def test_action_clipped_by_original_source_and_issuer_bounds(self):
        issuer,authority,action=self.values(lineage.V2)
        issuer['expires_at_utc']='2099-01-01T00:04:00Z'
        action['issuer_sha256']=digest(issuer)
        with self.assertRaisesRegex(ValueError,'finalization_interval'):
            c.validate_action(action,issuer=issuer,authority=authority)
        action['expires_at_utc']=issuer['expires_at_utc']
        self.assertEqual(action,c.validate_action(action,issuer=issuer,authority=authority))

    def test_default_issuer_policy_stays_v1(self):
        self.assertEqual(source.LIFETIME,inspect.signature(owner.authorize_issuer).parameters['lifetime_policy'].default)
