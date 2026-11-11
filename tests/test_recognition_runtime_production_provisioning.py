"""Actual production registry path on isolated enrolled owner files."""
import unittest
import pickle
from dataclasses import replace
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from src.review.recognition import authority,authorization,administration as a
from src.review.recognition import runtime_production_governance as governance
from src.review.recognition import runtime_schema_package_lineage as lineage
from src.review.recognition import runtime_finalization_schema_upgrade as upgrade
from src.review.recognition.rules import canonical
from tests import recognition_production_owner_fixture as fixture


class LateLifetimeHistoryTests(unittest.TestCase):
    def test_completed_entry_survives_later_lifetime_and_journal_extensions(self):
        config,*_=fixture.prepare(self,lifetime_before=False)
        from src.review.recognition import runtime_enrollment_transition_schema as plans
        with a.connect(config.control) as control:
            control.execute('BEGIN')
            edges=lineage.verify(control);plans.check_rows(control)
            rows=control.execute('SELECT * FROM '+plans.PLANS+' ORDER BY audit_sequence').fetchall()
            self.assertEqual(2,len(rows))
            self.assertLess(rows[0]['audit_sequence'],edges['L']['sequence'])
            self.assertLess(edges['L']['sequence'],edges['J']['sequence'])
            control.rollback()


class ProductionProvisioningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        host=unittest.TestCase();cls.addClassCleanup(host.doCleanups)
        cls.config,cls.session,cls.approval_id,cls.options,cls.key,cls.offset=fixture.prepare(host)

    def test_enrolled_journal_transition_and_signed_production_approval(self):
        proof,body,signature=fixture.signed(self.config,self.session,self.options['primary_token'],dict(kind='journal_install'),self.key)
        approval=proof['approvals'][0]
        self.assertEqual('production',approval.environment)
        authorization.verify(self.config.control,approval,proof['authority'],
            **authorization.migration_binding(upgrade.MIGRATION,upgrade.definitions()))
        with a.connect(self.config.control) as control:
            edges=lineage.verify(control);self.assertIn('J',edges)
            from src.review.recognition import runtime_enrollment_transition_schema as plans
            rows=control.execute('SELECT * FROM '+plans.PLANS+' ORDER BY source_generation').fetchall()
            self.assertEqual([3,5],[r['source_generation'] for r in rows])
            self.assertEqual(2,control.execute('SELECT count(*) FROM '+plans.HISTORY+' WHERE sequence=4').fetchone()[0])
        with self.assertRaises(Exception):
            authority.provision_production_authority(self.config,self.session,primary_token=self.options['primary_token'],
                serialized=canonical(body),signature='A'*88)
        with ThreadPoolExecutor(max_workers=1) as pool:
            with self.assertRaises(ValueError):pool.submit(governance.check_registered,proof['authority'],approval).result()
        with self.assertRaises(TypeError):pickle.dumps(proof['authority'])
        with self.assertRaises(ValueError):governance.check_registered(proof['authority'],replace(approval,environment='disposable'))
        with patch.object(governance.runtime,'_utc_now',return_value=body['expires_at_utc']):
            with self.assertRaisesRegex(ValueError,'production_governance_expired'):
                governance.check_registered(proof['authority'],approval)

    def test_unprovisioned_and_changed_scope_cannot_self_authorize(self):
        with self.assertRaises(ValueError):authority.provision_production_authority()
        proof,body,signature=fixture.signed(self.config,self.session,self.options['primary_token'],dict(kind='journal_install'),self.key)
        changed=deepcopy(body);changed['holder']['actor_id']=2
        with self.assertRaises(ValueError):
            authority.provision_production_authority(self.config,self.session,primary_token=self.options['primary_token'],
                serialized=canonical(changed),signature=signature)
