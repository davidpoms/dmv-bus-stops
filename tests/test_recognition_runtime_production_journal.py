"""R28 late control journal extension; isolated enrolled files, no production."""
from unittest.mock import patch
import unittest
import sqlite3
from copy import deepcopy
from src.review.recognition import administration as a, administration_schema as base, authorization
from src.review.recognition import runtime_finalization_schema_upgrade as upgrade
from src.review.recognition import runtime_schema_package_lineage as lineage
from src.review.recognition import runtime_enrollment_transition_schema as transition
from src.review.recognition.rules import digest,canonical
from src.review.recognition.trust import load
from tests.test_recognition_runtime_authority_lifetime_policy import LifetimePolicyMigrationTests as Existing
from tests.recognition_authorization_fixture import approval


class JournalUpgradeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Existing.setUpClass();cls.addClassCleanup(Existing.doClassCleanups)

    def setUp(self):
        self.f=Existing();self.f.setUp();self.config=self.f.config
        self.f.migrate()

    def migrate(self):
        proof=approval(self.config.control,**authorization.migration_binding(upgrade.MIGRATION,upgrade.definitions()))
        with patch.object(a,'target_identity',side_effect=authorization.target_identity):
            return upgrade.migrate_control(self.config,expected_generation=3,operator='r28-test',
                reason='exact late journal extension',approval=proof['authorization'],authority=proof['authority'])

    def test_late_extension_preserves_original_manifest_edges_and_is_idempotent(self):
        with a.connect(self.config.control) as conn:
            old={k:v['audit'] for k,v in lineage.verify(conn).items()}
            before=transition.historical_manifest(conn)
        self.assertTrue(self.migrate()['installed'])
        self.assertFalse(self.migrate()['installed'])
        with a.connect(self.config.control) as conn:
            base.check_control(conn);edges=lineage.verify(conn)
            self.assertIn('J',edges)
            self.assertEqual(old,{k:v['audit'] for k,v in edges.items() if k!='J'})
            self.assertEqual(before,transition.historical_manifest(conn))
            self.assertEqual(digest(edges['J']['before']),edges['J']['audit']['subject']['previous_schema_sha256'])

    def test_wrong_predecessor_and_unknown_package_rejected(self):
        self.migrate()
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('BEGIN IMMEDIATE')
            conn.execute('CREATE TABLE unrelated_extension(x)')
            with self.assertRaises(ValueError):lineage.verify(conn)
            conn.rollback()
        with self.assertRaises(ValueError):transition.validate_plan(dict(migration_id='arbitrary'))

    def test_sql_guard_allows_only_the_two_exact_packages(self):
        from tests.test_recognition_runtime_enrollment_transition import EnrollmentTransitionTests as Builder
        self.migrate()
        for package in (transition.PACKAGE,upgrade.PACKAGE,'arbitrary-journal-package'):
            with self.subTest(package=package),a.connect(self.config.control,write=True) as conn:
                conn.execute('BEGIN IMMEDIATE')
                plan=Builder.plan(self,conn,migration_id=package)
                row={k:plan[k] for k in ('plan_id','installation_id','source_generation','source_binding_sha256','source_profile_sha256')}
                row.update(created_at=a.timestamp(plan['created_at_utc']),deadline_at=a.timestamp(plan['deadline_at_utc']),
                    body_json=canonical(plan),body_sha256=digest(plan),audit_sequence=a._audit_head(conn)['sequence']+1)
                insert=lambda:conn.execute('INSERT INTO '+transition.PLANS+' ('+','.join(row)+') VALUES ('+','.join('?' for _ in row)+')',tuple(row.values()))
                if package=='arbitrary-journal-package':
                    with self.assertRaisesRegex(sqlite3.IntegrityError,'transition_scope_mismatch'):insert()
                    with self.assertRaises(ValueError):transition.validate_plan(plan)
                else:
                    transition.validate_plan(plan);insert()
                conn.rollback()

    def test_arbitrary_predecessor_hash_is_not_adopted(self):
        self.migrate()
        with a.connect(self.config.control,write=True) as conn:
            conn.execute('BEGIN IMMEDIATE')
            row=conn.execute("SELECT * FROM recognition_admin_audit WHERE json_extract(body_json,'$.action')=?",(upgrade.ACTION,)).fetchone()
            body=load(row['body_json']);body['subject']['previous_schema_sha256']='a'*64
            conn.execute('DROP TRIGGER recognition_admin_audit_immutable_update')
            conn.execute('UPDATE recognition_admin_audit SET body_json=?,body_sha256=? WHERE sequence=?',
                         (canonical(body),digest(body),row['sequence']))
            with self.assertRaisesRegex(ValueError,'lineage_edge_manifest_mismatch'):lineage.verify(conn)
            conn.rollback()
