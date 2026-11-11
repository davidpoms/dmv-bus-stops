"""In-memory schema/audit DATA only. No migration or authority issuance."""

from copy import deepcopy
import inspect
import sqlite3
import unittest

from src.review.recognition import administration as admin, administration_schema as base
from src.review.recognition import approval_schema, local_readiness
from src.review.recognition import runtime_profile_schema as profile
from src.review.recognition import runtime_activation_authority_schema as authority
from src.review.recognition import runtime_execution_attempt_schema as attempts
from src.review.recognition import runtime_enrollment_transition_schema as transition
from src.review.recognition import runtime_execution_claim_schema as claims
from src.review.recognition import runtime_activation_authority_issuance as issuer
from src.review.recognition import runtime_schema_package_lineage as lineage
from src.review.recognition.rules import canonical, digest
from src.review.recognition.trust import TrustError


INSTALLATION = 'cb776ac8-9fa2-4891-b42d-80bbed2d285f'
NOW = '2026-11-09T12:00:00Z'


def normalized(objects):
    return {key: ' '.join(sql.split()) for key, sql in objects.items()}


def fixture(order='ATEL', *, mutate=None, endpoint=None):
    """Create an endpoint schema and synthetic typed audits, not a migration.

    Binding is minimal DATA for this narrow predicate; it cannot pass full runtime
    enrollment/admission. All authority/lifecycle/attempt business rows are empty.
    """
    conn = sqlite3.connect(':memory:', isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    definitions = base.definitions()
    definitions.update(approval_schema.definitions())
    definitions.update(local_readiness.definitions())
    definitions.update(profile.definitions())
    root_before = normalized(definitions)
    definitions.update(claims.definitions())
    root_after = normalized(definitions)
    packages = dict(A=(authority.MIGRATION, authority.ACTION, authority.definitions()),
                    T=(attempts.MIGRATION, attempts.ACTION, attempts.definitions()),
                    E=(transition.MIGRATION, transition.ACTION, transition.definitions()),
                    L=(lineage.MIGRATION, lineage.ACTION, lineage.successor_definitions()))
    audits = []
    def audit(key, action, migration, before, after):
        subject = dict(migration_id=migration, previous_schema_sha256=digest(before),
            installed_schema_sha256=digest(after), installation_id=INSTALLATION,
            generation=1, reason='synthetic schema lineage only')
        audits.append([key, action, subject])
    audit('root', claims.ACTION, claims.MIGRATION, root_before, root_after)
    maps = {}
    for key in order:
        migration, action, delta = packages[key]
        before = normalized(definitions)
        definitions.update(delta)
        after = normalized(definitions)
        audit(key, action, migration, before, after)
        maps[key] = (before, after)
    if mutate:
        mutate(audits)
    if endpoint:
        endpoint(definitions)
    for sql in base.definitions().values():
        conn.execute(sql)
    binding = dict(generation=1, installation_id=INSTALLATION)
    conn.execute('INSERT INTO recognition_admin_bindings VALUES(?,?,?)',
                 (1, canonical(binding), digest(binding)))
    for name, sql in definitions.items():
        if name not in base.definitions():
            conn.execute(sql)
    for key, action, subject in audits:
        admin._audit(conn, action, 'synthetic-lineage-test', NOW, subject)
    return conn, maps, audits


class SchemaPackageLineageTests(unittest.TestCase):
    def make(self, *args, **kwargs):
        conn, maps, audits = fixture(*args, **kwargs)
        self.addCleanup(conn.close)
        return conn, maps, audits

    def snapshot(self, conn):
        return '\n'.join(conn.iterdump())

    def test_all_original_orders_and_prefixes_keep_exact_historical_hashes(self):
        for order in ('A', 'AT', 'ATE'):
            with self.subTest(order=order):
                conn, maps, audits = self.make(order)
                before = self.snapshot(conn)
                edges = lineage.verify(conn)
                self.assertFalse(lineage.present(conn))
                self.assertEqual(maps['A'][1], edges['A']['after'])
                self.assertEqual(audits[1][2], authority.check_manifest_transition(conn))
                self.assertEqual(digest(maps['A'][1]), attempts.authority_manifest(conn))
                if 'T' in order:
                    self.assertEqual(maps['T'][1], edges['T']['after'])
                    self.assertEqual(audits[2][2], attempts.check_manifest_transition(conn))
                if 'E' in order:
                    self.assertEqual(digest(maps['E'][0]), transition.historical_manifest(conn))
                self.assertEqual(before, self.snapshot(conn))

    def test_all_cutover_positions_and_valid_prefixes(self):
        for order in ('AL', 'ALT', 'ALTE', 'ATL', 'ATLE', 'ATEL'):
            with self.subTest(order=order):
                conn, maps, audits = self.make(order)
                before = self.snapshot(conn)
                edges = lineage.verify(conn)
                self.assertTrue(lineage.present(conn))
                self.assertEqual(set(order), set(edges))
                for key in order:
                    self.assertEqual(maps[key][0], edges[key]['before'])
                    self.assertEqual(maps[key][1], edges[key]['after'])
                self.assertEqual(digest(maps['A'][1]), attempts.authority_manifest(conn))
                self.assertEqual(digest(maps['A'][0]), authority.historical_claim_manifest(conn))
                self.assertEqual(audits[1][2], authority.check_manifest_transition(conn))
                if 'T' in order:
                    expected = next(s for k, a, s in audits if k == 'T')
                    self.assertEqual(expected, attempts.check_manifest_transition(conn))
                if 'E' in order:
                    self.assertEqual(digest(maps['E'][0]), transition.historical_manifest(conn))
                    omitted = set(attempts.definitions())
                    self.assertEqual(digest({k:v for k,v in maps['E'][0].items() if k not in omitted}),
                        transition.historical_manifest(conn, exclude=(k for k in omitted)))
                self.assertEqual(digest(normalized(dict(base._control_objects(conn)))), claims.manifest(conn))
                self.assertEqual(before, self.snapshot(conn))
                # R11-E recognizes the exact schema, not a runtime credential.
                base.check_control(conn)
                from src.review.recognition.runtime_challenges import _deployment_binding
                with self.assertRaisesRegex(ValueError, 'installation_history_integrity_failure'):
                    _deployment_binding(conn)

    def test_invalid_predecessor_successor_and_self_assertion(self):
        for key in ('A', 'T', 'E', 'L', 'root'):
            for field in ('previous_schema_sha256', 'installed_schema_sha256'):
                with self.subTest(edge=key, field=field):
                    def tamper(audits):
                        next(s for k, a, s in audits if k == key)[field] = 'f'*64
                    conn, _, _ = self.make('ALTE', mutate=tamper)
                    with self.assertRaises(TrustError):
                        lineage.verify(conn)

    def test_missing_cutover_audit_cannot_be_manufactured_by_package_metadata(self):
        def tamper(audits):
            audits[:] = [r for r in audits if r[0] != 'L']
        conn, _, _ = self.make('ALTE', mutate=tamper)
        with self.assertRaises(TrustError):
            lineage.verify(conn)

    def test_missing_and_duplicate_every_edge(self):
        for key in ('A', 'T', 'E', 'L', 'root'):
            for duplicate in (False, True):
                with self.subTest(edge=key, duplicate=duplicate):
                    def tamper(audits):
                        if duplicate:
                            audits.append(deepcopy(next(r for r in audits if r[0] == key)))
                        else:
                            audits[:] = [r for r in audits if r[0] != key]
                    conn, _, _ = self.make('ATEL', mutate=tamper)
                    with self.assertRaises(TrustError):
                        lineage.verify(conn)

    def test_malformed_wrong_identity_scope_and_action(self):
        changes = (('migration_id', 'unknown-v3'), ('generation', True),
                   ('installation_id', 'c02eb31f-6a4d-41b4-8ea4-82fc6e745712'),
                   ('generation', 2), ('extra', None), ('previous_schema_sha256', 'F'*64))
        for field, value in changes:
            with self.subTest(field=field, value=value):
                def tamper(audits):
                    next(s for k, a, s in audits if k == 'L')[field] = value
                conn, _, _ = self.make('ALTE', mutate=tamper)
                with self.assertRaises(TrustError):
                    lineage.verify(conn)
        def wrong_action(audits):
            next(r for r in audits if r[0] == 'L')[1] = 'unrecognized_upgrade'
        conn, _, _ = self.make('ALTE', mutate=wrong_action)
        self.assertTrue(lineage.present(conn))
        with self.assertRaises(TrustError):
            lineage.verify(conn)

    def test_skipped_or_reordered_required_transition(self):
        for order in ('LA', 'TA', 'AEL', 'ATLEL', 'ALET'):
            with self.subTest(order=order):
                conn, _, _ = self.make(order)
                with self.assertRaises(TrustError):
                    lineage.verify(conn)

    def test_unexpected_ddl_and_unknown_schema_version(self):
        conn, _, _ = self.make('ALTE')
        conn.execute('CREATE TABLE unknown_schema_version_v3 (id INTEGER)')
        with self.assertRaisesRegex(TrustError, 'current_schema'):
            lineage.verify(conn)
        conn, _, _ = self.make('ALTE')
        conn.execute('DROP TRIGGER '+authority.AUTHORITIES+'_scope_guard')
        with self.assertRaisesRegex(TrustError, 'current_schema'):
            lineage.verify(conn)

    def test_original_schema_with_cutover_audit_is_ambiguous_and_rejected(self):
        def old_schema(objects):
            objects.update(authority.definitions())
        conn, _, _ = self.make('ATEL', endpoint=old_schema)
        with self.assertRaisesRegex(TrustError, 'current_schema'):
            lineage.verify(conn)

    def test_audit_integrity_and_isolation_still_enforced(self):
        conn, _, _ = self.make('ALTE')
        conn.execute('CREATE TEMP TABLE forbidden (id INTEGER)')
        conn.execute('DROP TABLE forbidden')
        with self.assertRaisesRegex(TrustError, 'isolated_admin_control_required'):
            lineage.verify(conn)
        conn, _, _ = self.make('ALTE')
        # Corrupt DATA in an explicitly unprotected test clone, never repair it.
        conn.execute('DROP TRIGGER recognition_admin_audit_immutable_update')
        conn.execute("UPDATE recognition_admin_audit SET body_sha256=? WHERE sequence=2", ('f'*64,))
        with self.assertRaisesRegex(ValueError, 'audit_integrity'):
            lineage.verify(conn)

    def test_no_mutation_or_authority_and_current_default_remains_v1(self):
        conn, _, _ = self.make('ALTE')
        conn.execute('PRAGMA query_only=ON')
        changes = conn.total_changes
        lineage.verify(conn)
        self.assertEqual(changes, conn.total_changes)
        for table in (authority.AUTHORITIES, authority.LIFECYCLE, attempts.ATTEMPTS,
                      attempts.HISTORY, claims.CLAIMS):
            self.assertEqual(0, conn.execute('SELECT count(*) FROM '+table).fetchone()[0])
        self.assertIsNone(conn.execute(
            "SELECT 1 FROM sqlite_master WHERE name='recognition_execution_claims'").fetchone())
        self.assertEqual('recognition-runtime-authority-lifetime-120s-v1', authority.LIFETIME)
        self.assertIn('a.timestamp(issued)+120', inspect.getsource(issuer._body))
        self.assertIn('lifetime_policy=storage.LIFETIME', inspect.getsource(issuer._body))
        with self.assertRaisesRegex(TrustError, 'unknown_projection'):
            lineage.manifest_at(conn, 'A', exclude=('recognition_admin_audit',))

    def test_exact_successor_delta_and_guard_restoration_metadata(self):
        old, new = authority.definitions(), lineage.successor_definitions()
        self.assertEqual(set(old), set(new))
        self.assertEqual({authority.AUTHORITIES, authority.AUTHORITIES+'_scope_guard'},
                         {k for k in old if old[k] != new[k]})
        # Current installed definitions have NOT been promoted to this metadata.
        self.assertIn('expires_at<=issued_at+120)', old[authority.AUTHORITIES])
        self.assertIn('COALESCE(', new[authority.AUTHORITIES])
        self.assertIn(lineage.MIGRATION, new[authority.AUTHORITIES+'_scope_guard'])

    def test_validation_is_fresh_and_transient_unknown_schema_rolls_back(self):
        conn, _, _ = self.make('ATLE')
        before = self.snapshot(conn)
        lineage.verify(conn)
        conn.execute('BEGIN IMMEDIATE')
        conn.execute('CREATE TABLE unexplained_intermediate_state (id INTEGER)')
        with self.assertRaisesRegex(TrustError, 'current_schema'):
            lineage.verify(conn)
        conn.rollback()
        lineage.verify(conn)
        self.assertEqual(before, self.snapshot(conn))
        statements = []
        conn.set_trace_callback(statements.append)
        lineage.verify(conn)
        conn.set_trace_callback(None)
        self.assertTrue(statements)
        self.assertTrue(all(s.lstrip().upper().startswith(('SELECT', 'PRAGMA')) for s in statements))

    def test_unknown_intervening_schema_audit_and_false_root_identity_reject(self):
        for root_identity in (False, True):
            with self.subTest(root_identity=root_identity):
                def tamper(audits):
                    extra = deepcopy(audits[0])
                    extra[1] = 'unreviewed_schema_installation'
                    if not root_identity:
                        extra[2]['migration_id'] = 'unreviewed-schema-v3'
                    audits.insert(2, extra)
                conn, _, _ = self.make('ALTE', mutate=tamper)
                with self.assertRaises(TrustError):
                    lineage.verify(conn)


if __name__ == '__main__':
    unittest.main()
